# Ferramentas do diálogo principal da Nyxal

## Estado e limites

O diálogo Qwen pode usar function calling por meio do `GerenciadorCapacidades` existente. A integração não substitui o contrato, o histórico de execução ou o validador do gerenciador.

Por padrão, só são anunciadas ferramentas de leitura de baixo impacto: hora local, pesquisa web, consulta METAR/TAF público e diagnósticos fixos do próprio projeto. O modelo não recebe um shell genérico, não recebe um executor HTTP arbitrário e não pode inventar nomes de capacidades.

A lista de ferramentas de leitura de dados locais/privados — arquivos, memória corporal, Gmail, agenda e Home Assistant — exige opt-in explícito por ambiente:

```bash
NYXAL_ENABLE_PRIVATE_READ_TOOLS=1
```

O opt-in adiciona apenas ferramentas de leitura que o registro de capacidades já suporta. Não habilita escrita.

As ações `salvar_nota`, `criar_lembrete` e `abrir_aplicativo` permanecem indisponíveis no function calling. O atual `GerenciadorCapacidades.executar()` não aplica uma política por capacidade e não possui uma fronteira de aprovação apropriada para essas ações; por isso elas não são expostas nem mesmo com `NYXAL_ENABLE_MUTABLE_TOOLS=1`. Esse ajuste fica reservado até a política de autorização por capacidade e a confirmação explícita estarem integradas e testadas.

## Function calling e recuperação

- O ciclo de ferramentas é limitado a três chamadas por turno.
- Argumentos têm de ser JSON objeto e passam pelo validador existente da capacidade.
- Ferramentas desconhecidas ou mutáveis são recusadas; resultado de ferramenta é truncado a um máximo configurado.
- O diálogo volta ao chat textual se o cliente Ollama não aceitar o parâmetro `tools`.
- As respostas do modelo e os resultados de ferramenta são dados, não instruções de sistema. O modelo não pode expandir a allowlist.

## Testes

O workflow Agent Stack compila `nixal_dialogo_qwen.py` e executa `teste_nyxal_function_calling.py`. A suíte cobre execução de ferramenta de leitura, limite total de chamadas, recusa de nomes desconhecidos, ocultação de ferramentas privadas por padrão, ações mutáveis indisponíveis e fallback para chat textual.

Essa integração não comprova funcionamento de microfone, sensores, serviços reais ou dados privados do computador.

## Consultas aeronáuticas AISWEB/DECEA

O diálogo principal pode usar duas ferramentas de consulta somente leitura:
- consultar_notam_aisweb: consulta NOTAMs por 1–10 códigos ICAO e, opcionalmente, por FIR.
- consultar_cartas_aisweb: pesquisa metadados/links de cartas ostensivas por ICAO, espécie/tipo, nome ou ciclo AIRAC.

Essas ferramentas são anunciadas como leitura de baixo impacto e não habilitam envio, escrita ou controle físico. O adaptador usa filtros fixos, valida os códigos ICAO, bloqueia redirecionamentos, limita a resposta XML a 2 MB e rejeita declarações DOCTYPE/ENTITY. Credenciais não são incluídas na resposta da Nyxal.

A API AISWEB/DECEA exige credenciais fornecidas pelo DECEA. Configure-as somente no ambiente local do serviço:
- NYXAL_AISWEB_API_KEY
- NYXAL_AISWEB_API_PASS

Sem as duas variáveis, a ferramenta retorna configuracao_pendente sem realizar tráfego de rede. Não coloque essas credenciais no Git, em prompts ou no histórico de conversa.

A resposta é material de apoio; o piloto precisa confirmar NOTAMs, cartas vigentes, AIP e briefing oficial antes de qualquer uso operacional. A integração não calcula mínimos, não decide aeronavegabilidade e não substitui julgamento do piloto.
