# M5 — Habitat NyxOS
## Contrato do habitat operacional

### Estado atual
A linha M5 evoluiu do habitat inicial até **M5.24 — voz supervisionada**.

Marcos concluídos e validados:

```
M5.1 observabilidade do host
M5.2 processos como entidade do habitat
M5.3 persistência operacional
M5.4 eventos Delta
M5.5 interface orientada a estado real
M5.6 recursos do habitat
M5.7 ciclo operacional residente
M5.8 dependências arquiteturais
M5.9 residência Linux
M5.10 gateway de atuação host
M5.11 controle de processos/aplicativos
M5.12 corpo térmico/ventilação
M5.13 fisiologia operacional
M5.14 plano central de controle
M5.15 gateway/presença de máquina
M5.16 adaptador host controlado
M5.17 sandbox físico reversível
M5.18 auditoria de atuação
M5.19 integração residente
M5.20 validação E2E
M5.21 AudioNyxOS
M5.22 VoiceNyxOS
M5.23 adaptadores STT/TTS
M5.24 voz supervisionada
```

### Objetivo
Transformar o NyxOS de uma interface conectada ao Runtime em um habitat de software persistente, observável e modular sobre o sistema hospedeiro, sem criar um kernel próprio nesta etapa.

Arquitetura:
```
HARDWARE
  ↓
HOST
  ↓
NYXOS
  ├── Runtime
  ├── Memória
  ├── Conhecimento
  ├── Corpo
  ├── Ferramentas
  ├── Processos
  ├── Eventos
  ├── Interface
  ├── Observabilidade
  └── Delta
       ↓
     NYXAL
```

### Limites atuais
M5 não concede:
- voz automática;
- escuta contínua;
- wake word;
- reprodução física automática;
- alteração automática de stable/main;
- treinamento automático;
- autoalteração arquitetural;
- implantação automática.

O gateway de atuação continua separado da interface de voz. STT/TTS permanecem nas bordas.

### Fechamento da fase
M5.24 fecha a linha de desenvolvimento do habitat nesta fase.

Antes de qualquer novo marco, deve existir uma revisão arquitetural que identifique:
1. lacuna operacional real;
2. objetivo mensurável;
3. contrato;
4. autoridade permitida;
5. reversibilidade;
6. testes;
7. critérios de promoção;
8. rollback.

Nenhum M6 é criado automaticamente.