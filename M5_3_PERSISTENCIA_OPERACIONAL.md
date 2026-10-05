# M5.3 — Persistência Operacional do NyxOS

## Objetivo

Garantir continuidade do habitat entre reinicializações sem transformar persistência operacional em conhecimento permanente.

O M5.3 cria uma única camada de persistência operacional do NyxOS que registra:

- identidade da versão da persistência;
- número de inicializações observadas;
- última observação do habitat;
- referência ao último ciclo do Runtime;
- estado resumido da última operação;
- histórico curto e limitado de persistências.

Fluxo:

```
Runtime / Habitat
      ↓
persistência operacional
      ↓
arquivo local atômico
      ↓
reinicialização
      ↓
restauração do contexto operacional
```

## Garantias

- escrita atômica;
- histórico limitado;
- restauração tolerante a arquivo ausente;
- arquivo corrompido não derruba a inicialização;
- somente estado operacional é persistido;
- nenhuma mensagem conversacional é persistida por esta camada;
- nenhum conhecimento é promovido;
- nenhuma arquitetura é modificada;
- nenhum comando externo é executado;
- nenhuma dependência nova é instalada;
- nenhum controle de processo ou hardware é permitido.

## Contrato

O arquivo possui, no mínimo:

```json
{
  "versao": "5.3.0",
  "origem": "persistencia_operacional_nyxos",
  "inicializacoes": 0,
  "ultima_persistencia": null,
  "ultimo_ciclo": null,
  "ultimo_habitat": null,
  "historico": []
}
```

O histórico guarda no máximo 50 entradas resumidas.

## Critério de conclusão

M5.3 é implementado quando:

1. o estado operacional sobrevive ao reinício;
2. a restauração é determinística e tolerante;
3. a escrita é atômica;
4. o histórico possui limite;
5. Runtime e API conseguem consultar a continuidade persistida;
6. conversação, conhecimento e arquitetura permanecem fora desta camada;
7. testes M5 e regressão N9/N10 passam.
