#!/usr/bin/env python3
"""
Persistência do subsistema de cristalização.

Cobrimos os critérios da auditoria:

1. Criar o cristal quando ele não existe.
2. Abrir um cristal existente sem alterá-lo.
3. Reinicializar sem duplicar nem perder dados.
4. Impedir reset destrutivo sem confirmação.
5. Backup e recuperação do último estado bom.
6. Corrupção preservada em quarentena, sem apagar a origem.
7. Gravação interrompida deixa o arquivo válido anterior utilizável.
8. Migração v1 -> v2 reaberta e comparada semanticamente.
9. IDs e referências inválidos detectados.
10. Deduplicação com preservação das relações.
11. Todos os consumidores no caminho canônico, independente do cwd.
12. Importar módulos não inicia modelo nem produz efeitos colaterais.
13. Falha de validação ou de concorrência não sobrescreve estado válido.
14. Caminhos configuráveis e rotação de backups documentada e testada.
15. Schema do cristal JSON e política de aceitação de candidato.

Cada teste roda em diretório temporário isolado, trocando os
caminhos do módulo. O cristal real da instalação nunca é tocado.

Executar:

    python3 testes/teste_persistencia_cristal.py

Os testes também são funções test_* para rodarem sob pytest, se o
ambiente tiver pytest instalado.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import gerenciador_cristal as g


# ============================================================
# ISOLAMENTO
# ============================================================

@contextlib.contextmanager
def cristal_isolado(legado=None):
    """Troca os caminhos do módulo por um diretório temporário.

    legado = bytes a serem colocados no arquivo legado antes do
    primeiro abrir, para exercitar a migração.
    """

    diretorios = (
        g.ARQUIVO,
        g.ARQUIVO_LEGADO,
        g.BACKUP_DIR,
    )

    with tempfile.TemporaryDirectory(
        prefix="teste_cristal_",
    ) as raiz:
        raiz = Path(raiz)

        g.ARQUIVO = raiz / "memoria" / "cristal" / "cristal.bin"
        g.ARQUIVO_LEGADO = raiz / "experimentos" / "cristal_gerenciador.bin"
        g.BACKUP_DIR = raiz / "memoria" / "backups"

        if legado is not None:
            g.ARQUIVO_LEGADO.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            g.ARQUIVO_LEGADO.write_bytes(
                legado
            )

        try:
            yield raiz
        finally:
            (
                g.ARQUIVO,
                g.ARQUIVO_LEGADO,
                g.BACKUP_DIR,
            ) = diretorios


def conhecimento(caminho=None):
    return g.reconstruir_conhecimento(
        *g.ler_arquivo(caminho)
    )


def ler_em_processo_separado(caminho, raiz):
    """Lê o cristal em um processo novo, simulando um reinício real."""

    script = raiz / "leitor_isolado.py"

    script.write_text(
        "import json, sys\n"
        f"sys.path.insert(0, {str(BASE_DIR)!r})\n"
        "import gerenciador_cristal as g\n"
        f"dados = g.ler_arquivo({str(caminho)!r})\n"
        "print(json.dumps(g.reconstruir_conhecimento(*dados), ensure_ascii=False))\n",
        encoding="utf-8",
    )

    processo = subprocess.run(
        [
            sys.executable,
            str(script),
        ],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    assert processo.returncode == 0, (
        f"O processo leitor falhou: {processo.stderr.strip()}"
    )

    return [
        tuple(tripla)
        for tripla in json.loads(
            processo.stdout.strip()
        )
    ]


# ============================================================
# PROCESSOS ISOLADOS E DEPENDÊNCIAS SIMULADAS
# ============================================================

STUB_OLLAMA = (
    "def chat(*args, **kwargs):\n"
    "    raise AssertionError(\n"
    "        'Nenhum modelo pode ser chamado durante a importação.'\n"
    "    )\n"
)


def ambiente_isolado(raiz, env_extra=None):
    """PATH mínimo, stub de ollama e caminhos do projeto no PYTHONPATH."""

    stub = raiz / "stub"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "ollama.py").write_text(STUB_OLLAMA, encoding="utf-8")

    ambiente = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONPATH": os.pathsep.join([str(stub), str(BASE_DIR)]),
    }

    ambiente.update(env_extra or {})

    return ambiente


def processo_isolado(script, raiz, env_extra=None, cwd="/"):
    """Roda um trecho de código em outro processo, fora do cwd do projeto.

    O cwd proposital é a raiz do sistema: qualquer caminho que dependa do
    diretório de trabalho aparece aqui como falha.
    """

    processo = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=ambiente_isolado(raiz, env_extra),
    )

    assert processo.returncode == 0, (
        f"O processo isolado falhou: {processo.stderr.strip()}"
    )

    return processo.stdout.strip()


def resultado_isolado(script, raiz, env_extra=None):
    """Extrai a linha RESULTADO do processo, ignorando avisos do módulo."""

    saida = processo_isolado(
        script,
        raiz,
        env_extra=env_extra,
    )

    for linha in reversed(saida.splitlines()):
        if linha.startswith("RESULTADO "):
            return json.loads(linha[len("RESULTADO "):])

    raise AssertionError(
        f"O processo isolado não devolveu um resultado: {saida}"
    )


# ============================================================
# 1. PERSISTÊNCIA APÓS REINÍCIO
# ============================================================

def test_persistencia_apos_reiniciar():
    """O que foi gravado continua lá na próxima abertura."""

    with cristal_isolado() as raiz:
        destino = raiz / "memoria" / "cristal" / "cristal.bin"

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        g.registrar_experiencia(
            "astro",
            "observa",
            "observação",
            caminho=destino,
        )

        gravado = conhecimento(destino)

        # Relemos em um processo novo: simula reiniciar a Nyxal.
        relido = ler_em_processo_separado(
            destino,
            raiz,
        )

        assert relido == gravado, (
            "O processo reiniciado não devolve o mesmo conhecimento."
        )

        assert ("astro", "observa", "observação") in relido, (
            "Conceito e relação novos não persistiram."
        )

        assert destino.exists(), (
            "O cristal autoritativo não foi criado."
        )


def test_persistencia_preserva_cabecalho_e_vocabulario():
    """Reiniciar não reescreve o vocabulário base do zero."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        conceitos_1, _, _ = g.abrir_ou_criar_cristal()

        ids_base = dict(conceitos_1)

        g.registrar_experiencia(
            "gato",
            "e_um",
            "animal",
            caminho=destino,
        )

        conceitos_2, _, _ = g.abrir_ou_criar_cristal()

        for nome, indice in ids_base.items():
            assert conceitos_2[nome] == indice, (
                f"O ID de {nome} mudou entre aberturas."
            )

        assert conceitos_2["gato"] > max(ids_base.values()), (
            "Conceito novo não recebeu ID acima dos existentes."
        )


