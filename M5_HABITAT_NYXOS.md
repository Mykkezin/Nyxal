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

### M5.2 — Processos como entidade do habitat

O segundo marco transforma a simples contagem de processos em uma observação estruturada do host:

```
/proc
  ↓
adaptador de processos
  ↓
entidades sanitizadas
  ↓
HabitatNixOS
  ↓
/api/public/status
```

Cada entidade exposta possui identidade mínima baseada em PID + instante de início do processo e telemetria de CPU/memória quando disponível.

O contrato mantém o campo legado `recursos.processos` como contagem total e adiciona `recursos.processos_habitat` com:

- total observado;
- limite de exposição;
- coleção limitada de entidades;
- modo somente leitura.

O adaptador não coleta argumentos de linha de comando, ambiente do processo nem executa comandos externos.

### M5.3 — Persistência operacional

O terceiro marco cria a continuidade durável do habitat sem criar uma segunda camada de memória semântica.

```
Runtime / Habitat
      ↓
PersistenciaOperacionalNixOS
      ↓
estado_nyxos_operacional.json
      ↓
reinicialização
      ↓
contexto operacional restaurado
```

A camada registra somente estado operacional resumido: inicializações, última persistência, referência ao último ciclo, última observação sanitizada do habitat e histórico curto.

A gravação usa substituição atômica. O histórico é limitado a 50 registros. Arquivo ausente ou corrompido não impede a inicialização; a camada recomeça com estrutura vazia válida.

Persistência operacional não significa conhecimento permanente. Conversação, conhecimento candidato, aprendizado, governança de evolução e arquitetura continuam em suas respectivas camadas.

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
