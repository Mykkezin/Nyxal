# Auditoria do subsistema de cristalização

Objetivo deste documento: transformar o estado "0/10" do checklist de
auditoria em um estado verificável, item por item, com evidência em código
e em teste executável.

## Proveniência do checklist (leia antes de confiar nos itens 6 a 10)

Não existe no repositório uma versão anterior deste checklist. Evidência:

- `git log --all -- docs/CRISTALIZACAO_AUDITORIA.md` está vazio: este arquivo
  nunca foi commitado antes desta correção.
- `git log --all -S "0/10"` só devolve `61b8e3e` (docs de arquitetura NyxOS),
  onde "10/10" se refere a tentativas de rollback, não à cristalização.
- Os contratos `O12`/`O13`/`O14`/`O15` citam "cristalização" apenas como nome
  de subsistema, sem itens numéricos.

Portanto a numeração 1-10 abaixo é **reconstrução por inferência** a partir do
código, dos testes e das instruções da auditoria recebida. Os itens 1 a 5
correspondem exatamente aos cinco critérios pedidos na solicitação de P0/P1.
Os itens 6 a 10 são os temas restantes declarados na própria auditoria
(fonte única, semântica fora da persistência, fidelidade, CI, observabilidade)
e devem ser lidos como tais, não como texto original recuperado do repositório.

## Escopo auditado

| Módulo | Papel | Persistência |
| --- | --- | --- |
| `gerenciador_cristal.py` | cristal estrutural com IDs (triplas) | binário append-only |
| `experiencia_qwen.py` | normaliza saída do Qwen e grava no cristal | binário |
| `pipeline_integrado.py` | Qwen → consenso → gate → cristal | binário |
| `cristalizacao.py` | cristal semântico por conceito | JSON |
| `ciclo_cristalizacao.py` | compressão com avaliação de fidelidade | JSON |

## Como verificar

```bash
python3 testes/teste_persistencia_cristal.py
# a matriz completa roda igual ao job de CI:
while IFS= read -r t; do [ -n "$t" ] && python3 "$t" >/dev/null 2>&1 || echo "FALHA $t"; done \
  < .github/matriz-validacao-raiz.txt
```

Resultados realmente obtidos com o `python3` do sistema (3.12, **sem** o
pacote `ollama` instalado), na data desta correção:

| Execução | Resultado |
| --- | --- |
| `testes/teste_persistencia_cristal.py` | **31 testes, 31 passaram, 0 falharam** |
| matriz `.github/matriz-validacao-raiz.txt` (88 entradas) | **executados=88 falhas=0** |
| `python3 gerenciador_cristal.py` (demo microetapa 41) | cristal demo v2, `ok: true` |
| `avaliar_cristal.py`, `testar_cristal.py`, `otimizar_cristal.py` | **não executados**: exigem `ollama` + modelo local; não importam `gerenciador_cristal`, logo não são afetados por esta correção |

A matriz já era executada pelo job "Nyxal Root Test Matrix" (runner
self-hosted) com `executados=87 falhas=0` na PR #240. O item novo é a suíte de
persistência, incluída no inventário; o job correspondente a esta branch só é
evidenciável depois do push.

---

## Checklist da auditoria

| # | Item | Estado |
| --- | --- | --- |
| 1 | Persistência (dados sobrevivem ao reinício do processo) | corrigido e validado |
| 2 | Proteção contra perda (nenhuma gravação apaga o anterior) | corrigido e validado |
| 3 | Integridade binária (formato validável e validado) | corrigido e validado |
| 4 | Deduplicação (experiência repetida não reescreve) | corrigido e validado |
| 5 | Expansão (IDs além de 1 byte, sem perda ao expandir) | corrigido e validado |
| 6 | Fonte única de verdade, caminho canônico e migração | corrigido e validado |
| 7 | Importar módulo não chama modelo nem produz efeito colateral | corrigido e validado |
| 8 | Fidelidade e política de aceitação do candidato reproduzíveis | **parcial** |
| 9 | Testes de cristalização rodando no CI sem `ollama` | corrigido e validado |
| 10 | Observabilidade (quem gravou qual tripla) | **não validado / em aberto** |

---

