# Nível 10 — Contrato Formal do Ciclo Local de Desenvolvimento

## 1. Objetivo

O Nível 10 transforma o pipeline de desenvolvimento já existente em um ciclo local
verificável e versionado capaz de:

1. detectar uma alteração nova na branch de desenvolvimento;
2. identificar exatamente o estado de origem e o novo estado observado;
3. preparar uma sincronização controlada;
4. executar apenas as validações permitidas pelo contrato;
5. registrar o resultado de forma determinística;
6. classificar o ciclo como aprovado ou rejeitado;
7. deixar evidência suficiente para auditoria e para o próximo ciclo.

O Nível 10 **não promove automaticamente alterações para `main`**.

## 2. Ponto de partida

O contrato parte das capacidades já concluídas no Nível 9:

```
limitação
→ hipótese
→ experimento
→ resultado
→ aprendizado
→ candidato
→ proposta
→ autorização externa
→ integração preparada
→ revisão/merge externo
→ registro em stable
→ rollback registrável
```

O Nível 10 não substitui esses gates. Ele adiciona um ciclo operacional ao redor do
desenvolvimento supervisionado.

## 3. Escopo

### Dentro do Nível 10

- observar uma branch de desenvolvimento explicitamente configurada;
- detectar mudança de referência/commit;
- registrar o commit anterior e o novo commit;
- preparar um ciclo identificável;
- executar validações determinísticas permitidas;
- registrar sucesso, falha, diagnóstico e evidências;
- impedir promoção quando a validação falhar;
- manter histórico dos ciclos;
- permitir recuperação/reexecução de um ciclo sem perder o registro anterior.

### Fora do Nível 10

O ciclo não pode, por conta própria:

- fazer merge em `main`;
- alterar `main` diretamente;
- publicar artefatos;
- instalar dependências automaticamente;
- executar código recebido sem que isso esteja explicitamente previsto por uma
  política de execução aprovada;
- autorizar sua própria evolução;
- transformar uma validação verde em autorização de integração;
- apagar evidências de ciclos anteriores.

## 4. Máquina de estados

O ciclo formal é:

```
observado
   ↓
alteracao_detectada
   ↓
sincronizacao_preparada
   ↓
validacao_em_execucao
   ↓
validacao_concluida
   ├──→ aprovado
   └──→ rejeitado
```

Estados terminais:

- `aprovado`
- `rejeitado`

Uma execução que falhar tecnicamente durante a validação também termina como
`rejeitado`, preservando o diagnóstico.

### Transições permitidas

| Estado atual | Próximos estados |
|---|---|
| observado | alteracao_detectada |
| alteracao_detectada | sincronizacao_preparada |
| sincronizacao_preparada | validacao_em_execucao |
| validacao_em_execucao | validacao_concluida |
| validacao_concluida | aprovado, rejeitado |
| aprovado | — |
| rejeitado | — |

Uma falha técnica durante a validação deve ser registrada como resultado de validação
malsucedido e então classificada como `rejeitado`, preservando o diagnóstico.

Nenhuma transição pode saltar diretamente de `alteracao_detectada` para
`aprovado`.

## 5. Identidade do ciclo

Cada ciclo deve possuir um identificador determinístico derivado, no mínimo, de:

- branch observada;
- commit anterior;
- commit novo.

O registro deve preservar:

- `ciclo_id`;
- `branch`;
- `commit_anterior`;
- `commit_novo`;
- timestamp;
- estado atual;
- histórico de estados;
- validações executadas;
- resultado;
- diagnóstico, quando houver.

O mesmo par branch/commit novo não deve gerar silenciosamente dois ciclos distintos.

## 6. Detecção

A detecção deve ser somente observacional.

Ao detectar:

```
commit_atual != commit_registrado
```

o sistema pode abrir um novo ciclo.

Se não houver alteração:

```
nenhuma alteração → nenhum ciclo novo
```

A ausência de mudança não deve ser registrada como uma falsa aprovação de
desenvolvimento.

