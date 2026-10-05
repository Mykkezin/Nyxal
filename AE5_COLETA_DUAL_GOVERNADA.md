# AE5 — COLETA DUAL GOVERNADA DE DATASETS

## Finalidade

A coleta dual é uma extensão de observabilidade da AE5. Ela não cria uma
segunda engine de evolução e não concede autoridade de treinamento.

Uma mesma transição operacional pode alimentar dois ativos futuros:

1. dataset cognitivo, destinado a avaliação e eventual fine-tuning de um
   modelo da família Qwen-Nyxal;
2. dataset sistêmico, destinado a avaliação e eventual treinamento de um
   modelo especializado em transições do sistema, para uso futuro no Nyx
   Kernel.

## Separação de responsabilidades

AE5 econômica:
- descobre e acompanha valor econômico;
- preserva evidências;
- mantém os gates de governança.

Coletor dual:
- serializa observações já produzidas;
- mantém provenance;
- evita duplicação recente;
- não interpreta uma ação como recomendação de treinamento;
- não executa treinamento.

Laboratório futuro:
- avalia qualidade;
- treina modelos apenas mediante gate próprio;
- registra resultados fora do ciclo residente.

## Dataset Qwen

O dataset utiliza transições:

estado anterior + causa observada
→ estado novo + aprendizado observado

O campo causalidade_comprovada permanece false até existir evidência formal
no Learning Loop capaz de sustentar essa causalidade.

No estado atual do Runtime, não existe memória conversacional dentro do ciclo
operacional. Portanto, a primeira geração do dataset usa contexto operacional
estruturado: necessidade, decisão, resultado, Delta e aprendizado. Conversa só
poderá entrar por contrato explícito posterior.

## Dataset Kernel

O dataset utiliza transições observadas:

estado sistêmico anterior
→ ação observada + Delta seguinte

A entrada contém:
- CPU;
- RAM;
- top 5 processos;
- último Delta observado.

A saída contém:
- delta_id observado;
- acao_ciclo observada.

O campo acao_autorizada descreve somente a política que já autorizou a ação
observada. treinamento_autorizado é sempre false.

O coletor não escreve uma ação recomendada para o futuro.

## Persistência

Os datasets ficam fora da árvore Git:

Nyxal-datasets/qwen-dataset.jsonl
Nyxal-datasets/kernel-dataset.jsonl

O cursor de emparelhamento e o índice de fingerprints ficam em JSON com
substituição atômica.

Cada registro JSONL é escrito por uma única operação append com O_APPEND,
seguida de fsync.

## Limites

- 1 transição por dataset por ciclo de residência;
- deduplicação exata por fingerprint dentro de 24 horas;
- máximo de 50.000 registros por dataset;
- cursor mantém somente o último ponto necessário para formar a próxima
  transição;
- auditoria registra gravações, duplicações e bloqueios.

Esses limites são limites de coleta. Eles não substituem os limites da AE5
econômica, que continuam governando descobertas de valor.

## Treinamento

O ciclo residente nunca treina automaticamente.

Não existe nesta camada:
- subprocess;
- Popen;
- shell;
- chamada de laboratório;
- fine-tuning;
- compilação de modelo;
- implantação;
- alteração de main;
- autorização implícita.

O caminho futuro é:

coleta
→ avaliação do dataset
→ proposta de treinamento
→ laboratório remoto
→ avaliação do modelo
→ autorização explícita
→ implantação controlada

## Observabilidade

A API autenticada expõe:

GET /api/ae5/datasets

O endpoint informa contagens, estado da coleta e invariantes. O conteúdo dos
datasets permanece fora da API.

## Estado

Contrato de coleta dual: implementado.

Treinamento Qwen-Nyxal: não implementado.

Treinamento de modelo para Nyx Kernel: não implementado.

Integração do modelo ao kernel: não implementada.

Regra:

**Dois datasets não significam dois agentes com autoridade.**
