# Nyxal Multi-Model Orchestrator — proposta de integração

Status: proposta isolada; não habilitada no runtime.
Branch: feat/multi-model-orchestrator-20261110
Base: main (preservada).

## 1. Objetivo

Permitir que a Nyxal coordene OpenAI (GPT) e Google Gemini como provedores auxiliares, sem transferir a identidade, a memória canônica, a autoridade operacional ou o controle dos agentes para qualquer provedor externo.

O usuário conversa com a Nyxal. Os provedores recebem somente o contexto mínimo necessário para a tarefa e devolvem resultados ao núcleo Nyxal.

## 2. Estado verificado na main em 2026-11-10

- nixal_agent_hub.py contém adaptadores internos para Gemini, Hermes, Letta e OpenAI/Grok.
- nixal_responses_api.py implementa chamada à Responses API da OpenAI e xAI.
- A política ativa do NyxalAgentHub é explicitamente somente Nyxal local: resolve_provider() força nyxal e provider_configured() desabilita respondentes externos.
- docs/NYXAL_AGENT_STACK.md documenta Hermes/Gemini, Letta e Google Workspace em leitura.
- docs/ROTEAMENTO_PROVEDORES_NYXAL.md confirma que a presença de chaves não habilita o chat remoto.
- README.md descreve evolução governada, autorização separada e proibição de promoção automática.
- REVISAO_ARQUITETURAL_POS_M5_24.md determina que nenhum novo marco ou autoridade seja inferido automaticamente.

Esta branch não altera esses arquivos nem tenta contornar a política ativa.

## 3. Arquitetura alvo

```text
Usuário
  |
Nyxal Core / identidade / sessão canônica
  |
Agentes Nyxal (seleção por intenção e competência)
  |
Orquestrador multi-modelo (capacidade opcional, explicitamente habilitada)
  |                         |
Adaptador OpenAI             Adaptador Gemini
  |                         |
GPT                         Gemini
  |                         |
  +------ resultados -------+
             |
   validação / crítica / síntese
             |
       resposta Nyxal
```

O orquestrador não é uma nova memória, agente autônomo ou autoridade de execução. É um coordenador de inferência subordinado ao Core existente.

## 4. Modos de operação

1. local_only (padrão obrigatório): comportamento atual; nenhum prompt é enviado a provedores remotos.
2. select_one: Nyxal escolhe um provedor habilitado para uma tarefa.
3. parallel_review: GPT e Gemini recebem a mesma tarefa delimitada em paralelo; Nyxal compara divergências e sintetiza.
4. sequential_critique: um provedor produz uma proposta e o outro faz crítica estruturada; Nyxal decide o que aproveitar.

O modo paralelo não deve ser usado indiscriminadamente. Aumenta latência, custo e exposição de dados. Para tarefas simples, preferir um único provedor ou o modelo local.

## 5. Contratos de segurança e dados

- Nenhuma chave, token OAuth, cookie, segredo ou credencial entra no Git.
- Segredos somente em ~/.config/nyxal/nyxal.env, com permissões 0600.
- O modo remoto permanece desligado até configuração e verificação explícitas.
- O usuário deve ser informado quando o conteúdo de uma solicitação sair da máquina e qual provedor o receberá.
- Minimizar o contexto: não enviar histórico completo ou memória inteira por padrão.
- Memória/cristalização canônica continuam sob controle do Core Nyxal; resultados externos são apenas dados candidatos.
- Respostas externas são conteúdo não confiável: não podem alterar instruções do sistema, identidade, políticas, arquivos, serviços ou permissões.
- Provedores não executam ferramentas locais diretamente. Qualquer ferramenta permanece atrás dos contratos e autorizações já existentes da Nyxal.
- Não sincronizar automaticamente respostas ou dados sensíveis para Letta.
- Não gravar prompts ou respostas em telemetria. Registrar apenas provedor, modelo, latência, status, IDs de correlação e consumo quando realmente fornecido pelo provedor.
- Timeout, limite de tamanho, validação de esquema e rejeição de redirects são obrigatórios.
- Se um provedor falhar, retornar falha identificável ou usar fallback explicitamente permitido; nunca afirmar que dois modelos participaram se apenas um respondeu.

## 6. Integração com agentes

Capitu, Dumont, Jaci e Caapora continuam sendo agentes da Nyxal. Cada agente pode declarar uma política de inferência, por exemplo:

- Capitu: síntese, escrita e diálogo; selecionar um modelo ou solicitar crítica paralela quando útil.
- Dumont: engenharia e código; solicitar uma segunda revisão em mudanças de alto impacto.
- Jaci: visão; usar apenas o backend visual apropriado, sem misturar geração de imagem com chat textual.
- Caapora: planejamento; preferir decomposição e revisão sequencial, sem conceder execução autônoma.

Esses são exemplos de roteamento, não permissões novas. A implementação deve primeiro mapear os nomes e contratos reais dos agentes existentes antes de conectá-los.

## 7. Google Workspace

