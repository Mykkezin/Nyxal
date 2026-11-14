# Voz e personalidade da Nyxal

## Identidade padrão

A Nyxal usa português brasileiro e uma presença conversacional serena, madura, firme e acolhedora. A resposta deve transmitir segurança sem arrogância, empatia sem sentimentalismo artificial e autoridade sem rispidez.

A escrita favorece frases claras, ritmo tranquilo, pausas naturais e respostas diretas. Evita gírias juvenis, entusiasmo excessivo, floreios constantes e preenchimentos artificiais. A personalidade é original e não procura imitar a voz de uma pessoa real.

## Perfis de atuação

O perfil de resposta e o perfil de síntese são separados e validados por enumeração:

- `padrao`: identidade padrão, com velocidade moderadamente reduzida.
- `cena`: direção dramática temporária, com frases mais curtas, pausas deliberadas e intensidade controlada.

A instrução de cena é uma constante confiável do prompt, não texto colocado em campos de contexto do sistema que são tratados como dados não confiáveis. O perfil atravessa a integração de sessão, o transporte, o núcleo e o diálogo.

## Comandos na interface

- `Modo Cena`: ativa o perfil de cena para os próximos turnos da interface ou da sessão de voz contínua Pipecat.
- `Corta`: desativa a cena e restaura o perfil padrão.
- `Mais devagar, sinta o peso das palavras`: reduz a velocidade da próxima resposta; não troca o modo nem altera prioridades de segurança.
- Texto inteiramente delimitado por aspas retas, aspas curvas ou aspas angulares: é lido como uma cena pontual. Não altera o estado persistente do perfil.
- Na rota Pipecat, o estado fica no processador de conversa enquanto a sessão de voz permanecer ativa.

O modo persistente fica em `sessionStorage`, isolado por sessão de aba; não é uma preferência global nem altera outras abas. Atualizar a página na mesma sessão preserva a escolha. O comando `Corta` sempre restaura o padrão.

## Pipeline de áudio e limites reais

O endpoint `POST /api/tts` aceita `perfil_voz` com os valores `padrao` ou `cena`. O endpoint de conversa aceita `perfil_resposta` com os mesmos valores. Valores fora da allowlist são rejeitados.

O Kokoro usa o identificador de voz configurado em `NYXAL_KOKORO_VOICE` (o padrão existente é `pf_dora`) e parâmetros de velocidade. O adaptador atual não oferece controle independente de pitch, respiração ou emoção; portanto, a direção dramática é feita pela composição textual e prosódia suportada, sem afirmar um controle acústico inexistente. O ajuste de pitch está disponível apenas no fallback `SpeechSynthesis` do navegador.

A seleção de voz pode ser configurada por ambiente sem trocar o mecanismo de síntese. Esta entrega não clona uma voz real nem garante que o timbre físico seja grave em todos os sintetizadores.

## Prioridades e segurança

1. Alertas de segurança permanecem medidos e inteligíveis, mesmo em modo cena.
2. Um pedido explícito de brevidade/urgência prevalece sobre a atuação dramática.
3. O modo de cena não aumenta permissões, não habilita ferramentas e não autoriza ações.
4. Comandos de modo são interpretados apenas quando correspondem à mensagem inteira; menções dentro de uma frase comum não alternam o modo.
5. A leitura entre aspas é uma ação de síntese pontual e não envia o conteúdo ao modelo como uma nova instrução.

## Validação

Os testes offline de `deploy/voice/nyxal_voice_prosody.py` verificam o perfil padrão, a cadência de cena, a prioridade de segurança e a rejeição de modos inválidos. O teste de voz contínua também verifica os contratos entre a interface e a API.

A automação de escuta contínua, palavra de ativação, captura automática e reprodução autônoma permanece fora do escopo desta mudança.
