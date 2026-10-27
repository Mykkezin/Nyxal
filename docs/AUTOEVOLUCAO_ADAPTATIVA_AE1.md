# Autoevolução adaptativa governada — AE1

## Objetivo

Permitir que a Nyxal identifique oportunidades de melhoria a partir das necessidades priorizadas pelo diagnóstico residente, mesmo quando o ciclo de alta frequência adia a investigação profunda.

## Fluxo

1. O Runtime produz necessidades com origem, problema, tipo, prioridade e motivo.
2. A AE1 reutiliza a necessidade selecionada para formular uma hipótese **provisória**, explicitamente marcada como gerada a partir de observação.
3. Falhas de ciclo observadas podem virar propostas de investigação de alta prioridade. O sistema registra o erro observado, mas não declara sua causa raiz.
4. A mesma necessidade recorrente atualiza a oportunidade existente e agrega ciclos observados, em vez de criar um arquivo por ciclo.
5. A oportunidade fica disponível para avaliação e preparação formal pelas etapas governadas que já existem.

## Limites de autoridade

- Hipóteses geradas automaticamente são propostas, não fatos confirmados.
- Sem necessidade observada ou falha real registrada, a AE1 não inventa uma oportunidade.
- A AE1 não gera nem executa código, não abre shell, não altera a arquitetura ou a branch estável, não faz merge nem implanta mudanças.
- Experimentos continuam sujeitos à AE2 e às solicitações formais existentes; avaliação continua com AE3.
- Os registros de recorrência mantêm os últimos 20 ciclos como evidência limitada, enquanto a retenção total de oportunidades permanece limitada a 200 arquivos.

## Persistência

As oportunidades são gravadas no diretório existente `Nyxal-evolution-opportunities`. Cada oportunidade contém a origem, prioridade, hipótese provisória, ciclos observados e estado de governança. Antes da persistência, os campos da necessidade observada passam por uma lista de permissões e limites de tamanho; campos extras do Runtime não são copiados. O JSON é escrito num temporário exclusivo com permissões restritas, sincronizado e substituído atomicamente para evitar que leitores vejam um arquivo parcial. Isso não concede autorização de integração nem substitui os gates AE2/AE3. A implementação reaproveita a AE1 existente; não introduz outro sistema de memória.
