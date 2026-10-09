# Segurança de origem HTTP da API Nyxal

A API da Nyxal é destinada a uso local e escuta em `127.0.0.1` por padrão. Cabeçalhos de navegador `Origin` são validados contra uma allowlist antes de as rotas GET/POST serem processadas.

Por padrão, são permitidas apenas origens loopback do Display local nas portas 3000, 5173 e 8010. Para uma implantação deliberada em outra origem HTTP(S), defina `NYXAL_API_CORS_ORIGIN` com origens completas e exatas separadas por vírgulas, por exemplo:

```bash
NYXAL_API_CORS_ORIGIN=https://nyxos.example.com,https://admin.example.com
```

Não use `*`: origens curinga e `null` são rejeitadas. Caminhos, credenciais embutidas, query strings e fragmentos não fazem parte de uma origem permitida. Requisições de clientes não-browser que omitem `Origin` continuam suportadas; rotas sensíveis continuam sujeitas à autenticação própria.

Não exponha a API em interfaces públicas ou de rede sem configurar autenticação forte e uma allowlist de origem restrita. CORS é uma camada adicional, não substitui autenticação.
