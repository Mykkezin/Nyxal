# AE2 — Experimento Isolado Automático sob Política

## Posição arquitetural

AE2 é a segunda camada de auto-evolution depois da descoberta AE1.

```
Habitat M5
   ↓
Ciclo residente
   ↓
AE1 — descoberta/preparação
   ↓
AE2 — execução experimental isolada sob política
   ↓
N9 — evolução controlada
   ↓
proposta
   ↓
autorização explícita
   ↓
integração
```

## Responsabilidade

AE2 automatiza somente a passagem de uma solicitação formal **já pronta para experimento**
para o caminho de evolução remota já governado pela Nyxal.

A política exige:

- solicitação no estado `pronta_para_experimento`;
- artefato Python existente;
- hipótese ainda provisória;
- `execucao_local == false`;
- `autorizacao_explicita == false`;
- `integracao_executada == false`;
- `stable_modificada == false`;
- objetivo, métrica, direção e baseline válidos.

Por ciclo residente, no máximo uma solicitação é processada.

## O que AE2 não faz

- não gera código;
- não executa código localmente;
- não cria autorização;
- não faz merge;
- não modifica `main`/stable;
- não promove conhecimento permanente;
- não altera arquitetura;
- não repete automaticamente uma solicitação que falhou;
- não substitui os gates do N9.

## Política de ativação

A classe AE2 nasce com execução automática **desabilitada**.

A ativação é deliberada pelo launcher através de `--habilitar-auto-experimento`.
Assim, instalar a camada não significa liberar execução remota involuntária.

Quando habilitado:

```
ciclo residente
  ↓
AE1 observa
  ↓
AE2 procura solicitação pronta
  ↓
valida gates
  ↓
Runtime.executar_solicitacao_evolucao_remota()
  ↓
Laboratório remoto
  ↓
resultado
  ↓
solicitação persistida
  ↓
candidato/proposta, se aprovado
  ↓
autorização continua falsa
```

## Falha e retry

Uma solicitação em `pronta_para_experimento` é selecionada deterministicamente pela data de criação
e pelo identificador. Depois que o caminho N9 inicia o experimento, o estado deixa de ser pendente.

Falhas remotas são registradas pela camada existente como evidência de `experimento_falhou`.
AE2 não executa retry automático.

## Natureza do isolamento

AE2 reutiliza o laboratório remoto já existente. Esse laboratório publica uma branch
`experimento/*`, executa o experimento no runner confiável e retorna `result.json`/logs.
Ele não deve ser tratado como sandbox de segurança absoluta; o contrato continua sem secrets,
sem permissões de escrita na stable e sem autorização de integração.

## Invariantes

```
execucao_local             = false
autorizacao_explicita      = false
integracao_executada       = false
stable_modificada          = false
arquitetura_modificada     = false
conhecimento_permanente    = false
```

AE2 aumenta autonomia operacional sem aumentar a autoridade de integração.
