# Autoavaliação direta da Nyxal (ambiente local)

## Por que esta ferramenta existe

O endpoint da Nyxal está configurado por padrão em `127.0.0.1:8010`, e o Display Vite encaminha `/api` para esse loopback. O diagnóstico remoto do GitHub não alcança o computador em que o runtime está rodando. Por isso, não devemos fabricar uma resposta como se tivéssemos perguntado à instância viva.

Este cliente deve ser executado na própria máquina da Nyxal. Ele envia três turnos à rota local `POST /api/agent/chat`, usando `provedor: nyxal`:
1. solicita uma autoavaliação fundamentada na evidência acessível à Nyxal;
2. apresenta a resposta de volta como hipótese não confiável e pede um plano governado AE/LLC;
3. solicita uma auditoria que separa o que está resolvido, parcialmente mitigado e não resolvido com base nas evidências disponíveis.

## Segurança e limites

- Host fixo em `127.0.0.1`; não há parâmetro de URL remota, proxy arbitrário ou conexões externas.
- Usa `NYXAL_API_PORT` (padrão 8010) e, se configurado, envia `NYXAL_API_TOKEN` apenas no cabeçalho Bearer.
- Não lê o repositório, não executa comandos, não aplica alterações sugeridas, não abre PR, não faz merge e não autoriza integração.
- A conversa não é salva automaticamente. Para guardá-la, informe `--saida` com um caminho novo; o arquivo é criado com permissão `0600` e não é sobrescrito.
- A resposta da Nyxal é uma hipótese de modelo, não evidência por si só. A auditoria deve exigir logs, resultados de testes e critérios de aceitação.

## Atualidade das evidências

Os fatos de CI e validação incluídos nos prompts são uma fotografia histórica registrada em **2026-10-24T04:26:07Z**. Esta ferramenta não consulta o GitHub, workflows, Billing nem configurações de Actions; ela só conversa com a API local `127.0.0.1`. Portanto, a fotografia não representa necessariamente o estado atual. O prompt de auditoria pede que a Nyxal marque o estado atual como **não verificado** quando não houver evidência mais recente. Antes de atualizar a fotografia, verifique os links e as execuções reais, registre a hora UTC e preserve a distinção entre teste local, execução pública e CI do repositório privado.
- Esta ferramenta verifica propostas conversacionais; não executa um experimento AE2 real. O experimento real deve passar pelas solicitações formais existentes e pelos gates AE2/AE3/AE4/LLC.
- Caso a API não esteja ativa, a ferramenta termina com uma mensagem de erro sem fingir que a Nyxal respondeu.

## Como executar

Com a API local já iniciada, execute dentro da árvore do repositório:

```bash
python3 falar_com_nyxal_autoavaliacao.py
```

Para escolher uma porta local diferente:

```bash
NYXAL_API_PORT=8011 python3 falar_com_nyxal_autoavaliacao.py --timeout 120
```

Para guardar explicitamente o resultado em um arquivo novo:

```bash
python3 falar_com_nyxal_autoavaliacao.py --saida "$HOME/nyxal-autoavaliacao-2026-10-24.json"
```

Não use o arquivo de saída se a conversa contiver informação confidencial, a menos que o caminho seja apropriado para esse conteúdo.

## Critérios para afirmar que uma deficiência foi resolvida

Uma boa resposta da Nyxal deverá identificar uma H1 falsificável, evidência atual, baseline, experiência mínima e critério de rejeição. Depois, a correção precisa ser aplicada por um caminho autorizado e testada de forma reproduzível.

Para o snapshot registrado em 2026-10-24T04:26:07Z, a distinção era:
- o runner padrão do repositório público conseguiu executar um workflow mínimo;
- o job privado da Nyxal parou antes da primeira etapa, sem runner atribuído;
- 29 testes da política defensiva foram executados localmente em Python 3.13, mas isso não valida o workflow privado em Python 3.12;
- o estado do runner privado só será considerado resolvido quando o job privado obtiver um runner real, os passos de checkout/compilação/teste forem executados e houver logs e códigos de saída.

Nenhuma opinião produzida pela IA substitui esses critérios.
