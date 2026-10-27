# Evolução da inteligência da Nyxal — plano técnico

## Objetivo

Elevar a Nyxal de uma interface residente com um núcleo conversacional para um sistema pessoal de IA confiável, com roteamento de modelos, contexto recuperável, ferramentas com permissões, avaliação contínua e conversa natural. A meta não é declarar paridade com GPT, Grok ou Gemini sem medições: é tornar cada capacidade verificável e melhorar por etapas.

## Diagnóstico de arquitetura

A Nyxal já possui peças úteis: nixal_agent_hub.py (Qwen/local, Gemini, Hermes e Letta, dependendo da configuração), núcleo conversacional, módulos persistentes de memória e investigação, registro Delta, runtime residente, observabilidade, gateway de atuação, endpoints VPS e uma capacidade visual. O primeiro trabalho é conectar essas peças pelo fluxo real da conversa e expor seu estado — não criar um segundo sistema de memória ou de ferramentas.

O OpenJarvis é uma referência de arquitetura, não um modelo de linguagem que torne qualquer aplicação automaticamente mais inteligente. O projeto organiza a pilha em cinco primitivas: inteligência/modelos, engine de inferência, agentes, ferramentas e memória, e aprendizagem baseada em traces. A arquitetura também destaca fallback entre engines, recuperação documental com atribuição de fontes, telemetry e avaliação de agentes. Referências: <https://github.com/open-jarvis/OpenJarvis> e <https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/overview.md>.

## Prioridades

### P0 — experiência e capacidades visíveis

- Recuperar indicadores do sistema no modo de voz: CPU, RAM, disco, GPU e temperaturas, sempre exibindo “—”/indisponível quando o hardware ou driver não fornecer leitura.
- Recuperar clima com atualização periódica, relógio e reflexões originais a cada três horas.
- Expor conversa por texto, acesso rápido à VPS, modos de trabalho de cibersegurança defensiva e Data Science, e geração visual na própria interface.
- Manter a captura de voz, a interrupção por fala e o recolhimento visual independentes dos painéis auxiliares.

### P1 — modelos e qualidade conversacional

- Definir contrato comum para engines/provedores: geração, streaming, modelos disponíveis, saúde, timeout, erro, limite de contexto e metadados de uso.
- Suportar provedores opcionais em modo configurável, inclusive APIs compatíveis com OpenAI quando habilitadas. Credenciais devem existir somente no ambiente/gerenciador de segredos, nunca no Git.
- Preferir resposta em streaming, para reduzir latência percebida e permitir renderizar texto enquanto a voz é preparada.
- Medir naturalidade em português, continuidade entre turnos, latência do primeiro token/áudio, interrupções, alucinações e recuperação depois de falha de provedor.
- Preservar fallback local quando um serviço remoto não estiver configurado ou estiver indisponível.

### P2 — recuperação de contexto e memória

- Fazer o núcleo recuperar contexto relevante de memória conversacional persistente, investigações, episódios e conhecimento já existentes.
- Preservar origem, horário, confiança e estado de validação dos trechos recuperados.
- Deduplicar contexto e limitar o tamanho enviado ao modelo; começar com busca textual/SQLite FTS5 e avaliar busca vetorial apenas com benchmarks.
- Evitar armazenar inferências como fatos confirmados e evitar memória paralela redundante.

### P3 — ferramentas e especialidades

- Descrever cada capacidade por contrato: nome, schema de entrada/saída, escopo, permissões, timeout, auditoria e condições de aprovação.
- Criar fluxos de especialidade para cibersegurança defensiva, Data Science, engenharia de software, pesquisa e geração visual; cada fluxo deve fornecer método, ferramentas reais e critérios de conclusão, não apenas um rótulo.
- Manter a VPS e qualquer ação de sistema atrás do gateway de atuação, com operações permitidas explícitas. Não conceder shell irrestrito ao modelo.

### P4 — traces, avaliação e aprendizagem

- Registrar traces estruturados: pergunta, modelo/engine selecionado, contexto recuperado, ferramentas invocadas, resultados, latência, erros e avaliação.
- Montar uma bateria reproduzível em português: factualidade, raciocínio, memória, uso de ferramentas, segurança, qualidade visual e conversação por voz.
- Usar os ciclos AE/LLC para formular hipóteses e avaliar melhorias, primeiro em modo de proposta; mudanças automáticas devem passar por testes, limites de recursos e rollback.
- Comparar cada versão com uma linha de base antes de promover roteamento, prompts ou modelos.

## Critérios de aceite

Uma melhoria só é considerada concluída quando existe: (1) contrato e fonte identificáveis; (2) teste automatizado; (3) comportamento observado em máquina real quando depende de hardware, microfone, driver ou credenciais; (4) métrica comparável antes/depois; (5) fallback e mensagem explícita quando indisponível.

O framework, a memória e o roteamento podem aumentar muito a utilidade do sistema, mas a capacidade-base de raciocínio, conhecimento e linguagem depende dos modelos realmente configurados, do contexto disponível e das ferramentas que funcionam. A Nyxal não deve alegar paridade com modelos de fronteira sem avaliações que a sustentem.
