# M5.9 — Residência Linux do NyxOS

## Objetivo

Transformar a API e o ciclo operacional residente em serviços persistentes do Linux, eliminando a necessidade de manter um terminal aberto para sustentar a residência.

## Arquitetura

```
Linux / systemd
      ↓
nyxos.target
   ├── nyxal-api.service
   │      ↓
   │   nyxal_web_api.py
   │
   └── nyxos-residente.service
          ↓
      executar_nyxos_residente.py
          ↓
      Runtime / Habitat / AE1 → AE5
```

A API e o ciclo residente permanecem serviços separados. Isso permite reinicialização independente e evita misturar transporte HTTP com o ciclo operacional.

## Política

M5.9 muda somente a forma de residência do processo.

Não muda:

- autorização de evolução;
- autorização de integração;
- branch main;
- planta_nixal/planta.json;
- política da AE2;
- controle físico do computador;
- semântica das capacidades.

A AE2 continua desabilitada. O serviço residente não passa a flag de habilitação experimental.

## Ambiente Python da residência

A residência usa obrigatoriamente o ambiente virtual do próprio projeto:

```
~/Nyxal/.venv/bin/python
```

Isso evita que o systemd execute a aplicação com um interpretador global que não contém as dependências do Nyxal.

O instalador valida:

1. existência e executabilidade de `.venv/bin/python`;
2. importação da API e do launcher residente pelo mesmo interpretador.

Se essa validação falhar, os serviços não são instalados/iniciados.

## Instalação local

O instalador trabalha no escopo do usuário através de systemd --user:

```bash
cd ~/Nyxal
bash deploy/systemd/instalar_nyxos_servicos.sh
```

O instalador habilita e inicia o target imediatamente.

Para verificar:

```bash
systemctl --user status nyxos.target
systemctl --user status nyxal-api.service
systemctl --user status nyxos-residente.service
```

O instalador também tenta habilitar o lingering da conta. Se a política do sistema impedir essa operação, ele informa o comando para execução manual.

## Configuração

Segredos e tokens não entram no repositório. O serviço aceita opcionalmente o arquivo:

```
~/.config/nyxal/nyxal.env
```

Esse arquivo pode conter variáveis como NYXAL_API_TOKEN e outras configurações locais já suportadas pela API.

## Reinício

Falha do processo resulta em reinício automático após 3 segundos.

Encerramento manual do serviço continua disponível com systemctl --user stop.

## Artefatos

- deploy/systemd/nyxal-api.service;
- deploy/systemd/nyxos-residente.service;
- deploy/systemd/nyxos.target;
- deploy/systemd/instalar_nyxos_servicos.sh;
- deploy/systemd/desinstalar_nyxos_servicos.sh;
- teste_m5_9_residencia_linux.py.

## Ordem de engenharia

M5.9 é deliberadamente anterior à camada de atuação do host.

A sequência registrada em `ORDEM_ENGENHARIA_NYXOS.md` é:

```
M5.8 dependências
   ↓
M5.9 residência Linux
   ↓
M5.10 gateway de atuação
   ↓
M5.11 processos e aplicativos
   ↓
M5.12 corpo térmico e ventilação
   ↓
M5.13 fisiologia operacional
   ↓
M5.14 plano central de controle
   ↓
M5.15 presença de máquina
```

A auto-evolution AE1→AE5 permanece paralela e governada, sem receber autoridade implícita sobre essas camadas.

## Critério de conclusão

M5.9 será considerado implementado quando:

1. as três unidades forem validadas estruturalmente;
2. API e ciclo residente puderem ser iniciados pelo systemd --user;
3. o ciclo residente permanecer sem max-ciclos;
4. AE2 continuar desabilitada;
5. a residência não conceder autoridade adicional;
6. não houver alteração em main ou na planta autoritativa.


## Perfil residente leve

A residência contínua usa explicitamente `NyxalRuntime(modo_residente=True)`.

Nesse perfil, o ciclo operacional mantém observação corporal, diagnóstico, necessidades, decisão, ação autorizada, observação do resultado, avaliação, experiência, aprendizado e persistência, mas adia a investigação profunda para execução sob demanda. Isso evita repetir uma investigação arquitetural pesada a cada intervalo curto de residência.

O perfil residente também usa `log_nyxal_residente.json`, separado do log histórico completo do Runtime, evitando carregar um arquivo histórico local potencialmente grande durante a inicialização do serviço.

A investigação profunda permanece disponível no Runtime normal, com `modo_residente=False`.
