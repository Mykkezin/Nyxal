# Linha de base de segurança HTTP da Nyxal

## Objetivo e limite

Esta etapa reduz a superfície de exposição da API atual. Ela não transforma a Nyxal em um sistema operacional formalmente verificado nem substitui uma auditoria completa do runtime, dos conectores, das dependências e do host.

## Proteções aplicadas

- **Bind local obrigatório:** `nyxal_web_api.py` recusa iniciar quando `NYXAL_API_HOST` não é `localhost` ou um endereço de loopback. O servidor da biblioteca padrão fala HTTP e não deve ser exposto diretamente à Internet.
- **CORS por lista de permissão:** a API não emite `Access-Control-Allow-Origin: *`. Por padrão, aceita somente as origens locais da própria porta (`localhost`, `127.0.0.1` e `[::1]`). Origens adicionais precisam ser explícitas.
- **Rejeição de origem web não autorizada:** pedidos a `/api/*` que tragam um cabeçalho `Origin` não permitido são rejeitados, inclusive preflight `OPTIONS`.
- **Autorização de rotas para clientes não locais:** os endpoints `/api/*` passam pela verificação local/Bearer antes do processamento. Rotas que já exigem token continuam exigindo-o também em loopback.
- **Cabeçalhos defensivos:** respostas JSON e de bytes incluem `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` e `Cache-Control: no-store`. A versão do servidor deixa de anunciar a versão detalhada do Python.
- **Hardening systemd:** as unidades da API e do residente usam `ProtectSystem=full`, proteção de tunables/módulos/cgroups do kernel, restrições SUID/SGID, `LockPersonality`, `RestrictRealtime`, `SystemCallArchitectures=native`, conjunto vazio de capacidades Linux, famílias de endereço limitadas a Unix/IPv4/IPv6, `ProtectClock` e `ProtectKernelLogs`. Não foi ativado `PrivateDevices` nem `ProtectHome` para evitar interromper acesso a hardware, modelos e estado do usuário sem validação no host real.
- **Permissões de segredos locais:** o instalador aplica modo `0700` ao diretório `~/.config/nyxal`, modo `0600` ao arquivo `nyxal.env` existente e falha se esse caminho for um link simbólico ou outro tipo de objeto que não seja arquivo regular.
- **Resistência inicial à exaustão de conexões:** a API limita o processamento a oito requisições HTTP simultâneas, define timeout de socket de 30 segundos e devolve `503 Service Unavailable` com `Retry-After` quando os slots estão cheios. Isso limita a criação ilimitada de threads, mas não substitui rate limiting no proxy nem garante resistência a todo DoS.
- **Testes reproduzíveis:** `teste_seguranca_api.py` valida as políticas de origem, testa o `NyxalAPIHandler` isolado, simula saturação do servidor HTTP e confirma a presença das proteções no código sem carregar modelos externos.

## Mapeamento dos seis princípios arquiteturais

| Princípio-alvo | Situação verificada nesta etapa | Próxima camada necessária |
|---|---|---|
| Microkernel e verificação formal | A Nyxal é atualmente uma aplicação de espaço de usuário sobre Linux; não há kernel próprio verificado formalmente. | Definir especificação mínima do kernel e modelo de ameaças; avaliar uma base como seL4 antes de qualquer promessa de prova. |
| Segurança de memória | A pilha atual é majoritariamente Python e depende de bibliotecas nativas; isso não equivale a segurança de memória garantida. | Manter componentes privilegiados mínimos e implementar novos componentes críticos em linguagem com segurança de memória; verificar compatibilidade de CPU antes de depender de tagging. |
| Micro-VMs e isolamento absoluto | As unidades centrais da API e do residente agora têm hardening systemd básico; processos ainda compartilham o kernel do Linux e não rodam em micro-VMs por aplicação. | Validar as novas restrições no host real e reforçar o sandbox incrementalmente; só depois avaliar micro-VMs para componentes que executam código não confiável. |
| Segurança baseada em capacidades | O gateway de atuação existente restringe ações registradas e exige autorização explícita no nível da aplicação. Isso não é uma capacidade inforjável imposta pelo kernel. | Separar identidades/contas de serviço, limitar recursos acessíveis por componente e criar concessões específicas e revogáveis para cada operação. |
| Armazenamento imutável e proteção de chaves | A aplicação ainda mantém estado mutável em arquivos locais. Esta etapa não adiciona imagem-base imutável, TPM ou criptografia pós-quântica. | Separar imagem de sistema e dados graváveis; assinar artefatos, usar atualizações transacionais e definir um modelo de chaves com suporte de hardware real. |
| Zero Trust de rede | A API deixa de aceitar bind público direto e não aceita CORS wildcard. Não existe ainda uma política global de firewall default-drop nem identidade criptográfica por processo. | Expor por VPN ou proxy HTTPS autenticado, restringir egress por serviço e definir identidades/autorizações para cada integração. |

A ordem importa: primeiro fechar a superfície de exposição e medir o comportamento; depois endurecer cada serviço sem quebrar observabilidade, inferência ou integrações; por fim avaliar substituições arquiteturais maiores com critérios verificáveis.

## Configuração CORS

Use uma lista de origens exatas separadas por vírgula, sem caminhos ou barras finais:

```bash
NYXAL_API_CORS_ORIGINS="https://nyxal.example,https://painel.nyxal.example"
```

A variável legada `NYXAL_API_CORS_ORIGIN` continua aceita para uma única origem, mas `*` e `null` são rejeitados deliberadamente. Remova qualquer configuração antiga com wildcard antes de reiniciar a API.

## Fronteira com proxy reverso

