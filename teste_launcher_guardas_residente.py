import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAUNCHER = ROOT / "executar_nyxos_residente.py"
SERVICE = ROOT / "deploy/systemd/nyxos-residente.service"

source = LAUNCHER.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")
tree = ast.parse(source)

def verificar(condicao, descricao):
    if not condicao:
        raise AssertionError(descricao)
    print(f"[PASS] {descricao}")

flags = {
    "--habilitar-ae1-descoberta",
    "--habilitar-ae4-ciclo-evolucao",
    "--habilitar-autoreparo-residente",
}
flags_store_true = set()

for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    if not isinstance(node.func, ast.Attribute):
        continue
    if node.func.attr != "add_argument" or not node.args:
        continue
    arg = node.args[0]
    if not isinstance(arg, ast.Constant) or arg.value not in flags:
        continue
    for kw in node.keywords:
        if kw.arg == "action" and isinstance(kw.value, ast.Constant):
            if kw.value.value == "store_true":
                flags_store_true.add(arg.value)

verificar(flags_store_true == flags, "Novas flags são opt-in")
verificar(
    "habilitar_ae1 = (" in source and "if habilitar_ae1" in source,
    "AE1 depende da configuração explícita",
)
verificar(
    "if args.habilitar_ae4_ciclo_evolucao:" in source,
    "AE4 depende da configuração explícita",
)

auto_ae3_condicional = any(
    isinstance(node, ast.Assign)
    and any(
        isinstance(target, ast.Name)
        and target.id == "auto_avaliacao"
        for target in node.targets
    )
    and isinstance(node.value, ast.IfExp)
    and isinstance(node.value.test, ast.Attribute)
    and node.value.test.attr == "habilitar_ae4_ciclo_evolucao"
    and isinstance(node.value.test.value, ast.Name)
    and node.value.test.value.id == "args"
    and isinstance(node.value.body, ast.Call)
    and isinstance(node.value.body.func, ast.Name)
    and node.value.body.func.id == "AutoAvaliacaoAE3"
    and isinstance(node.value.orelse, ast.Constant)
    and node.value.orelse.value is None
    for node in ast.walk(tree)
)

verificar(
    auto_ae3_condicional,
    "AE3 só é instanciada quando AE4 está habilitada",
)

verificar(
    'contexto["auto_avaliacao_ae3_habilitada"]' in source,
    "Relatório AE3 utiliza seu estado efetivo",
)
verificar(
    "if args.habilitar_autoreparo_residente" in source
    and "else None" in source,
    "Autorreparo desabilitado por padrão",
)
verificar(
    "args.habilitar_ae5_descoberta and not args.habilitar_ae4_ciclo_evolucao"
    in source,
    "AE5 exige AE4",
)
verificar(
    'contexto["autoreparo_residente_habilitado"]' in source,
    "M5.25 usa o estado efetivo do autorreparo",
)
verificar(
    all(flag in service for flag in flags),
    "Serviço versionado declara as flags explicitamente",
)

with tempfile.TemporaryDirectory(prefix="nyxal-guard-home-") as home_temporario:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HOME"] = home_temporario

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--habilitar-autoreparo-residente",
            "--max-ciclos", "0",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    verificar(
        result.returncode == 2
        and "autorreparo bloqueado fora do checkout canônico" in result.stderr,
        "Autorreparo recusado fora de ~/Nyxal antes de iniciar o residente",
    )

    ae5_result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--habilitar-ae5-descoberta",
            "--max-ciclos", "0",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    verificar(
        ae5_result.returncode == 2
        and "--habilitar-ae5-descoberta requer "
        "--habilitar-ae4-ciclo-evolucao" in ae5_result.stderr,
        "AE5 recusada sem AE4 antes de iniciar o residente",
    )

print("\nTESTE_LAUNCHER_GUARDAS_RESIDENTE_OK")
