# Checkpoint pós-M5.24

## Estado

M5.24 — voz supervisionada — integrado em `main`.

## Implementação

- PR #37: mergeado.
- Merge commit: `a5d6b12834af728c81917e7080abbc092d1e561c`.
- Operação: `VozNyxOS.executar_supervisionado(arquivo_audio)`.
- Caminho: STT explícito → texto → TTS explícito → arquivo de áudio.
- Resultado: estruturado e registrado.
- Dependências externas: permanecem na borda.

## Governança

- Voz automática: desabilitada.
- Execução automática: desabilitada.
- Execução física: desabilitada.
- Captura contínua: não habilitada.
- Wake word: não habilitado.
- Reprodução física automática: não habilitada.
- Autoridade de evolução: não concedida.
- Nenhum M6 foi criado.
- Nenhuma AE6 foi criada.

## Validação

O HEAD do PR #37 (`74d03be96d8084651139b37dce8918ecbf69c615`) teve 14/14 checks do GitHub Actions concluídos com sucesso antes do merge.

O teste dedicado `teste_m5_24_voz_supervisionada.py` valida:

- caminho STT → TTS;
- rejeição de entrada vazia;
- ausência de STT;
- ausência de TTS;
- preservação das invariantes de voz automática.

## Estado arquitetural

M5.23 permanece integrado.
M5.24 fecha a operação supervisionada de voz sem conceder autoridade automática.

A cadeia LLC.1 → LLC.10 permanece separada da autorização de evolução.

## Próxima decisão

O próximo marco deve ser definido por revisão arquitetural pós-M5.24, considerando estado real do Runtime, Habitat, LLC, evidências operacionais e lacunas restantes.

Nenhum M6 ou AE6 é criado automaticamente por este checkpoint.
