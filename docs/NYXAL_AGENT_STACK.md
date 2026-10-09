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

A camada principal foi adicionada ao Nyxal, mas provedores remotos e contas externas só ficam conectados depois de configurar credenciais e verificar a conexão. A API não deve declarar credenciais válidas apenas porque um arquivo existe. O modelo visual configurado é **gemini-nano-banana-2.1**, identificado na documentação oficial de modelos do Gemini API.

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

A criação/edição visual usa **NYXAL_GEMINI_IMAGE_MODEL=gemini-nano-banana-2.1**. O modelo de texto padrão é **gemini-3.8-flash** (confirme a disponibilidade para sua conta e região na documentação oficial: https://ai.google.dev/gemini-api/docs/models).

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

Para compartilhar essa memória com skills executadas pelo Hermes no host local:
```bash
python3 ~/Nyxal/scripts/nyxal_letta_memory.py recall
python3 ~/Nyxal/scripts/nyxal_letta_memory.py remember --summary "Resumo duradouro aprovado pelo operador"
```

O comando `recall` é somente leitura. `remember` só funciona quando `LETTA_MEMORY_SYNC_ENABLED=true`, pede ao agente Letta que atualize a memória com o resumo e bloqueia gravação se a sincronização estiver desligada. O Hermes precisa ter acesso ao diretório local `~/Nyxal` e ao arquivo `~/.config/nyxal/nyxal.env`; em sandbox isolado, esses caminhos podem não estar disponíveis. Não declare que consultou a memória se o comando falhar.

Docs oficiais: https://docs.letta.com/concepts/stateful-agents e https://docs.letta.com/api/resources/agents/subresources/messages

## 4. Google Workspace (Gmail, Calendar, Contatos e Drive)

A integração do Google Workspace começa em **somente leitura**: Gmail (mensagens), Calendar (eventos dos próximos 14 dias), Contacts/People (nomes, e-mails e telefones) e Drive (metadados, sem baixar o conteúdo). Não envia, apaga, arquiva ou altera e-mails, agenda, contatos ou arquivos.

1. Ative as APIs **Gmail**, **Google Calendar**, **People** e **Google Drive** no mesmo projeto Google Cloud.
2. Crie credenciais OAuth para **Desktop App** e baixe o JSON.
3. Guarde-o em **~/.config/nyxal/google-oauth-client.json**; nunca dentro do repositório.
4. Instale as dependências opcionais e autorize:

```bash
cd ~/Nyxal
source .venv/bin/activate
python -m pip install -r deploy/agent/requirements-gmail.txt
python scripts/autorizar_gmail_nyxal.py
```

O navegador abrirá para consentimento. O token fica em **~/.config/nyxal/google-workspace-token.json** com permissão **0600**. Como o conjunto de permissões inclui Calendar, Contacts e Drive, o token anterior só-Gmail não basta: execute a autorização novamente e conceda os quatro escopos somente leitura.

Endpoints locais:
- **GET /api/integracoes/google/status**
- **GET /api/integracoes/gmail/mensagens?q=is:unread%20newer_than:7d&limit=10**
- **GET /api/integracoes/gmail/mensagem?id=ID_DA_MENSAGEM**
- **GET /api/integracoes/google/agenda?days=14&limit=20**
- **GET /api/integracoes/google/contatos?limit=25**
- **GET /api/integracoes/google/drive?limit=25**

Os escopos são exclusivamente **gmail.readonly**, **calendar.readonly**, **contacts.readonly** e **drive.metadata.readonly**. Não há envio de e-mail, alteração de agenda/contatos, exclusão de mensagens nem download de conteúdo do Drive. O titular da conta deve aprovar OAuth; APIs e consentimento são configurados em Google Cloud: https://developers.google.com/workspace/gmail/api/auth/web-server

## 5. WhatsApp

1. Execute **bash deploy/agent/configurar_nyxal_agent.sh** e responda às perguntas de WhatsApp. O script grava o modo escolhido e uma allowlist com números específicos — nunca libera todos os remetentes.
2. Execute **hermes whatsapp**. O assistente instala dependências e exibe o QR para o telefone.
3. No celular, abra WhatsApp → Configurações → Aparelhos conectados → Conectar um aparelho e leia o QR.
4. Inicie o serviço com **hermes gateway install** e **hermes gateway start**; confira com **hermes gateway status**.

Escolha **self-chat** para conversar com a Nyxal através da sua própria conta vinculada, ou **bot** se tiver um número separado para o agente. O bridge Hermes usa Baileys/WhatsApp Web, não a API oficial da Meta, e carrega um pequeno risco de restrição da conta; não use mensagens em massa nem automatize contato com pessoas que não iniciaram a conversa. O diretório **~/.hermes/platforms/whatsapp/session** contém credenciais da sessão e nunca deve entrar no Git.

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

**GET /api/agent/contexto** observa CPU/load average, RAM, armazenamento da home, processos, serviços systemd do usuário/sistema, GPU/VRAM via sysfs (e `nvidia-smi` quando disponível) e sensores térmicos via `lm-sensors`/sysfs — tudo em modo somente leitura. Telemetria de GPU/temperatura aparece como indisponível quando o driver/sensor não a fornece; não há valores simulados. Também é possível consultar **GET /api/public/residencia** e **GET /api/public/status**.

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
