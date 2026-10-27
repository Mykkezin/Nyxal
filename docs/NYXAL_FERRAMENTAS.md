# Ferramentas da Nyxal: function calling, MCP e governança

## Arquitetura

O Core reaproveita o registro de capacidades existente em `nixal_capacidades.py`. O diálogo local Qwen (`nixal_dialogo_qwen.py`) anuncia somente ferramentas de uma lista permitida, valida as chamadas e devolve os resultados ao modelo. O modelo não recebe um terminal, não executa código arbitrário e não pode criar permissões citando nomes de ferramentas.

`nixal_tool_use.py` implementa adaptadores. `nyxal_mcp_tools.py` é um servidor MCP opcional e separado da API principal; ele oferece um conjunto de ferramentas em modo de leitura, mas não precisa estar iniciado para o function calling do diálogo principal funcionar.

A identidade e as regras operacionais permanecem definidas em `deploy/agent/NYXAL_SOUL.md`. Os resultados de ferramentas são dados observados e não instruções privilegiadas.

## Ferramentas do diálogo

Por padrão, o modelo pode usar consultas de baixo impacto:

| Ferramenta | Finalidade | Política |
|---|---|---|
| `obter_hora` | Hora local do sistema | Leitura |
| `pesquisar_web` | Pesquisar e devolver títulos/URLs | Leitura; fonte externa não confiável |
| `consultar_metar_taf` | METAR/TAF pela AviationWeather.gov Data API | Leitura; apoio aeronáutico |
| `consultar_notam_aisweb` | Consultar NOTAMs pela API AISWEB/DECEA | Leitura; exige credenciais da API |
| `consultar_cartas_aisweb` | Pesquisar metadados/links de cartas oficiais | Leitura; exige credenciais da API |
| `executar_diagnostico` | Diagnósticos fixos de Git, serviços e recursos | Leitura; sem comandos arbitrários |

Leituras de arquivos pessoais, Gmail, Calendar, Home Assistant e notas persistidas exigem opt-in independente. Escrita de nota, criação de lembrete e abertura de aplicativos têm outro opt-in e exigem solicitação explícita na mensagem atual. Capacidades que exigem uma confirmação separada permanecem bloqueadas até existir um fluxo de confirmação apropriado.

### Coordenação local por papéis especializados

A conversa principal possui um modo opt-in de coordenação em até duas passagens curtas: **Arquiteto** propõe objetivo, passos e critérios de validação; **Revisor de Segurança e Qualidade** examina riscos e testes. O diálogo Qwen normal faz a síntese final e, se necessário, solicita ferramentas pelo mesmo catálogo governado.

Para ativar, peça explicitamente, por exemplo: `Use modo especialistas para planejar esta mudança` ou `Faça uma revisão multiagente desta arquitetura`.

- O modo não é ativado em perguntas comuns; não aumenta a latência nem o uso de tokens quando não é solicitado.
- As duas passagens extras só são executadas quando o provedor configurado é local (`ollama`, `local` ou `nyxal`). Se o provedor não for local, o diálogo segue normalmente e informa que a coordenação local não foi ativada.
- É uma coordenação de papéis com o mesmo modelo local, não um conjunto de modelos independentes nem um CrewAI paralelo.
- As passagens dos especialistas não recebem ferramentas; se tentarem emitir chamadas de ferramenta, a passagem é descartada e a conversa principal continua.
- Cada passagem tem entrada limitada a 8.000 caracteres e saída limitada a 1.500 caracteres. São no máximo duas passagens extra por pedido.
- Os resumos são tratados como rascunhos não confiáveis. A resposta final usa o ciclo atual de function calling, limites, opt-ins e autorização; a coordenação não concede permissões e não executa ações por si só.
- Falhas em qualquer passagem são fail-open: a resposta normal continua, sem bloquear o diálogo.
- A resposta estruturada do núcleo expõe apenas um resumo allowlisted do modo (`estado`, perfis, quantidade de passagens e flags de execução das passagens). Os resumos completos, prompts e textos internos não são retornados pela API.

### Opt-ins do function calling

- Para disponibilizar arquivos pessoais, Gmail, agenda, Home Assistant e notas: `NYXAL_ENABLE_PRIVATE_READ_TOOLS=1`.
- Para anunciar salvar nota, criar lembrete e abrir aplicativos permitidos: `NYXAL_ENABLE_MUTABLE_TOOLS=1`.
- Os dois opt-ins são independentes. Um não habilita o outro.
- `NYXAL_FUNCTION_CALLING_ENABLED=false` desabilita o function calling no diálogo local.

