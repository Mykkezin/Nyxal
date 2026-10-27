# Defesa autônoma governada da Nyxal

## Objetivo

Construir a capacidade de perceber ataques contra a própria Nyxal, conter danos de forma proporcional, preservar evidências, restaurar serviços e aprender com incidentes. O princípio é **defender primeiro, responder dentro de um escopo autorizado e nunca retaliar contra sistemas externos**.

A defesa não pode dar à Nyxal autoridade irrestrita apenas por detectar uma ameaça. Detecção, decisão, autorização e execução são etapas distintas.

## Estado desta entrega

O módulo `nixal_defesa_autonoma.py` implementa uma política determinística isolada. Ele recebe eventos estruturados e devolve recomendações auditáveis. **Não executa nenhuma recomendação**: não altera firewall, não mata processos, não revoga credenciais, não isola serviços, não modifica arquivos e não faz conexões de rede.

O workflow dedicado executa os testes unitários dessa política e do gate de preparação dry-run. A API registra falhas de Bearer por um produtor interno (`api-auth`), sem guardar token, cabeçalhos ou corpo, e encaminha recomendações ao `ExecutorDefesaGovernada` para preparação simulada. Eventos e planos permanecem somente em memória; o executor que efetua efeitos reais no host continua desabilitado e não está implementado.

## Ciclo de resposta

```text
sinal observado
  → validação e normalização do evento
  → correlação temporal e avaliação de confiança
  → decisão determinística com escopo limitado
  → preservação mínima de evidências + alerta
  → recomendação de contenção reversível
  → autorização por capacidade/operador quando exigida
  → executor isolado e allowlisted
  → verificação de saúde e reversão
  → revisão do incidente e aprendizado governado
```

Os dados dos eventos são tratados como entrada não confiável. Cada tipo de evento exige uma origem de sinal permitida (por exemplo, `api-auth`, `integrity-monitor` ou `health-monitor`); eventos críticos exigem também `evidencia_id`. Esses campos são gates de esquema, não autenticação criptográfica: o adaptador deve derivar a fonte de observadores locais autenticados e jamais aceitar `fonte_sinal` diretamente de um cliente remoto. O motor não recebe comandos de shell nem aceita conteúdo arbitrário como alvo de ação; os serviços privilegiados são uma allowlist codificada. Os identificadores de evidência, credencial e artefato são validados e não devem conter segredos.

## Respostas proporcionais

| Sinal | Resposta sugerida | Limite |
|---|---|---|
| Falha de autenticação isolada | Contador transitório em memória | Não bloqueia por uma única falha |
| 3 ou mais falhas na janela de 60 s | Para origem remota, recomendar limite de taxa; para loopback, somente alerta | Recomendação exige aprovação explícita nesta fase |
| 8 ou mais falhas na janela de 60 s | Bloqueio temporário de 300 s apenas para IP não-loopback | Recomendação exige aprovação explícita e nunca é executada por este módulo |
| Origem suspeita | Correlacionar sinais; limitar taxa se confiança ≥ 0,7 | Não basta, por si só, para bloqueio permanente |
| Tentativa de exploração | Preservar evidências; bloqueio curto se confiança ≥ 0,9 | Honeypot isolada só é recomendada com confiança ≥ 0,95 e aprovação |
| Violação de integridade | Alertar e propor isolamento do serviço conhecido | Isolamento disruptivo exige aprovação |
| Credencial comprometida | Alertar e propor revogação por identificador | Segredo nunca entra na decisão; revogação exige aprovação |
| Artefato possivelmente malicioso | Preservar evidência e propor quarentena | Não executa nem apaga o artefato; requer aprovação |
| Serviço indisponível | Diagnóstico de leitura e proposta de reinício | Reinício exige aprovação |
| Recuperação verificada | Solicitar revisão do incidente | Não limpa evidências nem remove bloqueios automaticamente |

