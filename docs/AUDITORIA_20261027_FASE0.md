# Auditoria 2026-10-27 — inventário inicial e primeira correção

Escopo: Fase 0 (proteção e verdade) + primeiros lotes P0/P2. Trabalho em
`git worktree` isolado baseado em `origin/main`; o checkout `/home/nyxal/Nyxal`
permanece em `feat/delta-platform-foundation-20261027` com seus estados
operacionais intactos.

## Proteção do checkout (evidência)

`git status` em `/home/nyxal/Nyxal` no início e depois de toda a auditoria é
idêntico: 3 modificados (`capacidades_nixal.json`, `estado_corpo_nixal.json`,
`estado_nyxal_runtime.json`) e 15 não rastreados.

Classificação dos não rastreados:

| Tipo | Arquivos |
| --- | --- |
| Dados operacionais gravados pelo runtime | `estado_nyxos_operacional.json`, `eventos_delta_nyxos.json`, `fisiologia_operacional_nyxos.json`, `gateway_atuacao_nyxos.json`, `log_nyxal_residente.json`, `memoria_aprendizado_nixal.json`, `plano_central_controle_nyxos.json`, `presenca_maquina_nyxos.json`, `auditoria_atuacao_nyxos.jsonl` (+ `.lock`) |
| Evidência de corrupção a preservar | `auditoria_atuacao_nyxos.jsonl.corrompido-cadeia-20261009-194314-139499` |
| Código fora do versionamento | `nyxal_desktop_flotante.py` (24 KiB, 2026-10-25) |
| Backups | `nyxal_desktop_flotante.py.bak-20261024-233453`, `.bak-20261024-235035` |

Existem dois `git stash` em `main` rotulados como backup de estados
(`backup-estados-antes-holograma`, `backup-estados-antes-atualizacao-interface`).
Não foram tocados.

### Os três JSONs "modificados" são artefatos derivados, não trabalho humano

Importar `nixal_capacidades` reescreve `capacidades_nixal.json` no diretório do
projeto. Reproduzi isso em um worktree limpo de `origin/main`: o diff gerado foi
**212 inserções / 5 remoções**, e o diff já presente no checkout vivo é
**212 / 5** — numericamente idêntico. O arquivo rastreado contém 5 capacidades
sem `politica`; o runtime regrava 10 capacidades com `politica: somente_leitura`.

Consequências: (1) `git status` nunca estará limpo nesse checkout enquanto o
serviço residente rodar; (2) o campo `politica` no JSON é decorativo — a fila
governada usa o default da classe `Capacidade`
(`nixal_capacidades.py:79`), então a ausência da chave em `origin/main` não
desativa nenhuma capacidade. Confirmado por execução: as 5 capacidades do
catálogo commitado carregam `somente_leitura` e a fila aceita e conclui tarefa.

## GitHub: superfície real

Uma PR aberta e duas issues abertas — o escopo pendente é pequeno e nomeável.

- **#231** `feat(api): integrar ordens governadas à API local` — aberta na
  auditoria, `MERGEABLE`, `mergeStateStatus: CLEAN`, sem review pendente, 7 checks
  `SUCCESS`, 0 commits atrás de `origin/main`. **Integrada em 2026-10-28T02:13:40Z
  como `a899432`** pelo fluxo normal (merge commit, convenção do repositório).
- **#167** CI instável, atualizada 2026-10-28. **#103** defesa governada,
  atualizada 2026-10-28.

## PR #231 validada localmente

`python3 -m unittest` no branch da PR: `teste_nixal_fila_tarefas_segura` 29/29
OK e `teste_api_security_auth` 36/36 OK.

Contratos conferidos no código: as três rotas passam pelo gate de autorização
(`nyxal_web_api.py:1212-1216`); a resposta HTTP não reflete argumentos, prompts
nem erro bruto (`_resumir_ordem_api`, `_resumir_tarefa_ordem_api`); corpo
limitado a 16 KiB / ordem a 2000 caracteres, rejeitando chaves JSON duplicadas e
constantes não finitas; a fila aceita **somente** `politica == "somente_leitura"`
(`nixal_fila_tarefas.py:535-551`); o executor exige o ID da própria ordem antes
de executar (`nixal_executor_ordens.py:181` com `tarefa_id_esperado`), então uma
tarefa anterior nunca é consumida como se fosse da ordem nova; tarefa
interrompida vira `resultado_indeterminado` e não repete sozinha
(`nixal_fila_tarefas.py:415-440`); a fila recusa caminho dentro do checkout
(`nixal_fila_tarefas.py:97-103`).

