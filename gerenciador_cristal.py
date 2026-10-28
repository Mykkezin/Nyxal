import json
import os
import shutil
import struct
from datetime import datetime
from pathlib import Path


# ============================================================
# MICROETAPA 41
# GERENCIADOR AUTOMÁTICO DO CRISTAL
# MEMÓRIA IDEMPOTENTE
#
# Novidade desta versão:
#
# Se uma experiência já existir exatamente no cristal,
# ela não será gravada novamente.
#
# Resultado esperado:
#
# experiência repetida
#       ↓
# DUPLICADO
#       ↓
# 0 bytes
#
# ============================================================
# MICROETAPA 41.2
# PERSISTÊNCIA SEGURA
#
# 1. abrir_ou_criar_cristal() é o ponto de entrada ÚNICO.
#    Ela nunca apaga um cristal existente.
# 2. Toda gravação usa arquivo temporário + rename atômico.
#    Uma falha no meio da gravação preserva o arquivo anterior.
# 3. Cada gravação faz backup anterior em memoria/backups/.
# 4. cristal.bin corrompido vai para quarentena, nunca é deletado.
# 5. Versão 2 do formato amplia IDs e comprimentos para
#    2 bytes, mantendo leitura da versão 1.
# ============================================================


# ============================================================
# CAMINHOS
#
# ARQUIVO        = fonte autoritativa do cristal.
# ARQUIVO_LEGADO = formato temporário antigo. Continuamos
#                  lendo e migrando por cópia, nunca por deleção.
#
# Os três caminhos são resolvidos a partir da raiz do projeto, então
# abrir o cristal funciona igual não importa o diretório de trabalho
# do processo. Cada um tem override por variável de ambiente, usado
# por testes e por instalações fora do padrão.
# ============================================================

RAIZ_PROJETO = Path(__file__).resolve().parent

CAMINHO_AUTORITATIVO = "memoria/cristal/cristal.bin"
CAMINHO_LEGADO = "experimentos/cristal_gerenciador.bin"
CAMINHO_BACKUPS = "memoria/backups"


def resolver_caminho(caminho_relativo, variavel_ambiente):
    override = os.environ.get(variavel_ambiente)

    if override:
        return Path(
            override,
        ).expanduser().resolve()

    return (RAIZ_PROJETO / caminho_relativo).resolve()


def caminho_do_projeto(*partes):
    """Caminho absoluto dentro do projeto, independente do cwd."""

    return RAIZ_PROJETO.joinpath(*partes)


ARQUIVO = resolver_caminho(
    CAMINHO_AUTORITATIVO,
    "NYXAL_CRISTAL_ARQUIVO",
)

ARQUIVO_LEGADO = resolver_caminho(
    CAMINHO_LEGADO,
    "NYXAL_CRISTAL_LEGADO",
)

BACKUP_DIR = resolver_caminho(
    CAMINHO_BACKUPS,
    "NYXAL_CRISTAL_BACKUPS",
)

MAX_BACKUPS_PRESERVADOS = 20


# ============================================================
# DICIONÁRIO BASE
# ============================================================

CONCEITOS_BASE = [
    "hipótese",
    "observação",
    "experimento",
    "evidência",
    "resultado",
    "pergunta",
    "investigação",
    "dado",
    "padrão",
    "incerteza",
    "conclusão",
    "teoria",
    "explicação",
    "erro",
    "previsão",
    "nova",
    "correta",
    "incorreta",
    "provisória",
]


RELACOES_BASE = [
    "nasce_de",
    "pode_ser_testada_por",
    "pode_receber",
    "pode_ser_modificada_por",
    "pode_estar",
    "pode_gerar",
    "pode_testar",
    "pode_modificar",
    "continua_sendo",
    "precisa_lidar_com",
    "tem_caracteristica",
    "pode_ser_apoiada_por",
    "pode_ser_contradita_por",
    "pode_orientar",
    "pode_ser_revisada_por",
    "pode_conter",
    "pode_reduzir",
    "pode_explicar",
    "pode_gerar_previsao",
    "pode_conter_erro",
]


# ============================================================
# EXPERIÊNCIAS DE TESTE
# ============================================================

EXPERIENCIAS_TESTE = [
    (
        "observação",
        "pode_gerar",
        "hipótese",
    ),
    (
        "modelo",
        "pode_gerar_previsao",
        "previsão",
    ),
    (
        "evidência",
        "depende_de",
        "observação",
    ),
    (
        "simulação",
        "representa",
        "modelo",
    ),

    # Repetição exata da experiência 1
    (
        "observação",
        "pode_gerar",
        "hipótese",
    ),
]


# ============================================================
# FORMATO
#
# CABEÇALHO (5 bytes, igual nas duas versões)
#
#   NXCM            = MAGIC
#   um byte         = versão
#
# REGISTROS
#
#   01 conceito : tipo + largura do nome + nome
#   02 relação  : tipo + largura do nome + nome
#   03 bloco    : tipo + largura da quantidade
#                 + quantidade × (3 ids)
#
# A largura dos campos inteiros depende da versão:
#
#   versão 1 = 1 byte  (ids 0..255, nomes até 255 bytes)
#   versão 2 = 2 bytes (ids 0..65535, nomes até 65535 bytes)
# ============================================================