# ============================================================
# 2. PROTEÇÃO CONTRA PERDA
# ============================================================

def test_abrir_nao_apaga_cristal_existente():
    """abrir_ou_criar_cristal() é não destrutivo."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        antes = conhecimento(destino)
        bytes_antes = destino.read_bytes()

        g.abrir_ou_criar_cristal()

        assert conhecimento(destino) == antes, (
            "Abrir o cristal apagou conhecimento."
        )

        assert destino.read_bytes() == bytes_antes, (
            "Abrir o cristal reescreveu o arquivo."
        )


def test_inicializar_deprecated_nao_destroi():
    """inicializar_cristal() continua existindo, mas não apaga."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        antes = conhecimento(destino)

        g.inicializar_cristal()

        assert conhecimento(destino) == antes, (
            "inicializar_cristal() voltou a ser destrutivo."
        )


def test_reset_destrutivo_exige_confirmacao():
    """Sem confirmação explícita o reset é recusado."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        antes = conhecimento(destino)

        try:
            g.reset_destrutivo_cristal()
        except PermissionError:
            recusa = None
        else:
            raise AssertionError(
                "reset_destrutivo_cristal() sem confirmação não falhou."
            )

        assert conhecimento(destino) == antes, (
            "O reset recusado mesmo assim alterou o cristal."
        )


def test_reset_destrutivo_faz_backup_antes_de_apagar():
    """O reset confirmado preserva o conteúdo anterior em backup."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        antes = conhecimento(destino)

        g.reset_destrutivo_cristal(
            confirmacao_explicita=True,
        )

        assert conhecimento(destino) == [], (
            "O cristal não foi zerado pelo reset confirmado."
        )

        backups = g.listar_backups(destino)

        assert backups, (
            "O reset confirmado não gerou backup."
        )

        restaurado = g.reconstruir_conhecimento(
            *g.ler_bytes_cristal(
                backups[-1].read_bytes()
            )[:3]
        )

        assert restaurado == antes, (
            "O backup do reset não contém o conhecimento anterior."
        )


def test_cristal_corrompido_vai_para_quarentena_e_recupera_backup():
    """Arquivo ilegível nunca é deletado: vai para quarentena."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        ultimo_saudavel = conhecimento(destino)

        # Corrompemos o cristal ativo com bytes sem sentido.
        destino.write_bytes(
            b"NXCM" + bytes([1]) + b"\xff\xffresto"
        )

        recuperado = g.abrir_ou_criar_cristal()

        assert recuperado is not None, (
            "A recuperação por backup não devolveu um cristal."
        )

        assert g.reconstruir_conhecimento(*recuperado) == ultimo_saudavel, (
            "O backup restaurado não corresponde ao último estado válido."
        )

        quarentena = sorted(
            destino.parent.glob(f"{destino.name}.corrompido-*")
        )

        assert quarentena, (
            "O arquivo corrompido não foi preservado em quarentena."
        )

        assert quarentena[-1].read_bytes() == b"NXCM" + bytes([1]) + b"\xff\xffresto", (
            "A quarentena não preserva os bytes originais do arquivo corrompido."
        )


def test_falha_no_meio_da_gravacao_preserva_original():
    """Escrita atômica: se a troca falhar, o arquivo anterior fica."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        bytes_antes = destino.read_bytes()
        conhecimento_antes = conhecimento(destino)

        substituto = g.os.replace

        def replace_que_falha(*_, **__):
            raise OSError(
                "Simulação de queda no meio da troca atômica."
            )

        g.os.replace = replace_que_falha

        try:
            g.gravar_atomicamente(
                bytes_antes + b"\x01\x00\x05lixo",
                destino,
            )
        except OSError:
            falhou = True
        else:
            falhou = False
        finally:
            g.os.replace = substituto

        assert falhou, (
            "A gravação com falha simulada deveria propagar o erro."
        )

        assert destino.read_bytes() == bytes_antes, (
            "Uma gravação interrompida alterou o cristal anterior."
        )

        assert conhecimento(destino) == conhecimento_antes, (
            "Uma gravação interrompida alterou o conhecimento."
        )

        sobras = sorted(
            destino.parent.glob(f".{destino.name}.tmp-*")
        )

        assert not sobras, (
            "A gravação interrompida deixou arquivo temporário para trás."
        )


