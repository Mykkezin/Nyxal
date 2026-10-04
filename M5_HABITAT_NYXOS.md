# M5 — Habitat NyxOS
## Contrato inicial do habitat operacional

### Objetivo

Transformar o NyxOS de uma interface conectada ao Runtime em um habitat de software persistente,
observável e modular sobre o sistema hospedeiro, sem criar um kernel próprio nesta etapa.

Arquitetura-alvo:

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

### M5.1 — Observabilidade do host

O primeiro marco conecta o corpo computacional já existente ao dashboard por uma ponte
de habitat somente leitura:

```
host Linux
   ↓
corpo computacional
   ↓
adaptador do habitat
   ↓
/api/public/status
   ↓
dashboard NyxOS
```

São expostos para a interface:

- estado do sistema hospedeiro;
- CPU;
- memória;
- armazenamento;
- quantidade de processos;
- uptime;
- sinal resumido de GPU quando disponível.

### Invariantes

- nenhuma alteração de hardware;
- nenhuma alteração de energia, RGB, ventoinhas ou dispositivos;
- nenhuma escrita em arquivos de estado pelo adaptador;
- nenhuma execução de comandos externos;
- nenhuma instalação de dependências;
- nenhuma autorização de evolução;
- N9/N10 permanecem intactos;
- ausência de dado real aparece como indisponível, nunca como valor inventado.

### Portabilidade

O primeiro suporte é Linux porque o corpo computacional atual já lê `/proc` e `/sys`.
O adaptador fica separado para permitir implementações futuras para outros hospedeiros
sem contaminar o núcleo.

### Próximos marcos M5

```
M5.1 observabilidade do host
M5.2 processos como entidade do habitat
M5.3 persistência operacional
M5.4 eventos Delta de primeira classe
M5.5 interface orientada a estado real
M5.6 ferramentas e módulos como recursos do habitat
M5.7 ciclo operacional residente
```

O objetivo não é afirmar consciência. O objetivo é construir o ambiente persistente no qual
percepção, memória, decisão, aprendizagem e evolução possam ser observados e avaliados.