MAGIC = b"NXCM"

VERSAO_1 = 1
VERSAO_2 = 2

VERSAO_ATUAL = VERSAO_2

# Mantido por compatibilidade com o código da microetapa 41.
VERSAO = VERSAO_1

FORMATOS_INT = {
    1: "B",
    2: "H",
}

TIPO_CONCEITO = 1
TIPO_RELACAO = 2
TIPO_BLOCO = 3


def limite_de(largura):
    """Maior valor representável em uma largura de bytes."""
    return 256 ** largura - 1


def largura_da_versao(versao):
    if versao == VERSAO_1:
        return 1

    if versao == VERSAO_2:
        return 2

    raise ValueError(
        f"Versão não suportada: {versao}"
    )


# ============================================================
# CODIFICAÇÃO
# ============================================================

def escrever_inteiro(valor, largura):
    return struct.pack(
        FORMATOS_INT[largura],
        valor,
    )


def escrever_ids(
    sujeito_id,
    relacao_id,
    objeto_id,
    largura,
):
    return struct.pack(
        FORMATOS_INT[largura] * 3,
        sujeito_id,
        relacao_id,
        objeto_id,
    )


def codificar_conceito(
    nome,
    largura=1,
):
    dados = nome.encode("utf-8")

    if len(dados) > limite_de(largura):
        raise ValueError(
            f"Conceito excede {limite_de(largura)} bytes."
        )

    return (
        bytes([TIPO_CONCEITO])
        + escrever_inteiro(len(dados), largura)
        + dados
    )


def codificar_relacao(
    nome,
    largura=1,
):
    dados = nome.encode("utf-8")

    if len(dados) > limite_de(largura):
        raise ValueError(
            f"Relação excede {limite_de(largura)} bytes."
        )

    return (
        bytes([TIPO_RELACAO])
        + escrever_inteiro(len(dados), largura)
        + dados
    )


def codificar_bloco(
    sujeito_id,
    relacao_id,
    objeto_id,
    largura=1,
    quantidade=1,
):
    limite = limite_de(largura)

    for nome, valor in (
        ("sujeito", sujeito_id),
        ("relação", relacao_id),
        ("objeto", objeto_id),
    ):
        if not 0 <= valor <= limite:
            raise ValueError(
                f"ID de {nome} fora do limite: {valor}"
            )

    if not 0 <= quantidade <= limite:
        raise ValueError(
            f"Quantidade do bloco fora do limite: {quantidade}"
        )

    return (
        bytes([TIPO_BLOCO])
        + escrever_inteiro(quantidade, largura)
        + escrever_ids(
            sujeito_id,
            relacao_id,
            objeto_id,
            largura,
        )
    )


# ============================================================
# LEITURA DE STRING
# ============================================================

def ler_string(
    dados,
    posicao,
    largura=1,
):
    fim_do_tamanho = posicao + largura

    if fim_do_tamanho > len(dados):
        raise ValueError(
            "Tamanho da string ausente."
        )

    tamanho = int.from_bytes(
        dados[posicao:fim_do_tamanho],
        "little",
    )

    posicao = fim_do_tamanho
    fim = posicao + tamanho

    if fim > len(dados):
        raise ValueError(
            "String incompleta."
        )

    texto = dados[posicao:fim].decode(
        "utf-8"
    )

    return texto, fim


# ============================================================
# LEITURA DO CRISTAL
# ============================================================

