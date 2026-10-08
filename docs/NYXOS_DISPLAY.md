# Integração Nyxal-Display

O `Mykkezin/Nyxal` permanece como núcleo do NyxOS. O `Mykkezin/Nyxal---DISPLAY` é uma aplicação React/Vite separada que fornece somente a camada visual.

## Contrato

```text
Nyxal Core
  ├─ núcleo conversacional
  ├─ persistência e Delta
  ├─ residência systemd
  ├─ recursos do habitat
  ├─ KVM/libvirt e VPS
  └─ API HTTP :8010
             │
             ▼
Nyxal-Display
  ├─ desktop visual
  ├─ Infinity
  ├─ janelas e módulos
  └─ apresentação de estado
```

O Display não deve manter uma segunda fonte de verdade para estado operacional. Em particular, estados de VPS, serviços, Delta, presença, datasets e conversa são obtidos do Core.

## Rotas consumidas pelo Display

- `GET /api/public/status` — identidade, habitat, presença, Delta, recursos e contagens AE5.
- `GET /api/public/nyxos/contexto` — contexto operacional público, incluindo gateway.
- `GET /api/public/residencia` — observação das unidades systemd.
- `GET /api/vps/status`, `/api/vps/instances`, `/api/vps/contexto` — estado real das VPS.
- `POST /api/vps/action` e `POST /api/vps/provisionar` — operações VPS já expostas pelo Core.
- `POST /api/chat` — conversa com o núcleo.
- `POST /api/stt` e `POST /api/tts` — voz processada pelo Core.

## Execução

O serviço `nyxos-display.service` serve o build estático em `127.0.0.1:3000`. O launcher gráfico do NyxOS abre esse endereço. O Display, por sua vez, consulta a API do Core em `127.0.0.1:8010`.

O build pode ser instalado com `deploy/display/instalar_nyxos_display.sh`. O Node/npm são necessários somente para construir o frontend; o serviço residente usa o servidor estático Python do próprio Nyxal.

## Governança

O Display não adiciona autorização à arquitetura. Ele apenas apresenta e solicita as operações explicitamente expostas pelo Core. Não existe execução arbitrária de shell pelo frontend.