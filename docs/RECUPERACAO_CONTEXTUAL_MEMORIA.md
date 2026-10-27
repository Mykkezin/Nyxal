# Recuperação contextual da memória da Nyxal

## Objetivo

A Nyxal combina fontes persistentes que já existem no projeto para dar continuidade a perguntas sobre investigações e conhecimento candidato. Esta camada não introduz um banco vetorial paralelo e não altera as fontes de memória.

## Fontes consultadas

- **Memória de investigação** (MemoriaInvestigacaoNixal): ciclos com necessidade, pergunta, hipótese, estado, testes, avaliações e proveniência.
- **Contexto histórico relevante** (ContextoHistoricoRelevanteNixal): pesquisa lexical local de investigações relevantes, com status epistemológico.
- **Memória de conhecimento candidato** (MemoriaConhecimentoNixal): candidatos originados de avaliações suportadas, ainda explicitamente não permanentes.

RecuperadorContextoNixal coordena as consultas e retorna os resultados separados por fonte, incluindo estado da consulta, relevância lexical e proveniência permitida.

## Seleção e segurança

- Busca lexical local ponderada, com limites de consulta e número de resultados. É uma baseline mensurável; não afirma ser busca semântica vetorial.
- Candidatos precisam ter origem suportada, texto e tipo válidos e permanecer marcados como não permanentes.
- Itens sem sobreposição lexical suficiente são omitidos; textos duplicados são deduplicados, e candidatos quase idênticos a uma investigação recuperada são excluídos.
- O recuperador é somente leitura: não promove conhecimento, não escreve nos arquivos consultados, não executa ferramentas e não modifica a arquitetura.
- Se um arquivo de memória estiver corrompido, a fonte é marcada como degradada, não se converte silenciosamente em memória gravável e o arquivo original é preservado.
- O núcleo injeta apenas resumos limitados, com segredos redigidos e campos permitidos. O contexto é explicitamente rotulado como dado histórico/candidato não confiável, nunca como instrução ou prova do estado atual.
- A resposta estruturada informa o estado e os IDs consultados, mantendo conhecimento_permanente=false.

## Por que não ChromaDB agora?

Antes de adicionar embeddings, é melhor medir a qualidade da recuperação sobre os registros existentes: precisão dos resultados, omissões, duplicação, latência e tamanho do contexto. O armazenamento atual mantém a proveniência e os estados epistemológicos. Um banco vetorial adicional só deve ser considerado se uma avaliação reproduzível demonstrar que a busca lexical é insuficiente.

## Validação

A suíte teste_nixal_recuperador_contexto.py cobre recuperação relevante, exclusão de candidatos sem relevância, deduplicação, remoção de candidatos já representados no histórico e preservação de arquivos corrompidos. teste_nucleo_contexto_persistente.py valida a passagem de contexto ao diálogo sem iniciar um modelo real.
