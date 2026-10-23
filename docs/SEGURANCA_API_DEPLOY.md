# Segurança da API Nyxal — implantação

## Padrão seguro

A API deve ficar em loopback (`NYXAL_API_HOST=127.0.0.1`) quando o acesso for local. Não publique a porta 8010 diretamente na internet.

Ao vincular a API a um endereço não local, configure um token forte e aleatório em `NYXAL_API_TOKEN`. A inicialização agora é recusada se o endereço configurado não for loopback e o token estiver ausente. Endpoints protegidos recebem o token em `Authorization: Bearer <token>`.

## Reverse proxy / túnel

Se a API permanecer em loopback e for publicada por reverse proxy, configure:

```sh
NYXAL_API_BEHIND_PROXY=1
NYXAL_API_TOKEN='<segredo-forte-gerado-fora-do-repositório>'
```

O modo proxy faz a API exigir autenticação mesmo quando a conexão chega pelo loopback. Cabeçalhos comuns de proxy (`Forwarded`, `X-Forwarded-For` ou `X-Real-IP`) também desativam o atalho de confiança local. Configure o proxy para substituir esses cabeçalhos, não confiar em valores enviados pelo cliente, e aplique autenticação de borda (por exemplo, VPN/Tailscale ou Access). Nunca grave o token no JavaScript do Display, no Git, em logs ou em imagens de contêiner.

A API continua servindo `/health` e `/api/public/status` sem token para health checks e status mínimo. Dados operacionais detalhados, presença, Delta, datasets, gateway e estado de VPS requerem autenticação quando a API está em modo de rede/proxy. Ações e provisionamento de VPS também exigem autenticação quando a API está em modo de rede/proxy.

## CORS

CORS fica desabilitado por padrão. Para um Display hospedado em outra origem, configure uma origem exata, por exemplo:

```sh
NYXAL_API_CORS_ORIGIN='https://display.exemplo.invalid'
```

Não use `*` como origem permissiva. CORS não substitui autenticação, e um endpoint de rede não deve ser exposto apenas porque o navegador bloqueia algumas chamadas cross-origin.

## Validação

Execute:

```sh
python teste_api_security_auth.py
python teste_api_chat_sem_voz.py
```

O primeiro teste levanta um servidor HTTP local efêmero e verifica o limite de autenticação com requests reais, incluindo simulação de reverse proxy. Execute também a suíte principal e revise a configuração do proxy antes de publicar.
