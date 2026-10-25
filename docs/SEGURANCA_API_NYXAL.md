# Linha de base de segurança HTTP da Nyxal

## Objetivo e limite

Esta etapa reduz a superfície de exposição da API atual. Ela não transforma a Nyxal em um sistema operacional formalmente verificado nem substitui uma auditoria completa do runtime, dos conectores, das dependências e do host.

## Proteções aplicadas

- **Bind local obrigatório:** `nyxal_web_api.py` recusa iniciar quando `NYXAL_API_HOST` não é `localhost` ou um endereço de loopback. O servidor da biblioteca padrão fala HTTP e não deve ser exposto diretamente à Internet.
- **CORS por lista de permissão:** a API não emite `Access-Control-Allow-Origin: *`. Por padrão, aceita somente as origens locais da própria porta (`localhost`, `127.0.0.1` e `[::1]`). Origens adicionais precisam ser explícitas.
- **Rejeição de origem web não autorizada:** pedidos a `/api/*` que tragam um cabeçalho `Origin` não permitido são rejeitados, inclusive preflight `OPTIONS`.
- **Autenticação de origem remota:** uma origem web não-loopback precisa apresentar Bearer mesmo quando o socket do backend é loopback; isso evita confiar apenas no endereço visto atrás de um proxy.
- **Autorização de rotas para clientes não locais:** os endpoints `/api/*` passam pela verificação local/Bearer antes do processamento. Rotas que já exigem token continuam exigindo-o também em loopback.
- **Cabeçalhos defensivos:** respostas JSON e de bytes incluem `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` e `Cache-Control: no-store`. A versão do servidor deixa de anunciar a versão detalhada do Python.
- **Hardening systemd inicial:** as unidades da API e do residente passam a usar `ProtectSystem=full`, proteção de tunables/módulos/cgroups do kernel, restrição SUID/SGID, `LockPersonality`, `RestrictRealtime` e `SystemCallArchitectures=native`. Não foi ativado `PrivateDevices` nem `ProtectHome` para evitar interromper acesso a dados de hardware, modelos e estado do usuário sem validação no host real.
- **Testes reproduzíveis:** `teste_seguranca_api.py` valida loopback e a política de origens sem precisar subir serviços externos.

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

## Acesso remoto seguro

Mantenha a API ligada em loopback. Para acesso remoto, exponha somente uma **VPN** ou um **proxy reverso HTTPS com autenticação e controle de acesso próprios**. O proxy deve ser tratado como fronteira de segurança: as conexões encaminhadas ao servidor local aparecem como loopback e, portanto, o proxy precisa autenticar os usuários antes de encaminhar pedidos. Não encaminhe a porta HTTP da Nyxal diretamente à Internet.

`NYXAL_API_TOKEN` continua necessário para endpoints que já exigem Bearer. CORS não é autenticação e não substitui uma camada de acesso remoto.


## Modo de reverse proxy autenticado

A API continua vinculada a loopback. Se for publicada atrás de um proxy reverso, habilite explicitamente `NYXAL_API_BEHIND_PROXY=1` e configure `NYXAL_API_TOKEN` no serviço. A inicialização é recusada quando o modo proxy está habilitado sem token.

Nesse modo, toda requisição GET exceto `/health` e toda requisição POST exige `Authorization: Bearer <token>`, incluindo endpoints ainda não implementados e assets do shell. O proxy deve autenticar o usuário externo e injetar o Bearer do serviço somente no tráfego upstream, após a autenticação. Nunca entregue o token ao JavaScript/browser.

Em acesso local direto, cabeçalhos `Forwarded`, `X-Forwarded-For` e `X-Real-IP` desativam o atalho de confiança no loopback. A API também valida `Host` e a porta do listener para reduzir o risco de DNS rebinding. CORS não é autenticação e não substitui o modo proxy/token.

## Endurecimento incremental de serviços e credenciais

As unidades systemd da API e do residente usam, adicionalmente, um conjunto vazio de capacidades Linux (`CapabilityBoundingSet=`), limitam famílias de endereço a Unix/IPv4/IPv6 e ativam `ProtectClock=true` e `ProtectKernelLogs=true`. Isso reduz operações possíveis a partir desses processos, mas não os isola em um kernel separado e precisa ser testado no host onde a Nyxal roda.

O instalador da residência rejeita links simbólicos nos pais relevantes de `~/.config` (`.config`, `.config/systemd`, `systemd/user`, `autostart` e `nyxal`) antes e depois da criação dos diretórios; também rejeita um `nyxal.env` simbólico e objetos que não sejam arquivos regulares. As permissões ficam em `0700` no diretório de credenciais e `0600` no arquivo existente. Essa verificação reduz o risco de o instalador ajustar permissões, instalar unidades ou remover um autostart por um caminho redirecionado; ela não substitui a gestão de segredos do sistema operacional.

