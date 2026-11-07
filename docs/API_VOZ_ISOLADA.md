# API isolada para validação de voz

## Unidade

`deploy/systemd/nyxal-api-voz-isolada.service` foi criada para ser copiada como unidade de usuário `nyxal-api-voz-isolada.service`. Não tem seção `[Install]`, não é enabled e não referencia `nyxal-api.service`, `nyxos.target`, residente ou interface. O serviço só escuta em `127.0.0.1:8010`, usa o Python já instalado em `~/.venvs/nyxal-green-release`, e inicia com `env -i`: nenhum `nyxal.env`, `.env` do usuário ou variável importada pelo manager é carregada.

O ambiente seleciona `NYXAL_LLM_PROVIDER=ollama`, `NYXAL_AGENT_PROVIDER=nyxal`, `qwen2:7b` e `OLLAMA_HOST=http://127.0.0.1:11434`. Function calling, ferramentas privadas/mutáveis, escrita no workspace, ações VPS irreversíveis e MCP HTTP ficam desativados. A política de rede da unidade permite somente loopback. O filesystem fica estrito/read-only, com escrita liberada apenas em `~/.local/state/nyxal-voice-api-isolated/`.

## Persistência auditada

| Componente | Comportamento ao importar/iniciar | Caminho desta unidade |
| --- | --- | --- |
| `PersistenciaOperacionalNixOS` | Seu construtor carrega e salva imediatamente o contador de inicializações. | `estado_nyxos_operacional.json` sob `NYXAL_STATE_DIR` isolado. |
| `RegistroDeltaNixOS` | Carrega o registro no construtor; endpoints Delta podem gravar. | `eventos_delta_nyxos.json` sob `NYXAL_STATE_DIR` isolado. |
| Presença da máquina | O estado é carregado pelo módulo e usado nos endpoints de presença. | `presenca_maquina_nyxos.json` sob `NYXAL_STATE_DIR` isolado; `HOME` interno também é isolado. |
| Catálogo de capacidades | Os agentes criam `GerenciadorCapacidades` e registram o catálogo durante composição. | `capacidades_nixal.json` sob `NYXAL_STATE_DIR` isolado. |
| Log de capacidades | Era fixo no checkout; agora acompanha `NYXAL_STATE_DIR` quando definido. | `log_capacidades_nixal.json` isolado. |
| Memória conversacional | O núcleo carrega o arquivo na inicialização e grava turnos do `/api/chat`. | `conversas.json` isolado, explicitamente configurado. |
| Memória de investigação/conhecimento | O núcleo carrega essas memórias auxiliares ao ser composto. Os defaults antigos apontavam para arquivos no checkout. | `memoria_investigacao.json` e `memoria_conhecimento.json` isolados via novas variáveis de caminho. |
| Trilha HTTP | Por padrão gravaria em `XDG_STATE_HOME/nyxal/http-traces.jsonl`. | Desativada nesta unidade. |
| Notas/lembretes e fila | A API inicia o worker de lembretes; executor da fila é lazy. | `NYXAL_USER_DATA_DIR` aponta para `user-data/` isolado; HOME não contém sessão D-Bus/display, logo o worker não envia notificações. |
| Configuração Google | As classes derivam token/client de `NYXAL_CONFIG_DIR` ou `$HOME/.config/nyxal`. | Caminhos forçados para `config/nyxal/` isolado; nenhum segredo é herdado. |
| Runtime/cristalização | A cadeia de imports da API não instancia `nixal_runtime`, `gerenciador_cristal` nem ciclo de cristalização. | Não inicializados. |

O servidor também inicia `ServicoLembretesNixOS`; com ambiente sem `DISPLAY`, `WAYLAND_DISPLAY` ou `DBUS_SESSION_BUS_ADDRESS`, não envia notificações. Ele lê apenas `user-data/notas_lembretes.json`, dentro do isolamento. A API não inicia o residente NyxOS, MCP, Ollama, desktop ou interface. Ollama já deve estar ativo localmente.

## Preparação e execução controlada

Antes da unidade, a regressão `teste_nyxal_state_dir_api.py` verifica em subprocesso com HOME temporário que estado operacional, Delta, presença, capacidades, memórias auxiliares e log ficam no diretório fornecido e que os arquivos homônimos no checkout não mudam.

O procedimento de instalação em `~/.config/systemd/user/` copia somente esta unidade, depois executa `systemctl --user daemon-reload` e **apenas** `systemctl --user start nyxal-api-voz-isolada.service`. Não executar `enable`, nem iniciar outras unidades. O smoke test conversacional grava somente `conversas.json` e seus arquivos de lock/atômicos no diretório isolado.

O `NYXAL_STATE_DIR` também abriga os JSONs de inicialização criados pelo import. Antes/depois do start, a auditoria compara hashes do checkout (exceto `.git` e bytecode), `NyxOS`, `~/.local/share/nyxal`, `~/.local/state/nyxal` e `~/.nyxal`. O diretório novo de isolamento é verificado separadamente e não entra na comparação do estado operacional.
