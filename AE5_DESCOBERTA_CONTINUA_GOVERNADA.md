# AE5 — DESCOBERTA CONTÍNUA GOVERNADA DE VALOR ECONÔMICO

## 1. Finalidade

AE5 é a camada de descoberta contínua de valor econômico do Nyxal.

Seu objetivo não é acumular limitações técnicas. É observar sinais persistentes vindos das camadas já existentes e identificar oportunidades que possam produzir, preservar ou proteger valor econômico mensurável.

Pergunta central:

Existe uma oportunidade tecnicamente sustentada que possui uma hipótese explícita de valor econômico, evidência observável e base suficiente para merecer formalização?

AE5 deve transformar:

sinal técnico
→ hipótese de valor
→ evidência observada
→ repetição e consistência
→ oportunidade econômica candidata
→ formalização sob governança

Não é permitido transformar automaticamente:

sinal técnico
→ valor monetário

Sem ligação explícita entre fenômeno técnico e métrica econômica, o valor econômico permanece desconhecido.

## 2. Posição arquitetural

Habitat
→ Ciclo residente
→ AE1 descoberta técnica
→ AE2 experimento isolado
→ AE3 comparação e aprendizagem
→ AE4 orquestração e auditoria
→ AE5 descoberta contínua de valor econômico
→ formalização
→ N9
→ autorização explícita
→ integração controlada

AE5 é uma camada de interpretação, acumulação e observabilidade. Não é uma nova engine de execução.

## 3. Auditoria do estado anterior

### AE1

AE1 persiste oportunidades fora da árvore Git em Nyxal-evolution-opportunities.
A identidade atual da oportunidade depende de ciclo_id + limitação + hipótese. Portanto, a mesma limitação e hipótese podem gerar oportunidades distintas em ciclos distintos.
Isso é útil para preservar proveniência, mas gera potencial de duplicação semântica.

### AE4

AE4 persiste auditorias em Nyxal-evolution-ae4.
Quando não existe identificador persistido ligando uma oportunidade AE1 a uma solicitação AE2, a relação é deliberadamente somente observacional.
AE5 não pode converter coincidência temporal em causalidade.

### N9

N9 persiste solicitações em Nyxal-evolution-requests.
Uma solicitação pronta para experimento contém hipótese, objetivo, métrica, direção de melhoria e baseline.
Isso é formalização técnica. Não é prova automática de retorno econômico.

### Conclusão da auditoria

Os mecanismos atuais permitem reconciliar fontes, mas a AE5 anterior media principalmente repetição técnica. O novo contrato acrescenta uma camada econômica explícita sem criar uma segunda memória nem substituir N9.

## 4. Diferença em relação à AE5 anterior

A política anterior classificava maturidade por repetição observada, usando como referência pelo menos 3 observações e 2 sucessos em uma janela de ciclos.

Esse critério continua válido apenas como indicador de persistência técnica.

Persistência técnica NÃO significa valor econômico.

Uma otimização pode ser recorrente e ainda:
- não possuir impacto econômico;
- possuir impacto econômico desconhecido;
- ter benefício menor que o custo de implementação;
- possuir benefício técnico mas nenhum mecanismo econômico demonstrado;
- reduzir um custo cuja unidade econômica ainda não foi definida;
- possuir ganho com risco que anule o benefício.

## 5. Fontes aceitas

AE5 pode consumir somente dados persistidos pelas camadas existentes ou entradas externas que tenham contrato explícito.

AE1 fornece limitação, hipótese, ciclo, prioridade e evidências registradas.
AE4 fornece auditoria, ciclo, etapas, estados, vínculos e resultado observacional.
N9 fornece solicitações formais e seus campos de experimento.
AE2 e AE3 podem fornecer resultados, comparações, baseline e aprendizagem já persistidos.

AE5 não deve executar novamente AE1, AE2 ou AE3 para fabricar evidência.

## 6. Modelo mínimo de valor econômico

Cada linha econômica deve distinguir:

problema técnico
hipótese de valor
mecanismo de valor
tipo de valor
métrica econômica
unidade
direção de melhoria
referência econômica ou baseline fornecido
evidências
incertezas

### Tipos de valor

