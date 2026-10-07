# LLC.6 — Integridade de Proveniência da Evidência

## Estado atual

**Implementação concluída e validada no CI.**

A LLC.5 prova propriedades longitudinais sobre o conteúdo fornecido. A LLC.6 acrescenta a garantia de que a evidência utilizada pelo protocolo causal possui uma cadeia de proveniência verificável desde um artefato observacional do LLC.4 até a transição e o ciclo LLC que a utilizaram.

## Propriedade

> **Toda evidência usada pelo protocolo causal longitudinal deve possuir uma cadeia de proveniência verificável desde um artefato observacional do LLC.4 até a transição e o ciclo LLC que a utilizaram.**

## Implementação

O componente `ProvenienciaEvidenciaLLC` verifica:

1. origem e versão esperadas do LLC.4;
2. modo somente leitura;
3. identidade determinística do snapshot;
4. identidade determinística da observação;
5. correspondência entre snapshot e observação;
6. timestamp válido e consistente;
7. identidade completa da métrica;
8. `transicao_id` e `ciclo_id`;
9. ausência de causalidade pré-existente.

Quando todos os gates passam, `proveniencia_evidencia_valida = true`.

Quando qualquer gate falha, `proveniencia_evidencia_valida = false`.

## Relação com LLC.5

A LLC.6 não substitui a LLC.5:

    LLC.4
    evidência observacional
            ↓
    LLC.6
    proveniência verificável
            ↓
    LLC.5
    evidência causal longitudinal

A proveniência íntegra não é causalidade.

## Testes

O teste dedicado cobre:

- observação LLC.4 válida;
- adulteração do id da observação;
- adulteração do snapshot_id;
- origem incompatível;
- modo diferente de somente leitura;
- timestamp inválido;
- métrica divergente;
- cadeia snapshot → observação → transição → ciclo;
- causalidade pré-existente;
- ausência de execução externa;
- invariantes de governança.

O workflow `.github/workflows/llc6-proveniencia-validation.yml` executa a validação correspondente.

## Estado de CI

A validação de LLC.6 foi concluída com sucesso no CI utilizado para a integração atual do projeto.

A cadeia LLC.1 → LLC.10 possui validação integrada e permanece separada de qualquer autorização de evolução.

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

## Fechamento

A LLC.6 está fechada como camada arquitetural validada.

Nenhuma nova camada LLC é criada por este documento.
