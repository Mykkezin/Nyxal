# Ferramentas operacionais governadas

## Integração

`nixal_tool_use.py` fornece adaptadores para o `GerenciadorCapacidades` já usado por `AgenteNixalQwen`. A inicialização do agente registra ferramentas no catálogo existente; não cria um segundo executor ou sistema de memória.

## Perfil padrão

Por padrão, somente três ferramentas operacionais são registradas:

- `pesquisar_web`: consulta pública e retorna títulos/URLs; conteúdo externo é não confiável.
- `consultar_metar_taf`: consulta pública por ICAO e não substitui briefing oficial de voo.
- `executar_diagnostico`: executa apenas diagnósticos fixos de leitura; não aceita comandos arbitrários.

## Dados pessoais e locais

O acesso a arquivos de usuário, Gmail, calendário, estados do Home Assistant e notas/lembretes não é registrado por padrão. A ativação exige opt-in explícito no ambiente do processo:

```text
NYXAL_ENABLE_PRIVATE_READ_TOOLS=1
```

Use essa configuração somente no serviço/ambiente em que esse acesso foi autorizado. Reinicie o serviço depois de alterar variáveis de ambiente. Os adaptadores permanecem de leitura; o conteúdo retornado pode ser privado e deve ser compartilhado apenas em respostas solicitadas pelo operador.

## Ações mutáveis continuam desativadas

O gerenciador atual não aplica uma política por ferramenta no momento da execução. Por isso, `incluir_acoes=True` falha de forma explícita e não registra ações parciais. `salvar_nota`, `criar_lembrete` e `abrir_aplicativo` não são expostos ao agente até que haja enforcement de autorização por capacidade, testes de pedido explícito e auditoria adequados.

Nenhuma dessas ferramentas autoriza shell livre, execução de código recebido pela web, controle físico de dispositivos ou contenção de rede.

## Testes

```bash
python3 -m py_compile nixal_tool_use.py nixal_agente_qwen.py teste_nixal_tool_use.py
python3 -m unittest -v teste_nixal_tool_use
```
