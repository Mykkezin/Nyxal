# Integração AMD Developer Cloud — Nyxal / NyxOS

## O que esta integração faz

O módulo `nixal_amd_developer_cloud.py` conecta o diálogo da Nyxal a um endpoint de inferência compatível com a API OpenAI, normalmente vLLM executando com ROCm dentro de uma VM da AMD Developer Cloud. O diálogo local via Ollama continua sendo o padrão quando `NYXAL_LLM_PROVIDER` não for configurado.

A integração não provisiona VMs, não altera cobranças da AMD e não ativa automaticamente a GPU. A VM e o servidor de inferência precisam ser criados e inicializados pelo titular da conta AMD.

## 1. Criar o ambiente AMD

1. Entre na [AMD Developer Cloud](https://www.amd.com/en/developer/resources/cloud-access/amd-developer-cloud.html) usando a conta do programa de desenvolvedores AMD.
2. Crie uma VM GPU elegível e escolha uma imagem ROCm/vLLM, quando disponível.
3. Siga o guia oficial [How to Get Started on the AMD Developer Cloud](https://www.amd.com/en/developer/resources/technical-articles/2025/how-to-get-started-on-the-amd-developer-cloud-.html) para iniciar a VM e adicionar uma chave SSH.
4. Inicie um servidor de inferência com API OpenAI-compatible e confirme que o endpoint /v1/models responde dentro da VM.

Os nomes de modelos válidos dependem do modelo instalado e do nome que o servidor anuncia. Configure `NYXAL_AMD_CLOUD_MODEL` com esse identificador exato.

## 2. Conectar a Nyxal com um túnel SSH

A opção recomendada é manter a API de inferência acessível somente na VM e transportar o tráfego por SSH, sem abrir a porta do modelo publicamente.

No computador que executa a Nyxal, abra um terminal e mantenha este túnel ativo, substituindo o usuário e o IP pelos dados exibidos no painel da VM:

    ssh -N -L 8000:127.0.0.1:8000 <usuario-ssh>@<ip-publico-da-vm>

O servidor de inferência remoto precisa escutar na porta 8000 da própria VM. Se utilizar outra porta, altere ambos os números no túnel e na configuração abaixo.

Edite o arquivo de ambiente já usado pelo serviço residente:

    mkdir -p ~/.config/nyxal
    nano ~/.config/nyxal/nyxal.env

Adicione as variáveis. Use o nome exato do modelo disponível na VM:

    NYXAL_LLM_PROVIDER=amd_cloud
    NYXAL_AMD_CLOUD_BASE_URL=http://127.0.0.1:8000/v1
    NYXAL_AMD_CLOUD_MODEL=Qwen/Qwen2.5-7B-Instruct
    NYXAL_AMD_CLOUD_API_KEY=

Se a VM/servidor exigir uma chave, defina NYXAL_AMD_CLOUD_API_KEY nesse arquivo. Não faça commit do arquivo de ambiente, tokens, chave SSH privada ou credenciais da conta AMD.

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

    .venv/bin/python teste_nixal_amd_developer_cloud.py
    .venv/bin/python teste_dialogo_qwen_56_5_5.py
    .venv/bin/python teste_api_chat_sem_voz.py
