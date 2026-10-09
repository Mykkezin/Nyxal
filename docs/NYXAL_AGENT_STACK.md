# Nyxal Agent Stack — Hermes, Gemini, Letta, Gmail e voz

## Arquitetura pretendida

```text
Nyxal Display
    ↓ POST /api/agent/chat
Nyxal Core / NixalAgentHub
    ├── Hermes Agent API (agente executor e gateway de mensagens)
    │      └── modelo escolhido no Hermes (Gemini pode ser o modelo principal)
    ├── Gemini API (provedor direto e fallback configurável)
    ├── Letta (agente stateful e memória persistente)
    └── Qwen/Ollama local (fallback privado)
            ↓
    observabilidade local somente leitura
    Gmail OAuth somente leitura
    skills versionadas no repositório
    Kokoro TTS — voz feminina brasileira pf_dora
```

A camada principal foi adicionada ao Nyxal, mas provedores remotos e contas externas só ficam conectados depois de configurar credenciais e verificar a conexão. A API não deve declarar credenciais válidas apenas porque um arquivo existe.

## 1. Configurar credenciais locais

Execute na máquina Nyxal:

```bash
cd ~/Nyxal
bash deploy/agent/configurar_nyxal_agent.sh
```

O script escreve somente em **~/.config/nyxal/nyxal.env** e **~/.hermes/.env**, com permissões restritas. Ele não escreve chaves no Git. O serviço **nyxal-api.service** já lê **~/.config/nyxal/nyxal.env**; depois de alterar o arquivo, reinicie a API:

```bash
systemctl --user restart nyxal-api.service
```