Lacuna de integração: nenhuma tela consome as rotas novas. `grep` em `interface/`
por `agent/orders` não retorna nada; só `docs/NYXAL_FERRAMENTAS.md`, a API e o
teste citam a rota. A fila está exposta como capacidade, não como função do
produto.

## Cadeia conversacional: 4 falhas pré-existentes

`teste_integracao_nucleo_conversacional.py` executa 46 verificações e falha 4 —
**no `origin/main` puro**, ou seja, não é regressão da #231.

Valores reais observados versus esperados:

| Asserção | Esperado pelo teste | Observado |
| --- | --- | --- |
| mensagem não armazenada | `False` | `True` |
| memória conversacional ausente | `False` | `True` |
| segunda resposta | `"Agora são 23:30:16."` | `"Agora são 22 horas, 57 minutos e 42 segundos."` |
| chamadas do agente | 3 entradas, incluindo o objetivo canônico | 2 entradas |

Diagnóstico: as duas primeiras são um contrato desatualizado — o teste é da
série 56.5.x, quando a cadeia não persistia; hoje persiste, e os guardas que
importam (`conhecimento_permanente`, `arquitetura_modificada`) continuam
`False`. As duas últimas são não-determinismo real: na segunda mensagem o
`AgenteDeterministico` é contornado e a capacidade `obter_hora` executa o relógio
do sistema, então o teste depende do horário do computador. Não corrigi ainda:
mexer nesse contrato exige decidir se a persistência atual é a desejada.

## Cobertura de testes: o número que importa

203 arquivos `teste_*.py` na raiz; **107 delas nunca são citadas por nenhum
workflow**. O CI roda 17 passos `python3 -m unittest` nominais mais 2 `discover`
restritos a `deploy/delta` e `deploy/voice`. Inclui os testes da cadeia central
(`teste_integracao_nucleo_conversacional`, `teste_integracao_interface_corpo_residente`).

Efeito colateral de rodá-los: o `python3` do sistema não tem `ollama`, `mcp`,
`httpx2` nem `pytest`; o serviço residente usa `.venv/bin/python`, que **tem**
`ollama`. Por isso `teste_nyxal_function_calling` (37), `teste_nucleo_contexto_persistente`
(20), `teste_nixal_workspace_edits` (14) e `teste_nixal_dialogo_router` (10)
passam no venv e dão `ImportError` no interpretador do CI. Não há
`requirements.txt` nem `pyproject.tom` na raiz para documentar isso.

Advertência metodológica: rodar os 203 módulos em um único processo produz 9
"falhas" que somem com isolamento — contaminação de estado entre módulos, não
defeito do código. Os números acima são de processos separados.

## Issue #167: causa confirmada, culpa não é do plano

`gh api /actions/runners` retorna **exatamente um runner** (id 21 "Nyxal",
online, `self-hosted, Linux, X64`, `assigned_jobs: null`), e 22 dos 23 workflows
usam `runs-on: self-hosted` — fora `nyxal-remote-lab.yml:31`. Últimas 200 runs:
**94 cancelled, 59 success, 37 skipped, 10 failure**.

Os sintomas descritos na issue são cancelamento na fila, não arquivos perdidos:
run 40614724133 criada 01:23:11Z e cancelada 01:23:22Z com o job `habitat` em
**0 steps**. Falhas reais de código foram corrigidas antes desta auditoria
(`SyntaxError` em literal de bytes, sanada em `12aaa12`; o push seguinte ficou
todo verde).

Corrigido neste lote: `/tmp/nyxal-ci-evidence.json` era escrito por dois
workflows com o mesmo nome fixo (`nyxal-nivel9-validation.yml:289`,
`security-baseline.yml:93,105`) e `/tmp/nyxal-package` era compartilhado
(`nyxal-nivel9-validation.yml:203,212`) — migrados para `RUNNER_TEMP`, que o
runner isola por job. `grep /tmp/` nos workflows agora retorna vazio.

