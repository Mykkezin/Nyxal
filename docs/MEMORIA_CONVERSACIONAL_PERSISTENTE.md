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

## Diagnóstico

A resposta estruturada do núcleo contém \`memoria_conversacional_estado\`:
- \`persistencia_ativa\`: armazenamento local validado e disponível.
- \`memoria_volatil\`: o processo usa somente RAM.
- \`memoria_degradada\`: não continue gravando; preserve o arquivo e investigue a causa.

Para mudar o local do arquivo, defina \`NYXAL_CONVERSATION_MEMORY_PATH\` no ambiente do serviço. O diretório deve ser acessível ao usuário que executa a API e não deve ser um link simbólico.

## Validação

\`teste_nixal_memoria_conversacional.py\` cobre reinício de instância, janela de mensagens, permissões, corrupção, schema desconhecido, limpeza e concorrência entre instâncias. \`teste_nucleo_contexto_persistente.py\` cobre a restauração do histórico pelo núcleo sem iniciar um modelo real.

A persistência é local ao computador e não sincroniza sessões entre máquinas. Nenhum banco vetorial ou framework de agente adicional é introduzido.
