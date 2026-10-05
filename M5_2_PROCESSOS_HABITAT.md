# M5.2 — Processos como Entidade do Habitat

## Objetivo

Transformar a contagem simples de processos do M5.1 em uma observação estruturada do conjunto de processos do host.

O M5.2 adiciona identidade e telemetria mínima para processos, mantendo a fronteira de somente leitura:

```
/proc
  ↓
adaptador de processos
  ↓
entidades do habitat
  ↓
HabitatNixOS
  ↓
/api/public/status
```

## Entidade de processo

Cada processo observado possui, quando disponível:

- `id`: identidade estável dentro da amostra, formada por PID + instante de início do processo;
- `pid`: identificador do processo;
- `nome`: nome curto do processo;
- `estado`: estado reportado pelo kernel;
- `uso_cpu_percentual`: uso estimado durante a janela de observação;
- `memoria_rss_percentual`: participação aproximada na memória física;
- `memoria_rss_mb`: memória residente do processo.

A API expõe somente os primeiros processos de maior carga, com limite configurável e teto de segurança.

## Regras

- somente leitura;
- nenhuma execução de processo;
- nenhum sinal enviado a processos;
- nenhum encerramento, pausa ou prioridade alterada;
- nenhum comando externo;
- nenhuma dependência nova;
- nenhum argumento de linha de comando coletado;
- nenhuma variável de ambiente de processo coletada;
- nenhuma persistência;
- nenhuma autorização de evolução;
- N9/N10 permanecem inalterados.

## Compatibilidade

O campo legado `recursos.processos`, que contém a contagem total observada pelo M5.1, permanece preservado.

O M5.2 adiciona `recursos.processos_habitat` com a estrutura:

```json
{
  "total": 0,
  "limite": 12,
  "entidades": []
}
```

Assim, consumidores existentes não precisam mudar apenas para continuar lendo a contagem total.

## Indisponibilidade

Processos que desaparecem durante a janela de amostragem são ignorados. Campos individuais sem leitura disponível permanecem como `null`; nenhum valor é inventado.

## Critério de conclusão

M5.2 é considerado implementado quando:

1. o adaptador lê processos reais do host sem comandos externos;
2. cada entidade possui identidade mínima e telemetria sanitizada;
3. o limite de exposição é controlado;
4. o contador legado permanece compatível;
5. testes de sintaxe, contrato, coleta real e segurança passam;
6. N9/N10 continuam passando por regressão.