## Itens corrigidos

### 1. Persistência

- **Problema e causa-raiz.** `inicializar_cristal()` chamava
  `ARQUIVO.unlink()` e recriava o arquivo vazio; quem a importasse perdia o
  cristal. Não havia um único ponto de entrada: cada consumidor resolvia o
  próprio caminho.
- **Correção.** `abrir_ou_criar_cristal()` é a entrada única: abre o
  existente, migra do legado quando o autoritativo ainda não existe e só cria
  um cristal novo quando não há nada a preservar. A abertura usa
  `ler_arquivo_validado()`, que nunca regrava o que leu.
- **Teste positivo.** `test_persistencia_apos_reiniciar` grava duas
  experiências, relê em **processo separado** (`subprocess`) e exige
  conhecimento idêntico; `test_persistencia_preserva_cabecalho_e_vocabulario`
  confere cabeçalho e vocabulário base.
- **Teste negativo.** `test_abrir_nao_apaga_cristal_existente` e
  `test_inicializar_deprecated_nao_destroi` falham se qualquer abertura
  reduzir o conteúdo.
- **Resultado.** Aprovados nos 31.

### 2. Proteção contra perda

- **Problema e causa-raiz.** Quatro buracos: `unlink()` na inicialização;
  reset sem confirmação; `open(..., "w")` truncante; corrupção tratada como
  perda.
- **Correção.**
  - `inicializar_cristal()` continua exportada, marcada **DEPRECATED**, com
    aviso e redirecionamento — não foi apagada.
  - `reset_destrutivo_cristal()` é a única via que remove, exige
    `confirmacao_explicita=True` (senão levanta `PermissionError`) e faz
    backup verificável antes.
  - Toda gravação passa por `gravar_atomicamente()`: temporário no mesmo
    diretório, `flush` + `os.fsync`, `os.replace`, `fsync` do diretório e
    limpeza do temporário em `finally`.
  - `backup_cristal()` antes de cada escrita destrutiva;
    `caminho_checkpoint()` guarda o último estado **confirmado**;
    `quarentenar_cristal()` move (nunca deleta) conteúdo ilegível;
    `recuperar_ultimo_backup()` prefere o checkpoint e depois os backups do
    mais novo ao mais velho, validando cada candidato antes de restaurar.
  - Rotação documentada: `MAX_BACKUPS_PRESERVADOS = 20` via `podar_backups()`.
- **Testes positivos.** `test_reset_destrutivo_faz_backup_antes_de_apagar`,
  `test_backup_anterior_a_cada_gravacao`,
  `test_cristal_corrompido_vai_para_quarentena_e_recupera_backup`,
  `test_falha_no_meio_da_gravacao_preserva_original`,
  `test_checkpoint_recupera_o_ultimo_estado_bom`,
  `test_rotacao_de_backups_preserva_os_mais_recentes`.
- **Testes negativos.** `test_reset_destrutivo_exige_confirmacao` (recusa e
  arquivo intacto), `test_criar_cristal_nao_sobrescreve_estado_existente`
  (criação sobre cristal existente levanta `CristalAlterado`),
  `test_checkpoint_nao_e_envenenado_por_conteudo_invalido` (conteúdo reprovado
  pela validação nunca vira estado bom).
- **Correção adicional desta rodada.** O checkpoint passou a ser atualizado
  **só se o conteúdo recém-trocado passa em `validar_bytes_cristal`**; antes
  ele registrava qualquer byte escrito, o que degradava o "último estado bom"
  para "última escrita".
- **Limitação.** Não há bloqueio entre processos (`flock`): a proteção contra
  corrida é compare-and-swap (item 3), que recusa a sobrescrita mas não
  serializa os escritores.

### 3. Integridade binária e concorrência

- **Problema e causa-raiz.** O parser aceitava praticamente qualquer byte: sem
  checagem de versão conhecida, sem referência declarada, e a primeira versão
  desta auditoria comparava bytes inteiros, o que quebrava um formato
  append-only cuja ordem de registros é semanticamente válida.
