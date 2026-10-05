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

## Instalação local

O instalador trabalha no escopo do usuário através de systemd --user:

```bash
cd ~/Nyxal
bash deploy/systemd/instalar_nyxos_servicos.sh
```

Para iniciar imediatamente:

```bash
systemctl --user start nyxos.target
```

Para verificar:

```bash
systemctl --user status nyxos.target
systemctl --user status nyxal-api.service
systemctl --user status nyxos-residente.service
```

Para a residência sobreviver ao logout e poder iniciar sem uma sessão gráfica, o instalador também apresenta o comando de loginctl enable-linger.

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

## Critério de conclusão

M5.9 será considerado implementado quando:

1. as três unidades forem validadas estruturalmente;
2. API e ciclo residente puderem ser iniciados pelo systemd --user;
3. o ciclo residente permanecer sem max-ciclos;
4. AE2 continuar desabilitada;
5. a residência não conceder autoridade adicional;
6. não houver alteração em main ou na planta autoritativa.
