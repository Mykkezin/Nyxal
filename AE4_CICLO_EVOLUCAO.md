# AE4 — Ciclo Residente de Evolução

## Posição arquitetural

```
Habitat M5
   ↓
Ciclo residente
   ↓
AE1 — descoberta
   ↓
AE2 — experimento isolado sob política
   ↓
AE3 — comparação + aprendizagem
   ↓
AE4 — orquestração e auditoria do ciclo de evolução
   ↓
proposta / autorização explícita
   ↓
integração
```

## Responsabilidade

AE4 transforma AE1, AE2 e AE3 em uma passagem residente explícita e observável.

Em cada ciclo, ela:

1. executa a descoberta AE1;
2. chama a política AE2 já existente;
3. avalia o experimento com AE3 quando houver experimento;
4. registra um resumo auditável das três etapas;
5. expõe o estado final sem conceder autoridade de integração.

## Vínculo entre etapas

AE2 atualmente consome solicitações formais pendentes do repositório global.
Por isso, AE4 não presume que a solicitação processada por AE2 tenha sido causada
pela oportunidade produzida por AE1 no mesmo ciclo.

O registro usa vínculo **observacional** até existir um identificador explícito
persistido ligando oportunidade e solicitação.

Isso evita inventar causalidade a partir de coincidência temporal.

## Persistência

Os resumos são persistidos fora da árvore Git em:

`Nyxal-evolution-ae4/ae4-ciclo-<id>.json`

A identidade do registro é determinística por `ciclo_id`, com escrita atômica
e retenção máxima de 200 auditorias.

## Falhas e limites

- AE4 não faz retry automático.
- AE2 continua limitada a um experimento por ciclo.
- Uma falha de AE1/AE2/AE3 fica registrada sem liberar autoridade extra.
- A saída AE3 continua sendo evidência/candidato/proposta; nunca autorização.
- AE4 não executa código localmente e não modifica `main`/stable.

## Invariantes

```
autorizacao_explicita      = false
integracao_executada       = false
stable_modificada          = false
arquitetura_modificada     = false
conhecimento_permanente    = false
```

## Estado

AE4 é uma camada de **orquestração**, não uma nova engine de evolução.
Ela reutiliza os mecanismos já validados e torna o ciclo AE1→AE2→AE3 auditável.

Após a auditoria, a AE5 pode consumir somente esse resultado para acumular sinais
repetidos, sem executar novamente AE1, AE2 ou AE3.