def test_backup_anterior_a_cada_gravacao():
    """Cada gravação preserva o estado anterior em backup."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        g.registrar_experiencia(
            "experimento",
            "testa",
            "hipótese",
            caminho=destino,
        )

        backups = g.listar_backups(destino)

        assert len(backups) >= 2, (
            f"Esperávamos backups por gravação, encontramos {len(backups)}."
        )

        mais_antigo = g.reconstruir_conhecimento(
            *g.ler_bytes_cristal(
                backups[0].read_bytes()
            )[:3]
        )

        assert ("experimento", "testa", "hipótese") not in mais_antigo, (
            "O backup mais antigo já contém a gravação mais recente."
        )


# ============================================================
# 3. INTEGRIDADE BINÁRIA
# ============================================================

def test_integridade_de_cristal_valido():
    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        resultado = g.validar_integridade(destino)

        assert resultado["ok"] is True, (
            "Cristal válido foi rejeitado pela validação."
        )

        assert resultado["triplas"] == 1, (
            "A contagem de triplas não confere."
        )

        assert resultado["versao"] in (g.VERSAO_1, g.VERSAO_2), (
            "A versão relatada é inesperada."
        )


def test_integridade_detecta_magic_invalido():
    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        bom = destino.read_bytes()

        destino.write_bytes(
            b"NXXZ" + bom[4:]
        )

        try:
            g.validar_integridade(destino)
        except ValueError:
            return

        raise AssertionError(
            "MAGIC inválido passou na validação de integridade."
        )


def test_integridade_detecta_string_truncada():
    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        bom = destino.read_bytes()

        # Recortamos o arquivo no meio de um nome de conceito.
        destino.write_bytes(
            bom[:-3]
        )

        try:
            g.validar_integridade(destino)
        except ValueError:
            return

        raise AssertionError(
            "String truncada passou na validação de integridade."
        )


def test_integridade_detecta_tipos_desconhecidos():
    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        bom = destino.read_bytes()

        destino.write_bytes(
            bom + bytes([99, 1, 0])
        )

        try:
            g.validar_integridade(destino)
        except ValueError:
            return

        raise AssertionError(
            "Tipo de registro desconhecido passou na validação."
        )


def test_integridade_detecta_referencia_orfa():
    """Bloco que aponta para ID nunca declarado é rejeitado."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        dados = g.serializar_cristal(
            {
                nome: indice
                for indice, nome in enumerate(g.CONCEITOS_BASE)
            },
            {
                nome: indice
                for indice, nome in enumerate(g.RELACOES_BASE)
            },
            [
                [
                    (
                        0,
                        0,
                        len(g.CONCEITOS_BASE) + 7,
                    )
                ]
            ],
            g.VERSAO_2,
        )

        # Forjamos bytes com um ID de objeto que nunca foi declarado.
        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destino.write_bytes(
            dados
        )

        try:
            g.validar_integridade(destino)
        except ValueError:
            return
        except Exception as erro:
            raise AssertionError(
                f"A referência órfã deveria gerar ValueError: {erro}"
            )

        raise AssertionError(
            "Referência órfã passou na validação de integridade."
        )


def test_gravacao_interrompida_por_escrita_parcial_pode_ser_recuperada():
    """Um append truncado é detectado e o backup devolve os dados."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        saudavel = conhecimento(destino)

        # Imitamos um processo morto no meio de um registro de bloco.
        com_parcial = destino.read_bytes() + bytes(
            [g.TIPO_BLOCO, 1, 0]
        )

        destino.write_bytes(
            com_parcial
        )

        try:
            g.validar_integridade(destino)
        except ValueError:
            recuperado = g.abrir_ou_criar_cristal()

            assert g.reconstruir_conhecimento(*recuperado) == saudavel, (
                "A recuperação do append truncado não devolveu os dados."
            )

            return

        raise AssertionError(
            "Um bloco pela metade passou na validação de integridade."
        )


# ============================================================
# 4. DEDUPLICAÇÃO
# ============================================================

def test_experiencia_repetida_nao_cresce_arquivo():
    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        primeira = g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        assert primeira["classificacao"] == "REUTILIZAÇÃO", (
            f"Classificação inesperada: {primeira['classificacao']}"
        )

        tamanho_apos_primeira = destino.stat().st_size

        segunda = g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        assert segunda["classificacao"] == "DUPLICADO", (
            f"Experiência repetida: {segunda['classificacao']}"
        )

        assert segunda["crescimento"] == 0, (
            "Experiência duplicada cresceu o arquivo."
        )

        assert destino.stat().st_size == tamanho_apos_primeira, (
            "O arquivo cresceu apesar da deduplicação."
        )

        triplas = [
            tripla
            for tripla in conhecimento(destino)
            if tripla == ("observação", "pode_gerar", "hipótese")
        ]

        assert len(triplas) == 1, (
            f"Esperávamos 1 cópia da tripla, encontramos {len(triplas)}."
        )


def test_deduplicacao_sobrevive_a_reinicio():
    """A deduplicação usa o arquivo, não a memória do processo."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        tamanho_antes = destino.stat().st_size

        # Reabrimos o arquivo, como um processo novo.
        g.abrir_ou_criar_cristal()

        resultado = g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
            caminho=destino,
        )

        assert resultado["classificacao"] == "DUPLICADO", (
            "Após reiniciar, a experiência repetida não foi deduplicada."
        )

        assert destino.stat().st_size == tamanho_antes, (
            "Repetição após reinício cresceu o arquivo."
        )


# ============================================================
# 5. EXPANSÃO ALÉM DE 1 BYTE
# ============================================================

