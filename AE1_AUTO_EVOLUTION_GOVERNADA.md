# AE1 — Auto-Evolution Governada da Nyxal

## Posição arquitetural

AE1 é a primeira camada após o Habitat M5. Ela fica acima do ciclo residente e abaixo da governança N9.

```
Habitat M5
   ↓
Ciclo residente
   ↓
AE1 — descoberta/preparação de evolução
   ↓
N9 — evolução controlada
   ↓
autorização explícita
   ↓
integração
```

## Responsabilidade

A primeira versão da auto-evolution pode:

1. observar resultados de ciclos residentes;
2. identificar limitações/necessidades candidatas a melhoria;
3. associar uma hipótese provisória já produzida pelo ciclo;
4. registrar uma oportunidade de evolução;
5. preparar uma solicitação formal quando houver dados suficientes;
6. manter a solicitação fora de `main`.

## Não permitido em AE1

- alterar `main`;
- executar código candidato fora do isolamento previsto no N9;
- autorizar integração;
- fazer merge;
- promover conhecimento automaticamente para verdade permanente;
- substituir os gates de governança;
- modificar arquitetura diretamente;
- disparar evolução remota sem a política/gate correspondente.

## Princípio

A auto-evolution ganha autonomia primeiro na **descoberta e preparação**, não na autoridade final.

Assim:

```
autonomia crescente
       ≠
autoridade irrestrita
```

A função final da auto-evolution deverá reutilizar `EvolucaoControladaNixal`, `SolicitacaoEvolucaoNixal`, laboratório remoto, candidatos e Governança de Evolução já existentes.

## Etapas futuras

- AE1: descobrir e preparar;
- AE2: executar experimento isolado sob política;
- AE3: comparar e aprender automaticamente;
- AE4: ciclo residente de evolução;
- AE5: descoberta contínua com governança.

A autorização explícita para integração continua sendo a barreira entre uma evolução candidata e uma alteração estável.
