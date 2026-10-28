# Ferramentas operacionais governadas

Este documento resume as regras implementadas pela Nyxal para chamadas de ferramentas. A especificação detalhada, exemplos de configuração e limitações por integração ficam em [`docs/NYXAL_FERRAMENTAS.md`](NYXAL_FERRAMENTAS.md).

## Arquitetura

`nixal_tool_use.py` fornece adaptadores para o `GerenciadorCapacidades` existente em `nixal_capacidades.py`. `nixal_dialogo_qwen.py` anuncia apenas nomes de uma lista permitida, valida os argumentos, aplica política/autorização e envia os resultados de volta ao Qwen. `nyxal_mcp_tools.py` é um servidor MCP opcional e separado; o function calling do diálogo principal não depende de iniciar o servidor MCP.

Conteúdo web, resultados de ferramentas e arquivos lidos são dados não confiáveis, não novas instruções de sistema. O modelo não recebe shell livre nem permissão para executar código arbitrário.

## Ferramentas padrão

Estas consultas não alteram o estado do sistema:

| Ferramenta | Escopo |
|---|---|
| `obter_hora` | Horário local |
| `pesquisar_web` | Busca pública; páginas/URLs retornadas não são executadas |
| `consultar_metar_taf` | METAR/TAF pela AviationWeather.gov Data API |
| `consultar_notam_aisweb` | NOTAMs via AISWEB/DECEA; exige credenciais oficiais |
| `consultar_cartas_aisweb` | Pesquisa metadados/links de cartas ostensivas; exige credenciais oficiais |
| `executar_diagnostico` | Apenas verificações fixas de Git e serviços; sem comandos fornecidos pelo modelo |

## Dados privados e ações mutáveis

Leitura de arquivos pessoais, Gmail, Calendar, Home Assistant e notas/lembretes exige opt-in no ambiente do processo:

```text
NYXAL_ENABLE_PRIVATE_READ_TOOLS=1
```

Editar arquivos do projeto tem um opt-in separado, `NYXAL_ENABLE_WORKSPACE_WRITE=1`, além de `NYXAL_ENABLE_MUTABLE_TOOLS=1`. A ferramenta primeiro prepara um diff limitado e vinculado ao hash do arquivo; nenhuma escrita acontece até o operador enviar a confirmação exata em uma mensagem posterior. Caminhos fora do workspace, symlinks, arquivos sensíveis/operacionais e diffs grandes demais para revisão completa são recusados. Detalhes e limites estão em `docs/NYXAL_FERRAMENTAS.md`.

Salvar uma nota, criar um lembrete e abrir um aplicativo permitido exigem um opt-in independente:

```text
NYXAL_ENABLE_MUTABLE_TOOLS=1
```

Mesmo quando as ações mutáveis são anunciadas, elas só são executadas quando a mensagem atual contém um pedido explícito reconhecido para a ação e a capacidade está registrada com a política esperada. Menções de comandos em textos citados, pedidos de resumo ou explicações não concedem autorização. Capacidades que exigem confirmação separada continuam bloqueadas até existir um fluxo de confirmação apropriado. Ações mutáveis permanecem desativadas por padrão.

Altere as variáveis apenas no ambiente autorizado do processo. Não grave credenciais em arquivos versionados, prompts, logs ou frontend. Após alterar variáveis, reinicie o serviço da Nyxal para que o registro de ferramentas seja reconstruído.

## Limites

- Gmail e Calendar permanecem somente leitura; esta integração não envia e-mails nem altera eventos.
- Home Assistant permanece somente leitura; não são acionados interruptores, fechaduras, alarmes ou outros dispositivos físicos.
- O MCP não recebe shell livre; o HTTP opcional exige opt-in, bearer token forte e loopback. Leituras privadas dependem do opt-in correspondente.
- Dados METAR/TAF, NOTAMs e cartas ajudam na consulta, mas não substituem briefing operacional, fontes oficiais vigentes ou julgamento do piloto.
- Falta de credenciais, indisponibilidade de rede ou autorização insuficiente devem resultar em estado pendente/erro; não devem ser apresentados como sucesso.

## Testes principais

```bash
python3 -m py_compile nixal_capacidades.py nixal_tool_use.py nixal_dialogo_qwen.py nyxal_mcp_tools.py
python3 -m unittest -v teste_nixal_tool_use teste_nyxal_tool_use teste_nyxal_function_calling
python3 teste_mcp_stdio.py
```

Os testes exercitam política de capacidades, allowlists, autorização de ações, validação de argumentos, proteções de privacidade, chamadas em lote/limite de ferramentas, integração MCP e limites de resposta. Execuções remotas precisam ser verificadas no SHA atual antes de considerar a PR aprovada.