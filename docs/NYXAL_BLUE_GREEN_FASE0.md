# Nyxal — Blue/Green local: Fase 0

## Estado deste trabalho

Esta alteração prepara exclusivamente a Fase 0: backup verificável e inventário de divergências. A Fase 1 não deve ser ligada ao systemd antes de executar a Fase 0, revisar o relatório e confirmar os caminhos reais no host.

O script não atualiza o checkout, não executa git pull, não apaga estado operacional e não altera configurações da instalação. Ele pausa temporariamente apenas as unidades systemd de usuário que já estavam ativas, captura os dados, verifica os hashes e tenta restaurar exatamente o conjunto de serviços que estava ativo. A retomada normal do residente pode atualizar contadores/eventos de inicialização; o arquivo de backup representa o estado capturado antes dessa retomada. Se houver uma unit system-level ativa com o mesmo nome, ou se os caminhos de estado contiverem links simbólicos, o script aborta para evitar atuar sobre uma instalação ambígua.

## Diferenças importantes em relação ao rascunho inicial

- A instalação observada usa `systemd --user`, com units em `~/.config/systemd/user/`; não se deve presumir que `/etc/systemd/system/nyxal-api.service` é o serviço ativo.
- O caminho conhecido da memória conversacional é `~/.local/share/nyxal/conversas.json`; trilhas de aprovação/auditoria ficam sob `~/.local/state/nyxal/`. O estado operacional e o Delta também têm arquivos no checkout. O script inventaria esses locais e registra ausências em vez de assumir `~/.nyxal/estado`.
- Os módulos atuais incluem `gerenciador_cristal.py`, `nixal_delta.py`, `nixal_aprovacao_defesa.py`, `nixal_auditoria_defesa.py` e `nixal_memoria_conversacional.py`. Os nomes genéricos do rascunho não correspondem ao repositório atual.
- A lista de dados inclui o cristal autoritativo, backups/checkpoint, cristal legado, estados do habitat, Delta, memória local, diários e unidades/overrides conhecidos.
- O arquivo de ambiente é incluído no backup com permissões restritas, mas o seu conteúdo nunca é impresso no relatório. Linhas `Environment=` também são redigidas no diff de unidades.
- O manifesto SHA-256 é verificado antes e depois de criar o tarball, e o arquivo é extraído para um diretório temporário para um ensaio de restauração. Nada é restaurado por cima do estado vivo.

## Como executar no host

1. Leia o script antes de executá-lo. Não faça merge desta branch apenas para conseguir executá-lo na instalação viva.
2. Baixe somente o script para um diretório temporário — isso não modifica o checkout da Nyxal:

   ```bash
   curl -fsSLo /tmp/nyxal_fase0.sh https://raw.githubusercontent.com/Mykkezin/Nyxal/ops-blue-green-fase0-20261028/deploy/ops/nyxal_fase0.sh
   less /tmp/nyxal_fase0.sh
   ```

3. A partir da conta Linux que executa a Nyxal, rode:

   ```bash
   sudo bash /tmp/nyxal_fase0.sh
   ```

   O script usa `SUDO_USER` para localizar a conta correta. O destino padrão é `$HOME/Nyxal` da conta original e o backup fica sob `/var/backups/nyxal/`. Se o checkout real estiver em outro local, defina `NYXAL_REPO_DIR` explicitamente ao invocar o script.

4. Guarde o caminho `fase0_...` mostrado no fim. A saída informa o arquivo `estado_vivo.tar.gz`, a soma SHA-256, o manifesto e `divergencias.log`.
5. Revise `divergencias.log` e envie o conteúdo desse relatório. Não envie o tarball nem o arquivo `.env`. O relatório evita imprimir valores de segredos, embora ainda contenha caminhos locais, estado Git e fingerprints de arquivos.

## Critérios para continuar

Não configurar `ExecStartPre`, não reiniciar para uma versão Green e não cortar tráfego para o novo runtime até revisar o relatório. Depois do inventário, a Fase 1 deverá usar os nomes de arquivo e as funções reais da `main`; o preflight precisa ser estritamente somente leitura. Em especial, corrupção deve fazer o preflight falhar e preservar o arquivo original — a quarentena deve ser uma etapa de recuperação separada, nunca uma ação do preflight.

## O que o script comprova — e o que não comprova

Comprova que o conteúdo incluído no snapshot tem hashes consistentes e que o tarball consegue ser extraído com os mesmos hashes. Não comprova a integridade semântica de cada subsistema, não prova que os dados ausentes não existam em outro lugar e não testa uma restauração destrutiva na instalação. Essas validações dependem do inventário e das etapas seguintes, com caminho de rollback revisado antes do cut-over.