- **Correção.** `validar_bytes_cristal(dados, origem)` e
  `validar_integridade(caminho)` conferem, nesta ordem: MAGIC `NXCM`; versão
  conhecida (1 ou 2); strings com comprimento e payload completos; nomes de
  conceito e relação sem duplicação; blocos referenciando apenas IDs **já
  declarados antes deles**; tipo de registro desconhecido interrompe a leitura;
  round-trip **semântico** (re-serializar e reler devolve as mesmas estruturas —
  não igualdade byte a byte).
- **CAS.** `gravar_atomicamente(..., esperado_antes=bytes)` levanta
  `CristalAlterado` se outro escritor mudou o arquivo desde a leitura. Todas as
  escritoras do módulo (`registrar_experiencia`, `expandir_cristal`,
  `criar_cristal_novo`, `migrar_do_legado`) agora pré-validam os bytes
  resultantes e gravam com `esperado_antes`.
- **Testes positivos.** `test_integridade_de_cristal_valido`,
  `test_v1_legivel_sem_migracao`.
- **Testes negativos.** `test_integridade_detecta_magic_invalido`,
  `test_integridade_detecta_string_truncada`,
  `test_integridade_detecta_tipos_desconhecidos`,
  `test_integridade_detecta_referencia_orfa`,
  `test_gravacao_interrompida_por_escrita_parcial_pode_ser_recuperada`,
  `test_gravacao_concorrente_e_recusada_sem_sobrescrever` (recusa, conteúdo
  mais novo preservado, nenhum `.tmp-` órfão).

### 4. Deduplicação

- **Problema.** A checagem existia, mas nada a provava: uma regressão poderia
  regravar a tripla repetida sem ninguém notar.
- **Correção e evidência.** Tripla já presente devolve
  `classificacao="DUPLICADO"`, `crescimento=0` e nenhum byte alterado. Como a
  checagem lê o arquivo, vale também após reiniciar o processo.
- **Testes.** `test_experiencia_repetida_nao_cresce_arquivo`,
  `test_deduplicacao_sobrevive_a_reinicio` (segundo processo).

### 5. Expansão além de 1 byte

| Versão | Bytes por campo | Capacidade de IDs | Nome máximo |
| --- | --- | --- | --- |
| 1 | 1 | 0..255 (256 conceitos) | 255 bytes |
| 2 | 2 | 0..65535 | 65535 bytes |

- **Correção.** `VERSAO_1`/`VERSAO_2`/`VERSAO_ATUAL`, `FORMATOS_INT`,
  `largura_da_versao()`, `limite_de()`, `escrever_inteiro()`,
  `escrever_ids()`; o cabeçalho segue com 5 bytes (`NXCM` + versão) e a
  largura é derivada da versão, sem campo redundante. `ler_string()` e os
  codificadores aceitam `largura` explícita.
- **Sem truncamento silencioso.** `registrar_experiencia()` ao atingir o teto
  da versão levanta `ValueError` orientando `expandir_cristal()`.
- **Correção desta rodada.** `expandir_cristal()` lia o `tamanho_anterior`
  **depois** da escrita, relatando crescimento zero; agora captura os bytes
  antes, pré-valida o resultado e grava com CAS.
- **Testes.** `test_v2_armazena_ids_acima_de_255` (300+ registros, IDs > 255,
  reconstrução e integridade), `test_v1_e_preservado_e_pode_ser_expandido_sem_perda`,
  `test_v1_legivel_sem_migracao`.

### 6. Fonte autoritativa, caminho canônico e migração

- **Problema e causa-raiz.** Dois caminhos concorrentes
  (`experimentos/cristal_gerenciador.bin` e `memoria/cristal/cristal.bin`) e
  todos os caminhos eram **relativos ao cwd**: rodando de outro diretório — ou
  no runner self-hosted do CI — cada processo apontava para um cristal
  diferente.
- **Correção.**

  ```python
  RAIZ_PROJETO = Path(__file__).resolve().parent
  CAMINHO_AUTORITATIVO = "memoria/cristal/cristal.bin"
  resolver_caminho(relativo, variavel_ambiente)   # override explícito ou raiz
  caminho_do_projeto(*partes)                     # p/ consumidores
  ```

  Overrides: `NYXAL_CRISTAL_ARQUIVO`, `NYXAL_CRISTAL_LEGADO`,
  `NYXAL_CRISTAL_BACKUPS`. `ARQUIVO_DEMO` e os caminhos de
  `cristalizacao.py`/`ciclo_cristalizacao.py` também são ancorados.
  `experiencia_qwen` não importa mais o `Path` por valor: usa
  `caminho_do_cristal()`, que consulta `gerenciador_cristal.ARQUIVO` no momento
  do uso.

