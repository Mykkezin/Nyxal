# LLC.6 — Integridade de Proveniência da Evidência

## Estado atual
**Implementação inicial concluída na branch feat/llc-evidence-provenance; CI pendente de confirmação.**

A LLC.5 já prova uma propriedade mais forte sobre o conteúdo fornecido:
- pelo menos 3 ciclos distintos;
- mesma ação esperada;
- mesma métrica;
- controle válido;
- ordem temporal;
- influência decisória comprovada;
- consistência direcional.

A revisão do código da LLC.5 identificou uma lacuna anterior à causalidade: o avaliador recebe observações em dicionários e valida campos declarativos, mas não verificava de forma suficiente que cada observação era realmente derivada de uma observação produzida pelo LLC.4.

A LLC.6 implementa a propriedade:

> **Toda evidência usada pelo protocolo causal longitudinal deve possuir uma cadeia de proveniência verificável desde um artefato observacional do LLC.4 até a transição e o ciclo LLC que a utilizaram.**

## Implementação

O componente ProvenienciaEvidenciaLLC verifica:

1. origem e versão esperadas do LLC.4;
2. modo somente leitura;
3. identidade determinística do snapshot;
4. identidade determinística da observação;
5. correspondência entre snapshot e observação;
6. timestamp válido e consistente;
7. identidade completa da métrica;
8. transicao_id e ciclo_id;
9. ausência de causalidade pré-existente.

Quando todos os gates passam, proveniencia_evidencia_valida = true.
Quando qualquer gate falha, proveniencia_evidencia_valida = false.

## Relação com LLC.5

A LLC.6 não substitui o LLC.5.

    LLC.4
    evidência observacional
            ↓
    LLC.6
    proveniência verificável
            ↓
    LLC.5
    evidência causal longitudinal

A proveniência íntegra não é causalidade.

## Testes implementados

O teste dedicado cobre:
- observação LLC.4 válida;
- adulteração do id da observação;
- adulteração do snapshot_id por alteração do snapshot;
- origem incompatível;
- modo diferente de somente leitura;
- timestamp inválido;
- métrica divergente;
- cadeia snapshot → observação → transição → ciclo;
- causalidade pré-existente;
- ausência de execução externa;
- invariantes de governança.

## CI

Foi criado o workflow .github/workflows/llc6-proveniencia-validation.yml.

O workflow compila e executa LLC.4, LLC.5 e LLC.6.

O fechamento da implementação depende do runner do GitHub confirmar o novo workflow como verde.

## Limite arquitetural

A LLC.6 não adiciona:
- coleta automática;
- execução de ações;
- treinamento automático;
- autoalteração;
- integração automática;
- alteração de main;
- conhecimento permanente.

## Governança

    autorizacao_explicita = false
    integracao_executada = false
    stable_modificada = false
    arquitetura_modificada = false
    conhecimento_permanente = false
    execucao_local = false
    treinamento_automatico = false
    implantacao_automatica = false
    causalidade_ambiental_comprovada = false

## Critério de avanço

A LLC.6 só será considerada fechada depois de:

    implementação
        ↓
    testes determinísticos
        ↓
    CI verde
        ↓
    checkpoint

Nenhuma nova camada será criada antes desse fechamento.
