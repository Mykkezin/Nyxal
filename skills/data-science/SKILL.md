# Habilidade Nyxal: Data Science

## Objetivo

Transformar dados em conclusões úteis, com métodos reproduzíveis, rastreabilidade e honestidade estatística. Reutilizar ferramentas Python, dados e observabilidade existentes; não inventar dados nem criar pipelines paralelos sem necessidade.

## Fluxo de trabalho

1. Especificar a pergunta de negócio/científica, a população, o período, a unidade de análise e a decisão que será apoiada.
2. Verificar origem, esquema, tipos, granularidade, valores ausentes, duplicatas, outliers, qualidade, viés e permissões de uso.
3. Elaborar análise exploratória e estabelecer uma linha de base antes de escolher modelos.
4. Selecionar métodos estatísticos ou modelos compatíveis com a pergunta, considerando pressupostos, amostragem, confusão, vazamento de dados e validade externa.
5. Construir um pipeline Python reproduzível com dependências declaradas, sementes quando aplicável, divisão de dados adequada e métricas relevantes.
6. Comparar alternativas com baseline e conjunto de validação; quantificar incerteza e fazer análise de erros.
7. Apresentar gráficos legíveis, explicação dos resultados, limitações e próximos experimentos sugeridos.

## Guardrails

- Preservar privacidade, minimizar dados pessoais e não enviar dados sensíveis a provedores externos sem autorização.
- Não afirmar causalidade a partir de correlação ou de uma análise observacional simples.
- Não fabricar valores, métricas, amostras, citações ou resultados de experimentos.
- Evitar leakage entre treino e teste e declarar as escolhas que possam distorcer a avaliação.
- Distinguir resultado computado, hipótese interpretativa e recomendação.
- Manter código, parâmetros e etapas de transformação rastreáveis para permitir reprodução.

## Critérios de conclusão

Toda análise deve incluir pergunta, fonte e período dos dados, verificações de qualidade, método, baseline, métricas, incerteza, limitações e código ou passos reproduzíveis. Se os dados não sustentarem uma conclusão, reportar isso claramente.
