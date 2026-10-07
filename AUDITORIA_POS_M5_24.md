# Auditoria Arquitetural Pós-M5.24

## Estado

Esta auditoria verifica a diferença entre a arquitetura efetivamente integrada em `main` e os identificadores/versionamentos internos de componentes históricos.

## Resultado

### 1. Runtime

`nixal_runtime.py` continua declarando `VERSAO = "fase_01"`.

Isso não significa que o Runtime atual contenha apenas a Fase 01: o arquivo integra investigação, hipóteses, memória, evolução remota, persistência operacional, Delta e Learning Loop.

Entretanto, o identificador de versão permanece histórico porque a suíte `teste_nyxal_runtime.py` valida explicitamente `runtime.VERSAO == "fase_01"`.

**Conclusão:** não alterar o identificador sem um contrato de migração e atualização da suíte. O estado atual é uma dívida de versionamento interno, não uma falha funcional comprovada.

### 2. Ciclo residente

`nixal_ciclo_residente.py` declara `VERSAO = "5.8.0"`, embora o ciclo seja utilizado pelo launcher atual que compõe componentes até M5.24.

Assim como no Runtime, trata-se de um identificador histórico do componente. Não há evidência suficiente nesta auditoria para afirmar que a alteração do valor seja necessária ou segura.

**Conclusão:** preservar o valor nesta fase e registrar como dívida de versionamento.

### 3. Voz

M5.24 possui contrato próprio e teste determinístico para o ciclo supervisionado STT → TTS. Os invariantes de voz automática, execução automática e execução física permanecem falsos.

**Conclusão:** nenhuma lacuna funcional nova foi identificada nesta revisão documental.

### 4. Residência

O launcher `executar_nyxos_residente.py` compõe Runtime, AE1→AE5, fisiologia, presença, plano central e gateway, mantendo execução física desabilitada.

**Conclusão:** a residência está arquiteturalmente composta, mas esta auditoria não transforma a composição em evidência empírica contínua. Evidência real deve continuar sendo registrada separadamente.

## Dívidas identificadas

| Item | Tipo | Ação agora |
|---|---|---|
| `NyxalRuntime.VERSAO = fase_01` | versionamento histórico | preservar |
| `CicloResidenteNixOS.VERSAO = 5.8.0` | versionamento histórico | preservar |
| evidência residente contínua | evidência operacional | não inventar |
| voz automática | escopo | permanecer desabilitada |
| M6/AE6 | governança | não criar automaticamente |

## Critério para próxima alteração

Uma futura correção de versionamento só deve ocorrer quando houver:

1. novo contrato explícito de versão;
2. atualização dos testes dependentes;
3. análise de compatibilidade;
4. alteração pequena e reversível;
5. CI completo verde;
6. checkpoint correspondente.

## Veredito

Não foi encontrada nesta revisão uma falha que justifique alterar o Runtime ou criar um novo marco arquitetural.

O principal achado é **dívida de nomenclatura/versionamento histórico**. Ela está documentada e deve permanecer separada de mudanças funcionais.

Portanto, a arquitetura permanece **fechada em M5.24**, aguardando uma necessidade operacional mensurável antes de qualquer nova implementação.