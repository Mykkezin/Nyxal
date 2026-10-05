# AE3 — Comparação e Aprendizagem Automática

## Posição arquitetural

```
AE1 — descoberta
   ↓
AE2 — experimento isolado
   ↓
AE3 — comparação + aprendizagem
   ↓
proposta
   ↓
autorização explícita
   ↓
integração
```

## Responsabilidade

AE3 recebe somente o resultado já produzido pelo AE2/N9.

Ela valida que:

- existe comparação formal com baseline;
- a decisão da comparação é booleana;
- o aprendizado persistente foi registrado;
- a evidência pode ser classificada como melhoria, rejeição ou inconclusiva.

A camada apenas interpreta o resultado. A comparação matemática e o registro do aprendizado
continuam sendo responsabilidade do `EvolucaoControladaNixal` e do
`AprendizadoPersistenteNixal`, já existentes.

## Classificação

### melhoria_comprovada

O resultado experimental supera o baseline segundo a direção da métrica
e o aprendizado foi efetivamente registrado.

### evolucao_rejeitada

O experimento terminou, a comparação existe, mas o resultado não supera o baseline.
O aprendizado da avaliação ainda é preservado como evidência.

### resultado_inconclusivo

A resposta não possui comparação válida ou não confirma o registro do aprendizado.

## Invariantes

```
execucao_local             = false
autorizacao_explicita      = false
integracao_executada       = false
stable_modificada          = false
arquitetura_modificada     = false
conhecimento_permanente    = false
```

AE3 não cria uma segunda memória semântica. Ela reutiliza o aprendizado persistente já
existente e devolve um resumo auditável ao ciclo residente.

## Fluxo

```
AE2
 ↓
resultado N9
 ↓
comparação existente
 ↓
aprendizado existente
 ↓
AE3 classifica
 ↓
ciclo residente observa
```

AE3 fecha automaticamente a etapa de avaliação sem transformar uma melhoria observada
em autorização de integração.