def test_v2_armazena_ids_acima_de_255():
    """A versão 2 representa mais de 256 conceitos."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        g.criar_cristal_novo(
            destino,
            versao=g.VERSAO_2,
        )

        assert g.ler_bytes_cristal(
            destino.read_bytes()
        )[3] == g.VERSAO_2, (
            "O cristal novo não está na versão 2."
        )

        esperados = []

        for indice in range(300):
            sujeito = f"conceito_{indice}"
            objeto = f"alvo_{indice}"

            g.registrar_experiencia(
                sujeito,
                "mapeia",
                objeto,
                caminho=destino,
                backup_antes_de_gravar=False,
            )

            esperados.append(
                (
                    sujeito,
                    "mapeia",
                    objeto,
                )
            )

        conceitos, relacoes, blocos = g.ler_arquivo(destino)

        assert len(conceitos) == len(g.CONCEITOS_BASE) + 600, (
            f"Contagem de conceitos incorreta: {len(conceitos)}"
        )

        ids_altos = [
            indice
            for indice in conceitos.values()
            if indice > 255
        ]

        assert ids_altos, (
            "Nenhum ID acima de 255 foi armazenado."
        )

        maior_id = max(
            id_
            for bloco in blocos
            for tripla in bloco
            for id_ in tripla
        )

        assert maior_id > 255, (
            f"O maior ID nos blocos é {maior_id}, deveria passar de 255."
        )

        atual = conhecimento(destino)

        for tripla in esperados:
            assert tripla in atual, (
                f"Tripla com ID alto não reconstruída: {tripla}"
            )

        assert g.validar_integridade(destino)["ok"] is True, (
            "O cristal expandido não passou na validação de integridade."
        )


def test_v1_e_preservado_e_pode_ser_expandido_sem_perda():
    """Um cristal legado v1 migra, cresce em v1 e então expande."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        conceitos_v1 = {
            f"concept_{indice}": indice
            for indice in range(256)
        }

        relacoes_v1 = {
            f"rel_{indice}": indice
            for indice in range(10)
        }

        blocos_v1 = [
            [
                (
                    0,
                    0,
                    1,
                )
            ]
        ]

        g.gravar_atomicamente(
            g.serializar_cristal(
                conceitos_v1,
                relacoes_v1,
                blocos_v1,
                versao=g.VERSAO_1,
            ),
            destino,
        )

        resultado_v1 = g.validar_integridade(destino)

        assert resultado_v1["versao"] == g.VERSAO_1, (
            "O cristal forjado não é lido como v1."
        )

        assert resultado_v1["largura"] == 1, (
            "A largura relatada para v1 não é 1 byte."
        )

        # O v1 está cheio: não cabe um conceito novo além de 256.
        try:
            g.registrar_experiencia(
                "extra",
                "rel_0",
                "concept_0",
                caminho=destino,
            )
        except ValueError:
            cheio = True
        else:
            cheio = False

        assert cheio, (
            "O v1 deveria recusar o 257º conceito."
        )

        assert conhecimento(destino) == [
            (
                "concept_0",
                "rel_0",
                "concept_1",
            )
        ], (
            "A recusa do v1 alterou o conhecimento existente."
        )

        informacao = g.expandir_cristal(
            destino,
            nova_versao=g.VERSAO_2,
        )

        assert informacao["versao_anterior"] == g.VERSAO_1, (
            "A expansão não relatou a versão anterior correta."
        )

        assert informacao["versao_atual"] == g.VERSAO_2, (
            "A expansão não gerou versão 2."
        )

        assert conhecimento(destino) == [
            (
                "concept_0",
                "rel_0",
                "concept_1",
            )
        ], (
            "A expansão perdeu conhecimento."
        )

        g.registrar_experiencia(
            "extra",
            "rel_0",
            "concept_0",
            caminho=destino,
        )

        concepts_depois, _, _ = g.ler_arquivo(destino)

        assert "extra" in concepts_depois, (
            "Após expandir, o conceito novo não entrou."
        )

        assert concepts_depois["extra"] == 256, (
            f"ID do conceito expandido incorreto: {concepts_depois['extra']}"
        )

        assert g.validar_integridade(destino)["ok"] is True, (
            "O cristal expandido não passou na validação de integridade."
        )


def test_v1_legivel_sem_migracao():
    """Cristais v1 existentes continuam legíveis pelo leitor atual."""

    with cristal_isolado() as raiz:
        destino = g.ARQUIVO

        dados_v1 = g.serializar_cristal(
            {
                nome: indice
                for indice, nome in enumerate(g.CONCEITOS_BASE)
            },
            {
                nome: indice
                for indice, nome in enumerate(g.RELACOES_BASE)
            },
            [
                [
                    (
                        1,
                        5,
                        0,
                    )
                ]
            ],
            versao=g.VERSAO_1,
        )

        g.gravar_atomicamente(
            dados_v1,
            destino,
        )

        conceitos, relacoes, blocos = g.abrir_ou_criar_cristal()

        assert g.reconstruir_conhecimento(
            conceitos,
            relacoes,
            blocos,
        ) == [
            (
                "observação",
                "pode_gerar",
                "hipótese",
            )
        ], (
            "A leitura compatível de v1 devolveu conhecimento diferente."
        )

        resultado = g.validar_integridade(destino)

        assert resultado["versao"] == g.VERSAO_1, (
            "O cristal v1 foi regravado como v2 sem querer."
        )


# ============================================================
# MIGRAÇÃO DO LEGADO
# ============================================================

def test_migracao_copia_legado_para_fonte_autoritativa():
    """O legado é copiado, nunca movido nem apagado."""

    legado = g.serializar_cristal(
        {
            nome: indice
            for indice, nome in enumerate(g.CONCEITOS_BASE)
        },
        {
            nome: indice
            for indice, nome in enumerate(g.RELACOES_BASE)
        },
        [
            [
                (
                    1,
                    5,
                    0,
                )
            ]
        ],
        versao=g.VERSAO_1,
    )

    with cristal_isolado(
        legado=legado,
    ) as raiz:
        assert not g.ARQUIVO.exists(), (
            "A fonte autoritativa já existia antes do abrir."
        )

        conceitos, relacoes, blocos = g.abrir_ou_criar_cristal()

        assert g.reconstruir_conhecimento(
            conceitos,
            relacoes,
            blocos,
        ) == [
            (
                "observação",
                "pode_gerar",
                "hipótese",
            )
        ], (
            "A migração não trouxe o conhecimento do legado."
        )

        assert g.ARQUIVO_LEGADO.exists(), (
            "A migração apagou o arquivo legado."
        )

        assert g.ARQUIVO_LEGADO.read_bytes() == legado, (
            "A migração alterou o arquivo legado."
        )

        assert g.ARQUIVO.read_bytes() == legado, (
            "A migração não preservou os bytes do legado por cópia."
        )


