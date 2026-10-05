# M5.8 — Dependências Arquiteturais

## Estado

**Proposta supervisionada — não autoritativa.**

Este marco nasce diretamente da evidência operacional acumulada pela AE5: a linha madura identificou que as relações entre componentes da arquitetura não estão declaradas formalmente na planta.

## Objetivo

Construir o primeiro mapa auditável de dependências entre componentes já presentes em `planta_nixal/planta.json`, sem modificar a planta, o Runtime, o ciclo residente ou os gates de evolução.

## Critério desta primeira versão

A relação só entra no mapa quando existe evidência direta de importação entre dois componentes já declarados na planta. Isso evita transformar inferência arquitetural em fato.

Mapa atual:

| Origem | Destino | Evidência |
|---|---|---|
| `agente_qwen` | `capacidades` | `nixal_agente_qwen.py` importa `GerenciadorCapacidades` |
| `composicao` | `agente_qwen` | `nixal_composicao.py` importa `AgenteNixalQwen` |
| `executor_contexto` | `operacoes_contexto` | `executor_contexto_nixal.py` importa `OperacoesContextoNixal` |
| `interpretacao_qwen` | `gerenciador_cristal` | `experiencia_qwen.py` importa símbolos do gerenciador |

## O que ainda não está sendo afirmado

O mapa não pretende ser um grafo completo da arquitetura. Ele não presume dependências de dados, runtime, persistência ou ordem temporal sem evidência específica.

Também não incorpora automaticamente módulos posteriores do Habitat NyxOS à planta histórica 56.4.2. Essa decisão fica para uma revisão arquitetural específica.

## Artefatos

- `m5_8_dependencias_arquiteturais_proposta.json` — mapa estruturado, não autoritativo.
- `teste_m5_8_dependencias_arquiteturais.py` — validação estrutural da proposta.
- `teste_m5_8_cobertura_importacoes.py` — reconciliação automática entre os imports diretos encontrados nos componentes Python da planta e as relações declaradas na proposta.

## Checkpoint de validação — 2026-10-05

A proposta foi validada em duas camadas no branch de desenvolvimento:

- `teste_m5_8_dependencias_arquiteturais.py`: **PASSOU**.
- `teste_m5_8_cobertura_importacoes.py`: **PASSOU**.
- relações diretas encontradas nos componentes Python da planta: **4**.
- relações declaradas na proposta: **4**.
- relações encontradas na fonte e ausentes na proposta: **0**.
- relações declaradas na proposta sem evidência direta: **0**.

Conclusão deste checkpoint: o mapa está **completo dentro do critério declarado de importação direta**. Isso não o transforma em autoridade arquitetural e não autoriza alteração da planta.

## Invariantes

```
autorizacao_explicita      = false
integracao_executada       = false
stable_modificada          = false
arquitetura_modificada     = false
conhecimento_permanente    = false
```

## Próxima decisão

Revisar o mapa proposto. Somente após essa revisão poderá ser considerada uma atualização da planta autoritativa. Nenhuma atualização é executada por este marco automaticamente.
