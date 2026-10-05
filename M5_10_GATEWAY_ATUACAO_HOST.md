# M5.10 — Gateway de Atuação do Host

## Objetivo

Criar uma fronteira única, explícita e auditável entre uma intenção já transformada em contrato estruturado e uma ação concreta sobre o host.

M5.10 não adiciona ainda o catálogo de operações de processos e aplicativos. Essa atuação concreta fica reservada ao M5.11.

## Arquitetura

```
intenção
   ↓
seleção semântica
   ↓
contrato de ação
   ↓
validação de política
   ↓
Gateway de Atuação do Host
   ↓
executor registrado
   ↓
ação permitida
   ↓
resultado
   ↓
observabilidade / Delta
```

A seleção semântica continua separada do executor.

O Qwen pode participar da seleção de uma capacidade, mas não recebe acesso direto ao gateway e nunca produz shell para execução.

## Contrato

Cada ação de host deve possuir, no mínimo:

- nome estável;
- descrição;
- objetivo;
- argumentos e tipos;
- domínio;
- nível de risco;
- indicação de reversibilidade;
- regra de autorização explícita.

O allowlist é composto somente pelas ações registradas em código pelo sistema.

M5.10 inicia com **zero ações concretas por padrão**.

## Política

Antes de chamar qualquer executor, o gateway verifica:

1. a entrada é um objeto estruturado;
2. a ação existe no allowlist;
3. não existem argumentos desconhecidos;
4. argumentos obrigatórios existem;
5. tipos e valores declarados são válidos;
6. autorização de atuação, quando exigida, está presente.

Uma falha de qualquer uma dessas verificações impede a chamada do executor.

## Proteções

O gateway não interpreta shell, comandos arbitrários, texto natural ou código.

Ele não usa subprocess, os.system, Popen, eval ou exec como mecanismo genérico de atuação.

Também não concede autorização para:

- modificar arquitetura;
- promover conhecimento permanente;
- integrar alterações em main;
- executar evolução autônoma.

## Dry-run

A interface suporta o modo dry-run.

Nesse modo, contrato e política são exercitados, mas o executor não é chamado.

Isso permite validar uma futura ação de host antes de colocá-la em operação real.

## Observabilidade

Cada tentativa é registrada em log_atuacao_host_nixal.json.

O histórico é limitado a 100 eventos.

Quando um executor real é concluído e um registrador Delta é fornecido, o gateway registra a mudança observada como evento sistema.

## Escopo de M5.11

A próxima etapa adicionará as primeiras ações concretas de processos, aplicativos conhecidos e terminal, sempre atravessando este gateway.

## Critério de conclusão

M5.10 é considerado validado quando:

1. existe uma fronteira única de atuação;
2. há contratos declarativos;
3. existe allowlist explícito;
4. política é executada antes do executor;
5. argumentos são validados;
6. linguagem natural e shell arbitrário não atravessam a fronteira;
7. dry-run é comprovado;
8. execução real de teste ocorre apenas após autorização;
9. o resultado é observável;
10. Delta pode registrar a ação;
11. invariantes de evolução permanecem inalterados;
12. M5.9 continua funcional.

M5.10 não autoriza integração em main.
