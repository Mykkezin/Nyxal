## Pipeline controlado de desenvolvimento

A primeira versão do pipeline cria áreas externas à árvore Git:

- `~/Nyxal-incoming`: artefatos recebidos.
- `~/Nyxal-workspace`: cópias temporárias para análise.
- `~/Nyxal-experiments`: cópias em ambiente experimental.
- `~/Nyxal-reports`: relatórios JSON dos ciclos.

Fluxo atual:

`incoming → análise → workspace → validação de sintaxe → experiments → candidato/rejeitado → relatório`

Nesta versão, código recebido **não é executado**. Arquivos Python passam somente por `py_compile`. Não há instalação automática de dependências, merge, publicação ou integração em `main`.

Um artefato classificado como `candidato` ainda não foi promovido para a versão estável.

Próximas extensões controladas:

1. manifesto/contrato do artefato;
2. detecção de dependências;
3. sandbox de testes permitidos;
4. avaliação;
5. aprovação/rejeição registrada;
6. integração controlada;
7. eventos Delta e relatório consolidado.
