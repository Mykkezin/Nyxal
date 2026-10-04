#!/usr/bin/env python3
"""
NIXAL — TESTE 56.5.6
Reflexão filosófica diária com rotação aleatória e histórico sem repetição.

O teste é estrutural e, quando Node está disponível, executa o algoritmo
da interface em um ambiente local mínimo para verificar persistência,
troca diária, ausência de repetição dentro do ciclo e reinício controlado.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INTERFACE = BASE_DIR / "interface" / "index.html"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def extrair_bloco_reflexao(html: str) -> str:
    marcador_inicio = "    // ================= REFLEXÃO FILOSÓFICA DIÁRIA ================="
    marcador_fim = "    // ================= CHAT COMMAND INTERACTION ================="

    inicio = html.find(marcador_inicio)
    fim = html.find(marcador_fim)

    if inicio < 0 or fim < 0 or fim <= inicio:
        raise AssertionError("Bloco da reflexão diária não encontrado.")

    return html[inicio:fim]


def executar_teste_node(bloco: str) -> tuple[bool, str]:
    node = shutil.which("node")
    if not node:
        return True, "Node indisponível; validação estrutural preservada."

    runner = r'''
const vm = require('node:vm');
const fs = require('node:fs');

const storage = new Map();

const math = Object.create(Math);
math.random = () => 0;

const context = {
  console,
  Math: math,
  localStorage: {
    getItem(key) {
      return storage.has(key) ? storage.get(key) : null;
    },
    setItem(key, value) {
      storage.set(key, String(value));
    }
  },
  document: {
    getElementById() {
      return { innerText: '' };
    }
  }
};

const bloco = fs.readFileSync(process.argv[2], 'utf8');

const codigo = bloco + '\n' + [
  'globalThis.__api = {',
  '  catalogo: REFLEXOES_NYXAL,',
  '  selecionar: selecionarReflexaoDiaria,',
  '  chaveData: chaveDataReflexao,',
  '  estado: carregarEstadoReflexao',
  '};'
].join('\n');

vm.runInNewContext(codigo, context);

const api = context.__api;
const catalogo = api.catalogo;
const selecionar = api.selecionar;
const chaveData = api.chaveData;
const estado = api.estado;

if (!Array.isArray(catalogo) || catalogo.length < 12) {
  throw new Error('Catálogo de reflexões insuficiente.');
}

const ids = catalogo.map(item => item.id);

if (new Set(ids).size !== ids.length) {
  throw new Error('Existem IDs de reflexões repetidos.');
}

const primeiroDia = new Date(2026, 9, 4, 10, 0, 0);
const primeira = selecionar(primeiroDia);
const novamenteMesmoDia = selecionar(new Date(2026, 9, 4, 20, 0, 0));

if (primeira.id !== novamenteMesmoDia.id) {
  throw new Error('A mesma data precisa manter a mesma reflexão.');
}

const usadas = [primeira.id];

for (let indice = 1; indice < catalogo.length; indice += 1) {
  const dia = new Date(2026, 9, 4 + indice, 10, 0, 0);
  const reflexao = selecionar(dia);

  if (usadas.includes(reflexao.id)) {
    throw new Error('Repetição detectada antes do fim do ciclo.');
  }

  usadas.push(reflexao.id);
}

const depoisDoCiclo = selecionar(
  new Date(2026, 9, 4 + catalogo.length, 10, 0, 0)
);

const estadoFinal = estado();

if (estadoFinal.ciclo < 2) {
  throw new Error('O catálogo não reiniciou o ciclo após consumir todas as reflexões.');
}

if (!ids.includes(depoisDoCiclo.id)) {
  throw new Error('Reflexão do novo ciclo inválida.');
}

console.log('REFLEXAO_NODE_OK');
console.log('CATALOGO=' + catalogo.length);
console.log('CHAVE_INICIAL=' + chaveData(primeiroDia));
console.log('PRIMEIRO_ID=' + primeira.id);
console.log('CICLO_FINAL=' + estadoFinal.ciclo);
'''

    with tempfile.TemporaryDirectory() as pasta:
        pasta_path = Path(pasta)
        bloco_path = pasta_path / "bloco_reflexao.js"
        runner_path = pasta_path / "runner.js"

        bloco_path.write_text(bloco, encoding="utf-8")
        runner_path.write_text(runner, encoding="utf-8")

        processo = subprocess.run(
            [node, str(runner_path), str(bloco_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        saida = (processo.stdout + processo.stderr).strip()
        return processo.returncode == 0, saida


def main() -> None:
    verificar(
        INTERFACE.exists(),
        "interface principal existe",
    )

    html = INTERFACE.read_text(encoding="utf-8")
    bloco = extrair_bloco_reflexao(html)

    verificar(
        "REFLEXOES_NYXAL = [" in bloco,
        "catálogo local de reflexões filosóficas está presente",
    )

    verificar(
        bloco.count("id: '") >= 12,
        "catálogo possui quantidade suficiente de entradas",
    )

    verificar(
        "localStorage.getItem" in bloco
        and "localStorage.setItem" in bloco,
        "histórico das reflexões é persistido localmente",
    )

    verificar(
        "Math.random()" in bloco,
        "seleção diária utiliza aleatoriedade",
    )

    verificar(
        "candidatos = REFLEXOES_NYXAL.filter" in bloco
        and "!usadas.includes(reflexao.id)" in bloco,
        "reflexões já usadas são excluídas do ciclo atual",
    )

    verificar(
        "if (!candidatos.length)" in bloco
        and "ciclo += 1" in bloco,
        "novo ciclo só começa após consumir o catálogo",
    )

    verificar(
        "estado.ultimoDia === hoje" in bloco
        and "estado.reflexaoId" in bloco,
        "a mesma reflexão permanece durante o dia",
    )

    verificar(
        "renderReflexaoDiaria();" in html,
        "a reflexão diária é inicializada ao carregar o dashboard",
    )

    verificar(
        "dailyReflectionText" in html
        and "dailyReflectionAuthor" in html
        and "dailyReflectionWork" in html,
        "card visual possui campos para reflexão, autoria e obra",
    )

    ok_node, saida_node = executar_teste_node(bloco)

    verificar(
        ok_node,
        f"algoritmo diário passou no teste dinâmico: {saida_node}",
    )

    print()
    print("=" * 64)
    print("TESTE — REFLEXÃO DIÁRIA 56.5.6")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