| Caminho | Papel |
| --- | --- |
| `memoria/cristal/cristal.bin` | fonte autoritativa do cristal estrutural |
| `experimentos/cristal_gerenciador.bin` | legado, somente leitura, preservado |
| `memoria/backups/cristal_backup_*.bin` | backups com rotação de 20 |
| `memoria/backups/cristal_ultimo_bom.bin` | checkpoint do último estado validado |
| `<arquivo>.corrompido-<timestamp>` | quarentena (movido, nunca deletado) |
| `memoria/cristalizacao.json` | cristal semântico (derivado, JSON) |
| `memoria/cristal_atual.json` | cristal do ciclo de compressão (derivado, JSON) |

- **Migração (por cópia, validada antes de gravar).** Se o autoritativo não
  existe e o legado existe: lê, **valida os bytes do legado**, grava atomicamente
  no autoritativo com `esperado_antes=b""`, reabre e compara
  semanticamente. O legado nunca é modificado. Legado ilegível é preservado
  como está, com aviso, e um cristal novo é criado.
- **`memoria/cristal/` e `memoria/backups/` entraram no `.gitignore`**: são
  dados operacionais, não código-fonte. O legado rastreado continua
  versionado até decisão separada de remoção.
- **Testes.** `test_migracao_copia_legado_para_fonte_autoritativa`,
  `test_migracao_recusa_legado_corrompido_sem_tocar_destino`,
  `test_caminhos_do_projeto_nao_dependem_do_cwd` (roda com `cwd=/`),
  `test_variaveis_de_ambiente_redirecionam_todos_os_consumidores`.
- **Estado do ambiente vivo observado.** `memoria/cristal/cristal.bin` =
  589 bytes, versão 1, 19 conceitos / 21 relações / 5 blocos, integridade
  `ok: true`; legado intacto nos mesmos 589 bytes; apenas o checkpoint existe em
  `memoria/backups/`. Nada desta rodada alterou esse conteúdo (as correções
  estão no worktree; a instalação viva ainda precisa da integração).

### 7. Importar não chama modelo nem escreve

- **Problema e causa-raiz.** `ciclo_cristalizacao.py` executava o ciclo
  completo (chamadas ao Qwen, leitura e gravação de memória, impressão) no topo
  do módulo; `cristalizacao.py` e `experiencia_qwen.py` faziam
  `import ollama` no topo, o que quebrava qualquer import no ambiente sem o
  pacote.
- **Correção.** A guarda `def main()` + `if __name__ == "__main__"` veio da
  PR #240 (commit `8f69201`) e foi preservada. `ollama` agora é importado
  dentro de `gerar_candidato`, `verificar_requisito`, `cristalizar`,
  `reconstruir` e `interpretar`.
- **Testes.** `test_import_dos_consumidores_nao_inicia_modelo_nem_escreve`
  importa os quatro consumidores em processo separado, com um **stub** de
  `ollama` que levanta `AssertionError` ao ser chamado, e exige: nenhuma saída
  além do marcador, nenhum arquivo criado no caminho configurado, e que o
  modelo só seja tocado quando a função é invocada.
  `test_ciclo_cristalizacao_import.py` cobre o mesmo contrato na raiz e está
  na matriz.

### 9. Cristalização no CI

A suíte `testes/teste_persistencia_cristal.py` entrou em
`.github/matriz-validacao-raiz.txt` (88 entradas) e o workflow passou a ser
disparado também por mudanças em `testes/**/*.py` e nos cinco módulos do
subsistema. Ela roda com o `python3` do runner, sem `ollama` e sem escrever no
checkout — os mesmos dois critérios do inventário original. Evidência local:
`executados=88 falhas=0`.