def test_migracao_recusa_legado_corrompido_sem_tocar_destino():
    """Legado ilegível não contamina a fonte autoritativa."""

    legado_sujado = b"NXCM\x01\xff\xfflixo"

    with cristal_isolado(
        legado=legado_sujado,
    ) as raiz:
        conceitos, relacoes, blocos = g.abrir_ou_criar_cristal()

        assert g.ARQUIVO_LEGADO.read_bytes() == legado_sujado, (
            "A abertura mexeu no arquivo legado corrompido."
        )

        assert g.validar_integridade(g.ARQUIVO)["ok"] is True, (
            "A fonte autoritativa não ficou íntegra."
        )

        assert g.reconstruir_conhecimento(
            conceitos,
            relacoes,
            blocos,
        ) == [], (
            "Diante de legado corrompido deveríamos criar cristal vazio."
        )

        assert len(conceitos) == len(g.CONCEITOS_BASE), (
            "O cristal novo não traz o vocabulário base completo."
        )


# ============================================================
# 11. CAMINHO CANÔNICO INDEPENDENTE DO CWD
# ============================================================

def test_caminhos_do_projeto_nao_dependem_do_cwd():
    """Rodando de fora do projeto, os caminhos continuam ancorados nele."""

    script = (
        "import json, os\n"
        "import gerenciador_cristal as g\n"
        "import cristalizacao, ciclo_cristalizacao, experiencia_qwen\n"
        "print('RESULTADO ' + json.dumps({\n"
        "    'cwd': os.getcwd(),\n"
        "    'binario': str(g.ARQUIVO),\n"
        "    'legado': str(g.ARQUIVO_LEGADO),\n"
        "    'backups': str(g.BACKUP_DIR),\n"
        "    'demo': str(g.ARQUIVO_DEMO),\n"
        "    'ciclo': str(ciclo_cristalizacao.ARQUIVO_CRISTAL),\n"
        "    'cristalizacao': str(cristalizacao.ARQUIVO),\n"
        "    'consumidor': str(experiencia_qwen.caminho_do_cristal()),\n"
        "}))\n"
    )

    with cristal_isolado() as raiz:
        dados = resultado_isolado(
            script,
            raiz,
        )

        assert dados["cwd"] == "/", (
            "O processo isolado não rodou fora do projeto."
        )

        for nome, caminho in dados.items():
            if nome == "cwd":
                continue

            assert os.path.isabs(caminho), (
                f"{nome} não é um caminho absoluto: {caminho}"
            )

            assert caminho.startswith(str(BASE_DIR)), (
                f"{nome} escapou da raiz do projeto: {caminho}"
            )

        assert dados["binario"] == str(
            BASE_DIR / "memoria" / "cristal" / "cristal.bin"
        ), "A fonte autoritativa não é a esperada."

        assert dados["consumidor"] == dados["binario"], (
            "experiencia_qwen não segue o caminho canônico do gerenciador."
        )


def test_variaveis_de_ambiente_redirecionam_todos_os_consumidores():
    """A configuração explícita vale para o gerenciador e para os consumidores."""

    script = (
        "import json\n"
        "import gerenciador_cristal as g\n"
        "import experiencia_qwen\n"
        "conceitos, relacoes, blocos = g.abrir_ou_criar_cristal()\n"
        "print('RESULTADO ' + json.dumps({\n"
        "    'binario': str(g.ARQUIVO),\n"
        "    'consumidor': str(experiencia_qwen.caminho_do_cristal()),\n"
        "    'backups': sorted(p.name for p in g.BACKUP_DIR.glob('*')),\n"
        "    'ok': g.validar_integridade()['ok'],\n"
        "}))\n"
    )

    with cristal_isolado() as raiz:
        alvo = raiz / "config" / "cristal.bin"

        dados = resultado_isolado(
            script,
            raiz,
            env_extra={
                "NYXAL_CRISTAL_ARQUIVO": str(alvo),
                "NYXAL_CRISTAL_LEGADO": str(
                    raiz / "config" / "legado.bin"
                ),
                "NYXAL_CRISTAL_BACKUPS": str(
                    raiz / "config" / "backups"
                ),
            },
        )

        assert dados["binario"] == str(alvo), (
            "A variável de ambiente não redirecionou o gerenciador."
        )

        assert dados["consumidor"] == str(alvo), (
            "O consumidor continua preso ao caminho importado por valor."
        )

        assert alvo.exists(), (
            "O caminho configurado não recebeu o cristal."
        )

        assert dados["ok"] is True, (
            "O cristal criado no caminho configurado não é íntegro."
        )

        assert dados["backups"] == ["cristal_ultimo_bom.bin"], (
            "Os backups não seguiram a configuração."
        )


# ============================================================
# 12. IMPORTAÇÃO SEM EFEITOS COLATERAIS
# ============================================================

def test_import_dos_consumidores_nao_inicia_modelo_nem_escreve():
    """Importar não chama o Qwen, não escreve memória e nada imprime."""

    script = (
        "import gerenciador_cristal\n"
        "import cristalizacao\n"
        "import ciclo_cristalizacao\n"
        "import experiencia_qwen\n"
        "print('IMPORTADO')\n"
        "assert hasattr(ciclo_cristalizacao, 'main'), 'ciclo sem main()'\n"
        "assert hasattr(cristalizacao, 'main'), 'cristalizacao sem main()'\n"
        "try:\n"
        "    experiencia_qwen.interpretar('uma observação')\n"
        "except AssertionError:\n"
        "    print('MODELO_SO_QUANDO_CHAMADO')\n"
        "try:\n"
        "    cristalizacao.cristalizar('uma hipótese')\n"
        "except AssertionError:\n"
        "    print('MODELO_SO_QUANDO_CHAMADO_CRISTALIZACAO')\n"
    )

    with cristal_isolado() as raiz:
        destino_binario = raiz / "config" / "cristal.bin"

        saida = processo_isolado(
            script,
            raiz,
            env_extra={
                "NYXAL_CRISTAL_ARQUIVO": str(destino_binario),
                "NYXAL_CRISTAL_BACKUPS": str(raiz / "config" / "backups"),
            },
        )

        assert saida.splitlines()[0] == "IMPORTADO", (
            f"A importação imprimiu efeitos colaterais: {saida}"
        )

        assert "MODELO_SO_QUANDO_CHAMADO" in saida, (
            "experiencia_qwen não adiou o uso do modelo."
        )

        assert "MODELO_SO_QUANDO_CHAMADO_CRISTALIZACAO" in saida, (
            "cristalizacao não adiou o uso do modelo."
        )

        assert not destino_binario.exists(), (
            "A importação criou o cristal autoritativo."
        )

        assert not (raiz / "config" / "backups").exists(), (
            "A importação criou backups."
        )