Gmail, Calendar, Contacts e Drive são ferramentas independentes dos modelos. O Core Nyxal mantém o OAuth e os escopos. GPT/Gemini recebem somente resumos ou resultados explicitamente selecionados pela Nyxal, nunca tokens OAuth.

O estado documentado na main é somente leitura. Enviar e-mail, criar/alterar eventos ou modificar arquivos exige uma etapa separada de autorização e não faz parte desta integração.

## 8. Configuração futura proposta

Os nomes abaixo são uma proposta de contrato, não variáveis ativadas nesta branch:

```dotenv
NYXAL_MULTI_MODEL_ENABLED=false
NYXAL_MULTI_MODEL_MODE=local_only
NYXAL_OPENAI_API_KEY=
NYXAL_OPENAI_MODEL=
NYXAL_GEMINI_API_KEY=
NYXAL_GEMINI_MODEL=
NYXAL_MULTI_MODEL_TIMEOUT_SECONDS=60
NYXAL_MULTI_MODEL_MAX_PARALLEL=2
```

A chave OpenAI deve usar a Responses API já implementada em nixal_responses_api.py. O adaptador Gemini deve reutilizar o código existente após revisão de segurança. Não criar clientes duplicados antes de auditar esses contratos.

## 9. Plano de implementação seguro

Fase A — inventário e contrato:
- confirmar chamadas reais do chat e formato de sessão/histórico;
- mapear agentes e seus limites;
- auditar testes atuais e dependências;
- manter memória/cristalização fora do escopo.

Fase B — orquestrador puro:
- criar coordenador sem efeitos colaterais, com adaptadores injetáveis;
- testar execução paralela, timeout, falha parcial, cancelamento e síntese;
- testar que o modo local não chama nenhum provedor.

Fase C — integração controlada:
- conectar o coordenador ao ponto de extensão já existente no Agent Hub;
- manter local_only como padrão;
- expor estado de configuração sem revelar segredos;
- não mudar o endpoint ou contrato de conversa sem testes de compatibilidade.

Fase D — validação local:
- executar suíte unitária e regressões relevantes;
- validar com chaves de teste e chamadas reais somente após consentimento/configuração do operador;
- medir custo, latência, privacidade e comportamento em falha;
- produzir relatório antes de qualquer proposta de merge.

Fase E — revisão:
- revisão humana do diff;
- aprovação explícita antes de merge/deploy;
- rollback documentado;
- nenhuma alteração automática de main, memória, cristalização ou serviços.

## 10. Critérios de aceite

- local_only é o padrão em instalação nova e após falha de configuração.
- Nenhuma chamada externa ocorre quando o recurso está desabilitado.
- GPT e Gemini podem ser chamados em paralelo apenas quando ambos estiverem configurados e o modo for explicitamente habilitado.
- Resposta final sempre pertence à Nyxal e identifica limitações/divergências relevantes.
- Falha de um provedor não descarta silenciosamente a resposta do outro.
- Nenhuma credencial aparece em logs, respostas de status, testes ou Git.
- Histórico e memória não são duplicados ou sobrescritos pelo orquestrador.
- Nenhuma ação em host, e-mail, agenda, arquivos ou serviços é executada por instrução retornada por modelo externo.
- Testes existentes de governança, API, memória e cristalização continuam aprovados.

## 11. Fora de escopo

- Alterar a memória persistente ou a cristalização.
- Habilitar automaticamente provedores remotos.
- Mudar a identidade ou os agentes existentes.
- Conceder autonomia de execução.
- Enviar e-mails ou alterar calendário.
- Implantar ou reiniciar serviços na máquina do usuário.
- Criar um novo marco M6/AE6 ou alterar a autoridade de governança.

## Decisão

Esta branch registra a proposta e os limites necessários. Ela não habilita integração remota e não deve ser mesclada até que a implementação, os testes e a revisão arquitetural sejam concluídos.


## 12. Implementação isolada nesta branch

Foram adicionados:

- `nixal_multi_model_orchestrator.py`: coordenador sem clientes de rede ou leitura de credenciais. Recebe adaptadores OpenAI/Gemini por injeção, limita os provedores aceitos, oferece modo local, seleção única, revisão paralela e crítica sequencial. Erros retornam apenas a classe da exceção, não mensagens potencialmente sensíveis.
- `teste_nixal_multi_model_orchestrator.py`: testes unitários para modo local sem chamadas, execução paralela, síntese injetada pela Nyxal, falha parcial, seleção explícita, crítica sequencial, validação de entradas e não exposição de mensagens de exceção.

Comando de teste na raiz do checkout:

```bash
python3 -m unittest teste_nixal_multi_model_orchestrator.py -v
```

Limite desta entrega: o coordenador ainda não está conectado ao endpoint de chat nem aos adaptadores reais do Agent Hub. Portanto, a criação dos arquivos não comprova que Gemini ou OpenAI estejam conectados, autenticados ou aptos a responder. Essa integração requer uma etapa separada de wiring, revisão do contrato de sessão e testes locais. Nenhuma chamada remota foi feita por esta implementação.
