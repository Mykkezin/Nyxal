# LLC.6 — Integridade de Proveniência da Evidência

## Estado
Proposta arquitetural — não implementada.

A LLC.5 já prova uma propriedade mais forte sobre o conteúdo fornecido:
- pelo menos 3 ciclos distintos;
- mesma ação esperada;
- mesma métrica;
- controle válido;
- ordem temporal;
- influência decisória comprovada;
- consistência direcional.

A revisão do código da LLC.5 identificou uma lacuna anterior à causalidade: o avaliador recebe observações em dicionários e valida campos declarativos, mas não verifica de forma suficiente que cada observação é realmente derivada de uma observação produzida pelo LLC.4.

Isso permite que uma estrutura sintética declare:
`evidencia_ambiental_observacional = true`
sem que a proveniência completa da observação seja verificável.

A próxima propriedade arquitetural proposta é, portanto:

> **Toda evidência usada pelo protocolo causal longitudinal deve possuir uma cadeia de proveniência verificável desde um artefato observacional do LLC.4 até a transição e o ciclo LLC que a utilizaram.**

## O que essa propriedade NÃO prova

Ela não prova causalidade.

A separação permanece:

```
proveniência íntegra
        ↓
evidência observacional autêntica
        ↓
protocolo longitudinal
        ↓
evidência causal dentro do desenho
```

Também não autoriza:
- integração;
- alteração de stable;
- treinamento;
- autoalteração;
- execução arbitrária;
- implantação automática.

## Gates propostos

A futura implementação deverá rejeitar a evidência se qualquer gate falhar.

### Gate 1 — origem LLC.4

A observação deve declarar uma origem/versionamento compatível com o produtor observacional do LLC.4.

Campos esperados:
- `origem`;
- `versao`;
- `modo`.

A observação deve continuar em modo somente leitura.

### Gate 2 — identidade da observação

O identificador da observação deve ser verificável.

O LLC.4 já produz um `id` determinístico a partir de:
- `snapshot_id`;
- caminho da métrica;
- valor;
- timestamp.

A próxima camada deve recomputar essa identidade e rejeitar divergência.

### Gate 3 — identidade do snapshot

`snapshot_id` deve existir e ser referenciável por um artefato observacional verificável.

Não basta aceitar uma string arbitrária.

A verificação deve permitir demonstrar:

```
snapshot observado
      ↓ hash determinístico
snapshot_id declarado
```

### Gate 4 — cadeia de proveniência

A evidência deve manter a cadeia:

```
snapshot_id
    ↓
observacao_id
    ↓
transicao_id
    ↓
ciclo_id
```

Nenhum elo pode ser criado apenas por inferência posterior.

### Gate 5 — integridade temporal

Timestamps devem ser interpretados como instantes temporais válidos, preferencialmente normalizados para UTC.

A comparação não deve depender somente de comparação lexical de strings.

A relação temporal necessária deve ser explicitamente verificável.

### Gate 6 — identidade da métrica

A métrica usada na observação deve corresponder exatamente à métrica declarada pelo protocolo:
- nome;
- caminho;
- unidade;
- direção;
- fonte.

### Gate 7 — causalidade não pré-existente

Uma observação de entrada não pode chegar ao protocolo já marcada como causalidade comprovada.

A conclusão causal deve continuar sendo produzida somente pelo gate longitudinal.

## Resultado esperado

Quando todos os gates de proveniência passam:

```
proveniencia_evidencia_valida = true
```

Quando qualquer gate falha:

```
proveniencia_evidencia_valida = false
```

e a evidência não pode ser usada para elevar `causalidade_ambiental_comprovada`.

## Testes mínimos

A implementação futura deverá provar pelo menos:

1. observação LLC.4 válida aceita;
2. `id` adulterado rejeitado;
3. `snapshot_id` adulterado rejeitado;
4. versão/origem incompatível rejeitada;
5. modo diferente de somente leitura rejeitado;
6. timestamp inválido rejeitado;
7. timestamp inconsistente rejeitado;
8. métrica divergente rejeitada;
9. cadeia `snapshot → observação → transição → ciclo` íntegra aceita;
10. cadeia quebrada rejeitada;
11. causalidade pré-existente rejeitada;
12. invariantes de governança preservadas.

## Limite arquitetural

Esta proposta não adiciona coleta automática ao Runtime.

A captura continua explícita e somente leitura.

A propriedade a provar é **integridade e rastreabilidade da evidência**, não autonomia causal.

## Governança

```
autorizacao_explicita = false
integracao_executada = false
stable_modificada = false
arquitetura_modificada = false
conhecimento_permanente = false
execucao_local = false
treinamento_automatico = false
implantacao_automatica = false
causalidade_ambiental_comprovada = false
```

A proposta não altera `main`.

## Critério de avanço

A implementação só deve começar depois de transformar cada gate acima em comportamento observável e teste determinístico.

Nenhuma integração no Runtime será feita apenas para demonstrar a feature.

O objetivo é tornar a evidência causal do LLC.5 **auditável até sua origem**, antes de aumentar a autonomia do sistema.
