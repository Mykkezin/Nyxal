# Ordem de Engenharia — NyxOS

## Princípio

A engenharia do NyxOS avança da residência para a atuação e só depois para automação de atuação.

A ordem evita transformar a Nyxal em um processo com acesso irrestrito ao host antes que existam contratos, observabilidade, validação e reversibilidade suficientes.

## Sequência

### M5.8 — Dependências arquiteturais
Estado: proposta validada, não autoritativa.

- mapear dependências observadas entre componentes declarados na planta;
- validar cobertura por evidência direta;
- manter a planta autoritativa inalterada até revisão.

### M5.9 — Residência Linux
Estado: fechado operacionalmente.

- API como serviço residente;
- ciclo operacional residente como serviço separado;
- agrupamento em target NyxOS;
- reinício supervisionado por systemd;
- configuração local fora do Git;
- AE2 permanece desabilitada.

### M5.10 — Gateway de atuação do host
Estado: fechado.

- criar uma fronteira única para ações sobre o host;
- iniciar com allowlist vazio até M5.11 registrar as primeiras ações concretas;
- contratos explícitos de ação;
- allowlist de operações;
- validação de argumentos;
- resultado observável;
- nenhuma execução arbitrária de shell;
- política separada da decisão semântica.

### M5.11 — Controle de processos e aplicativos
Estado: fechado.
- listar processos como já observado pelo habitat;
- controlar apenas operações explicitamente registradas;
- iniciar/encerrar processos por capacidade;
- abrir aplicativos por identificadores conhecidos;
- abrir terminal por solicitação;
- registrar Delta e resultado da ação;
- sem transformar texto do Qwen em comando shell.

### M5.12 — Corpo térmico e ventilação
Estado: fechado.
- consolidar sensores térmicos reais;
- detectar tendência e estresse térmico;
- definir estados corporais térmicos;
- criar interface de atuação para ventoinhas somente onde o host expuser controle suportado;
- limites de segurança, histerese e fallback;
- começar com modo supervisionado antes de qualquer controle automático contínuo.

### M5.13 — Fisiologia operacional
Estado: fechado.
- heartbeat formal do NyxOS;
- latência e regularidade dos ciclos;
- estado de presença;
- estados corporais como normal, estresse térmico e recuperação;
- conceito de febre como estado derivado de evidências térmicas e temporais;
- persistência e Delta dos estados.

### M5.14 — Plano central de controle
Estado: em implementação e validação.
- unificar observação, decisão e atuação;
- expor uma superfície principal de comandos;
- preservar a separação entre intenção, capacidade e executor;
- permitir que a Nyxal seja o ponto principal da máquina sem conceder autoridade implícita de evolução.

### M5.15 — Presença de máquina
- integração de boot/login e disponibilidade do serviço;
- interface principal persistente;
- voz como canal de entrada/saída;
- retomada segura após reinicialização;
- observabilidade da saúde de toda a pilha.

## Auto-evolution

AE1 → AE5 permanece como camada de descoberta, experimentação governada, avaliação e acúmulo de evidências.

Ela evolui em paralelo ao Habitat, mas não recebe automaticamente poder sobre a nova camada de atuação.

Nenhuma AE6 é criada por esta sequência.

## Ordem de autoridade

A ordem de engenharia é:

residência
→ atuação controlada
→ controle de processos/aplicativos
→ corpo térmico
→ fisiologia operacional
→ plano central de controle
→ presença de máquina

A autorização de integração permanece separada em N9.
