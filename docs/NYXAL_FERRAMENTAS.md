# Ferramentas locais da Nyxal e política de uso

## Escopo nesta versão

\`nixal_tool_use.py\` contém adaptadores limitados; \`nyxal_mcp_tools.py\` os expõe como um servidor MCP opcional. Esse servidor é separado da API principal e **não ativa automaticamente function calling no chat principal**. A integração final do ciclo de ferramentas ao diálogo local ainda exige alterações nos módulos já existentes do Core e do diálogo.

O princípio é reutilizar os conectores, o registro de capacidades e a memória já existentes — não executar código retornado pelo modelo, nem aceitar um terminal genérico.

## Ferramentas MCP disponíveis

| Ferramenta | Acesso |
|---|---|
| \`status_ferramentas\` | Estado das integrações, sem expor tokens |
| \`pesquisar_web\` | Pesquisa web; devolve títulos e URLs para conferência |
| \`consultar_metar_taf\` | METAR/TAF públicos por identificador ICAO |
| \`consultar_estado_home_assistant\` | Consulta estados via Home Assistant REST, somente GET |
| \`buscar_arquivos\` / \`ler_arquivo\` | Busca/leitura de arquivos em pastas permitidas, com bloqueio de caminhos sensíveis |
| \`consultar_gmail\` / \`ler_email\` | Gmail OAuth, somente leitura |
| \`consultar_agenda\` | Google Calendar OAuth, somente leitura |
| \`listar_notas_lembretes\` | Consulta da persistência local existente |
| \`diagnosticar_sistema\` | Consultas de diagnóstico fixas; não aceita comando arbitrário |

## Como executar o servidor MCP

No computador da Nyxal, depois de obter esta branch:

\`\`\`bash
cd ~/Nyxal
./.venv/bin/python nyxal_mcp_tools.py
\`\`\`

O processo usa transporte stdio do \`MCPServer\`. No cliente MCP, configure \`command\` para o caminho absoluto de \`~/Nyxal/.venv/bin/python\` e \`args\` para o caminho absoluto de \`~/Nyxal/nyxal_mcp_tools.py\`. Não coloque tokens no arquivo de configuração do cliente.

Para testar os adaptadores sem consultar contas externas:

\`\`\`bash
./.venv/bin/python teste_nyxal_tool_use.py
\`\`\`

## Google Workspace

A implementação reaproveita \`IntegracaoGmailNixOS\`. Credenciais permanecem fora do repositório, sob \`~/.config/nyxal\` por padrão. Os escopos são os quatro já existentes: Gmail readonly, Calendar readonly, Contacts readonly e Drive metadata readonly. A função de status verifica configuração; a presença de um arquivo sozinha não prova que a conta está acessível.

Não existe envio de e-mail, alteração de eventos, exclusão/arquivamento de mensagens, gravação de contatos nem download de arquivos do Drive nessa integração.

## Notas e lembretes locais

A persistência é separada da memória conversacional e usa \`~/.local/share/nyxal/notas_lembretes.json\` (pode ser alterada com \`NYXAL_USER_DATA_DIR\`). O diretório é criado com permissão \`0700\` e o arquivo com \`0600\`; gravação usa arquivo temporário e \`os.replace\`. JSON inválido não é sobrescrito silenciosamente.

Os adaptadores de criação de notas e lembretes estão disponíveis no registro local com política de pedido explícito, mas não são expostos por este servidor MCP de somente leitura. Lembretes vencidos podem ser entregues pelo adaptador de notificações se \`notify-send\` e um ambiente de sessão gráfica/D-Bus estiverem disponíveis. Se a API estiver parada ou não houver sessão de desktop, a notificação não é garantida.

## Home Assistant

Para habilitar consulta local, configure no ambiente do processo MCP/API:

- \`NYXAL_HOME_ASSISTANT_URL\`: URL-base da instância Home Assistant.
- \`NYXAL_HOME_ASSISTANT_TOKEN\`: token de longa duração.

Não grave o token no Git, no frontend, em mensagens ou logs. O adaptador recusa redirecionamentos e só faz GET; retorna atributos em uma lista permitida. **Acionar interruptores, fechaduras, alarmes ou outros dispositivos não está habilitado** nesta versão.

## Aviação

METAR/TAF são consultados na API pública do [AviationWeather.gov Data API](https://aviationweather.gov/data/api/). Informe o identificador ICAO com quatro caracteres, por exemplo \`SBSP\` ou \`SBGR\`. Os dados são apoio à consulta e não substituem briefing oficial, NOTAMs, AIP/cartas, ATIS, instrução nem julgamento do piloto.

**NOTAMs e cartas aeronáuticas ainda não estão ligados** nesta implementação. Não devem ser tratados como consultados ou disponíveis.

## Controles de segurança

- Resultados da web, arquivos, mensagens e eventos externos são dados não confiáveis, nunca instruções privilegiadas.
- A busca e leitura de arquivos bloqueiam locais típicos de credenciais e limitam tamanho/quantidade.
- O controle de computador é limitado a nomes de aplicativos permitidos e diagnósticos fixos. Não existe execução de comandos arbitrários, código gerado pelo modelo ou shell livre.
- Não há rotas para enviar e-mails, modificar Calendar ou acionar Home Assistant.
- Não afirmar que uma ferramenta funcionou sem resultado real. Diferenciar configuração pendente, falha externa e execução concluída.
