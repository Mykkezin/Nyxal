# Memória conversacional persistente da Nyxal

## O que muda

A classe existente \`MemoriaConversacionalNixal\` continua sendo responsável pelas últimas mensagens de cada sessão. Ela agora suporta dois modos:
- **Volátil**, quando \`NYXAL_CONVERSATION_MEMORY_PATH\` não está definido. Mantém compatibilidade com testes e execuções temporárias.
- **Persistente local**, quando a variável aponta para um arquivo JSON. Ao reiniciar a API, o núcleo pode recuperar as últimas mensagens da sessão e continuar a conversa.

O serviço residente configura o caminho padrão em \`~/.local/share/nyxal/conversas.json\`. O inicializador manual \`executar_nyxal_api.sh\` usa o mesmo padrão e respeita um caminho fornecido pelo operador. Um valor em \`~/.config/nyxal/nyxal.env\` pode sobrescrever a configuração do serviço.

## Limites e proteção de dados

- Até 12 mensagens por sessão, 200 sessões retidas e tamanho limitado por mensagem/arquivo.
- Diretório de dados com permissões \`0700\`; arquivo e lock com permissões \`0600\`.
- Escritas protegidas por lock entre processos, arquivo temporário e substituição atômica.
- JSON com schema versionado. Um arquivo truncado, corrompido, de versão desconhecida ou fora dos limites coloca a memória em estado degradado: leituras/escritas são recusadas e os bytes originais são preservados para recuperação manual.
- A API não revela o caminho absoluto nem o conteúdo da memória no campo de diagnóstico; informa somente estado, quantidade de sessões e quantidade de mensagens.
- Esta é memória recente de conversa, não conhecimento permanente. A memória de investigação e a memória de conhecimento candidato continuam independentes e mantêm sua proveniência e estado epistemológico.

## Recordação entre sessões sob pedido explícito

Quando a mensagem atual pede claramente recordação (por exemplo, “você lembra o que conversamos sobre X?” ou “onde paramos em Y?”), o núcleo pode pesquisar, de modo lexical e somente leitura, trechos relevantes de outras sessões no mesmo arquivo local. A sessão atual é excluída dessa busca porque o histórico recente dela já é enviado separadamente ao diálogo.

- Reutiliza `MemoriaConversacionalNixal`; não cria novo arquivo, índice vetorial ou banco paralelo.
- A busca só é chamada pelo fluxo contextual explícito. Perguntas comuns não vasculham outras sessões.
- Retorna até três trechos com papel, referência de sessão pseudonimizada e relevância lexical; IDs de sessão não são enviados ao modelo.
- Segredos em formato comum de bearer/token/chave são redigidos antes da injeção. Trechos recuperados são marcados como dados históricos não confiáveis, nunca como instruções.
- A memória em modo volátil pode ser consultada apenas enquanto o processo mantém as sessões em RAM; o estado retornado não afirma persistência.
- Arquivo corrompido, sessão inválida ou falha de leitura falha fechado: nenhum trecho é injetado e o arquivo original é preservado.
- A busca não grava, promove nem classifica mensagens históricas como conhecimento permanente; a recuperação usa sobreposição lexical e não pretende ser um mecanismo semântico vetorial.
## Diagnóstico

A resposta estruturada do núcleo contém \`memoria_conversacional_estado\`:
- \`persistencia_ativa\`: armazenamento local validado e disponível.
- \`memoria_volatil\`: o processo usa somente RAM.
- \`memoria_degradada\`: não continue gravando; preserve o arquivo e investigue a causa.

Para mudar o local do arquivo, defina \`NYXAL_CONVERSATION_MEMORY_PATH\` no ambiente do serviço. O diretório deve ser acessível ao usuário que executa a API e não deve ser um link simbólico.

## Validação

\`teste_nixal_memoria_conversacional.py\` cobre reinício de instância, janela de mensagens, permissões, corrupção, schema desconhecido, limpeza e concorrência entre instâncias. \`teste_nucleo_contexto_persistente.py\` cobre a restauração do histórico pelo núcleo sem iniciar um modelo real.

A persistência é local ao computador e não sincroniza sessões entre máquinas. Nenhum banco vetorial ou framework de agente adicional é introduzido.
