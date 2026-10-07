# Checkpoint pós-M5.23

## Estado

M5.23 — adaptadores de voz STT/TTS — integrado ao `main`.

## Integração

- PR #34: mergeado.
- Merge commit: `195b1186a19e3be058b55e57c827e29461a91704`.
- Base: `main`.
- Adaptador STT: `faster-whisper`.
- Adaptador TTS: `Kokoro`.
- Contrato preservado: `VozNyxOS` recebe callables STT/TTS.
- Dependências externas permanecem na borda.
- Injeção de dependência permanece disponível para validação determinística.

## Governança

- Voz automática permanece desabilitada.
- Execução física automática não foi habilitada.
- Nenhuma autoridade de evolução foi concedida.
- Nenhum M6 é criado automaticamente.
- O checkpoint M5.22 permanece histórico e não é alterado retroativamente.

## Validação

O HEAD do PR #34 (`e8060bd01546d3117f38c24f7bd7bd5864114da7`) teve 14/14 checks do GitHub Actions concluídos com sucesso antes do merge.

## Próxima decisão

O próximo marco deverá ser definido explicitamente antes de implementação, com objetivo, escopo, contrato, autoridade, reversibilidade, validação e documentação.
