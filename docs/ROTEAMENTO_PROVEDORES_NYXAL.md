# Roteamento inteligente de provedores da Nyxal

> **Política ativa: SOMENTE NYXAL LOCAL para respostas de conversa.** Gemini, OpenAI, Grok, Hermes e Letta estão desabilitados como respondentes do chat, mesmo que existam credenciais ou variáveis antigas no ambiente. O modo `auto` resolve para `nyxal`. A geração de imagens é uma capacidade separada e pode ter um backend visual próprio; isso não habilita Gemini para responder texto.


A intenção continua sendo classificada para anexar o playbook especializado apropriado (engenharia reversa autorizada, cibersegurança defensiva ou Data Science), mas a resposta textual permanece no Qwen local da Nyxal. Não há tentativa de chamar provedor remoto no fluxo normal do chat.

Esta é uma camada de roteamento determinística baseada em marcadores de intenção, coberta por testes; não é um classificador semântico treinado nem garante que um provedor seja sempre melhor. O núcleo carrega o playbook local de cada habilidade especializada quando ele existe, tanto nos provedores remotos quanto no fallback Qwen local. Os playbooks reforçam escopo autorizado, evidências, separação entre fatos e hipóteses e proibição de declarar ações não verificadas. Cada resposta inclui metadados de rota. O endpoint de estado do agente agrega latência, classes e provedores dos últimos 100 eventos em memória. A telemetria não armazena mensagens nem respostas, e os eventos são descartados quando o processo reinicia.

## OpenAI e Grok (xAI)

Os dois adaptadores usam a Responses API oficial. O provedor só é selecionado automaticamente quando a chave e um ID de modelo estão configurados. O adaptador recusa hosts fora das origens oficiais e redirecionamentos HTTP, para não encaminhar credenciais a um destino diferente.

Arquivo privado de ambiente, por exemplo ~/.config/nyxal/nyxal.env (defina permissões 0600 e não faça commit):

\`\`\`dotenv
NYXAL_AGENT_PROVIDER=auto
# Descomente e preencha apenas quando decidir usar cada provedor.
# NYXAL_OPENAI_API_KEY=SUA_CHAVE_OPENAI
# NYXAL_OPENAI_MODEL=ID_DE_MODELO_DISPONIVEL_NA_SUA_CONTA
# NYXAL_GROK_API_KEY=SUA_CHAVE_XAI
# NYXAL_GROK_MODEL=ID_DE_MODELO_DISPONIVEL_NA_SUA_CONTA
\`\`\`

Também são aceitos OPENAI_API_KEY e XAI_API_KEY. A configuração opcional de URL-base é restringida a https://api.openai.com/v1 para OpenAI e https://api.x.ai/v1 para Grok. Sem chave ou modelo, os dois provedores permanecem desativados.

Usar serviços externos pode ter custos e enviar o conteúdo de suas mensagens para os provedores configurados. Ative-os apenas após revisar custos e políticas de dados. A rota local permanece disponível como fallback.

Referências oficiais:
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses
- xAI Responses API: https://docs.x.ai/developers/rest-api-reference/inference/chat
