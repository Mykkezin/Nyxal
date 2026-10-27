# Ativação da residência, autoevolução e autoreparo NyxOS

## O que fica ativo no serviço residente

A unidade `nyxos-residente.service` usa o ambiente virtual do projeto e passa explicitamente:

- `--habilitar-aprendizado`: permite que o Runtime reutilize o aprendizado persistido entre ciclos.
- `--habilitar-auto-experimento`: liga AE2 para processar no máximo uma solicitação formal por ciclo, desde que esteja pronta, tenha um artefato Python dentro do repositório e passe todos os gates.
- `--habilitar-ae5-descoberta`: liga a descoberta contínua governada de valor econômico e o coletor dual de transições já observadas pelo Runtime/habitat.
- `--continuar-em-erro`: mantém o ciclo de supervisão vivo quando um ciclo funcional retorna erro, em vez de encerrar antes de o autoreparo completar suas verificações.

AE1/AE3/AE4 permanecem conectados pelo launcher existente. Com essa configuração, o perfil residente ativa AE1→AE5 e o reaproveitamento do aprendizado persistido. AE2 continua limitado a solicitações formais prontas e experimentos remotos governados; não gera nem executa código arbitrário localmente.

AE5 registra sinais e oportunidades econômicas candidatas. O coletor dual guarda transições observadas em `Nyxal-datasets`, fora da árvore Git, com deduplicação e limites próprios. Esses registros **não significam que houve treinamento do modelo**: treinamento automático, implantação e integração continuam desabilitados. AE5 também não cria por conta própria uma solicitação N9 nem autoriza mudanças em `main`.

## Autorreparo supervisionado

`nixal_autoreparo_residente.py` é chamado pelo Ciclo Residente M5.7. Em cada ciclo:

1. faz GET de `/health` exclusivamente em loopback;
2. verifica a sessão gráfica antes de tentar recuperar o desktop;
3. após três falhas consecutivas, pode reiniciar apenas `nyxal-api.service` ou `nyxos-interface.service`;
4. limita cada unidade a três tentativas por 15 minutos, com intervalo mínimo de 90 segundos;
5. grava ações e estados resumidos em `~/.local/state/nyxal/autoreparo-residente.jsonl`, sem tokens, corpos HTTP ou mensagens de exceção.

Não executa shell arbitrário, não altera ficheiros de código, não instala pacotes, não mexe em firewall, não muda permissões fora do seu ficheiro de auditoria e não toca no kernel. O systemd continua responsável por reiniciar processos que terminam abruptamente. Se a API exigir configuração inválida, o circuito de tentativas impede reinicializações repetitivas.

## Aplicar no computador

Os merges do GitHub não atualizam automaticamente o checkout local nem as unidades instaladas na máquina. Depois que a mudança for integrada em `main`, no PC que executa a Nyxal:

```bash
cd ~/Nyxal
git pull --ff-only origin main
bash deploy/systemd/instalar_nyxos_servicos.sh
bash deploy/systemd/diagnosticar_nyxos_local.sh
```

O instalador recarrega as unidades e reinicia explicitamente a API e o residente, para não deixar processos ativos a usar configuração anterior. O desktop só é reiniciado quando `graphical-session.target` está ativo. Se estiver ausente, aguarde uma sessão gráfica e execute:

```bash
systemctl --user restart nyxos-interface.service
```

Se a API ou o residente continuar falhando, colete o diagnóstico sem exibir o arquivo de segredos:

```bash
journalctl --user -u nyxal-api.service -u nyxos-residente.service -u nyxos-interface.service -n 100 --no-pager
```

A partir dessas mensagens será possível identificar a dependência, importação ou configuração concreta que impede a inicialização. O script de diagnóstico não lê nem imprime valores de `nyxal.env`.

## Limite atual da autoevolução

O projeto possui descoberta AE1, experimento remoto AE2, avaliação AE3, coordenação AE4, descoberta AE5, aprendizado persistido e os gates N9/LLC. Ativar o ciclo significa que essas capacidades existentes passam a trabalhar no perfil residente; **não significa que a Nyxal já possa alterar e integrar seu próprio código sem revisão**.

O próximo passo técnico para geração autônoma de melhorias de código continua sendo ligar um gerador de patch isolado, uma worktree descartável, testes e benchmarks reproduzíveis, verificação de segurança, comparação com baseline e artefato reversível à governança já existente. A proposta deve permanecer aguardando autorização explícita para promoção. Nenhuma melhoria pode sobrescrever `main` nem alterar o kernel diretamente.

O objetivo de produto deve ser um NyxOS distribuível sobre Linux primeiro: boot reprodutível, instalação declarativa, atualização assinada, recuperação comprovável, runtime local/privado e fronteira de permissões clara. Um kernel próprio fica condicionado a uma necessidade técnica demonstrada, não à vontade de dar à IA acesso irrestrito ao host.