A janela e os limiares são parâmetros configuráveis em código e deverão ser calibrados com evidências reais antes de qualquer ativação em produção. A política limita a janela a 3.600 segundos, o bloqueio a 3.600 segundos e cada limiar a 1.000.000 para impedir configurações absurdas. O estado do contador é limitado a 2.048 origens em memória; entradas novas substituem o registro menos recentemente usado quando esse limite é atingido. O histórico de falhas por origem é limitado a 128 eventos e as operações de contagem usam lock para tolerar chamadas concorrentes. Um IP observado em um evento não prova identidade ou intenção; as recomendações precisam ser correlacionadas com telemetria confiável antes de serem aplicadas.

## O que “atacar” significa nesta arquitetura

A resposta ativa aceitável é **defesa de ativos próprios e autorizados**, por exemplo:

- bloquear temporariamente uma origem no perímetro que a Nyxal administra;
- limitar taxa e rejeitar tráfego malformado;
- isolar um serviço da própria Nyxal para conter uma intrusão;
- revogar uma credencial que pertença ao ambiente sob administração;
- encaminhar atividade suspeita para uma honeypot interna isolada, sem saída para redes externas;
- executar varreduras de verificação apenas em inventário próprio, quando houver uma futura tarefa de teste explicitamente autorizada.

O motor desta entrega não faz nenhuma dessas operações. Apenas emite intenções tipadas e informa explicitamente `executor_autorizado=false` e `efeito_executado=false`. O construtor de recomendações exige aprovação humana por padrão; somente a notificação de operador dispensa explicitamente essa aprovação, pois não altera o estado de segurança. Não há exceções implícitas para novos tipos de ação.

## Barreiras obrigatórias antes de integrar um executor

1. **Escopo de propriedade:** cada ação precisa referenciar recurso pertencente ao ambiente ou formalmente autorizado. Não aceitar alvos arbitrários fornecidos por um evento.
2. **Mínimo privilégio:** executor separado do modelo de linguagem, sem shell genérico e sem acesso irrestrito à rede.
3. **Allowlist por ação:** cada tipo de ação tem parâmetros, limites e recursos definidos. Caminhos de arquivos precisam ser resolvidos e verificados antes de qualquer movimentação.
4. **Autorização:** todas as recomendações que alteram estado — limitar taxa, bloquear, isolar, reiniciar, revogar credenciais, colocar artefatos em quarentena ou encaminhar à honeypot — exigem aprovação explícita nesta fase. Os campos de origem/evidência no evento são validação de esquema, não prova criptográfica; só um adaptador autenticado e uma política de autoridade separada poderiam justificar contenção autônoma limitada mais adiante.
5. **Reversão:** bloqueios expiram; contenções têm procedimento de retorno conhecido e logs de auditoria sem segredos.
6. **Evidência:** guardar somente metadados necessários, com horário confiável, origem da observação e integridade verificável. Não guardar tokens, corpos privados ou segredos em logs.
7. **Proteção contra abuso do sinal:** correlacionar eventos, limitar frequência, tratar dados fornecidos pelo atacante como não confiáveis e não permitir que um único alerta provoque ação destrutiva.
8. **Verificação pós-ação:** checar saúde, falsos positivos e efeitos colaterais; suspender automação diante de dados insuficientes ou comportamento não previsto.

## Ações proibidas

A política não deve gerar nem autorizar retaliação contra terceiros: exploração de sistemas alheios, execução de código remoto, roubo de credenciais, exfiltração, destruição de dados, malware, persistência clandestina, DDoS, varredura indiscriminada ou tentativa de “hackear de volta”. A defesa ativa termina na contenção dos recursos próprios e na coleta legal e proporcional de evidências.

## Integração futura com autonomia e aprendizado

- **Observabilidade:** transformar logs autenticados em eventos normalizados, eliminando tokens e payloads sensíveis.
- **Motor de política:** avaliar a severidade, a confiança, a frequência e os limites de ação.
- **Gate de preparação:** validar e deduplicar propostas em modo dry-run; o executor que efetua efeitos reais só poderá ser considerado após testes específicos de autorização, idempotência, escopo, expiração e reversão.
- **AE/LLC:** medir falsos positivos, tempo de contenção, recuperação e recorrência; gerar hipóteses e propostas. Aprendizado pode recomendar mudança de política, mas não deve editar ou ativar silenciosamente regras privilegiadas.
- **Governança:** manter a trilha observar → hipótese → experimento isolado → comparação → aprendizado → proposta → autorização explícita → implantação validada.