Evidência do runner (job `matriz-raiz`, run `40738936479`): as 87 entradas da
raiz passaram, e a nova falhou antes de executar porque o passo de log montava
`$RUNNER_TEMP/matriz-raiz/$teste.log` — caminho com barra para entrada em
subdiretório. O passo agora achata `/` em `_` no nome do log, e a mesma matriz
roda localmente com `executados=88 falhas=0`.

---

## Item 8 — parcial, com evidência do que falta

- **Feito.** A **política de aceitação** saiu do `if` embutido no `main()` e
  virou função pura e testável:
  `ciclo_cristalizacao.candidato_aceitavel(fidelidade_atual, tamanho_atual,
  fidelidade_candidato, tamanho_candidato)` — aceita somente candidato com
  fidelidade **não inferior** e tamanho **menor**. `salvar_cristal` recusa
  candidato que não seja objeto JSON não vazio, e o caminho do ciclo é
  independente do cwd. Nada é gravado sem a política ser satisfeita.
- **Testes.** `test_politica_de_aceitacao_do_candidato` (tabela verdade:
  fiel-e-menor aceita; menor-menos-fiel rejeita; sem-redução rejeita;
  candidato inválido não sobrescreve; JSON truncado vai para quarentena e
  devolve o estado inicial sem mutar a constante do módulo) e, para o cristal
  semântico, `test_schema_invalido_do_cristal_json_preserva_arquivo`
  (`cristalizacao.validar_cristal_semantico` + `adicionar_conceito`, que recusa
  sobrescrever conceito existente sem `substituir=True`).
- **Falta (por isso é parcial).** A **medição** de fidelidade
  (`medir_fidelidade` → 14 requisitos julgados pelo modelo) continua
  dependente do `qwen2:7b` local e não tem como ser reproduzida no CI nem em
  teste determinístico. Enquanto isso, o número que alimenta a política não é
  verificável independentemente; só a decisão que o consome é.

## Item 10 — em aberto

Nenhum registro de proveniência por escrita: não se sabe qual processo gravou
qual tripla, quando, nem com base em qual evidência. O subsistema de atuação já
usa `auditoria_atuacao_nyxos.jsonl` como padrão; o cristal ainda não. Exige
decisão de formato (registro no próprio log append-only ou arquivo lateral) e
política de retenção. Não foi implementado nem testado nesta rodada.

---

## Especificação do formato binário

Cabeçalho: `NXCM` + 1 byte de versão. A partir dele, a largura dos campos
inteiros é 1 byte na versão 1 e 2 bytes little-endian na versão 2.

Registros, na ordem do log:

| Tipo | Conteúdo |
| --- | --- |
| 1 — conceito | `largura(nome)` + nome UTF-8 |
| 2 — relação | `largura(nome)` + nome UTF-8 |
| 3 — bloco | `largura(quantidade)` + `quantidade × (sujeito, relação, objeto)` |

Contratos: v1 legível indefinidamente; append preserva a base inteira; o mesmo
byte pode aparecer em posições diferentes do log (por isso a validação é
estrutural e semântica, nunca byte a byte); capacidade anunciada pelo formato
(`limite_de(largura)`), sem truncamento silencioso.

## Recuperação

Ordem de preferência quando o autoritativo está ilegível:
checkpoint → backups do mais novo ao mais velho → cristal novo. Cada candidato
é validado antes de virar estado ativo; o arquivo ruim é movido para
quarentena. Recuperar nunca deleta origem.

## Pendências registradas

1. Mediação de fidelidade automatizada (item 8) — bloqueada por dependência de
   modelo local.
2. Observabilidade por escrita (item 10).
3. Decisão sobre o legado `experimentos/cristal_gerenciador.bin` (remover ou
   manter) e sobre unificar as linhagens binária/JSON.
4. Lock interprocesso (`flock`) se a concorrência real aparecer; hoje o CAS
   recusa a sobrescrita mas não serializa.
5. `avaliar_cristal.py`, `testar_cristal.py`, `otimizar_cristal.py` seguem
   fora do CI por exigirem `ollama`; não foram executados nesta rodada.
6. Deploy na instalação viva (`/home/nyxal/Nyxal`) exige autorização humana
   explícita: é a instalação em uso pelos serviços do NyxOS.
