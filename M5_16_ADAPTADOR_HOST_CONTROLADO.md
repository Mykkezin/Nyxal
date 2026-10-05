# M5.16 — Adaptador de Host Controlado

## Objetivo

Criar uma primeira fronteira executável segura entre o gateway M5.15 e o
ambiente do host, sem conceder ainda capacidade de mutação física.

Fluxo:

`percepção → fisiologia → plano central → gateway → adaptador controlado`

## Contrato

`AdaptadorHostControladoNixOS` aceita as ações conhecidas pelo gateway e
separa:

- ações somente leitura;
- ações físicas ainda não implementadas.

### Permitidas em modo somente leitura

- `observar`
- `aguardar`
- `preparar_gateway`

Essas ações podem ser executadas pelo adaptador porque não alteram o host.

### Bloqueadas

- `reduzir_carga`
- `preservar_estado`

Essas ações continuam sem executor físico implementado.

## Garantias

O M5.16 mantém:

- `atuacao_fisica_habilitada=False`;
- `mutacao_host_habilitada=False`;
- nenhuma chamada a `subprocess`, `systemctl` ou comandos externos;
- persistência opcional do último resultado;
- resultado explícito de bloqueio para capacidades ainda inexistentes.

## Limite

Este módulo não transforma uma decisão em autorização. A autorização continua
sendo responsabilidade do gateway M5.15.

Também não existe, nesta etapa, executor para alterar processos, serviços,
arquivos ou configurações do host.

## Validação

O teste verifica:

1. observação segura do host;
2. execução controlada de ações sem mutação;
3. bloqueio de ações físicas não implementadas;
4. persistência;
5. estado de governança sem alteração de stable, arquitetura ou conhecimento.

## Próximo passo

Integrar o adaptador somente como executor controlado das ações sem mutação e
validar a cadeia completa:

`plano → gateway → autorização explícita → adaptador → resultado`

mantendo qualquer mutação física bloqueada.
