# LLC — Learning Loop Causal

## Estado atual: LLC.3 validado

O LLC possui tres camadas distintas:

1. **LLC.1 — influencia decisoria**
2. **LLC.2 — feedback operacional**
3. **LLC.3 — evidencia causal por contraste controlado**

## LLC.3

O protocolo adiciona uma camada para consequencias externas sem usar sucesso operacional como substituto de causalidade.

Fluxo:

```
aprendizado -> decisao -> acao -> resultado
                    -> feedback operacional
                    -> novo aprendizado
                    -> metrica externa
                    -> controle
                    -> contrafactual
                    -> repeticoes
                    -> evidencia causal controlada
```

A metrica exige nome, unidade, fonte, direcao de melhoria, tolerancia e desenho experimental suportado.

Cada observacao precisa fornecer:

- `contrafactual_validado = true`;
- `controle_valido = true`;
- nenhum confundidor declarado;
- valor antes/depois da intervencao;
- valor antes/depois do controle.

O efeito e calculado como:

```
efeito = (intervencao_depois - intervencao_antes)
       - (controle_depois - controle_antes)
```

O gate exige pelo menos tres contrastes validos e melhoria consistente na direcao declarada.

## Limite

A marca `causalidade_ambiental_comprovada` significa evidencia valida **dentro do protocolo controlado fornecido**. Nao e uma prova universal nem autoriza inferencia causal fora do desenho experimental.

O teste LLC.3 usa dados sinteticos para validar a estrutura e os gates. O Runtime nao coleta automaticamente uma metrica causal nem escolhe um grupo de controle.

## Governanca

LLC.3 nao:

- treina modelo;
- implanta modelo;
- modifica arquitetura;
- integra em `main`;
- cria memoria nova;
- executa boot adicional;
- cria AE6;
- autoriza alteracoes estaveis.

Invariantes:

```
autorizacao_explicita = false
integracao_executada = false
stable_modificada = false
arquitetura_modificada = false
conhecimento_permanente = false
execucao_local = false
treinamento_automatico = false
implantacao_automatica = false
```

## Validacao

O teste dedicado verifica LLC.1, LLC.2 e LLC.3, incluindo rejeicao por repeticoes insuficientes e preservacao das invariantes.

M5 permanece congelado em `feat/m5-habitat-nyxos`.

`feat/llc-learning-loop` continua separada de `main`.