Configure variáveis no ambiente do serviço que executa a Nyxal; não as grave no repositório. A configuração só é lida quando o registro compartilhado é criado, então reinicie o serviço local depois de alterar variáveis de ambiente.

## NOTAMs e cartas aeronáuticas (AISWEB/DECEA)

Os adaptadores `consultar_notam_aisweb` e `consultar_cartas_aisweb` estão registrados como somente leitura no diálogo Qwen e disponíveis também no MCP opcional. Eles consultam a API oficial do AISWEB/DECEA, que exige credenciais individuais. A página oficial de acesso à API é:

- [API AISWEB para desenvolvedores — DECEA](https://ais.decea.mil.br/?i=publicacoes&p=api)
- [Portal AISWEB de NOTAMs](https://ais.decea.mil.br/?i=notam)
- [API AISWEB — documentação de parâmetros](https://documenter.getpostman.com/view/7201070/SzKQyg3H)

Peça as credenciais ao DECEA e defina estas variáveis **no ambiente local do processo**:

```bash
export NYXAL_AISWEB_API_KEY='credencial-fornecida-pelo-DECEA'
export NYXAL_AISWEB_API_PASS='senha-de-api-fornecida-pelo-DECEA'
```

Os valores acima são exemplos, não credenciais reais. Nunca os adicione ao Git, frontend, logs, prompt ou arquivo de configuração versionado. Sem as duas variáveis, as ferramentas retornam `configuracao_pendente` e não tentam consultar a API.

Exemplos de consultas:

- NOTAM de um ou mais aeródromos: `consultar_notam_aisweb(localidades="SBSP,SBGR")`.
- NOTAM filtrado por FIR: `consultar_notam_aisweb(localidades="SBSP", fir="SBBS")` (use o código FIR aplicável à consulta).
- Buscar cartas ostensivas de procedimento de um aeródromo: `consultar_cartas_aisweb(icao="SBSP", especie="IFR", tipo="IAC")`.
- Buscar por nome dentro do tipo selecionado: `consultar_cartas_aisweb(icao="SBSP", especie="IFR", tipo="IAC", nome="ILS")`.
- Consultar um ciclo específico: `consultar_cartas_aisweb(icao="SBSP", especie="IFR", tipo="IAC", dt="last_amdt")` ou usar uma data válida em `AAAA-MM-DD`.

As consultas são limitadas por tamanho, volume e tipos de parâmetros; a API só é chamada sobre HTTPS, redirecionamentos são recusados e respostas XML com declarações DOCTYPE/ENTITY são bloqueadas. As ferramentas retornam metadados/dados estruturados e não executam nem seguem instruções contidas no conteúdo externo.

**Limite operacional importante:** a presença do adaptador no código não prova que a conta esteja configurada ou que uma consulta real funcionou. Sem credenciais válidas, rede disponível e autorização concedida pelo DECEA, o estado será pendente ou a chamada falhará. Confirme os resultados diretamente em fontes oficiais, a publicação e sua validade antes de qualquer uso de voo. Uma resposta da Nyxal não substitui briefing oficial pré-voo, NOTAMs vigentes, AIP, cartas em vigor, ATIS, instrução ou julgamento do piloto.

O adaptador de cartas retorna metadados/links de cartas ostensivas e não baixa, interpreta ou valida automaticamente a carta para uso operacional.

## METAR/TAF

A consulta METAR/TAF usa a API pública [AviationWeather.gov Data API](https://aviationweather.gov/data/api/) e exige código ICAO com quatro caracteres, por exemplo `SBSP` ou `SBGR`. O resultado indica a fonte e inclui aviso operacional. Não substitui o briefing e a avaliação do piloto.

## Outras integrações

### Google Workspace

A implementação reaproveita `IntegracaoGmailNixOS`. Gmail e Calendar permanecem em modo somente leitura; os escopos de Google Workspace já usados pelo projeto não são ampliados por esta PR. A presença de um token/arquivo não garante que a conta esteja acessível: consulte o status e trate erros de autenticação de forma explícita.

Não existe envio de e-mail, alteração de eventos, exclusão/arquivamento de mensagens, gravação de contatos ou download de arquivos do Drive nesta integração.

### Home Assistant

Para consulta local, configure no ambiente do processo:

- `NYXAL_HOME_ASSISTANT_URL`: URL-base da instância Home Assistant.
- `NYXAL_HOME_ASSISTANT_TOKEN`: token de acesso de longa duração.

Nunca grave o token no Git, frontend, mensagens ou logs. O adaptador só faz GET, recusa redirecionamentos e devolve uma lista limitada de atributos. Acionar interruptores, fechaduras, alarmes ou qualquer dispositivo físico não está habilitado.

### Notas e lembretes

A persistência reutilizável está em `~/.local/share/nyxal/notas_lembretes.json` (sobrescrita de diretório por `NYXAL_USER_DATA_DIR`). O diretório usa permissão `0700`; o arquivo usa `0600`; gravação é atômica. JSON corrompido não é sobrescrito silenciosamente. O serviço de notificações é iniciado junto da API e depende de sessão desktop/D-Bus e de `notify-send`; portanto, notificações de desktop não são garantidas quando esses componentes não estão disponíveis.

### Servidor MCP opcional

Instale a dependência na virtualenv da Nyxal (o diálogo Qwen continua funcionando sem o MCP):

```bash
cd ~/Nyxal
./.venv/bin/python -m pip install -r deploy/agent/requirements-mcp.txt
```

**HTTP local ligado ao ciclo de vida da API (opcional e desligado por padrão):** defina estas variáveis no ambiente do serviço da Nyxal:

```bash
export NYXAL_MCP_HTTP_ENABLED=1
export NYXAL_MCP_HTTP_TOKEN="$(./.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
# O padrão é 127.0.0.1:8765
export NYXAL_MCP_HTTP_HOST=127.0.0.1
export NYXAL_MCP_HTTP_PORT=8765
```

O token precisa ter 32–256 caracteres ASCII seguros. Não grave o token no Git, logs, argumentos de processo ou frontend. O endpoint é `http://127.0.0.1:8765/mcp`; clientes devem enviar `Authorization: Bearer <token>`. Somente IPs literais de loopback são aceitos. O SDK mantém a proteção de Host/DNS rebinding, requisições sem bearer token são rejeitadas, a inicialização da API falha se o MCP explicitamente habilitado não confirmar readiness e o processo filho é encerrado junto da API.

**Stdio permanece disponível** para clientes MCP que iniciam o servidor como subprocesso:

```bash
./.venv/bin/python teste_mcp_stdio.py
```

No cliente stdio, configure `command` com o caminho absoluto de `~/Nyxal/.venv/bin/python` e `args` com o caminho absoluto de `~/Nyxal/nyxal_mcp_tools.py`. Sem `NYXAL_MCP_TRANSPORT`, o servidor usa stdio.

O MCP expõe consultas web, METAR/TAF, NOTAMs, cartas, Home Assistant somente leitura, busca/leitura limitada de arquivos, Gmail/Calendar, notas e diagnósticos. Leituras de arquivos pessoais, sensores, Gmail/Calendar e notas retornam bloqueio até que `NYXAL_ENABLE_PRIVATE_READ_TOOLS=1` esteja definido no ambiente do processo MCP. O servidor continua sem ações mutáveis.

Para executar os testes locais da branch:

```bash
./.venv/bin/python -m unittest -v teste_nyxal_function_calling teste_nyxal_tool_use
```

O workflow `Nyxal MCP stdio validation` também testa o protocolo stdio e as políticas das ferramentas em um runner hospedado isolado; ele não exige credenciais pessoais nem acesso a serviços locais.

## Segurança e limites conhecidos

- Conteúdo de páginas web, arquivos, mensagens, eventos, NOTAMs e cartas é dado externo não confiável, nunca instrução privilegiada.
- Os argumentos são validados no registro de capacidades; o número de chamadas, tamanho de resposta e conjunto de ferramentas são limitados.
- Não existe execução de shell/código arbitrário, envio ou alteração de e-mails/eventos nem atuação física via Home Assistant.
- Não afirmar que uma ferramenta funcionou sem um resultado de execução real; distinguir consulta concluída, ausência de resultados, erro de serviço e configuração pendente.
- Testes automatizados mockados demonstram validação de contrato, não provam que contas externas, credenciais locais, notificações do desktop ou a API em execução estejam operacionais.