## 7. Sincronização

A sincronização deve produzir um estado de trabalho identificável.

O ciclo deve saber exatamente:

- qual referência foi observada;
- qual referência foi preparada para validação;
- qual commit será validado.

A sincronização não significa promoção.

```
desenvolvimento
      ↓
estado preparado
      ↓
validação
      ↓
registro
      X
     main
```

## 8. Validação

A primeira implementação do Nível 10 deve privilegiar validações determinísticas
e não destrutivas.

São exemplos permitidos:

- compilação sintática Python;
- testes unitários/integrados explicitamente selecionados;
- verificações estruturais;
- validação de contratos;
- inspeção de estado Git.

Não fazem parte do contrato inicial:

- instalação arbitrária de pacotes;
- execução de comandos externos não declarados;
- execução automática de artefatos recebidos;
- publicação;
- merge.

## 9. Critério de aprovação

Um ciclo somente pode alcançar `aprovado` quando:

1. a alteração foi identificada;
2. o commit a validar está registrado;
3. a sincronização/preparação foi concluída;
4. todas as validações obrigatórias terminaram;
5. nenhuma validação obrigatória falhou;
6. o resultado foi persistido.

Qualquer falha obrigatória produz `rejeitado`.

`aprovado` significa:

> "este ciclo passou pelas validações definidas"

e **não** significa:

> "esta alteração está autorizada a entrar em stable".

## 10. Persistência e auditoria

Cada ciclo deve produzir um registro persistente e legível.

O histórico não deve ser sobrescrito para transformar uma falha em sucesso.

Uma reexecução deve criar uma nova tentativa vinculada ao ciclo original ou seguir
uma regra de identidade explicitamente registrada.

Os registros devem permitir reconstruir:

```
o que mudou
→ o que foi validado
→ quando foi validado
→ qual foi o resultado
→ por que foi aprovado/rejeitado
```

## 11. Relação com o Nível 9

O Nível 9 controla a fronteira:

```
proposta → autorização → integração → stable
```

O Nível 10 controla:

```
alteração em desenvolvimento
→ detecção
→ sincronização
→ validação
→ registro
```

Portanto:

**Nível 10 não substitui a governança do Nível 9.**

Uma validação Nível 10 aprovada pode fornecer evidência para uma futura proposta,
mas nunca concede autorização de integração por si só.

## 12. Invariantes obrigatórias

A implementação deve manter, no mínimo:

- `main` não é modificada pelo ciclo local;
- ausência de alteração não cria falso ciclo aprovado;
- commit validado é explicitamente identificável;
- falha de validação nunca resulta em `aprovado`;
- aprovação não equivale a autorização;
- registros anteriores não são apagados;
- execução automática de candidato permanece fora do contrato;
- cada transição é auditável;
- a máquina de estados rejeita transições inválidas.

## 13. Critérios de aceite do contrato

O Nível 10 só pode avançar para implementação operacional quando testes
determinísticos demonstrarem:

- criação correta do ciclo;
- identidade determinística;
- detecção de alteração;
- ausência de ciclo quando não há alteração;
- transições válidas;
- bloqueio de transições inválidas;
- validação bem-sucedida → `aprovado`;
- validação com falha → `rejeitado`;
- persistência do histórico;
- impossibilidade de transformar aprovação em autorização;
- `main` inalterada pelo ciclo.

## 14. Estado de implementação

O contrato já possui uma implementação inicial dos componentes mínimos:

- observador determinístico de branch/commit;
- máquina de estados persistente;
- executor integrado ao coordenador existente;
- classificação de aprovação/rejeição;
- nova tentativa explícita para ciclos rejeitados;
- suíte consolidada de testes.

A sincronização do Nível 10 é deliberadamente uma preparação verificável do commit
observado. O método legado de sincronização remota continua separado e não é
acionado automaticamente pelo ciclo Nível 10.

A conclusão formal do Nível 10 exige regressão completa e evidência de CI verde.