def ler_bytes_cristal(dados):
    """Decodifica bytes e devolve também a versão lida."""

    if len(dados) < 5:
        raise ValueError(
            "Cristal pequeno demais."
        )

    if dados[:4] != MAGIC:
        raise ValueError(
            "MAGIC inválido."
        )

    versao = dados[4]
    largura = largura_da_versao(versao)

    posicao = 5

    conceitos = {}
    relacoes = {}
    blocos = []

    while posicao < len(dados):
        tipo = dados[posicao]
        posicao += 1

        # ----------------------------------------------------
        # CONCEITO
        # ----------------------------------------------------

        if tipo == TIPO_CONCEITO:
            nome, posicao = ler_string(
                dados,
                posicao,
                largura,
            )

            if nome in conceitos:
                raise ValueError(
                    f"Conceito duplicado: {nome}"
                )

            conceitos[nome] = len(conceitos)

        # ----------------------------------------------------
        # RELAÇÃO
        # ----------------------------------------------------

        elif tipo == TIPO_RELACAO:
            nome, posicao = ler_string(
                dados,
                posicao,
                largura,
            )

            if nome in relacoes:
                raise ValueError(
                    f"Relação duplicada: {nome}"
                )

            relacoes[nome] = len(relacoes)

        # ----------------------------------------------------
        # BLOCO
        # ----------------------------------------------------

        elif tipo == TIPO_BLOCO:
            fim_do_contador = posicao + largura

            if fim_do_contador > len(dados):
                raise ValueError(
                    "Quantidade do bloco ausente."
                )

            quantidade = int.from_bytes(
                dados[posicao:fim_do_contador],
                "little",
            )

            posicao = fim_do_contador

            tamanho_do_bloco = quantidade * 3 * largura

            if posicao + tamanho_do_bloco > len(dados):
                raise ValueError(
                    "Bloco incompleto."
                )

            bloco = []

            for _ in range(quantidade):
                sujeito_id = int.from_bytes(
                    dados[posicao:posicao + largura],
                    "little",
                )
                relacao_id = int.from_bytes(
                    dados[posicao + largura:posicao + 2 * largura],
                    "little",
                )
                objeto_id = int.from_bytes(
                    dados[posicao + 2 * largura:posicao + 3 * largura],
                    "little",
                )

                posicao += 3 * largura

                # Um bloco só pode referenciar nomes já declarados
                # antes dele no log. Referência adiante ou ID órfão
                # significa arquivo truncado ou corrompido.
                if sujeito_id >= len(conceitos):
                    raise ValueError(
                        f"Bloco referencia conceito inexistente: id {sujeito_id}."
                    )

                if objeto_id >= len(conceitos):
                    raise ValueError(
                        f"Bloco referencia conceito inexistente: id {objeto_id}."
                    )

                if relacao_id >= len(relacoes):
                    raise ValueError(
                        f"Bloco referencia relação inexistente: id {relacao_id}."
                    )

                bloco.append(
                    (
                        sujeito_id,
                        relacao_id,
                        objeto_id,
                    )
                )

            blocos.append(bloco)

        else:
            raise ValueError(
                f"Tipo desconhecido: {tipo}"
            )

    return (
        conceitos,
        relacoes,
        blocos,
        versao,
    )


def caminho_padrao(caminho=None):
    return ARQUIVO if caminho is None else Path(caminho)


def ler_arquivo(caminho=None):
    (
        conceitos,
        relacoes,
        blocos,
        _,
    ) = ler_bytes_cristal(
        caminho_padrao(caminho).read_bytes()
    )

    return (
        conceitos,
        relacoes,
        blocos,
    )


# ============================================================
# SERIALIZAÇÃO COMPLETA
# ============================================================

def serializar_cristal(
    conceitos,
    relacoes,
    blocos,
    versao=VERSAO_ATUAL,
):
    """Reconstrói os bytes inteiros do cristal."""

    largura = largura_da_versao(versao)

    dados = bytearray()
    dados.extend(MAGIC)
    dados.append(versao)

    for nome in conceitos:
        dados.extend(
            codificar_conceito(nome, largura)
        )

    for nome in relacoes:
        dados.extend(
            codificar_relacao(nome, largura)
        )

    for bloco in blocos:
        if len(bloco) > limite_de(largura):
            raise ValueError(
                "Bloco excede a capacidade da versão."
            )

        dados.append(TIPO_BLOCO)
        dados.extend(
            escrever_inteiro(len(bloco), largura)
        )

        for (
            sujeito_id,
            relacao_id,
            objeto_id,
        ) in bloco:
            dados.extend(
                escrever_ids(
                    sujeito_id,
                    relacao_id,
                    objeto_id,
                    largura,
                )
            )

    return bytes(dados)


# ============================================================
# ESCRITA ATÔMICA
#
# Escrevemos em um arquivo temporário do mesmo diretório,
# fsync, e então os.replace(). O renomear é atômico no mesmo
# sistema de arquivos, então o leitor nunca vê um cristal
# pela metade e o conteúdo anterior nunca é perdido.
# ============================================================

def sincronizar_diretorio(diretorio):
    try:
        descritor = os.open(
            str(diretorio),
            os.O_RDONLY,
        )
    except OSError:
        return

    try:
        os.fsync(descritor)
    except OSError:
        pass
    finally:
        os.close(descritor)


def caminho_checkpoint(destino):
    """Slot fixo com o último conteúdo já trocado com sucesso."""

    return BACKUP_DIR / f"{Path(destino).stem}_ultimo_bom.bin"


class CristalAlterado(RuntimeError):
    """O cristal mudou entre a leitura e a tentativa de gravação.

    Recusamos a escrita em vez de sobrescrever a versão mais nova.
    """


