# Nyxal — Protocolo de Desenvolvimento

## Objetivo

Estabelecer um ciclo versionado para desenvolvimento supervisionado da Nyxal:

1. Planejamento da alteração.
2. Registro da ordem no repositório.
3. Aplicação local pela Nyxal.
4. Execução de testes.
5. Registro do resultado.
6. Checkpoint Git.
7. Sincronização com a branch de desenvolvimento.
8. Promoção para `main` somente após validação.

## Papéis

- **ChatGPT:** supervisor/arquitetura, análise, planejamento e revisão das mudanças.
- **Nyxal local:** executor, verificador e registrador dos resultados.
- **Qwen:** camada de decisão temporária, utilizada apenas onde a arquitetura atual ainda depende dela.
- **GitHub:** ponte versionada e histórico de desenvolvimento.
- **MCP:** interface operacional local da Nyxal.

## Branches

- `main`: estado estável.
- `desenvolvimento/mcp-bridge`: trabalho de integração e automação.

## Regras de segurança

- Não modificar `main` diretamente durante desenvolvimento.
- Preferir alterações pequenas e reversíveis.
- Executar testes antes de criar checkpoint.
- Não gravar segredos, tokens ou chaves no repositório.
- Não promover conhecimento permanente apenas por alteração automática.
- Não executar autoalteração fora das permissões e ferramentas explicitamente definidas.
- Toda mudança automática deve deixar rastros verificáveis: arquivo alterado, teste executado e commit correspondente.

## Estado consolidado

A sequência Nível 9 / Nível 10 foi concluída e integrada em `main`, com regressão final validada.

Estado atual:

- Nível 9 — evolução controlada: concluído.
- Nível 10 — ciclo local formal: concluído.
- 56.5.5 — conversa contextual: integrado.
- 56.5.6 — voz contínua: integrado.
- M5 — Habitat NyxOS: iniciado.
- M5.1 — observabilidade real do host: implementado e validado.
- M5.3 — persistência operacional: implementada e validada pelo CI.
- M5.4 — eventos Delta de primeira classe: implementados e validados pelo CI.
- M5.5 — interface orientada ao estado real: implementada e validada pelo CI.
- M5.6 — ferramentas e módulos como recursos do habitat: implementados e validados pelo CI.
- M5.7 — ciclo operacional residente: implementado e validado pelo CI.

## Próximo objetivo

Avançar o M5/Habitat sem criar um kernel próprio.

Primeiro ciclo:

```
host
→ observabilidade
→ processos
→ persistência operacional
→ eventos Delta
→ interface orientada a estado real
→ ciclo operacional residente
```

O primeiro marco M5.1 mantém a ponte somente leitura e não altera hardware, estado persistente ou os gates de evolução.

M5.7 conclui o Habitat NyxOS desta fase. O próximo estágio é integrar uma camada de auto-evolution governada sobre o ciclo residente, reutilizando o N9 para manter autorização explícita, isolamento de candidatos e reversibilidade.

