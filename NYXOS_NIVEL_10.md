# NyxOS — Nível 10

Primeira implementação do habitat persistente experimental.

## Estrutura

Linux
→ NyxOS
→ runtime / memory / knowledge / body / tools / projects /
experiments / processes / events / interface / delta / logs

## Critério desta etapa

O habitat precisa:

- existir de forma persistente em disco;
- preservar estado entre reaberturas;
- registrar processos;
- registrar eventos;
- registrar mudanças Delta;
- permanecer separado do kernel Linux;
- ser uma base integrável ao Runtime existente.

Esta etapa não declara o Nível 10 concluído. O fechamento exige integrar o Runtime real, memória, ferramentas, interface, observabilidade e Delta em um fluxo operacional único e testado.