# ============================================================
# 13. RECUSA DE ESCRITA CONCORRENTE
# ============================================================

def test_gravacao_concorrente_e_recusada_sem_sobrescrever():
    """Se outro processo escreveu antes, a versão mais nova é preservada."""

    with cristal_isolado() as raiz:
        g.abrir_ou_criar_cristal()

        base = g.ARQUIVO.read_bytes()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
        )

        concorrente = g.ARQUIVO.read_bytes()

        assert concorrente != base, (
            "A escrita concorrente não alterou o arquivo."
        )

        try:
            g.gravar_atomicamente(
                base + b"\x00\x00",
                esperado_antes=base,
            )
        except g.CristalAlterado:
            recusa = None
        else:
            raise AssertionError(
                "gravar_atomicamente aceitou sobrescrever versão mais nova."
            )

        assert recusa is None

        assert g.ARQUIVO.read_bytes() == concorrente, (
            "A recusa alterou o conteúdo mais recente."
        )

        assert g.validar_integridade()["ok"] is True, (
            "O cristal deixou de ser íntegro após a recusa."
        )

        temporarios = [
            arquivo.name
            for arquivo in g.ARQUIVO.parent.iterdir()
            if ".tmp-" in arquivo.name
        ]

        assert temporarios == [], (
            f"Restaram arquivos temporários: {temporarios}"
        )


def test_criar_cristal_nao_sobrescreve_estado_existente():
    """A criação nunca substitui um cristal já preenchido."""

    with cristal_isolado() as raiz:
        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
        )

        antes = g.ARQUIVO.read_bytes()

        try:
            g.criar_cristal_novo()
        except g.CristalAlterado:
            recusa = None
        else:
            raise AssertionError(
                "criar_cristal_novo() substituiu um cristal existente."
            )

        assert recusa is None

        assert g.ARQUIVO.read_bytes() == antes, (
            "A criação recusada mesmo assim reescreveu o cristal."
        )

        assert len(conhecimento()) > 0, (
            "O conhecimento existente foi perdido."
        )


def test_checkpoint_nao_e_envenenado_por_conteudo_invalido():
    """Bytes inválidos podem ser escritos, mas nunca viram estado bom."""

    with cristal_isolado() as raiz:
        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
        )

        estado_bom = conhecimento()

        assert estado_bom, (
            "A experiência não chegou ao cristal."
        )

        assert g.caminho_checkpoint(g.ARQUIVO).read_bytes() == (
            g.ARQUIVO.read_bytes()
        ), (
            "O checkpoint não acompanhava o último estado gravado."
        )

        antes_da_tentativa = g.caminho_checkpoint(
            g.ARQUIVO
        ).read_bytes()

        lixo = b"NXCM\x01\xff\xff\xfflixo"

        try:
            g.validar_bytes_cristal(lixo, g.ARQUIVO)
        except Exception:
            reprovado = None
        else:
            raise AssertionError(
                "A validação estrutural aceitou bytes de lixo."
            )

        assert reprovado is None

        g.gravar_atomicamente(
            lixo,
            g.ARQUIVO,
        )

        assert g.ARQUIVO.read_bytes() == lixo, (
            "A escrita explícita não deveria ter sido bloqueada."
        )

        assert g.caminho_checkpoint(g.ARQUIVO).read_bytes() == (
            antes_da_tentativa
        ), (
            "O checkpoint registrou um conteúdo que a validação reprova."
        )

        recuperado = g.reconstruir_conhecimento(
            *g.abrir_ou_criar_cristal()
        )

        assert recuperado == estado_bom, (
            "A abertura não restaurou o último estado bom real."
        )

        assert g.validar_integridade()["ok"] is True, (
            "O cristal restaurado não voltou a ser íntegro."
        )


# ============================================================
# 14. FIDELIDADE DO CHECKPOINT E ROTAÇÃO DE BACKUPS
# ============================================================

def test_checkpoint_recupera_o_ultimo_estado_bom():
    """A recuperação devolve o estado mais recente, não o penúltimo."""

    with cristal_isolado() as raiz:
        g.abrir_ou_criar_cristal()

        g.registrar_experiencia(
            "observação",
            "pode_gerar",
            "hipótese",
        )

        g.registrar_experiencia(
            "hipótese",
            "pode_gerar",
            "previsão",
        )

        estado = conhecimento()

        assert ("hipótese", "pode_gerar", "previsão") in estado, (
            "A última experiência não chegou ao cristal."
        )

        g.ARQUIVO.write_bytes(
            b"NXCM\x01lixo\x00\x00"
        )

        recuperado = g.reconstruir_conhecimento(
            *g.abrir_ou_criar_cristal()
        )

        assert recuperado == estado, (
            "A recuperação perdeu a experiência mais recente."
        )


