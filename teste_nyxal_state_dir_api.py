import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class TestDiretorioEstadoAPI(unittest.TestCase):
    def test_estado_operacional_fica_fora_do_checkout(self):
        with tempfile.TemporaryDirectory(prefix="nyxal-state-dir-") as temp:
            base = Path(temp)
            home = base / "home"
            state = base / "state"
            home.mkdir()
            state.mkdir()

            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONPATH": str(ROOT),
                "HOME": str(home),
                "USER": "nyxal-test",
                "LOGNAME": "nyxal-test",
                "LANG": "C.UTF-8",
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "NYXAL_USER_DATA_DIR": str(home / ".local/share/nyxal"),
                "NYXAL_STATE_DIR": str(state),
                "NYXAL_HTTP_TRACE_ENABLED": "0",
                "NYXAL_MCP_HTTP_ENABLED": "0",
                "NYXAL_API_HOST": "127.0.0.1",
                "NYXAL_API_PORT": "18010",
                "NYXAL_TEST_REPO_DIR": str(ROOT),
            }

            script = r'''
import json
import os
from pathlib import Path

repo = Path(os.environ["NYXAL_TEST_REPO_DIR"]).resolve()
state = Path(os.environ["NYXAL_STATE_DIR"]).resolve()
nomes = (
    "capacidades_nixal.json",
    "estado_nyxos_operacional.json",
    "eventos_delta_nyxos.json",
    "presenca_maquina_nyxos.json",
)
antes = {
    nome: (repo / nome).read_bytes()
    if (repo / nome).is_file() else None
    for nome in nomes
}

import nyxal_web_api as api

assert api.STATE_DIR == state
assert Path(api.PERSISTENCIA_OPERACIONAL.caminho).resolve() == (
    state / "estado_nyxos_operacional.json"
)
assert Path(api.DELTA_NYXOS.caminho).resolve() == (
    state / "eventos_delta_nyxos.json"
)
assert Path(api.PRESENCA_MAQUINA.arquivo).resolve() == (
    state / "presenca_maquina_nyxos.json"
)
assert (state / "estado_nyxos_operacional.json").is_file()

catalogo_estado = state / "capacidades_nixal.json"
assert catalogo_estado.is_file(), (
    "O catálogo não foi criado no diretório de estado."
)
dados_catalogo = json.loads(catalogo_estado.read_text(encoding="utf-8"))
assert isinstance(dados_catalogo, (dict, list)) and dados_catalogo, (
    "O catálogo do diretório de estado está vazio ou tem formato inesperado."
)

import nixal_capacidades as capacidades
import nixal_composicao_56_3_9 as compositor

assert Path(capacidades.ARQUIVO_CAPACIDADES).resolve() == catalogo_estado
assert Path(compositor.ARQUIVO_CAPACIDADES).resolve() == catalogo_estado

depois = {
    nome: (repo / nome).read_bytes()
    if (repo / nome).is_file() else None
    for nome in nomes
}
assert antes == depois, "A importação modificou arquivos no checkout."
print("STATE_DIR_TEST_OK")
'''

            resultado = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=45,
            )

            self.assertEqual(
                resultado.returncode,
                0,
                f"stdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}",
            )
            self.assertIn("STATE_DIR_TEST_OK", resultado.stdout)


if __name__ == "__main__":
    unittest.main()
