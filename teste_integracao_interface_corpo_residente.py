from pathlib import Path

from nyxal_web_api import caminho_interface, read_nyxos_contexto


def test_contexto_operacional_expoe_corpo_fisiologia_plano_e_gateway():
    contexto = read_nyxos_contexto()

    assert contexto["sucesso"] is True
    assert "corpo" in contexto
    assert "fisiologia" in contexto
    assert "plano_central_controle" in contexto
    assert "gateway_atuacao" in contexto
    assert "runtime" in contexto

    governanca = contexto["governanca"]
    assert governanca["execucao_fisica_habilitada"] is False
    assert governanca["autorizacao_explicita"] is False
    assert governanca["integracao_executada"] is False
    assert governanca["arquitetura_modificada"] is False
    assert governanca["conhecimento_permanente"] is False


def test_interface_principal_e_recurso_visual_sao_servidos_como_arquivos():
    index = caminho_interface("index.html")
    imagem = caminho_interface("nyxal-presenca.jpg")

    assert index is not None
    assert index.is_file()
    assert imagem is not None
    assert imagem.is_file()


def test_caminho_interface_rejeita_traversal():
    assert caminho_interface("../estado_corpo_nixal.json") is None


def test_contexto_nao_concede_autoridade():
    contexto = read_nyxos_contexto()
    governanca = contexto["governanca"]

    assert governanca == {
        "execucao_fisica_habilitada": False,
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
    }
