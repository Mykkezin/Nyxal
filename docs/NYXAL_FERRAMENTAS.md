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
- Buscar cartas ostensivas de um aeródromo: `consultar_cartas_aisweb(icao="SBSP")`.
- Buscar um tipo de carta: `consultar_cartas_aisweb(icao="SBSP", especie="IFR", tipo="IAC")`.
- Consultar o ciclo vigente ou um ciclo especificado: `dt="last_amdt"` ou `dt="AAAA-MM-DD"`.

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

No computador da Nyxal, após obter a branch:

```bash
cd ~/Nyxal
./.venv/bin/python nyxal_mcp_tools.py
```

O processo usa transporte stdio do `MCPServer`. No cliente MCP, configure `command` com o caminho absoluto de `~/Nyxal/.venv/bin/python` e `args` com o caminho absoluto de `~/Nyxal/nyxal_mcp_tools.py`. Não coloque credenciais no arquivo de configuração do cliente.

O MCP expõe consultas web, METAR/TAF, NOTAMs, cartas, Home Assistant somente leitura, busca/leitura limitada de arquivos, Gmail/Calendar, notas e diagnósticos. O servidor não expõe ações para escrita de notas, criação de lembretes ou abertura de aplicativos.

Para executar os testes locais da branch:

```bash
./.venv/bin/python -m unittest -v teste_nyxal_function_calling teste_nyxal_tool_use
```

## Segurança e limites conhecidos

- Conteúdo de páginas web, arquivos, mensagens, eventos, NOTAMs e cartas é dado externo não confiável, nunca instrução privilegiada.
- Os argumentos são validados no registro de capacidades; o número de chamadas, tamanho de resposta e conjunto de ferramentas são limitados.
- Não existe execução de shell/código arbitrário, envio ou alteração de e-mails/eventos nem atuação física via Home Assistant.
- Não afirmar que uma ferramenta funcionou sem um resultado de execução real; distinguir consulta concluída, ausência de resultados, erro de serviço e configuração pendente.
- Testes automatizados mockados demonstram validação de contrato, não provam que contas externas, credenciais locais, notificações do desktop ou a API em execução estejam operacionais.