receita — geração ou proteção de receita;
custo — redução de custo operacional;
produtividade — redução mensurável de tempo ou esforço;
capacidade — aumento de capacidade útil;
confiabilidade — redução mensurável de falhas ou indisponibilidade;
risco — redução mensurável de perda esperada ou exposição;
eficiência de recursos — energia, computação, armazenamento ou recursos equivalentes;
capital — melhor utilização de capacidade ou ativos;
opcionalidade — capacidade que abre oportunidade econômica futura sem valor monetário demonstrado no presente.

Opcionalidade nunca deve ser apresentada como receita realizada ou economia realizada.

## 7. Regra de ligação econômica

Relação aceitável:

redução de CPU
→ menor consumo computacional
→ métrica econômica explicitamente definida

Relação insuficiente:

redução de CPU
→ isso gera economia

No segundo caso, valor econômico permanece desconhecido.

AE5 não inventa salário, preço, custo por hora, tarifa, receita, ROI ou qualquer coeficiente econômico ausente nas fontes.

## 8. Estados da descoberta econômica

sem_valor_identificado
→ valor_candidato
→ valor_observacional
→ valor_sustentado
→ maduro_para_formalizacao

sem_valor_identificado: existe sinal técnico, mas nenhuma ligação econômica válida.

valor_candidato: existe hipótese plausível de mecanismo econômico, ainda sem evidência suficiente.

valor_observacional: existe relação econômica explicitamente declarada e pelo menos uma observação compatível.

valor_sustentado: a relação econômica foi observada em ciclos distintos e possui evidência consistente.

maduro_para_formalizacao: existe mecanismo de valor, métrica, unidade, direção, referência válida, evidência repetida e ausência de contradição não resolvida.

Mesmo no estado maduro_para_formalizacao, AE5 não cria automaticamente solicitação N9.

## 9. Identidade econômica

A unidade persistente não deve depender somente de limitação + hipótese.

A identidade econômica deve usar, quando disponíveis:

limitação normalizada
hipótese normalizada
mecanismo de valor normalizado
tipo de valor
métrica econômica normalizada
unidade normalizada
direção de melhoria

Quando esses campos ainda não existirem, o registro pode continuar ligado a uma oportunidade técnica, mas deve ser marcado como valor_economico_nao_determinado.

Não é permitido inventar campos econômicos para tornar duas oportunidades iguais.

## 10. Deduplicação semântica

### Nível 1 — determinístico

Normalizar textos por espaços redundantes, casefold, Unicode e pontuação consistente, preservando os valores originais para auditoria.

Isso elimina duplicação exata sem apagar proveniência.

### Nível 2 — possível duplicata semântica

Quando duas linhas parecem representar a mesma oportunidade econômica, mas não possuem identidade determinística igual, AE5 pode marcá-las como possível_duplicata_semantica.

Possível duplicata não significa fusão.

Parecido não significa igual.

A marcação deve preservar:

IDs originais
fontes
diferenças
evidência que motivou a aproximação
estado da decisão

Qualquer fusão posterior deve preservar toda a proveniência.

## 11. Repetição não é valor

AE5 deve registrar separadamente:

persistencia_tecnica
consistencia_resultado
ligacao_economica
qualidade_evidencia
maturidade_economica

3 observações e 2 sucessos podem indicar persistência. Não podem, sozinhos, provar valor econômico.

## 12. Cadência

AE5 deve ser contínua sem transformar o residente de 5 segundos em um agregador econômico de alta frequência.

Política padrão:

- sinais podem ser recebidos a cada ciclo AE4;
- consolidação econômica no máximo uma vez a cada 60 segundos;
- no máximo 50 sinais novos processados por passagem;
- no máximo 20 ciclos distintos mantidos na janela operacional por linha;
- no máximo 200 linhas econômicas ativas;
- ausência de novos sinais produz sem_novos_sinais e não cria nova linha.

A cadência deve ser configurável, registrada e observável.

## 13. Continuidade temporal

Cada linha deve registrar:

primeiro sinal
último sinal
ciclos distintos
intervalo entre observações
idade
quantidade de observações
resultados compatíveis
resultados contraditórios
última avaliação econômica
próxima reavaliação

O objetivo é distinguir evento isolado de padrão econômico persistente.

## 14. Observabilidade obrigatória

Cada passagem AE5 deve registrar:

ae5_run_id
timestamp
janela
sinais_lidos
sinais_novos
duplicatas_deterministicas
possiveis_duplicatas_semanticas
linhas_criadas
linhas_atualizadas
linhas_promovidas_de_estado
linhas_rebaixadas
linhas_maduras
linhas_sem_valor
vinculos_n9_observados
inconsistencias
fontes_consultadas
tempo_processamento

Cada linha deve conservar as origens AE1, auditorias AE4, solicitações N9, experimentos e evidências relacionadas.

A observabilidade deve permitir responder:

Por que esta oportunidade foi considerada economicamente relevante?

Quais evidências sustentavam a classificação?

## 15. Contradição e rebaixamento

AE5 não possui apenas progressão de maturidade.

Nova evidência contraditória pode rebaixar uma linha de valor_sustentado para valor_observacional, valor_candidato ou sem_valor_identificado.

O rebaixamento deve registrar estado anterior, estado novo, evidência responsável, data e motivo.

Evidência negativa não pode ser apagada para preservar uma linha madura.

## 16. O que AE5 não pode fazer

- gerar código;
- executar código;
- criar artefato experimental;
- escolher valor monetário inexistente;
- inventar preço, salário, custo, receita ou baseline;
- converter melhoria técnica automaticamente em dinheiro;
- declarar ROI sem fórmula e dados válidos;
- declarar economia sem referência econômica;
- criar solicitação N9 automaticamente;
- iniciar experimento;
- fazer retry;
- autorizar integração;
- modificar main ou stable;
- alterar arquitetura;
- promover hipótese econômica a fato;
- esconder evidência negativa;
- criar segunda memória de aprendizagem;
- substituir AE1, AE2, AE3 ou AE4.

## 17. Relação com N9

Quando uma linha atingir maduro_para_formalizacao, AE5 apenas informa que existe base para formalização.

A criação da solicitação continua pertencendo ao fluxo N9.

Quando a relação for conhecida, deve existir vínculo explícito:

linha_economica_id → solicitacao_id

Sem esse vínculo, a relação permanece observacional.

## 18. Relação com aprendizado

AE5 consome aprendizado existente, mas não cria outra memória.

Aprendizado responde:

O que aprendemos com a experiência?

AE5 responde:

Existe valor econômico persistente associado a esse aprendizado?

As responsabilidades continuam separadas.

## 19. Relação com causalidade

AE5 pode afirmar uma relação causal somente quando os vínculos necessários estiverem explicitamente persistidos.

Sem vínculo persistido, a relação é correlacional ou observacional.

Proximidade temporal não é causalidade.

## 20. Invariantes de governança

autorizacao_explicita = false
integracao_executada = false
stable_modificada = false
arquitetura_modificada = false
conhecimento_permanente = false
execucao_local = false

AE5 aumenta continuidade da descoberta, qualidade da evidência e visibilidade de valor sem aumentar autoridade de integração.

## 21. Critério de aceite

AE5 só poderá ser considerada implementada quando existir prova reproduzível de que:

1. AE1 e AE4 alimentam AE5 sem duplicação exata;
2. sinais semelhantes podem ser relacionados sem perder proveniência;
3. ausência de ligação econômica mantém valor desconhecido;
4. valor econômico exige mecanismo e métrica explícitos;
5. baseline e referências ausentes não são inventados;
6. evidências contraditórias podem rebaixar uma linha;
7. N9 pode ser observado e reconciliado sem ser criado por AE5;
8. a cadência impede processamento econômico excessivo;
9. cada passagem possui observabilidade auditável;
10. a persistência sobrevive ao reinício;
11. AE5 não executa nem integra mudanças;
12. main e stable permanecem intocadas.

## 22. Princípio central

AE5 não deve perguntar apenas:

O que está dando errado repetidamente?

Ela deve perguntar:

O que está acontecendo repetidamente, qual valor isso pode gerar ou preservar, qual evidência sustenta essa ligação, qual parte ainda é desconhecida e quando existe base suficiente para transformar isso em uma hipótese econômica formal?

## 23. Estado do contrato

Este arquivo define o contrato-alvo da AE5 de descoberta contínua de valor econômico.

A implementação existente de nixal_descoberta_continua_ae5.py permanece como implementação anterior até migração explícita, revisão e testes.

Este contrato não concede autorização de integração, não modifica main e não autoriza AE6.

CONTRATO AE5
→ implementação
→ teste
→ evidência operacional
→ checkpoint