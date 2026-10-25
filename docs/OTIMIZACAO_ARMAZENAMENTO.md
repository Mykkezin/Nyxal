# Política de armazenamento da Nyxal

## Regra

O Git deve guardar código-fonte, testes e documentação estável. Logs gerados por
execuções locais e saídas temporárias pertencem ao estado operacional da máquina,
não ao histórico de código.

## Limites de logs

- `log_capacidades_nixal.json`: máximo de 1 MiB; um resultado individual acima
  de metade desse teto é resumido, e os registros mais antigos são removidos
  primeiro.
- `log_nyxal_runtime.json`: máximo de 512 KiB; ciclos muito grandes mantêm
  metadados e um marcador de resumo, sem persistir todo o payload.
- A leitura de logs preexistentes também é limitada a teto + 1 byte antes de
  fazer parse JSON. Se um log herdado ultrapassa o limite, o histórico antigo é
  descartado e a próxima execução grava um registro novo e limitado; um arquivo
  legado enorme não pode invalidar a proteção de memória na inicialização.
- Os logs são ignorados pelo Git depois que forem removidos do índice do projeto.
- `saida_cadeia_real_56_4_34.txt` é uma saída de execução histórica, não um
  arquivo de código; novas cópias locais também são ignoradas.

## Artefatos do GitHub Actions

O pacote completo publicado pelo workflow Nível 9/10 é retido por 3 dias, o
suficiente para recuperação recente sem acumular indefinidamente ZIPs completos.
Os resultados do laboratório remoto mantêm a retenção de 7 dias já configurada.
Uma rotina diária remove os ZIPs completos antigos com o nome exato
`nyxal-projeto-nivel10`, pois a nova regra de retenção não se aplica
retroativamente aos artefatos já existentes. Outros artefatos não são apagados. A consulta à lista de artefatos falha fechada: se `gh api --paginate` retornar erro, o job encerra antes de tentar exclusões. A suíte de armazenamento contém uma regressão estática para manter essa garantia e o filtro de nome/idade.

## Animação de inicialização sem vídeo

`interface/assets/nyxos-startup.mp4` (4.316.200 bytes; cerca de 4,12 MiB) foi
removido da árvore atual. A abertura usa `interface/startup.html`, uma animação
local em HTML/CSS/canvas com núcleo luminoso, órbitas, satélites, scanlines,
estrelas e barra de progresso. Ela não depende de bibliotecas ou mídia remotas,
respeita `prefers-reduced-motion` e segue para a interface local após a sequência.
Os dois launchers usam a página local; não precisam de um reprodutor de vídeo. O parâmetro de destino só aceita URLs absolutas HTTP/HTTPS sem credenciais; esquemas executáveis ou valores malformados voltam à interface local.

A animação segue a identidade visual do NyxOS, mas não é declarada uma reprodução
quadro a quadro do vídeo original, pois essa equivalência não foi verificada.

## Limites de medição

A árvore da `main` verificada antes desta série de limpeza somava 12,61 MiB de
blobs (494 arquivos). A árvore atual na branch de otimização soma **3,74 MiB**
(496 arquivos), incluindo a nova página de inicialização, uma redução estimada de
**8,87 MiB (70,4%)**. A API do GitHub informava aproximadamente 15.930 KB para o repositório
na última consulta à `main`. O número global continua incluindo os objetos
históricos: remover arquivos da árvore atual reduz checkouts e pacotes futuros,
mas não apaga os blobs dos commits antigos. Reescrever o histórico Git para
recuperar esse espaço seria uma operação separada e disruptiva; esta mudança
não altera commits antigos nem força branches.

A inspeção anterior encontrou oito ZIPs completos de projeto ainda não expirados,
somando cerca de 40 MiB. A rotina diária remove apenas artefatos com o nome exato
`nyxal-projeto-nivel10` depois de três dias; outros nomes, incluindo os
resultados do laboratório remoto, são preservados. A limpeza efetiva passa a
valer depois do merge na branch padrão.