## Validação

Execute localmente:

```bash
python -m py_compile nixal_defesa_autonoma.py teste_defesa_autonoma.py nixal_executor_defesa_governada.py teste_executor_defesa_governada.py
python -m unittest teste_defesa_autonoma.py teste_executor_defesa_governada.py -v
```

Os testes cobrem os limiares, expiração da janela, exceção para loopback, confiança, allowlists, aprovação humana, identificadores e ausência de efeitos colaterais. Um teste aprovado valida o comportamento determinístico do motor, não demonstra que a Nyxal inteira esteja protegida nem que alguma defesa esteja ativa no host.

## Integração atual da API — observação, não contenção

O gate de autenticação HTTP alimenta o motor determinístico com falhas de Bearer observadas dentro do handler. O cliente não escolhe `fonte_sinal`, confiança, decisão ou alvo; a fonte é atribuída pelo próprio servidor (`api-auth`). A trilha contém somente metadados mínimos e mantém no máximo 256 registros em memória. `GET /api/agent/defesa` é uma rota interna protegida e devolve até 50 registros recentes.

O evento usa o endereço do peer TCP observado pelo servidor. `Forwarded`, `X-Forwarded-For` e `X-Real-IP` não são usados como identidade. Em uma topologia com proxy, o peer pode ser o proxy local e não o cliente final; não se infere o IP remoto até existir configuração explícita de proxy confiável e testes correspondentes. O histórico é volátil, não contém tokens, corpos, query strings ou cabeçalhos e não é uma trilha forense durável.

A API agora encaminha as recomendações para `ExecutorDefesaGovernada.preparar` e expõe os resumos dos planos simulados no endpoint autenticado `GET /api/agent/defesa`. O gate aplica allowlist, idempotência limitada, TTL de plano e aprovação humana para recomendações que não sejam mero alerta. Ainda assim, esta entrega não bloqueia tráfego, não limita taxa, não reinicia serviços, não revoga credenciais e não altera arquivos. `executor_ativo=false`, `executor_autorizado=false` e `efeito_executado=false` permanecem invariantes; os planos não são persistidos. O TTL agora muda o estado do plano em memória para `expirado` e impede uma aprovação tardia de reativá-lo. Isso expira somente a proposta `dry-run`: não há efeito real para expirar, pois a execução física continua inexistente. Serviço de aprovação autenticada, executor real por capacidade, auditoria durável, TTL efetivo dos efeitos, rollback e integração de sinais além de falhas de Bearer permanecem pendentes.
## Gate de preparação governada — dry-run

`nixal_executor_defesa_governada.py` acrescenta uma fronteira separada entre recomendação e qualquer futura execução. Nesta fase ele **só prepara planos simulados**: não existe método de execução física, chamada de shell, ação de rede, escrita de arquivos operacionais, alteração de firewall, reinício de serviço, revogação de credencial ou quarentena real.

Controles incluídos:

- Allowlist fechada de tipos de recomendação e validação de escopo por tipo. Contenção de loopback, serviços fora da allowlist, identificadores com caminhos e durações fora do limite são rejeitados.
- Todas as recomendações além de um simples alerta exigem aprovação humana, mesmo que o objeto de entrada tente marcar o contrário. Um verificador de aprovação opcional só pode validar um comprovante; mesmo quando retorna aprovado, a saída continua `modo=dry_run`, `executor_ativo=false`, `executor_autorizado=false` e `efeito_executado=false`.
- Idempotência em memória por recomendação, com janela limitada; registros limitados a 256 por instância. Planos `dry-run` vencidos passam a `expirado` na consulta/preparação e não podem ser reativados por uma aprovação posterior. Não existe trabalhador nem mecanismo de execução real.
- Campos extras da entrada não são copiados para o plano, os motivos têm tamanho limitado e credenciais óbvias em formato Bearer/`token=` são redigidas.

Este gate é uma etapa de preparação e teste, não encerra a issue de defesa. Antes de qualquer efeito real, ainda será necessário um serviço de aprovação autenticada independente, executor por capacidades específicas, armazenamento de auditoria resistente a reinício, TTL/expiração efetiva dos efeitos, rollback testado e testes de replay/concorrência/proxy.
