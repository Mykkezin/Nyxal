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

## Próximo objetivo

Criar um ciclo local capaz de detectar novas alterações na branch de desenvolvimento, sincronizá-las, executar validações e registrar o resultado para o próximo ciclo de desenvolvimento.