def gravar_atomicamente(
    dados,
    caminho=None,
    checkpoint=None,
    esperado_antes=None,
):
    destino = caminho_padrao(caminho)

    # O checkpoint existe para a recuperação do cristal autoritativo.
    # Escrita de JSON derivado não deve popular memoria/backups.
    if checkpoint is None:
        checkpoint = destino == ARQUIVO

    if esperado_antes is not None:
        atuais = destino.read_bytes() if destino.exists() else b""

        if atuais != esperado_antes:
            raise CristalAlterado(
                f"Outro processo alterou {destino} antes desta gravação."
            )

    destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = destino.parent / (
        f".{destino.name}.tmp-{os.getpid()}-{datetime.now().strftime('%H%M%S_%f')}"
    )

    try:
        with open(
            temporario,
            "wb",
        ) as arquivo:
            arquivo.write(dados)
            arquivo.flush()
            os.fsync(arquivo.fileno())

        os.replace(temporario, destino)
        sincronizar_diretorio(destino.parent)

    finally:
        if temporario.exists():
            temporario.unlink()

    if checkpoint:
        # O checkpoint representa o último estado REALMENTE bom, então só
        # é atualizado quando o conteúdo recém-trocado passa na validação
        # estrutural. Um byte escrito por engano não apaga a referência boa.
        try:
            validar_bytes_cristal(
                dados,
                destino,
            )
        except Exception as erro:
            print(
                f"[CRISTAL] Checkpoint preservado: {destino} "
                f"não virou estado bom ({erro})."
            )
        else:
            destino_checkpoint = caminho_checkpoint(destino)

            destino_checkpoint.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                destino,
                destino_checkpoint,
            )

    return destino


# ============================================================
# BACKUP E QUARENTENA
# ============================================================

def timestamp_atual():
    return datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )


def listar_backups(caminho=None):
    destino = caminho_padrao(caminho)

    if not BACKUP_DIR.exists():
        return []

    prefixo = f"{destino.stem}_backup_"

    return sorted(
        (
            arquivo
            for arquivo in BACKUP_DIR.glob(f"{prefixo}*.bin")
            if arquivo.is_file()
        ),
        key=lambda arquivo: arquivo.name,
    )


def podar_backups(caminho=None):
    """Mantém apenas os backups mais recentes."""

    backups = listar_backups(caminho)

    excedentes = backups[:-MAX_BACKUPS_PRESERVADOS]

    for arquivo in excedentes:
        arquivo.unlink()

    return len(backups) - len(excedentes)


def backup_cristal(caminho=None):
    """Cópia de segurança do cristal atual, antes de gravar."""

    destino = caminho_padrao(caminho)

    if not destino.exists():
        return None

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_backup = BACKUP_DIR / (
        f"{destino.stem}_backup_{timestamp_atual()}.bin"
    )

    shutil.copy2(
        destino,
        caminho_backup,
    )

    podar_backups(destino)

    return caminho_backup


def quarentenar_cristal(caminho=None, motivo="corrompido"):
    """Move um arquivo ilegível para o lado, sem deletá-lo."""

    destino = caminho_padrao(caminho)

    if not destino.exists():
        return None

    destino_quarentena = destino.with_name(
        f"{destino.name}.{motivo}-{timestamp_atual()}"
    )

    shutil.move(
        str(destino),
        str(destino_quarentena),
    )

    return destino_quarentena


def candidatos_de_recuperacao(caminho=None):
    """Fontes de restauração, da mais nova para a mais antiga."""

    destino = caminho_padrao(caminho)

    candidatos = []

    checkpoint = caminho_checkpoint(destino)

    if checkpoint.exists():
        candidatos.append(
            checkpoint
        )

    candidatos.extend(
        reversed(
            listar_backups(destino)
        )
    )

    return candidatos


def recuperar_ultimo_backup(caminho=None):
    """Restaura o último estado íntegro e devolve o cristal lido.

    Começa pelo checkpoint do último estado confirmado e desce
    pela história de backups até encontrar bytes válidos.
    """

    destino = caminho_padrao(caminho)

    candidatos = candidatos_de_recuperacao(destino)

    if not candidatos:
        raise FileNotFoundError(
            f"Nenhum backup disponível para {destino}."
        )

    for candidato in candidatos:
        dados = candidato.read_bytes()

        try:
            validar_bytes_cristal(
                dados,
                candidato,
            )
        except Exception as erro:
            print(
                f"[CRISTAL] Backup inválido ignorado ({candidato}): {erro}"
            )

            continue

        gravar_atomicamente(
            dados,
            destino,
        )

        print(
            f"[CRISTAL] Cristal restaurado de {candidato}"
        )

        return ler_arquivo_validado(destino)

    raise FileNotFoundError(
        f"Nenhum backup íntegro disponível para {destino}."
    )


# ============================================================
# VALIDAÇÃO DE INTEGRIDADE
# ============================================================

def validar_bytes_cristal(dados, origem="<memória>"):
    """Checa as amarras estruturais de bytes do formato."""

    (
        conceitos,
        relacoes,
        blocos,
        versao,
    ) = ler_bytes_cristal(dados)

    # O round-trip semântico é a amarra do formato: reescrever o
    # cristal lido e reler precisa devolver exatamente os mesmos
    # conceitos, relações e blocos. Divergência indica bytes
    # truncados, fora de ordem ou de largura incompatível.
    (
        conceitos_reescritos,
        relacoes_reescritas,
        blocos_reescritos,
        versao_reescrita,
    ) = ler_bytes_cristal(
        serializar_cristal(
            conceitos,
            relacoes,
            blocos,
            versao,
        )
    )

    if (
        conceitos_reescritos != conceitos
        or relacoes_reescritas != relacoes
        or blocos_reescritos != blocos
        or versao_reescrita != versao
    ):
        raise ValueError(
            f"Integridade do cristal violada em {origem}: round-trip "
            "binário divergente."
        )

    conhecimento = reconstruir_conhecimento(
        conceitos,
        relacoes,
        blocos,
    )

    return {
        "arquivo": str(origem),
        "tamanho": len(dados),
        "versao": versao,
        "largura": largura_da_versao(versao),
        "conceitos": len(conceitos),
        "relacoes": len(relacoes),
        "blocos": len(blocos),
        "triplas": len(conhecimento),
        "ok": True,
    }


