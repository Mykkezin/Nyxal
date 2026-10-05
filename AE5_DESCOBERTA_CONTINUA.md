# AE5 — Descoberta Contínua com Governança

## Posição arquitetural

```
Ciclo residente
   ↓
AE1 — descoberta por ciclo
   ↓
AE2 — experimento isolado sob política
   ↓
AE3 — comparação + aprendizagem
   ↓
AE4 — orquestração e auditoria
   ↓
AE5 — acumulação contínua de evidência
   ↓
formalização externa
   ↓
N9 / autorização explícita
```

## Responsabilidade

AE5 não substitui a AE1.

A AE1 continua detectando e registrando oportunidades por ciclo.
A AE5 transforma observações repetidas em uma linha de evidência contínua,
agrupada por limitação + hipótese normalizadas.

Uma linha só é classificada como "madura_para_formalizacao" quando a política
configurada é atingida.

Política padrão:

- pelo menos 3 observações em ciclos distintos;
- pelo menos 2 ciclos observados com sucesso.

Os limiares são configuráveis no construtor e ficam registrados na linha.

## O que AE5 não faz

- não gera código;
- não inventa objetivo;
- não escolhe métrica;
- não fabrica baseline;
- não cria artefato experimental;
- não cria solicitação formal automaticamente;
- não executa experimento;
- não autoriza integração;
- não modifica main/stable;
- não promove conhecimento permanente.

Quando madura, a linha apenas informa que é hora de coletar os campos formais
necessários para uma solicitação N9.

## Persistência

As linhas ficam fora da árvore Git em:

Nyxal-evolution-discovery/linha-<id>.json

A identidade é determinística a partir da limitação e da hipótese normalizadas.
A escrita é atômica e a retenção máxima é de 200 linhas.

## Invariantes

```
autorizacao_explicita      = false
integracao_executada       = false
stable_modificada          = false
arquitetura_modificada     = false
conhecimento_permanente    = false
```

AE5 aumenta a continuidade da observação sem aumentar a autoridade da evolução.