O endereço remoto do navegador não pode ser inferido pelo socket do backend quando existe um proxy: a conexão encaminhada chega de loopback. Por isso, se uma solicitação `/api/*` contiver um cabeçalho `Origin` não-loopback permitido pela allowlist, a API também exige Bearer mesmo que o socket tenha vindo de loopback.

O desenho remoto recomendado é:

1. o navegador autentica-se no proxy/gateway HTTPS;
2. o gateway autoriza a sessão e aplica a política de acesso;
3. somente depois, o gateway injeta o Bearer interno no pedido à API local;
4. o segredo da API permanece server-side, nunca no JavaScript ou no armazenamento do navegador.

Não configure o proxy para injetar o Bearer em tráfego anônimo. A allowlist CORS, sozinha, não concede acesso. Clientes sem `Origin` continuam sujeitos à autenticação na borda se passarem pelo proxy; o backend não consegue distinguir um proxy confiável de outro processo local apenas olhando o endereço loopback.

## Acesso remoto seguro

Mantenha a API ligada em loopback. Para acesso remoto, exponha somente uma **VPN** ou um **proxy reverso HTTPS com autenticação e controle de acesso próprios**. O proxy deve ser tratado como fronteira de segurança: as conexões encaminhadas ao servidor local aparecem como loopback e, portanto, o proxy precisa autenticar os usuários antes de encaminhar pedidos. Não encaminhe a porta HTTP da Nyxal diretamente à Internet.

`NYXAL_API_TOKEN` continua necessário para endpoints que já exigem Bearer. O instalador do systemd restringe o diretório de configuração a `0700` e o arquivo `nyxal.env` a `0600`; links simbólicos e caminhos não regulares são recusados. CORS não é autenticação e não substitui uma camada de acesso remoto.

## Classificação de rotas para exposição remota

O prefixo `/api/public/` indica uma rota sem token no fluxo local legado; **não significa que a rota seja segura para publicação irrestrita na Internet**. O servidor continua vinculado a loopback, mas um proxy decide quais caminhos ficam externamente acessíveis.

| Classe | Rotas ou famílias | Política recomendada para gateway remoto |
|---|---|---|
| Saúde mínima | `GET /health` | Pode ser exposta somente se necessário para monitoramento; não retorna detalhes internos. |
| Estado para interface | `GET /api/public/status` | Expor apenas atrás de autenticação do gateway; retorna presença, habitat e outros dados operacionais. |
| Diagnóstico interno | `/api/public/nyxos/contexto`, `/api/public/residencia`, `/api/public/recursos`, `/api/public/operacional`, `/api/public/gateway`, `/api/public/presenca`, `/api/public/ae5`, `/api/public/dataset`, `/api/public/delta` | Não publicar diretamente; contêm estado interno, detalhes de serviços, contexto de governança, dataset ou eventos. |
| Dados pessoais e telemetria | `/api/integracoes/google/*`, `/api/integracoes/gmail/*`, `/api/agent/contexto`, `/api/agent/status` | Acesso autenticado e restrito; podem revelar e-mails, contatos, agenda, processos, serviços, modelos ou integrações. |
| Controle e efeitos | `/api/vps/*`, `/api/agent/image`, `/api/amd-cloud/check`, `/api/ae5/*`, `POST /api/chat`, `POST /api/agent/chat` | Somente atrás de autenticação do gateway e autorização de aplicação; não publicar para visitantes anônimos. |
| Consumo de recursos | `POST /api/stt`, `POST /api/tts` | Autenticar, limitar taxa e monitorar consumo; os limites de payload não evitam todos os ataques de esgotamento. |

Para uma instalação remota, aplique autenticação no **gateway inteiro por padrão** e libere somente as rotas necessárias. Não dependa apenas dos nomes de rota, CORS ou do token injetado por proxy. O gateway deve verificar a identidade da sessão antes de encaminhar cada requisição; a API ainda não implementa papéis multiusuário nem capacidades de acesso por recurso.

## Riscos ainda abertos

1. O servidor HTTP é baseado em `http.server`, não em um servidor de produção com TLS, rate limiting, gestão avançada de conexões e proteção completa contra DoS. O limite local de oito threads e o timeout de socket são defesas iniciais.
2. O acesso vindo de processos locais ainda é confiado como loopback; origens do navegador mitigam pedidos cross-site, mas não defendem contra malware/processos locais.
3. Os endpoints de diagnóstico marcados como públicos podem revelar informação operacional a qualquer cliente local. A publicação externa deve aplicar autenticação na borda e uma allowlist de rotas.
4. Ainda é necessária uma auditoria específica dos limites de payload, rate limiting, tratamento de erros, logs, sessão, tokens, OAuth/Gmail, gateway de atuação, provisionamento VPS, dependências e permissões systemd.
5. Não há ainda microkernel seL4, prova formal do kernel NyxOS, micro-VM por aplicação, capacidades criptográficas por recurso, sistema base imutável, TPM que mantenha chaves fora da RAM ou criptografia pós-quântica integrada. Esses itens são metas arquiteturais futuras, não controles presentes.

## Próxima sequência recomendada

1. Auditar rotas e classificar publicamente cada endpoint como público, local, autenticado ou privilegiado.
2. Adicionar testes HTTP end-to-end para CORS, autenticação, payloads inválidos e rejeição de bind externo.
3. Validar no host real o perfil systemd ampliado nesta etapa; avaliar `ProtectHome`, `PrivateDevices` e `ReadWritePaths` separadamente, somente após testes de compatibilidade com modelos, dispositivos e arquivos de estado.
4. Separar API conversacional de rotas privilegiadas (VPS, Gmail e atuação no host), com autorização explícita por operação e logs de auditoria sem segredos.
5. Definir uma trilha de verificação formal e proteção em hardware apenas quando houver plataforma/arquitetura compatível e critérios de prova verificáveis.