def validar_integridade(caminho=None):
    """Relê o arquivo e valida a integridade estrutural do cristal.

    Verifica MAGIC, versão conhecida, strings completas, ausência
    de nomes duplicados, referência apenas a IDs já declarados e
    round-trip binário do conhecimento.
    """

    destino = caminho_padrao(caminho)

    return validar_bytes_cristal(
        destino.read_bytes(),
        destino,
    )


def ler_arquivo_validado(caminho=None):
    """Lê e só devolve o cristal se a integridade passar."""

    destino = caminho_padrao(caminho)

    validar_integridade(destino)

    return ler_arquivo(destino)


# ============================================================
# PERSISTÊNCIA JSON DESENCAIXADA
#
# cristalizacao.py e ciclo_cristalizacao.py guardam seus cristais
# semânticos em JSON. Eles passam a usar esta gravação atômica para
# desacoplar a persistência sem mudar o formato do arquivo.
# ============================================================

def salvar_json_atomicamente(
    dados,
    caminho,
):
    destino = Path(caminho)

    texto = json.dumps(
        dados,
        ensure_ascii=False,
        indent=2,
    )

    gravar_atomicamente(
        texto.encode("utf-8"),
        destino,
        checkpoint=False,
    )

    return destino


def carregar_json_com_seguranca(
    caminho,
    padrao,
):
    """Carrega o JSON, devolvendo o padrão apenas se não houver arquivo.

    Se o arquivo existir e estiver ilegível, preservamos em quarentena
    e devolvemos o padrão, em vez de sobrescrever cegamente.
    """

    destino = Path(caminho)

    if not destino.exists():
        return padrao

    try:
        return json.loads(
            destino.read_bytes().decode("utf-8")
        )
    except Exception as erro:
        print(
            f"[CRISTAL] JSON ilegível em {destino}: {erro}"
        )

        quarentenar_cristal(
            destino,
            motivo="corrompido",
        )

        return padrao


# ============================================================
# CRIAÇÃO
# ============================================================

def criar_cristal_novo(caminho=None, versao=VERSAO_ATUAL):
    """Cria o cabeçalho com o vocabulário base, sem apagar nada."""

    destino = caminho_padrao(caminho)

    dados = serializar_cristal(
        {
            nome: indice
            for indice, nome in enumerate(CONCEITOS_BASE)
        },
        {
            nome: indice
            for indice, nome in enumerate(RELACOES_BASE)
        },
        [],
        versao,
    )

    # Validamos antes de gravar: um conteúdo inválido nunca chega a
    # substituir um estado válido.
    validar_bytes_cristal(dados, destino)

    # Só criamos onde ainda não existe nada a preservar.
    gravar_atomicamente(
        dados,
        destino,
        esperado_antes=b"",
    )

    return ler_arquivo(destino)


def migrar_do_legado(caminho=None):
    """Copia o cristal legado para a fonte autoritativa.

    O legado fica intacto: a migração é por cópia.
    """

    destino = caminho_padrao(caminho)

    if destino == ARQUIVO_LEGADO or not ARQUIVO_LEGADO.exists():
        return None

    ARQUIVO_LEGADO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dados = ARQUIVO_LEGADO.read_bytes()

    # Rejeita legado ilegível sem tocar no destino.
    validar_bytes_cristal(dados, ARQUIVO_LEGADO)

    gravar_atomicamente(
        dados,
        destino,
        esperado_antes=b"",
    )

    print(
        f"[CRISTAL] Migrado de {ARQUIVO_LEGADO} para {destino} "
        "(legado preservado)."
    )

    return destino


# ============================================================
# PONTO DE ENTRADA ÚNICO
# ============================================================