def test_rotacao_de_backups_preserva_os_mais_recentes():
    """A política de rotação mantém apenas os backups mais novos."""

    with cristal_isolado() as raiz:
        g.abrir_ou_criar_cristal()

        g.BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        criados = []

        for indice in range(
            g.MAX_BACKUPS_PRESERVADOS + 5
        ):
            nome = (
                f"cristal_backup_20261028_{indice:06d}_{indice:06d}.bin"
            )

            (g.BACKUP_DIR / nome).write_bytes(
                b"NXCM\x01"
            )

            criados.append(nome)

        g.podar_backups()

        restantes = [
            arquivo.name
            for arquivo in g.listar_backups()
        ]

        assert len(restantes) == g.MAX_BACKUPS_PRESERVADOS, (
            f"A rotação deveria deixar {g.MAX_BACKUPS_PRESERVADOS} "
            f"backups, ficou com {len(restantes)}."
        )

        assert restantes == criados[-g.MAX_BACKUPS_PRESERVADOS:], (
            "A rotação descartou os backups mais recentes."
        )

        assert (
            g.BACKUP_DIR / "cristal_ultimo_bom.bin"
        ).exists(), (
            "A rotação apagou o checkpoint do último estado bom."
        )

        for indice in range(3):
            g.registrar_experiencia(
                f"observacao-{indice}",
                "pode_gerar",
                f"hipotese-{indice}",
            )

        assert len(g.listar_backups()) <= g.MAX_BACKUPS_PRESERVADOS, (
            "Gravações reais ignoraram a política de rotação."
        )

        assert g.validar_integridade()["ok"] is True, (
            "O cristal perdeu integridade durante a rotação."
        )

        estado = conhecimento()

        assert len(estado) >= 3, (
            "A rotação corrompeu o conhecimento gravado."
        )


# ============================================================
# 15. CRISTALIZAÇÃO JSON: SCHEMA E POLÍTICA DE ACEITAÇÃO
# ============================================================

