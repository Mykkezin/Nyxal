#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
TEST_ROOT="$(mktemp -d /tmp/nyxal-memory-crystal-tests-XXXXXX)"
chmod 700 "$TEST_ROOT"

# Todos os defaults persistentes são redirecionados para este diretório.
# Nenhum teste deste runner deve gravar na memória residente ou no checkout.
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
export NYXAL_STATE_DIR="$TEST_ROOT/state"
export NYXAL_CONVERSATION_MEMORY_PATH="$TEST_ROOT/state/conversas.json"
export NYXAL_INVESTIGATION_MEMORY_PATH="$TEST_ROOT/state/memoria_investigacao.json"
export NYXAL_KNOWLEDGE_MEMORY_PATH="$TEST_ROOT/state/memoria_conhecimento.json"

cd "$ROOT"

echo "Diretório temporário de testes: $TEST_ROOT"
echo
echo "===== MEMÓRIA CONVERSACIONAL E PERSISTÊNCIA SEGURA ====="
"$PYTHON" -B -m unittest -v \
    teste_nixal_memoria_conversacional \
    teste_memorias_persistencia_segura

echo
echo "===== MEMÓRIA DE CONHECIMENTO ====="
"$PYTHON" -B teste_memoria_conhecimento.py

echo
echo "===== MEMÓRIA DE INVESTIGAÇÃO ====="
"$PYTHON" -B teste_memoria_investigacao_56_4_15.py

echo
echo "===== IMPORTAÇÃO SEGURA DA CRISTALIZAÇÃO ====="
"$PYTHON" -B teste_ciclo_cristalizacao_import.py

echo
echo "===== ISOLAMENTO DOS CAMINHOS DOS CRISTAIS ====="
"$PYTHON" -B -m unittest -v teste_cristal_state_dir_isolation

echo
echo "===== PERSISTÊNCIA BINÁRIA E CRISTALIZAÇÃO ====="
"$PYTHON" -B testes/teste_persistencia_cristal.py

echo
echo "SUCESSO: todas as suítes selecionadas terminaram sem erro."
echo "Estado temporário preservado para inspeção: $TEST_ROOT"