def abrir_ou_criar_cristal(caminho=None):
    """Ponto de entrada ÚNICO e não destrutivo do cristal.

    Abre o cristal existente; migra do legado se preciso;
    cria um novo apenas quando não há nada a preservar.
    Arquivo ilegível vai para quarentena e o último backup
    é restaurado.
    """

    destino = caminho_padrao(caminho)

    if not destino.exists():
        try:
            migrado = migrar_do_legado(destino)
        except Exception as erro:
            print(
                f"[CRISTAL] Legado {ARQUIVO_LEGADO} ilegível e foi "
                f"preservado sem migração: {erro}"
            )

            migrado = None

        if migrado is None:
            print(
                f"[CRISTAL] Nenhum cristal em {destino}. "
                "Criando cristal novo."
            )

            return criar_cristal_novo(destino)

    try:
        return ler_arquivo_validado(destino)
    except Exception as erro:
        print(
            f"[CRISTAL] Falha ao carregar {destino}: {erro}"
        )

        quarentenado = quarentenar_cristal(
            destino,
            motivo="corrompido",
        )

        if quarentenado is not None:
            print(
                f"[CRISTAL] Arquivo preservado em quarentena: {quarentenado}"
            )

        try:
            return recuperar_ultimo_backup(destino)
        except Exception as erro_backup:
            print(
                f"[CRISTAL] Recuperação por backup falhou: {erro_backup}. "
                "Criando cristal novo."
            )

            return criar_cristal_novo(destino)


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def inicializar_cristal():
    """DEPRECATED: abre sem destruir. Use abrir_ou_criar_cristal()."""

    print(
        "[AVISO] inicializar_cristal() é DEPRECATED e não apaga "
        f"mais o cristal. Use abrir_ou_criar_cristal(). Redirecionando."
    )

    return abrir_ou_criar_cristal()


def reset_destrutivo_cristal(
    confirmacao_explicita=False,
    fazer_backup=True,
    caminho=None,
    versao=VERSAO_ATUAL,
):
    """APENAS para testes. Exige confirmação explícita."""

    if not confirmacao_explicita:
        raise PermissionError(
            "Reset destrutivo exige confirmacao_explicita=True"
        )

    destino = caminho_padrao(caminho)

    if fazer_backup:
        caminho_backup = backup_cristal(destino)

        if caminho_backup is not None:
            print(
                f"[CRISTAL] Backup salvo em {caminho_backup}"
            )

    if destino.exists():
        destino.unlink()

    return criar_cristal_novo(
        destino,
        versao,
    )


# ============================================================
# EXPANSÃO DO FORMATO
# ============================================================

def expandir_cristal(caminho=None, nova_versao=VERSAO_ATUAL):
    """Reescreve o cristal em uma versão com campos maiores.

    A reescrita é validada antes de sair do papel, precedida de
    backup e recusada se outro processo tiver alterado o arquivo,
    então um cristal v1 cheio pode crescer sem perder nada.
    """

    destino = caminho_padrao(caminho)

    dados_antes = destino.read_bytes()

    (
        conceitos,
        relacoes,
        blocos,
        versao,
    ) = ler_bytes_cristal(dados_antes)

    if nova_versao < versao:
        raise ValueError(
            f"Não é possível rebaixar a versão {versao} para {nova_versao}."
        )

    dados = serializar_cristal(
        conceitos,
        relacoes,
        blocos,
        nova_versao,
    )

    tamanho_anterior = len(dados_antes)

    # Nada é gravado se a reescrita não reproduzir o mesmo
    # conhecimento lido.
    validar_bytes_cristal(dados, destino)

    backup_cristal(destino)

    gravar_atomicamente(
        dados,
        destino,
        esperado_antes=dados_antes,
    )

    validar_integridade(destino)

    return {
        "versao_anterior": versao,
        "versao_atual": nova_versao,
        "tamanho_anterior": tamanho_anterior,
        "tamanho_atual": destino.stat().st_size,
        "conceitos": len(conceitos),
        "relacoes": len(relacoes),
        "blocos": len(blocos),
    }


# ============================================================
# REGISTRAR EXPERIÊNCIA
# ============================================================