def test_schema_invalido_do_cristal_json_preserva_arquivo():
    """Um JSON fora do schema nunca substitui o último estado válido."""

    import cristalizacao

    valido = {
        "conceitos": {
            "Hipótese": {
                "conceito": "Hipótese",
                "essencia": "ideia provisória",
                "relacoes": ["observação"],
                "incerteza": "ainda sem evidência",
            }
        }
    }

    quebrados = [
        [],
        {"conceitos": []},
        {"conceitos": {"Hipótese": {}}},
        {
            "conceitos": {
                "Hipótese": {
                    "conceito": "Outro",
                    "essencia": "ideia",
                    "relacoes": [],
                    "incerteza": "",
                }
            }
        },
        {
            "conceitos": {
                "Hipótese": {
                    "conceito": "Hipótese",
                    "essencia": 12,
                    "relacoes": [],
                    "incerteza": "",
                }
            }
        },
        {
            "conceitos": {
                "Hipótese": {
                    "conceito": "Hipótese",
                    "essencia": "ideia",
                    "relacoes": "observação",
                    "incerteza": "",
                }
            }
        },
        {
            "conceitos": {
                "Hipótese": {
                    "conceito": "Hipótese",
                    "essencia": "ideia",
                    "relacoes": [12],
                    "incerteza": "",
                }
            }
        },
    ]

    anterior = cristalizacao.ARQUIVO

    with cristal_isolado() as raiz:
        destino = raiz / "memoria" / "cristalizacao.json"

        cristalizacao.ARQUIVO = destino

        try:
            cristalizacao.salvar(valido)

            esperado_no_arquivo = json.dumps(
                valido,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")

            assert destino.read_bytes() == esperado_no_arquivo, (
                "A gravação válida não produziu o formato esperado."
            )

            assert cristalizacao.carregar() == valido, (
                "A releitura do cristal JSON não foi fiel."
            )

            for quebrado in quebrados:
                try:
                    cristalizacao.salvar(quebrado)
                except ValueError:
                    continue

                raise AssertionError(
                    f"O schema aceitou um cristal inválido: {quebrado}"
                )

            assert destino.read_bytes() == esperado_no_arquivo, (
                "Uma gravação recusada alterou o arquivo válido."
            )

            novo = cristalizacao.adicionar_conceito(
                cristalizacao.carregar(),
                {
                    "conceito": "Previsão",
                    "essencia": "o que se espera",
                    "relacoes": ["hipótese"],
                    "incerteza": "teste pendente",
                },
            )

            assert set(novo["conceitos"]) == {"Hipótese", "Previsão"}, (
                "O acréscimo de conceito não preservou os anteriores."
            )

            try:
                cristalizacao.adicionar_conceito(
                    novo,
                    {
                        "conceito": "Previsão",
                        "essencia": "outra",
                        "relacoes": [],
                        "incerteza": "",
                    },
                )
            except ValueError:
                recusa = None
            else:
                raise AssertionError(
                    "adicionar_conceito sobrescreveu conceito existente."
                )

            assert recusa is None

            destino.write_bytes(
                b'{"conceitos": {"Hip'
            )

            assert cristalizacao.carregar() == {"conceitos": {}}, (
                "O JSON truncado não devolveu o padrão."
            )

            quarentena = [
                arquivo.name
                for arquivo in destino.parent.iterdir()
                if arquivo.name.startswith("cristalizacao.json.")
            ]

            assert quarentena, (
                "O JSON truncado não foi preservado em quarentena."
            )
        finally:
            cristalizacao.ARQUIVO = anterior


def test_politica_de_aceitacao_do_candidato():
    """Candidato só substitui o cristal se for fiel e menor."""

    import ciclo_cristalizacao

    assert ciclo_cristalizacao.candidato_aceitavel(
        92.9, 300, 92.9, 200,
    ) is True, (
        "Candidato fiel e menor foi rejeitado."
    )

    assert ciclo_cristalizacao.candidato_aceitavel(
        92.9, 300, 85.0, 50,
    ) is False, (
        "Candidato menor mas menos fiel foi aceito."
    )

    assert ciclo_cristalizacao.candidato_aceitavel(
        92.9, 300, 100.0, 300,
    ) is False, (
        "Candidato sem redução de tamanho foi aceito."
    )

    anterior = ciclo_cristalizacao.ARQUIVO_CRISTAL

    with cristal_isolado() as raiz:
        destino = raiz / "memoria" / "cristal_atual.json"

        ciclo_cristalizacao.ARQUIVO_CRISTAL = destino

        try:
            bom = {
                "conceito": "Hipótese",
                "essencia": "ideia provisória",
                "relacoes": ["observação"],
                "incerteza": "limites",
            }

            ciclo_cristalizacao.salvar_cristal(bom)

            conteudo_valido = json.dumps(
                bom,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")

            assert destino.read_bytes() == conteudo_valido, (
                "A gravação do ciclo não produziu o formato esperado."
            )

            for ruim in ([], {}, "texto", None):
                try:
                    ciclo_cristalizacao.salvar_cristal(ruim)
                except ValueError:
                    continue

                raise AssertionError(
                    f"O ciclo gravou um candidato inválido: {ruim}"
                )

            assert destino.read_bytes() == conteudo_valido, (
                "O candidato inválido sobrescreveu o cristal do ciclo."
            )

            destino.write_bytes(
                b'{"conceito": "Hip'
            )

            carregado = ciclo_cristalizacao.carregar_cristal()

            assert carregado == ciclo_cristalizacao.CRISTAL_INICIAL, (
                "O JSON ilegível não devolveu o estado inicial."
            )

            assert carregado is not ciclo_cristalizacao.CRISTAL_INICIAL, (
                "O carregador expõe o estado inicial mutável do módulo."
            )

            quarentena = [
                arquivo.name
                for arquivo in destino.parent.iterdir()
                if arquivo.name.startswith("cristal_atual.json.")
            ]

            assert quarentena, (
                "O JSON ilegível do ciclo não foi preservado."
            )
        finally:
            ciclo_cristalizacao.ARQUIVO_CRISTAL = anterior


# ============================================================
# EXECUTOR
# ============================================================

TESTES = [
    ("Persistência após reinício", test_persistencia_apos_reiniciar),
    ("Persistência preserva vocabulário", test_persistencia_preserva_cabecalho_e_vocabulario),
    ("Abrir não apaga cristal", test_abrir_nao_apaga_cristal_existente),
    ("inicializar_cristal não destrói", test_inicializar_deprecated_nao_destroi),
    ("Reset exige confirmação", test_reset_destrutivo_exige_confirmacao),
    ("Reset confirmado faz backup", test_reset_destrutivo_faz_backup_antes_de_apagar),
    ("Corrupção vira quarentena + backup", test_cristal_corrompido_vai_para_quarentena_e_recupera_backup),
    ("Falha na troca preserva original", test_falha_no_meio_da_gravacao_preserva_original),
    ("Backup anterior a cada gravação", test_backup_anterior_a_cada_gravacao),
    ("Integridade de cristal válido", test_integridade_de_cristal_valido),
    ("Integridade detecta MAGIC", test_integridade_detecta_magic_invalido),
    ("Integridade detecta string truncada", test_integridade_detecta_string_truncada),
    ("Integridade detecta tipo desconhecido", test_integridade_detecta_tipos_desconhecidos),
    ("Integridade detecta referência órfã", test_integridade_detecta_referencia_orfa),
    ("Append truncado é recuperável", test_gravacao_interrompida_por_escrita_parcial_pode_ser_recuperada),
    ("Deduplicação não cresce arquivo", test_experiencia_repetida_nao_cresce_arquivo),
    ("Deduplicação sobrevive a reinício", test_deduplicacao_sobrevive_a_reinicio),
    ("v2 armazena IDs acima de 255", test_v2_armazena_ids_acima_de_255),
    ("v1 cheio expande sem perda", test_v1_e_preservado_e_pode_ser_expandido_sem_perda),
    ("v1 continua legível", test_v1_legivel_sem_migracao),
    ("Migração copia o legado", test_migracao_copia_legado_para_fonte_autoritativa),
    ("Migração recusa legado corrompido", test_migracao_recusa_legado_corrompido_sem_tocar_destino),
    ("Caminho canônico independe do cwd", test_caminhos_do_projeto_nao_dependem_do_cwd),
    ("Variáveis de ambiente redirecionam", test_variaveis_de_ambiente_redirecionam_todos_os_consumidores),
    ("Importar não chama modelo nem escreve", test_import_dos_consumidores_nao_inicia_modelo_nem_escreve),
    ("Escrita concorrente é recusada", test_gravacao_concorrente_e_recusada_sem_sobrescrever),
    ("Criação não sobrescreve existente", test_criar_cristal_nao_sobrescreve_estado_existente),
    ("Checkpoint resiste a conteúdo inválido", test_checkpoint_nao_e_envenenado_por_conteudo_invalido),
    ("Rotação preserva os mais recentes", test_rotacao_de_backups_preserva_os_mais_recentes),
    ("Schema do cristal JSON validado", test_schema_invalido_do_cristal_json_preserva_arquivo),
    ("Política de aceitação do candidato", test_politica_de_aceitacao_do_candidato),
]


def main():
    print(
        "=== TESTES DE PERSISTÊNCIA DO CRISTAL ==="
    )

    print()

    falhas = []

    for nome, teste in TESTES:
        captura = io.StringIO()

        try:
            with contextlib.redirect_stdout(captura):
                teste()

            saida = captura.getvalue().strip()

            print(
                f"PASSOU: {nome}"
            )

            if saida:
                for linha in saida.splitlines():
                    print(
                        f"    {linha}"
                    )

        except Exception as erro:
            falhas.append(
                (
                    nome,
                    erro,
                )
            )

            print(
                f"FALHOU: {nome} -> {type(erro).__name__}: {erro}"
            )

    print()
    print(
        f"Total: {len(TESTES)} | "
        f"Passaram: {len(TESTES) - len(falhas)} | "
        f"Falharam: {len(falhas)}"
    )

    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
