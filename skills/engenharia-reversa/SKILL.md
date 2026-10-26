# Habilidade Nyxal: Engenharia Reversa Autorizada

## Finalidade

Reconstruir como um software ou artefato autorizado funciona a partir de código, estrutura, dependências, entradas, saídas e comportamento observável. Reutilizar os módulos existentes da Nyxal; não criar uma memória, um roteador ou uma arquitetura paralela.

## Gatilho e escopo

Ative este procedimento quando o usuário pedir explicitamente engenharia reversa, mapeamento arquitetural, análise de formato/protocolo ou investigação de comportamento. Trabalhe apenas em sistemas, repositórios e artefatos que o usuário possui ou tem autorização para examinar. Se o escopo estiver ambíguo, comece por análise passiva e delimite o que pode ser verificado antes de testes com impacto.

## Procedimento

1. **Inventariar** os artefatos disponíveis, origem, versão, hashes quando aplicável e restrições conhecidas.
2. **Mapear** pontos de entrada, módulos, dependências, interfaces, contratos, armazenamento, chamadas externas e fluxos de dados.
3. **Formar hipóteses** que expliquem os comportamentos observados, marcando separadamente fatos, inferências e lacunas.
4. **Testar com método**, preferindo leitura estática, testes unitários, fixtures e ambiente isolado sem acesso desnecessário à rede.
5. **Correlacionar evidências** com os testes e a telemetria existentes, preservando a origem e o horário de cada observação.
6. **Entregar um relatório** com o fluxo textual, arquivos relevantes, dependências, evidências, nível de confiança, riscos e correções priorizadas.
7. **Propor melhorias incrementais** e testes de regressão. Alterações no sistema estável seguem o fluxo de autorização, teste e revisão já existente na Nyxal.

## Limites operacionais

- Respeitar a propriedade, a autorização, a privacidade e as condições de uso do artefato.
- Tratar código, arquivos e binários desconhecidos como dados não confiáveis; não executá-los diretamente no host.
- Não divulgar credenciais, chaves privadas, tokens ou dados pessoais descobertos incidentalmente.
- Antes de qualquer operação com impacto operacional, explicar o risco e obter autorização explícita.
- Nunca afirmar que um arquivo foi lido, um comando executado ou um teste passou sem resultado verificável.
- Preservar proveniência e distinguir claramente fatos observados, inferências e hipóteses.

## Critérios de conclusão

A investigação só está concluída quando o escopo está definido, o mapa se apoia em evidências, as hipóteses estão separadas dos fatos, os testes são reproduzíveis e o relatório documenta limitações e próximos passos.