def registrar_experiencia(
    sujeito,
    relacao,
    objeto,
    caminho=None,
    backup_antes_de_gravar=True,
):
    destino = caminho_padrao(caminho)

    abrir_ou_criar_cristal(destino)

    dados_antes = destino.read_bytes()

    (
        conceitos,
        relacoes,
        blocos,
        versao,
    ) = ler_bytes_cristal(dados_antes)

    largura = largura_da_versao(versao)
    limite = limite_de(largura)

    experiencia = (
        sujeito,
        relacao,
        objeto,
    )

    # --------------------------------------------------------
    # CONHECIMENTO EXISTENTE
    # --------------------------------------------------------

    conhecimento_existente = (
        reconstruir_conhecimento(
            conceitos,
            relacoes,
            blocos,
        )
    )

    tamanho_antes = (
        destino.stat().st_size
    )

    # --------------------------------------------------------
    # DETECÇÃO DE DUPLICAÇÃO
    # --------------------------------------------------------

    if experiencia in conhecimento_existente:
        return {
            "classificacao": "DUPLICADO",
            "novos_conceitos": [],
            "relacao_nova": False,
            "ids_novos_conceitos": {},
            "id_nova_relacao": None,
            "tamanho_antes": tamanho_antes,
            "tamanho_depois": tamanho_antes,
            "crescimento": 0,
            "total_conhecimento": len(
                conhecimento_existente
            ),
            "passou": True,
        }

    # --------------------------------------------------------
    # DETECTAR CONCEITOS NOVOS
    # --------------------------------------------------------

    novos_conceitos = []

    if sujeito not in conceitos:
        novos_conceitos.append(
            sujeito
        )

    if (
        objeto not in conceitos
        and objeto not in novos_conceitos
    ):
        novos_conceitos.append(
            objeto
        )

    relacao_nova = (
        relacao not in relacoes
    )

    quantidade_novos_conceitos = (
        len(novos_conceitos)
    )

    # --------------------------------------------------------
    # CLASSIFICAÇÃO
    # --------------------------------------------------------

    if (
        quantidade_novos_conceitos == 0
        and not relacao_nova
    ):
        classificacao = "REUTILIZAÇÃO"

    elif (
        quantidade_novos_conceitos > 0
        and not relacao_nova
    ):
        classificacao = "CONCEITO NOVO"

    elif (
        quantidade_novos_conceitos == 0
        and relacao_nova
    ):
        classificacao = "RELAÇÃO NOVA"

    else:
        classificacao = (
            "CONCEITO + RELAÇÃO NOVOS"
        )

    # --------------------------------------------------------
    # ADICIONAR CONCEITOS
    # --------------------------------------------------------

    novos_ids_conceitos = {}

    for nome in novos_conceitos:
        novo_id = len(conceitos)

        if novo_id > limite:
            raise ValueError(
                "Limite de conceitos atingido. "
                "Use expandir_cristal() para ampliar o formato."
            )

        conceitos[nome] = novo_id

        novos_ids_conceitos[nome] = (
            novo_id
        )

    # --------------------------------------------------------
    # ADICIONAR RELAÇÃO
    # --------------------------------------------------------

    novo_id_relacao = None

    if relacao_nova:
        novo_id_relacao = len(relacoes)

        if novo_id_relacao > limite:
            raise ValueError(
                "Limite de relações atingido. "
                "Use expandir_cristal() para ampliar o formato."
            )

        relacoes[relacao] = (
            novo_id_relacao
        )

    # --------------------------------------------------------
    # REGISTROS
    # --------------------------------------------------------

    registros = []

    for nome in novos_conceitos:
        registros.append(
            codificar_conceito(nome, largura)
        )

    if relacao_nova:
        registros.append(
            codificar_relacao(relacao, largura)
        )

    registros.append(
        codificar_bloco(
            conceitos[sujeito],
            relacoes[relacao],
            conceitos[objeto],
            largura,
        )
    )

    # --------------------------------------------------------
    # GRAVAÇÃO ATÔMICA
    #
    # A base inteira é preservada e os registros novos são
    # acrescentados ao final. Nada é escrito direto no arquivo
    # definitivo, então uma falha no meio não corrompe o cristal.
    # --------------------------------------------------------

    dados_depois = dados_antes + b"".join(registros)

    validar_bytes_cristal(dados_depois, destino)

    if backup_antes_de_gravar:
        backup_cristal(destino)

    gravar_atomicamente(
        dados_depois,
        destino,
        esperado_antes=dados_antes,
    )

    tamanho_depois = (
        destino.stat().st_size
    )

    crescimento = (
        tamanho_depois
        - tamanho_antes
    )

    # --------------------------------------------------------
    # VERIFICAÇÃO
    # --------------------------------------------------------

    (
        conceitos_depois,
        relacoes_depois,
        blocos_depois,
    ) = ler_arquivo(destino)

    conhecimento_depois = (
        reconstruir_conhecimento(
            conceitos_depois,
            relacoes_depois,
            blocos_depois,
        )
    )

    passou = (
        conhecimento_depois[-1]
        == experiencia
    )

    return {
        "classificacao": classificacao,
        "novos_conceitos": novos_conceitos,
        "relacao_nova": relacao_nova,
        "ids_novos_conceitos": (
            novos_ids_conceitos
        ),
        "id_nova_relacao": (
            novo_id_relacao
        ),
        "tamanho_antes": tamanho_antes,
        "tamanho_depois": tamanho_depois,
        "crescimento": crescimento,
        "total_conhecimento": len(
            conhecimento_depois
        ),
        "passou": passou,
    }


# ============================================================
# IDS ANTIGOS
# ============================================================

def verificar_ids_originais(
    conceitos_originais,
    relacoes_originais,
    caminho=None,
):
    (
        conceitos,
        relacoes,
        _,
    ) = ler_arquivo(caminho)

    for nome, indice in conceitos_originais.items():
        if nome not in conceitos:
            return False

        if conceitos[nome] != indice:
            return False

    for nome, indice in relacoes_originais.items():
        if nome not in relacoes:
            return False

        if relacoes[nome] != indice:
            return False

    return True


# ============================================================
# RECONSTRUÇÃO
# ============================================================

def reconstruir_conhecimento(
    conceitos,
    relacoes,
    blocos,
):
    conceitos_invertidos = {
        indice: nome
        for nome, indice in conceitos.items()
    }

    relacoes_invertidas = {
        indice: nome
        for nome, indice in relacoes.items()
    }

    conhecimento = []

    for bloco in blocos:
        for (
            sujeito_id,
            relacao_id,
            objeto_id,
        ) in bloco:
            conhecimento.append(
                (
                    conceitos_invertidos[
                        sujeito_id
                    ],
                    relacoes_invertidas[
                        relacao_id
                    ],
                    conceitos_invertidos[
                        objeto_id
                    ],
                )
            )

    return conhecimento


