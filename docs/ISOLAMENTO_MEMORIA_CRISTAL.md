# Isolamento de memória e cristalização

## Regra de resolução de caminhos

Os caminhos persistentes da Nyxal seguem esta precedência:

1. Override específico do subsistema, quando definido.
2. Caminho relativo a `NYXAL_STATE_DIR`, quando definido.
3. Caminho legado ancorado na raiz do repositório, quando nenhuma configuração existir.

Overrides específicos:

| Subsistema | Variável |
| --- | --- |
| Cristal binário autoritativo | `NYXAL_CRISTAL_ARQUIVO` |
| Cristal binário legado | `NYXAL_CRISTAL_LEGADO` |
| Backups/checkpoints binários | `NYXAL_CRISTAL_BACKUPS` |
| Cristal semântico JSON | `NYXAL_CRISTALIZACAO_ARQUIVO` |
| Cristal do ciclo JSON | `NYXAL_CRISTAL_CICLO_ARQUIVO` |

Quando apenas `NYXAL_STATE_DIR=/caminho/nyxal` estiver definido, os caminhos ficam:

- `memoria/cristal/cristal.bin`
- `experimentos/cristal_gerenciador.bin`
- `memoria/backups`
- `memoria/cristalizacao.json`
- `memoria/cristal_atual.json`

Sem `NYXAL_STATE_DIR` e sem overrides específicos, os caminhos históricos dentro do repositório permanecem inalterados.

## Testes seguros

Execute na raiz do repositório:

```bash
bash validar_memoria_cristal_isolado.sh
```

O runner cria um diretório privado novo em `/tmp`, exporta `NYXAL_STATE_DIR` e os caminhos de memória, e executa as suítes de memória e cristalização selecionadas. O diretório temporário é preservado ao final para inspeção.

A suíte `teste_cristal_state_dir_isolation.py` verifica:

- redirecionamento de todos os cristais por `NYXAL_STATE_DIR`;
- precedência dos overrides específicos;
- preservação dos caminhos legados quando não há configuração;
- ausência de criação de arquivos durante a simples importação dos módulos.

Os testes de cristalização binária existentes também usam diretórios temporários e restauram os caminhos globais dos módulos após cada cenário.

## Limites

- O runner não instala dependências.
- Não inicia nem para serviços.
- Não acessa o Ollama nem solicita geração de modelo.
- Não ativa a cristalização autônoma.
- Não deve ser usado como autorização para copiar o estado temporário sobre a memória residente.
