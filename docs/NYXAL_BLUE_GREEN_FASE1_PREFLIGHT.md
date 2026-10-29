# Nyxal — Blue/Green local: Fase 1 (preflight somente-leitura)

## Objetivo e limites

Esta etapa interpreta o inventário obtido na Fase 0 e verifica se os dados são legíveis e estruturalmente íntegros antes de preparar uma cópia Green isolada. Ela é somente diagnóstica: não importa os módulos de runtime; não cria diretórios; não chama reparo/quarentena; não escreve nos JSONs/diários/cristais; não faz `git fetch`; não para nem reinicia serviços; não altera units.

O código devolve código de saída `2` quando há bloqueios. Isso é um resultado de diagnóstico, não uma falha que deva ser contornada. Alertas continuam exigindo revisão humana mesmo quando não há bloqueios.

## Por que a instalação viva deve ficar intacta

O relatório de 29/10/2026 indicou branch de funcionalidade com alterações rastreadas e muitos arquivos operacionais não rastreados, divergência de hashes em módulos críticos e ausência no checkout vivo de `nixal_aprovacao_defesa.py` e `nixal_auditoria_defesa.py`. Nenhum desses elementos deve ser descartado ou “corrigido” por `git reset`, `git clean`, checkout forçado ou atualização direta da instalação.

O preflight marca checkout sujo ou cujo `HEAD` não coincide com a referência local `origin/main` como bloqueio para uso como release Green. A solução futura é criar um checkout separado da referência revisada, e não limpar o checkout vivo.

## Como executar

Baixe o script da branch isolada, revise-o e execute-o com a conta da instalação selecionada explicitamente. O acesso ao backup da Fase 0 normalmente exige `sudo`:

```bash
curl -fsSLo /tmp/nyxal_preflight_fase1.py \
  https://raw.githubusercontent.com/Mykkezin/Nyxal/ops-blue-green-fase1-preflight-20261029/deploy/ops/nyxal_preflight_fase1.py

less /tmp/nyxal_preflight_fase1.py

sudo python3 /tmp/nyxal_preflight_fase1.py \
  --user nyxal \
  --home /home/nyxal \
  --repo /home/nyxal/Nyxal \
  --backup-dir /var/backups/nyxal/fase0_20261029_003725_067631022 \
  --expected-archive-sha256 ca920557cbf498205eb2415034a7ba5c263f0372eec8b6f5e25edcf247b21d5a
```

Substitua `<timestamp>` pelo nome exato do diretório criado na Fase 0. No caso registrado em 29/10/2026, o diretório foi `/var/backups/nyxal/fase0_20261029_003725_067631022`.

O relatório imprime somente nomes de arquivos, contagens, hashes e estados de validação; não imprime mensagens de conversa, conteúdo de diários nem valores de arquivos `.env`. O script não grava o relatório em arquivo: ele vai para a saída do terminal. Para salvá-lo localmente, a redireção pode ser feita pelo operador para um arquivo privado em `/tmp`.

## Caminhos efetivos e variáveis de ambiente

Os padrões usados correspondem aos caminhos observados na Fase 0: `~/.local/share/nyxal/conversas.json`, `~/Nyxal/eventos_delta_nyxos.json`, o cristal em `memoria/cristal/cristal.bin`, seu checkpoint e o cristal legado/experimental. A auditoria e o diário de aprovação ficam por padrão sob `$XDG_STATE_HOME/nyxal/` ou `~/.local/state/nyxal/`.

Se o processo estiver configurado com caminhos diferentes por variáveis de ambiente, informe explicitamente o caminho **localmente confirmado** pelo parâmetro correspondente:

- `--memory-path` para `NYXAL_CONVERSATION_MEMORY_PATH`.
- `--state-dir` para o diretório final `.../nyxal` (não apenas o pai `XDG_STATE_HOME`).
- `--delta-path` para o arquivo do Delta.
- `--crystal-path` para `NYXAL_CRISTAL_ARQUIVO`.
- `--checkpoint-path` para o checkpoint em `NYXAL_CRISTAL_BACKUPS`.
- `--manager-crystal-path` para `NYXAL_CRISTAL_LEGADO`.

Nunca cole aqui valores de `.env`, tokens ou credenciais. Se os caminhos efetivos não puderem ser confirmados, não interprete uma validação dos caminhos padrão como validação de todo o estado vivo.

### Confirmar com segurança o caminho de memória configurado

O preflight bloqueia se encontra \`NYXAL_CONVERSATION_MEMORY_PATH\` em uma configuração mas o operador ainda não passou um caminho explicitamente. Para extrair **somente essa variável** do drop-in conhecido, sem imprimir outras linhas de ambiente:

\`\`\`bash
python3 - <<'PY'
from pathlib import Path
import re

home = Path("/home/nyxal")
sources = [
    home / ".config/systemd/user/nyxal-api.service",
    home / ".config/systemd/user/nyxal-api.service.d/10-memoria-conversacional.conf",
    home / ".config/nyxal/nyxal.env",
]
pattern = re.compile(r"^\s*(?:Environment=)?NYXAL_CONVERSATION_MEMORY_PATH=(.*?)\s*$")
found = False
for source in sources:
    if not source.is_file():
        continue
    for line in source.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip().strip('"').strip("'")
        value = value.replace("%h", str(home))
        if value.startswith("~/"):
            value = str(home / value[2:])
        print(f"{source.name}: {value}")
        found = True
if not found:
    print("NYXAL_CONVERSATION_MEMORY_PATH não encontrada nessas fontes; verificar Environment efetivo da unit.")
PY
\`\`\`

Use o caminho confirmado em \`--memory-path\`. Se houver mais de uma definição, confirme qual fonte tem precedência na unit efetiva em vez de escolher uma por suposição.


## O que é validado

1. SHA-256 do tarball da Fase 0 comparado com o hash impresso pela execução original, hashes de cada membro e correspondência exata com o manifesto, sem extrair o arquivo no disco.
2. Estado do Git em modo sem escrita opcional do índice, comparação `HEAD`/`origin/main` local e presença dos módulos críticos.
3. JSONs operacionais conhecidos, contrato do Delta 5.4.0 e estrutura da memória conversacional, sem mostrar o conteúdo.
4. Formato binário `NXCM` dos cristais, inclusive versão, campos completos, nomes duplicados e referências de IDs; também compara o cristal atual com o checkpoint, mas nunca restaura um deles sobre o outro.
5. Cadeias SHA-256 da trilha moderna de auditoria, do diário de aprovação e da auditoria legada M5.18 (`auditoria_atuacao_nyxos.jsonl`). A auditoria legada é lida incrementalmente, com limite de 128 MiB no arquivo e 8 MiB por linha; ultrapassar esses limites bloqueia a validação e não é tratado como prova de corrupção.
6. Estado `systemd --user` das duas unidades, por consulta somente-leitura.

## Como interpretar o resultado

- `BLOQUEIO`: não migrar dados, não adicionar `ExecStartPre` às units azuis, não trocar portas e não fazer cutover. Corrija o plano ou crie um checkout Green isolado; não altere arquivos operacionais para fazer o teste passar.
- `ALERTA`: dado ou cadeia exige revisão especializada. Não eliminar artefatos históricos com nome de corrupção.
- `OK`: apenas a verificação individual passou; isso não substitui o teste integrado de Green nem autoriza, por si só, o cutover.

A próxima fase, depois de revisar esse relatório, é construir uma release Green isolada com diretórios/estado próprios e porta alternativa. A API azul deve continuar sob suas units atuais até que o Green passe nos testes e exista procedimento explícito de retorno.
