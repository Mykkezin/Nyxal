# Ativação da residência, autoevolução e autoreparo NyxOS

## O que fica ativo

A unidade residente usa o ambiente virtual do projeto e passa explicitamente:
- \`--habilitar-aprendizado\`: permite que o Runtime reutilize o aprendizado persistido entre ciclos.
- \`--habilitar-auto-experimento\`: liga AE2 para processar no máximo uma solicitação formal por ciclo, desde que ela esteja pronta, tenha um artefato Python dentro do repositório e passe todos os gates.
- \`--continuar-em-erro\`: mantém o ciclo de supervisão vivo quando um ciclo funcional retorna erro, em vez de encerrar antes de o autoreparo completar suas verificações.

AE1/AE3/AE4 permanecem conectados pelo launcher existente. AE2 **não gera código arbitrário**: usa o pipeline de experimento remoto já configurado e não concede autorização de integração nem altera \`main\`. Se não houver solicitações formais prontas, não inicia experimento. O suporte AE5 de descoberta econômica continua opcional.

## Autorreparo supervisionado

\`nixal_autoreparo_residente.py\` é chamado pelo Ciclo Residente M5.7. Em cada ciclo:
1. faz GET de \`/health\` exclusivamente em loopback;
2. verifica a sessão gráfica antes de tentar recuperar o desktop;
3. após três falhas consecutivas, pode reiniciar apenas \`nyxal-api.service\` ou \`nyxos-interface.service\`;
4. limita cada unidade a três tentativas por 15 minutos, com intervalo mínimo de 90 segundos;
5. grava ações e estados resumidos em \`~/.local/state/nyxal/autoreparo-residente.jsonl\`, sem tokens, corpos HTTP ou mensagens de exceção.

Não executa shell arbitrário, não altera ficheiros de código, não instala pacotes, não mexe em firewall, não muda permissões fora do seu ficheiro de auditoria e não toca no kernel. O systemd continua responsável por reiniciar processos que terminam abruptamente. Se a API exigir configuração inválida, o circuito de tentativas impede reinicializações repetitivas.

## Aplicar no computador

Os merges do GitHub não atualizam automaticamente o checkout local nem as unidades instaladas na máquina. No PC que executa a Nyxal:

\`\`\`bash
cd ~/Nyxal
git pull --ff-only origin main
bash deploy/systemd/instalar_nyxos_servicos.sh
bash deploy/systemd/diagnosticar_nyxos_local.sh
\`\`\`

O instalador agora reinicia explicitamente a API e o residente após recarregar as unidades, para não deixar processos ativos a usar configuração anterior. O desktop só é reiniciado quando \`graphical-session.target\` está ativo. Se estiver ausente, aguarde uma sessão gráfica e execute:

\`\`\`bash
systemctl --user restart nyxos-interface.service
\`\`\`

Se a API ou o residente continuar falhando, colete o diagnóstico sem exibir o arquivo de segredos:

\`\`\`bash
journalctl --user -u nyxal-api.service -u nyxos-residente.service -u nyxos-interface.service -n 100 --no-pager
\`\`\`

A partir dessas mensagens será possível identificar a dependência, importação ou configuração concreta que impede a inicialização. O script de diagnóstico não lê nem imprime valores de \`nyxal.env\`.

## O que ainda não é autoevolução total

O projeto já tem descoberta AE1, experimento remoto AE2, avaliação AE3 e coordenação AE4, além da governança de integração. Ativar o ciclo não significa que a Nyxal já possa inventar, executar e integrar alterações de código por conta própria. A próxima evolução arquitetural precisa de um gerador de patch isolado, uma worktree descartável, testes e benchmarks reproduzíveis, verificação de segurança, comparação com baseline, artefato reversível e autorização explícita para promoção. Nenhuma proposta deve conseguir sobrescrever \`main\` nem alterar o kernel diretamente.

O objetivo de produto deve ser um NyxOS distribuível sobre Linux primeiro: boot reprodutível, instalação declarativa, atualização assinada, recuperação comprovável, runtime local/privado e fronteira de permissões clara. Um kernel próprio fica condicionado a uma necessidade técnica demonstrada, não à vontade de dar à IA acesso irrestrito ao host.