Não executei, de propósito, por mexerem em checks que a proteção de branch pode
exigir por nome: deduplicar `teste_api_security_auth` entre `defesa-autonoma.yml:49`
e `nyxal-nivel9-validation.yml:114`; agrupar concorrência por PR; habilitar
`pull_request` nos 13 workflows que só têm `push`. Também não atribuí nada a
limite de plano: `queued: 0` e todas as falhas têm causa em passo visível.

## Issue #103: o P0 que encontrei e fechei

`POST /api/vps/action` despachava `destroy` e `autostart_off` direto para
`virsh` (`nixal_vps.py:301-320`) com autorização dada apenas por confiança de
loopback (`nyxal_web_api.py:1185-1198`): sem token, sem aprovação, sem
idempotência, sem auditoria. `deploy/systemd/nyxal-api.service` não define
`NYXAL_API_BEHIND_PROXY`, então esse é o arranjo instalado. Qualquer processo do
usuário derrubava a VM DELTA. O `window.confirm` do painel não é fronteira — é
JavaScript do navegador.

A correção deixa o painel como está (ele só envia `start`/`shutdown`/`reboot`,
conferido em `interface/js/nyxal-voice-console.js:559-564` e
`interface/index.html:4745-4765`) e exige Bearer para as irreversíveis, que
ademais permanecem desativadas por padrão. `teste_api_barreira_vps.py` cobre os
cinco caminhos, inclusive o de que o painel continua sem token.

O teste pré-existente `teste_api_security_auth.py:71-79` dava falsa segurança:
ele só exercita `PROXY_MODE = True`, enquanto a implantação real roda sem proxy.

Pendências da #103 ainda sem correção: aprovação humana independente
(`verificador_aprovacao` nunca é injetado — `nyxal_web_api.py:309` cria o
executor sem o callable, e não existe rota de aprovação); auditoria durável
restrita a `falha_autenticacao` (`nixal_auditoria_defesa.py:32`), sem cobrir
planos nem execuções de capacidade; sem correlacionador entre a trilha HTTP e o
ledger, o que impede ligar um 401 ao seu evento; estado de defesa por processo,
que zera no restart e permite criar plano duplicado; o ledger passa a recusar
gravação após 2048 registros e um `rm` do arquivo reinicia do `GENESIS_HASH` sem
aviso (`nixal_auditoria_defesa.py:336-344`).

## Deriva entre o unit do repositório e o unit instalado (afeta a memória)

`deploy/systemd/nyxal-api.service:12` define
`NYXAL_CONVERSATION_MEMORY_PATH=%h/.local/share/nyxal/conversas.json`, mas o unit
realmente instalado em `~/.config/systemd/user/nyxal-api.service` não tem essa
linha — o `diff` são exatamente essas duas linhas ausentes, e o arquivo alvo não
existe. `nixal_memoria_conversacional.py:115` lê essa variável para escolher o
caminho persistente. O `EnvironmentFile` (`~/.config/nyxal/nyxal.env`, permissão
600) não a define: seus 11 nomes são `NYXAL_AGENT_PROVIDER`, duas chaves Gemini,
duas Hermes, quatro Letta, voz Kokoro e modelo Whisper.

Duas conclusões: a persistência conversacional declarada no repositório não está
ativa como declarada na máquina (fase 4), e o mesmo unit não define
`NYXAL_API_BEHIND_PROXY` nem `NYXAL_API_TOKEN` — o que confirma que a porta
`/api/vps/action` estava aberta por confiança de loopback, e que hoje as ações
irreversíveis retornam 423 antes mesmo de qualquer token.

## Estado deste lote

Dois commits em `fix/p0-govacao-vps-20261027` sobre `6acc451`: `9be8972` (gate
de VM, 5 testes novos) e `70b7f43` (RUNNER_TEMP). Verificações reais:
`py_compile` OK, `teste_api_barreira_vps` 5/5, `teste_api_security_auth` 30/30
no baseline, `teste_nixal_vps` 20/20, YAML dos dois workflows válido. Nada foi
enviado ao remote. Serviços, Chrome e a VM DELTA não foram tocados; a API viva
responde em `/health` e continua rodando o código antigo do branch `feat/delta`
até uma implantação explícita.
