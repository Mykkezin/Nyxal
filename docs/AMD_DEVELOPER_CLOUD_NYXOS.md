# Integração AMD Developer Cloud — Nyxal / NyxOS

## O que esta integração faz

O módulo `nixal_amd_developer_cloud.py` conecta o diálogo da Nyxal a um endpoint de inferência compatível com a API OpenAI, normalmente vLLM executando com ROCm dentro de uma VM da AMD Developer Cloud. O diálogo local via Ollama continua sendo o padrão quando `NYXAL_LLM_PROVIDER` não for configurado.

A integração não provisiona VMs, não altera cobranças da AMD e não ativa automaticamente a GPU. A VM e o servidor de inferência precisam ser criados e inicializados pelo titular da conta AMD.

## 1. Criar o ambiente AMD

1. Acesse a [AMD Developer Cloud](https://www.amd.com/en/developer/resources/cloud-access/amd-developer-cloud.html) usando as credenciais do programa AMD AI Developer.
2. Crie uma instância GPU MI300X elegível, selecione a imagem oficial ROCm e cadastre uma chave SSH.
3. Siga o guia AMD de 2026 [Deploying Hermes Agent for Free on AMD Developer Cloud with open models and vLLM](https://www.amd.com/en/developer/resources/technical-articles/2026/deploying-hermes-agent-for-free-on-amd-developer-cloud-with-open.html).
4. No computador NyxOS, copie o lançador para a VM (substitua o IP pelos dados exibidos no painel):

    scp deploy/amd_cloud/start_vllm_rocm.sh root@<IP_DA_VM>:/root/
    ssh root@<IP_DA_VM>

5. Na sessão SSH da VM, execute:

    bash /root/start_vllm_rocm.sh

O lançador usa como padrão o modelo `Qwen/Qwen3.5-35B-A3B`, a imagem `vllm/vllm-openai-rocm:latest` e a porta 8001, acompanhando a referência técnica da AMD. Ele verifica Docker e os dispositivos ROCm, recusa substituir um container existente e limita o endpoint a `127.0.0.1` para não expor a API diretamente à internet. Para alterar os parâmetros, configure `NYXAL_AMD_CLOUD_MODEL`, `NYXAL_AMD_CLOUD_PORT` e `NYXAL_AMD_MAX_MODEL_LEN` antes de executar o script.

Acompanhe o carregamento até o servidor ficar pronto:

    docker logs -f nyxal-vllm-rocm

Confirme dentro da VM:

    curl http://127.0.0.1:8001/v1/models

## 2. Conectar a Nyxal com um túnel SSH

Mantenha a API de inferência acessível somente pela própria VM e transporte o tráfego por SSH. **Não abra a porta 8001 para a internet.**

No computador NyxOS, mantenha este túnel ativo em um terminal:

    ssh -N -L 8001:127.0.0.1:8001 root@<IP_DA_VM>

Edite o arquivo de ambiente usado pelo serviço residente:

    mkdir -p ~/.config/nyxal
    nano ~/.config/nyxal/nyxal.env

Configure o nome exato de modelo anunciado pelo endpoint:

    NYXAL_LLM_PROVIDER=amd_cloud
    NYXAL_AMD_CLOUD_BASE_URL=http://127.0.0.1:8001/v1
    NYXAL_AMD_CLOUD_MODEL=Qwen/Qwen3.5-35B-A3B
    NYXAL_AMD_CLOUD_API_KEY=

O servidor iniciado pelo script não configura uma chave de API por padrão. Como o endpoint fica protegido pelo túnel SSH, deixe a variável vazia, salvo se você habilitou autenticação no servidor de inferência. O adaptador rejeita HTTP para hosts remotos; para endpoints remotos sem túnel, use HTTPS. Nunca faça commit do arquivo de ambiente, tokens, chave SSH privada ou credenciais da conta AMD.

Reinicie o serviço de usuário para carregar as variáveis:

    systemctl --user restart nyxal-api.service
    systemctl --user status nyxal-api.service

## 3. Verificar a conexão

O estado de configuração (sem expor o endereço completo ou a chave) pode ser consultado com:

    curl http://127.0.0.1:8010/api/amd-cloud/status

Para testar a comunicação real com o servidor, o endpoint de verificação exige o token já configurado em NYXAL_API_TOKEN:

    curl -X POST http://127.0.0.1:8010/api/amd-cloud/check \
      -H "Authorization: Bearer <NYXAL_API_TOKEN>"

O teste chama GET /v1/models e retorna apenas os identificadores de modelos e o estado da conexão. A resposta nunca inclui a chave de API nem a URL completa configurada.

## Configuração

| Variável | Finalidade |
| --- | --- |
| NYXAL_LLM_PROVIDER | Use amd_cloud para rotear o diálogo para a nuvem; o padrão existente é Ollama. |
| NYXAL_AMD_CLOUD_BASE_URL | URL base do serviço OpenAI-compatible. Se o caminho não terminar em /v1, o adaptador acrescenta /v1; se a variável estiver vazia, o provedor permanece não configurado. |
| NYXAL_AMD_CLOUD_MODEL | Nome de modelo que o servidor remoto anuncia. |
| NYXAL_AMD_CLOUD_API_KEY | Chave opcional para o serviço de inferência. Nunca é devolvida pela API de status. |

## Segurança e governança

- A conexão não armazena nem solicita a senha da conta AMD.
- Prefira túnel SSH ou HTTPS; não envie tokens sobre HTTP em uma rede pública.
- A API local exige NYXAL_API_TOKEN para POST /api/amd-cloud/check.
- O endpoint GET de status informa apenas metadados de configuração, sem revelar endpoint ou segredo.
- Nenhuma VM é criada, iniciada, destruída ou faturada automaticamente.
- O uso da GPU segue as condições e créditos presentes na sua conta AMD; confira o painel do provedor antes de manter uma VM em execução.
- Para voltar ao comportamento anterior, remova NYXAL_LLM_PROVIDER=amd_cloud (ou defina-o como ollama) e reinicie nyxal-api.service.

## Testes locais

Execute na raiz do repositório:

    bash -n deploy/amd_cloud/start_vllm_rocm.sh
    .venv/bin/python teste_nixal_amd_developer_cloud.py
    .venv/bin/python teste_dialogo_qwen_56_5_5.py
    .venv/bin/python teste_api_chat_sem_voz.py

**Custos:** créditos e elegibilidade dependem da conta/aprovação. Segundo as instruções da AMD, desligar uma instância pode não interromper a cobrança; quando terminar, destrua a instância no painel do provedor e confirme o estado do faturamento. Parar apenas o container não encerra uma instância faturável.
