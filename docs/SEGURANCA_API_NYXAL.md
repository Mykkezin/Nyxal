# Linha de base de segurança HTTP da Nyxal

## Objetivo e limite

Esta etapa reduz a superfície de exposição da API atual. Ela não transforma a Nyxal em um sistema operacional formalmente verificado nem substitui uma auditoria completa do runtime, dos conectores, das dependências e do host.

## Proteções aplicadas

- **Bind local obrigatório:** `nyxal_web_api.py` recusa iniciar quando `NYXAL_API_HOST` não é `localhost` ou um endereço de loopback. O servidor da biblioteca padrão fala HTTP e não deve ser exposto diretamente à Internet.
- **CORS por lista de permissão:** a API não emite `Access-Control-Allow-Origin: *`. Por padrão, aceita somente as origens locais da própria porta (`localhost`, `127.0.0.1` e `[::1]`). Origens adicionais precisam ser explícitas.
- **Rejeição de origem web não autorizada:** pedidos a `/api/*` que tragam um cabeçalho `Origin` não permitido são rejeitados, inclusive preflight `OPTIONS`.
- **Autorização de rotas para clientes não locais:** os endpoints `/api/*` passam pela verificação local/Bearer antes do processamento. Rotas que já exigem token continuam exigindo-o também em loopback.
- **Cabeçalhos defensivos:** respostas JSON e de bytes incluem `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` e `Cache-Control: no-store`. A versão do servidor deixa de anunciar a versão detalhada do Python.
- **Testes reproduzíveis:** `teste_seguranca_api.py` valida loopback e a política de origens sem precisar subir serviços externos.

## Configuração CORS

Use uma lista de origens exatas separadas por vírgula, sem caminhos ou barras finais:

```bash
NYXAL_API_CORS_ORIGINS="https://nyxal.example,https://painel.nyxal.example"
```

A variável legada `NYXAL_API_CORS_ORIGIN` continua aceita para uma única origem, mas `*` e `null` são rejeitados deliberadamente. Remova qualquer configuração antiga com wildcard antes de reiniciar a API.

## Acesso remoto seguro

Mantenha a API ligada em loopback. Para acesso remoto, exponha somente uma **VPN** ou um **proxy reverso HTTPS com autenticação e controle de acesso próprios**. O proxy deve ser tratado como fronteira de segurança: as conexões encaminhadas ao servidor local aparecem como loopback e, portanto, o proxy precisa autenticar os usuários antes de encaminhar pedidos. Não encaminhe a porta HTTP da Nyxal diretamente à Internet.

`NYXAL_API_TOKEN` continua necessário para endpoints que já exigem Bearer. CORS não é autenticação e não substitui uma camada de acesso remoto.

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