A API também limita a oito conexões em processamento simultâneo e aplica timeout de socket de 30 segundos. Ao atingir o limite, responde `503 Service Unavailable` com `Retry-After: 1`. Isso não substitui rate limiting, autenticação na borda nem proteção contra todo tipo de DoS.
Antes do roteamento, rejeita `Transfer-Encoding` e cabeçalhos `Content-Length` duplicados, não ASCII ou não numéricos. O servidor não implementa corpos chunked; recusar enquadramento ambíguo reduz diferenças de interpretação entre proxy e backend. A regressão HTTP envia cabeçalhos desse tipo e confirma a rejeição antes da rota.

As rotas VPS, STT/TTS, chat e integrações Google/Gmail devolvem mensagens genéricas para exceções internas, sem refletir `str(erro)` nem `stderr` de processos externos na resposta HTTP. Os erros de validação de entrada continuam a usar estados HTTP e mensagens de validação próprias. A regressão VPS injeta um marcador secreto numa exceção e verifica que o marcador não chega ao cliente; detalhes de depuração não devem ser adicionados às respostas públicas.

## Classificação de rotas para exposição remota

O prefixo `/api/public/` indica uma rota sem token no fluxo local legado; **não significa que os dados sejam apropriados para exposição irrestrita à Internet**. Para uma implantação remota, autentique no gateway por padrão e libere somente as rotas necessárias.

| Classe | Rotas ou famílias | Política recomendada |
|---|---|---|
| Saúde mínima | `GET /health` | Pode ser pública se necessário ao monitoramento; manter resposta sem detalhes internos. |
| Estado para interface | `GET /api/public/status` | Atrás de autenticação do gateway; contém estado operacional. |
| Diagnóstico interno | `/api/public/nyxos/contexto`, `/api/public/residencia`, `/api/public/recursos`, `/api/public/operacional`, `/api/public/gateway`, `/api/public/presenca`, `/api/public/ae5`, `/api/public/dataset`, `/api/public/delta` | Não publicar diretamente; contém dados internos, serviços, governança, datasets ou eventos. |
| Dados pessoais e telemetria | `/api/integracoes/google/*`, `/api/integracoes/gmail/*`, `/api/agent/contexto`, `/api/agent/status` | Autenticação e autorização restritas. |
| Controle e efeitos | `/api/vps/*`, `/api/agent/image`, `/api/amd-cloud/*`, `/api/ae5/*`, `POST /api/chat`, `POST /api/agent/chat` | Autenticação no gateway e autorização da operação; nunca liberar para visitantes anônimos. |
| Consumo de recursos | `POST /api/stt`, `POST /api/tts` | Autenticar, limitar taxa e monitorar consumo. |

O modo `NYXAL_API_BEHIND_PROXY=1` exige `NYXAL_API_TOKEN` na inicialização; nesse modo, GET (exceto `/health`) e POST requerem Bearer. Mesmo fora desse modo, qualquer origem web não-loopback precisa autenticar quando passa pelo gate da API, inclusive se a conexão de socket parece local. `Origin` não é identidade e pode ser falsificado por clientes que não sejam navegadores.

## Riscos ainda abertos

1. O servidor HTTP é baseado em `http.server`, não em um servidor de produção com TLS, limites operacionais e gestão de conexões.
2. O acesso vindo de processos locais ainda é confiado como loopback; origens do navegador mitigam pedidos cross-site, mas não defendem contra malware/processos locais.
3. Os endpoints de diagnóstico marcados como públicos podem revelar informação operacional a qualquer cliente local. A publicação externa deve aplicar autenticação na borda e uma allowlist de rotas.
4. Ainda é necessária uma auditoria específica dos limites de payload, timeouts, tratamento de erros, logs, sessão, tokens, OAuth/Gmail, gateway de atuação, provisionamento VPS, dependências e permissões systemd.
5. Não há ainda microkernel seL4, prova formal do kernel NyxOS, micro-VM por aplicação, capacidades criptográficas por recurso, sistema base imutável, TPM que mantenha chaves fora da RAM ou criptografia pós-quântica integrada. Esses itens são metas arquiteturais futuras, não controles presentes.

## Próxima sequência recomendada

1. Auditar rotas e classificar publicamente cada endpoint como público, local, autenticado ou privilegiado.
2. Adicionar testes HTTP end-to-end para CORS, autenticação, payloads inválidos e rejeição de bind externo.
3. Aplicar sandboxing real aos serviços residentes (unidades systemd com `ProtectSystem`, `ProtectHome`, `PrivateDevices`, `RestrictAddressFamilies` e capacidades mínimas), validando cada serviço antes de ativar as restrições.
4. Separar API conversacional de rotas privilegiadas (VPS, Gmail e atuação no host), com autorização explícita por operação e logs de auditoria sem segredos.
5. Definir uma trilha de verificação formal e proteção em hardware apenas quando houver plataforma/arquitetura compatível e critérios de prova verificáveis.
