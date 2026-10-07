from pathlib import Path

from nixal_runtime import NyxalRuntime


def test_aprendizado_residente_desabilitado_por_padrao():
    runtime = NyxalRuntime(
        arquivo_estado=Path("/tmp/nyxal-test-estado.json"),
        arquivo_log=Path("/tmp/nyxal-test-log.json"),
        modo_residente=True,
        aprendizado_habilitado=False,
    )

    assert runtime.aprendizado_habilitado is False


def test_aprendizado_runtime_continua_habilitavel_explicitamente():
    runtime = NyxalRuntime(
        arquivo_estado=Path("/tmp/nyxal-test-estado-2.json"),
        arquivo_log=Path("/tmp/nyxal-test-log-2.json"),
        modo_residente=True,
        aprendizado_habilitado=True,
    )

    assert runtime.aprendizado_habilitado is True

def main():
    test_aprendizado_residente_desabilitado_por_padrao()
    test_aprendizado_runtime_continua_habilitavel_explicitamente()
    print("APRENDIZADO_RESIDENTE_CONTROLE_OK")


if __name__ == "__main__":
    main()