# ============================================================
# PRINCIPAL
#
# A demonstração da microetapa 41 precisa partir de um cristal
# vazio. Ela usa um arquivo próprio de demonstração e um reset
# destrutivo explícito, para nunca apagar o cristal real.
# ============================================================

ARQUIVO_DEMO = caminho_do_projeto(
    "experimentos",
    "cristal_gerenciador_demo.bin",
)


def main(caminho=ARQUIVO_DEMO):
    destino = Path(caminho)

    print(
        "=== MICROETAPA 41 ==="
    )

    print(
        "MEMÓRIA IDEMPOTENTE"
    )

    print()

    # --------------------------------------------------------
    # INICIALIZAÇÃO
    # --------------------------------------------------------

    reset_destrutivo_cristal(
        confirmacao_explicita=True,
        caminho=destino,
    )

    (
        conceitos,
        relacoes,
        blocos,
    ) = ler_arquivo(destino)

    conceitos_originais = dict(
        conceitos
    )

    relacoes_originais = dict(
        relacoes
    )

    print(
        f"Arquivo de demonstração: {destino}"
    )

    print(
        "=== ESTADO INICIAL ==="
    )

    print(
        f"Conceitos: "
        f"{len(conceitos)}"
    )

    print(
        f"Relações: "
        f"{len(relacoes)}"
    )

    print(
        f"Blocos: "
        f"{len(blocos)}"
    )

    print(
        f"Tamanho: "
        f"{destino.stat().st_size} bytes"
    )

    print()

    # --------------------------------------------------------
    # PROCESSAMENTO
    # --------------------------------------------------------

    for numero, experiencia in enumerate(
        EXPERIENCIAS_TESTE,
        start=1,
    ):
        sujeito, relacao, objeto = (
            experiencia
        )

        print(
            f"=== EXPERIÊNCIA {numero} ==="
        )

        print(
            f"{sujeito} "
            f"--{relacao}--> "
            f"{objeto}"
        )

        resultado = (
            registrar_experiencia(
                sujeito,
                relacao,
                objeto,
                caminho=destino,
                backup_antes_de_gravar=False,
            )
        )

        print(
            f"Classificação: "
            f"{resultado['classificacao']}"
        )

        if resultado[
            "novos_conceitos"
        ]:
            print(
                "Novos conceitos: "
                + ", ".join(
                    resultado[
                        "novos_conceitos"
                    ]
                )
            )
        else:
            print(
                "Novos conceitos: nenhum"
            )

        print(
            "Relação nova: "
            + (
                "sim"
                if resultado["relacao_nova"]
                else "não"
            )
        )

        print(
            f"Crescimento: "
            f"{resultado['crescimento']} bytes"
        )

        print(
            f"Total de conhecimento: "
            f"{resultado['total_conhecimento']}"
        )

        print(
            "Integridade: "
            + (
                "PASSOU"
                if resultado["passou"]
                else "FALHOU"
            )
        )

        print()

    # --------------------------------------------------------
    # IDS
    # --------------------------------------------------------

    ids_ok = verificar_ids_originais(
        conceitos_originais,
        relacoes_originais,
        destino,
    )

    print(
        "=== IDS ANTIGOS ==="
    )

    if ids_ok:
        print(
            "PASSOU: todos os IDs antigos "
            "permaneceram intactos."
        )
    else:
        print(
            "FALHOU: algum ID antigo mudou."
        )

    print()

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    (
        conceitos_finais,
        relacoes_finais,
        blocos_finais,
    ) = ler_arquivo(destino)

    conhecimento_final = (
        reconstruir_conhecimento(
            conceitos_finais,
            relacoes_finais,
            blocos_finais,
        )
    )

    esperado = [
        EXPERIENCIAS_TESTE[0],
        EXPERIENCIAS_TESTE[1],
        EXPERIENCIAS_TESTE[2],
        EXPERIENCIAS_TESTE[3],
    ]

    print(
        "=== VERIFICAÇÃO FINAL ==="
    )

    if conhecimento_final == esperado:
        print(
            "PASSOU: a experiência duplicada "
            "não foi armazenada novamente."
        )
    else:
        print(
            "FALHOU: o conhecimento final "
            "possui divergência."
        )

    print()

    print(
        "=== ESTADO FINAL ==="
    )

    print(
        f"Conceitos: "
        f"{len(conceitos_finais)}"
    )

    print(
        f"Relações: "
        f"{len(relacoes_finais)}"
    )

    print(
        f"Blocos: "
        f"{len(blocos_finais)}"
    )

    print(
        f"Triplas: "
        f"{len(conhecimento_final)}"
    )

    print(
        f"Tamanho: "
        f"{destino.stat().st_size} bytes"
    )

    print()

    print(
        "=== INTEGRIDADE ==="
    )

    print(
        json.dumps(
            validar_integridade(destino),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main(ARQUIVO_DEMO)
