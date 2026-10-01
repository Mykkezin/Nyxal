from pathlib import Path
import json
import logging

from mcp.server import MCPServer

from nixal_executor_ordens import ExecutorOrdensNixal


BASE_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="[Nyxal-MCP] %(message)s",
)

mcp = MCPServer("Nyxal")


executor = ExecutorOrdensNixal()


@mcp.tool()
def status_nyxal() -> str:
    """Retorna o estado operacional básico da Nyxal."""
    estado_path = BASE_DIR / "estado_nixal.json"

    if not estado_path.exists():
        return json.dumps(
            {
                "estado": "arquivo_de_estado_nao_encontrado",
                "diretorio": str(BASE_DIR),
            },
            ensure_ascii=False,
            indent=2,
        )

    try:
        estado = json.loads(estado_path.read_text(encoding="utf-8"))
        return json.dumps(estado, ensure_ascii=False, indent=2)
    except Exception as erro:
        return json.dumps(
            {
                "estado": "erro_ao_ler_estado",
                "erro": str(erro),
            },
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
def listar_arquivos() -> str:
    """Lista os arquivos do projeto Nyxal."""
    arquivos = []

    for caminho in sorted(BASE_DIR.iterdir()):
        if caminho.name.startswith("."):
            continue

        arquivos.append(
            {
                "nome": caminho.name,
                "tipo": "diretorio" if caminho.is_dir() else "arquivo",
            }
        )

    return json.dumps(
        arquivos,
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def ler_arquivo(nome_arquivo: str) -> str:
    """Lê um arquivo de texto do projeto Nyxal."""
    caminho = (BASE_DIR / nome_arquivo).resolve()

    try:
        caminho.relative_to(BASE_DIR)
    except ValueError:
        return "Erro: acesso fora do diretório da Nyxal não é permitido."

    if not caminho.exists():
        return f"Arquivo não encontrado: {nome_arquivo}"

    if not caminho.is_file():
        return f"O caminho não é um arquivo: {nome_arquivo}"

    try:
        return caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Arquivo não textual ou não UTF-8: {nome_arquivo}"
    except Exception as erro:
        return f"Erro ao ler arquivo: {erro}"


@mcp.tool()
def enviar_ordem(ordem: str) -> str:
    """Envia uma ordem para o executor operacional da Nyxal."""
    resultado = executor.atender(ordem)

    return json.dumps(
        resultado,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


@mcp.tool()
def listar_tarefas_pendentes() -> str:
    """Lista as tarefas atualmente pendentes na fila operacional da Nyxal."""
    tarefas = executor.listar_pendentes()

    return json.dumps(
        tarefas,
        ensure_ascii=False,
        indent=2,
        default=str,
    )


if __name__ == "__main__":
    mcp.run()