A criação/edição visual usa **NYXAL_GEMINI_IMAGE_MODEL=gemini-3.1-flash-image**. O modelo de texto padrão é **gemini-3.8-flash** (confirme a disponibilidade para sua conta e região na documentação oficial: https://ai.google.dev/gemini-api/docs/models).

O modo **auto** tenta Hermes, Gemini, Letta e depois o Qwen local. Hermes é o agente com ferramentas. Se Hermes estiver configurado para usar o Gemini, o Gemini será o modelo de raciocínio dentro desse agente; a API direta Gemini também pode ser habilitada como fallback. O roteador só chama provedores que estejam configurados.

## 2. Hermes Agent e Gemini

Instale e valide o Hermes seguindo a documentação oficial: https://hermes-agent.nousresearch.com/docs/getting-started/quickstart

```bash
hermes setup
hermes model
hermes
```

Primeiro confirme uma conversa normal. Depois, no Hermes, configure Google AI Studio/Gemini como provedor se esse for o modelo principal. Para expor a API ao Nyxal, a configuração usa:
- bind local **127.0.0.1**;
- porta **8642**;
- autenticação Bearer obrigatória;
- CORS desativado, pois o Core conversa server-to-server.

O segredo de acesso à API é configurado em **~/.hermes/.env** e o mesmo valor é guardado em **~/.config/nyxal/nyxal.env**. Não exponha a API Hermes na rede: ela oferece ferramentas com capacidade de terminal/arquivos. Use o backend Docker/sandbox do Hermes e confirme os controles de aprovação antes de ativar ações autônomas.

Documentação da API Hermes: https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server/

## 3. Letta para memória persistente

Escolha Letta Cloud ou uma instalação local/self-hosted. Crie um agente dedicado chamado Nyxal e configure:
- **LETTA_BASE_URL** (local normalmente **http://127.0.0.1:8283**; Cloud **https://api.letta.com**);
- **LETTA_AGENT_ID**;
- **LETTA_API_KEY** somente para a API que a exigir.

A integração lê os core-memory blocks e pode encaminhar uma interação para revisão de memória quando **LETTA_MEMORY_SYNC_ENABLED=true**. A sincronização inicia desligada. Antes de ativá-la, confira a política e o modelo do agente Letta; não inclua senhas, códigos de autenticação, tokens ou dados sensíveis na memória. A disponibilidade e a atualização da memória dependem de o servidor/agente Letta existir e estar acessível.

Docs oficiais: https://docs.letta.com/concepts/stateful-agents e https://docs.letta.com/api/resources/agents/subresources/messages

## 4. Gmail

A primeira integração é **somente leitura**: lista e lê mensagens autorizadas pela conta Google. Não envia, apaga, arquiva ou altera e-mails.

1. Ative a Gmail API em um projeto Google Cloud.
2. Crie credenciais OAuth para **Desktop App** e baixe o JSON.
3. Guarde-o em **~/.config/nyxal/google-oauth-client.json**; nunca dentro do repositório.
4. Instale as dependências opcionais e autorize:

```bash
cd ~/Nyxal
source .venv/bin/activate
python -m pip install -r deploy/agent/requirements-gmail.txt
python scripts/autorizar_gmail_nyxal.py
```

O navegador abrirá para consentimento. O token fica em **~/.config/nyxal/gmail-token.json** com permissão **0600**.

Endpoints locais:
- **GET /api/integracoes/gmail/status**
- **GET /api/integracoes/gmail/mensagens?q=is:unread%20newer_than:7d&limit=10**
- **GET /api/integracoes/gmail/mensagem?id=ID_DA_MENSAGEM**

A integração usa apenas **gmail.readonly**. Envio e edição precisam de escopos adicionais e confirmação explícita; não estão ativados nesta etapa. A API Gmail requer OAuth consentido pelo titular: https://developers.google.com/workspace/gmail/api/auth/web-server

## 5. WhatsApp

Para configurar a bridge pessoal oficial do Hermes Agent:
1. Execute **hermes gateway setup** e selecione WhatsApp.
2. Para a sessão pessoal, siga o assistente de pareamento e escaneie o QR no telefone em WhatsApp → Configurações → Aparelhos conectados → Conectar um aparelho.
3. Configure **WHATSAPP_ENABLED=true**, **WHATSAPP_MODE=bot** e **WHATSAPP_ALLOWED_USERS** com seu número/remetentes aprovados em **~/.hermes/.env**. Não use `*` para uma conta privada.
4. Instale/inicie o gateway com **hermes gateway install** ou rode **hermes gateway** em primeiro plano para testar.
5. Verifique com **hermes gateway status**.

A conta/telefone não está conectado até que o pareamento termine com sucesso. O bridge Baileys imita WhatsApp Web, é não oficial e tem risco de restrição; prefira um número dedicado e sem mensagens em massa.

Opções atuais:
- WhatsApp Cloud API oficial: exige Meta Business, credenciais e webhook HTTPS público; tipicamente usa um número de negócios separado.
- WhatsApp Agent Platform: só se a área **Settings → Agents** estiver disponível para sua conta e após criar o agente e obter a API key.
- Pareamento via WhatsApp Web/Baileys: pode exigir QR no seu telefone; é um caminho não equivalente à Cloud API oficial e deve ser avaliado quanto ao risco e às regras vigentes antes de usar sua conta pessoal.

Guias:
- https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/whatsapp-cloud.md
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/whatsapp.md

Antes de expor o gateway, instale as skills e identidade Nyxal com `bash deploy/agent/instalar_nyxal_agent.sh`. O instalador faz backup antes de substituir um `~/.hermes/SOUL.md` existente e pergunta antes de sobrescrever.

## 6. Sistema e serviços

**GET /api/agent/contexto** fornece observação local de CPU/load, memória, armazenamento da home, nomes de processos e unidades systemd em modo somente leitura. Também é possível consultar **GET /api/public/residencia** e **GET /api/public/status**.

A API executa consultas fixas e não fornece um executor arbitrário de shell. Reiniciar unidades, alterar arquivos, instalar software, enviar e-mail ou destruir/provisionar VPS continuam sendo ações separadas e exigem autorização explícita.

## 7. Skills

As skills versionadas vivem em **skills/** e podem ser instaladas em **~/.hermes/skills/** pelo script de instalação:

```bash
cd ~/Nyxal
bash deploy/agent/instalar_nyxal_agent.sh
```

Elas abrangem design, edição de imagem, edição audiovisual, desenvolvimento, observabilidade do sistema e triagem de e-mails. Skills fornecem procedimentos; a capacidade real depende das ferramentas e dos aplicativos instalados.

## 8. Voz feminina

O Nyxal Core já tem **NYXAL_KOKORO_VOICE=pf_dora** como padrão de TTS para voz feminina brasileira. O endpoint **POST /api/tts** continua usando Kokoro local. Se a voz local ou o modelo não estiverem instalados, o status do serviço deve ser tratado como indisponível — não como voz conectada.

Vozes Kokoro e instalação variam por distribuição: https://github.com/hexgrad/kokoro
