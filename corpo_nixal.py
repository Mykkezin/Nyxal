import glob
import json
import os
import re
import shutil
import time
from datetime import datetime


# ============================================================
# MICROETAPA 52.3
# CORPO DA NIXAL — MEMÓRIA CORPORAL
#
# Objetivos:
#
# 1. perceber o estado atual
# 2. manter separada a memória entre sessões
# 3. comparar somente estados da sessão atual
# 4. detectar mudanças significativas
# 5. registrar eventos corporais
#
# Nesta etapa:
#
# - somente leitura
# - nenhum hardware é controlado
# - nenhum RGB é alterado
# - nenhuma ventoinha é alterada
# - nenhum dispositivo externo é comandado
# - nenhuma decisão autônoma é tomada
# ============================================================


NOME = "Nixal"

INTERVALO_CICLO = 2.0

ARQUIVO_ESTADO_CORPO = (
    "estado_corpo_nixal.json"
)

ARQUIVO_MEMORIA_CORPORAL = (
    "memoria_corporal_nixal.json"
)

MAX_EVENTOS = 100


# ============================================================
# LIMIARES DE MUDANÇA SIGNIFICATIVA
# ============================================================

LIMITE_CPU = 10.0

LIMITE_RAM = 5.0

LIMITE_GPU = 15

LIMITE_TEMPERATURA = 3.0


# ============================================================
# TEMPO
# ============================================================

def agora_iso():
    return (
        datetime.now()
        .astimezone()
        .isoformat()
    )


# ============================================================
# LEITURA SEGURA
# ============================================================

def ler_texto(caminho):
    try:

        with open(
            caminho,
            "r",
            encoding="utf-8",
        ) as arquivo:

            return arquivo.read().strip()

    except (
        OSError,
        UnicodeDecodeError,
    ):

        return None


def ler_inteiro(caminho):

    valor = ler_texto(
        caminho
    )

    if valor is None:
        return None

    try:

        return int(
            valor
        )

    except ValueError:

        return None


# ============================================================
# CPU
# ============================================================

def ler_cpu():

    linhas = ler_texto(
        "/proc/stat"
    )

    if not linhas:
        return None

    for linha in linhas.splitlines():

        if not linha.startswith(
            "cpu "
        ):
            continue

        partes = linha.split()

        try:

            valores = [
                int(valor)
                for valor in partes[1:8]
            ]

        except ValueError:

            return None

        if len(valores) < 7:
            return None

        return valores

    return None


def calcular_uso_cpu(
    anterior,
    atual,
):

    if (
        anterior is None
        or atual is None
    ):
        return None

    total_anterior = sum(
        anterior
    )

    total_atual = sum(
        atual
    )

    idle_anterior = (
        anterior[3]
        + anterior[4]
    )

    idle_atual = (
        atual[3]
        + atual[4]
    )

    total_delta = (
        total_atual
        - total_anterior
    )

    idle_delta = (
        idle_atual
        - idle_anterior
    )

    if total_delta <= 0:
        return None

    uso = (
        1
        - (
            idle_delta
            / total_delta
        )
    ) * 100

    uso = max(
        0.0,
        min(
            100.0,
            uso,
        )
    )

    return round(
        uso,
        2,
    )


def classificar_cpu(
    uso,
):

    if uso is None:
        return "indisponivel"

    if uso < 20:
        return "baixa_carga"

    if uso < 60:
        return "carga_moderada"

    if uso < 85:
        return "carga_alta"

    return "carga_muito_alta"


# ============================================================
# MEMÓRIA
# ============================================================

def ler_memoria():

    texto = ler_texto(
        "/proc/meminfo"
    )

    if not texto:
        return None

    valores = {}

    for linha in texto.splitlines():

        partes = linha.split()

        if len(partes) < 2:
            continue

        chave = partes[0].rstrip(
            ":"
        )

        try:

            valor_kb = int(
                partes[1]
            )

        except ValueError:

            continue

        valores[
            chave
        ] = valor_kb

    total = valores.get(
        "MemTotal"
    )

    disponivel = valores.get(
        "MemAvailable"
    )

    if (
        total is None
        or disponivel is None
    ):
        return None

    usado = (
        total
        - disponivel
    )

    percentual = (
        usado
        / total
    ) * 100

    return {
        "total_gb": round(
            total
            / 1024
            / 1024,
            2,
        ),

        "disponivel_gb": round(
            disponivel
            / 1024
            / 1024,
            2,
        ),

        "usado_gb": round(
            usado
            / 1024
            / 1024,
            2,
        ),

        "uso_percentual": round(
            percentual,
            2,
        ),

        "estado": (
            classificar_memoria(
                percentual
            )
        ),
    }


def classificar_memoria(
    uso,
):

    if uso < 50:
        return "normal"

    if uso < 75:
        return "uso_moderado"

    if uso < 90:
        return "uso_alto"

    return "uso_muito_alto"


# ============================================================
# GPU — UEVENT
# ============================================================

def ler_uevent(
    caminho,
):

    texto = ler_texto(
        caminho
    )

    if not texto:
        return {}

    resultado = {}

    for linha in texto.splitlines():

        if "=" not in linha:
            continue

        chave, valor = (
            linha.split(
                "=",
                1,
            )
        )

        resultado[
            chave
        ] = valor

    return resultado


# ============================================================
# GPU — TEMPERATURAS
# ============================================================

def ler_temperaturas_gpu(
    device,
):

    temperaturas = []

    hwmon_base = os.path.join(
        device,
        "hwmon",
    )

    caminhos_hwmon = sorted(
        glob.glob(
            os.path.join(
                hwmon_base,
                "hwmon*",
            )
        )
    )

    for hwmon in caminhos_hwmon:

        nome_chip = ler_texto(
            os.path.join(
                hwmon,
                "name",
            )
        )

        sensores = sorted(
            glob.glob(
                os.path.join(
                    hwmon,
                    "temp*_input",
                )
            )
        )

        for entrada in sensores:

            valor = ler_inteiro(
                entrada
            )

            if valor is None:
                continue

            nome_sensor = os.path.basename(
                entrada
            )

            numero = nome_sensor[
                4:-6
            ]

            rotulo = ler_texto(
                os.path.join(
                    hwmon,
                    f"temp{numero}_label",
                )
            )

            temperatura = round(
                valor / 1000,
                2,
            )

            temperaturas.append(
                {
                    "sensor": nome_sensor,
                    "rotulo": rotulo,
                    "chip": nome_chip,
                    "temperatura_c": temperatura,
                    "estado": (
                        classificar_temperatura(
                            temperatura
                        )
                    ),
                }
            )

    return temperaturas


# ============================================================
# TEMPERATURA
# ============================================================

def classificar_temperatura(
    temperatura,
):

    if temperatura < 40:
        return "fria"

    if temperatura < 65:
        return "normal"

    if temperatura < 80:
        return "quente"

    return "muito_quente"


# ============================================================
# GPU
# ============================================================

def listar_gpus_reais():

    gpus = []

    caminhos = sorted(
        glob.glob(
            "/sys/class/drm/card[0-9]*"
        )
    )

    padrao = re.compile(
        r"^card[0-9]+$"
    )

    for caminho in caminhos:

        nome = os.path.basename(
            caminho
        )

        if not padrao.match(nome):
            continue

        device = os.path.join(
            caminho,
            "device",
        )

        vendor = ler_texto(
            os.path.join(
                device,
                "vendor",
            )
        )

        if vendor is None:
            continue

        eventos = ler_uevent(
            os.path.join(
                device,
                "uevent",
            )
        )

        uso = ler_inteiro(
            os.path.join(
                device,
                "gpu_busy_percent",
            )
        )

        temperaturas = (
            ler_temperaturas_gpu(
                device
            )
        )

        gpus.append(
            {
                "dispositivo": nome,

                "identidade": {
                    "vendor": vendor,

                    "driver": eventos.get(
                        "DRIVER"
                    ),

                    "pci_id": eventos.get(
                        "PCI_ID"
                    ),

                    "pci_subsys_id": (
                        eventos.get(
                            "PCI_SUBSYS_ID"
                        )
                    ),

                    "pci_slot": (
                        eventos.get(
                            "PCI_SLOT_NAME"
                        )
                    ),
                },

                "uso_percentual": uso,

                "estado_uso": (
                    classificar_gpu(
                        uso
                    )
                ),

                "temperaturas": (
                    temperaturas
                ),
            }
        )

    return gpus


def classificar_gpu(
    uso,
):

    if uso is None:
        return "indisponivel"

    if uso < 20:
        return "baixa_carga"

    if uso < 60:
        return "carga_moderada"

    if uso < 85:
        return "carga_alta"

    return "carga_muito_alta"


# ============================================================
# TEMPERATURAS GERAIS
# ============================================================

def ler_temperaturas():

    resultados = []

    caminhos = sorted(
        glob.glob(
            "/sys/class/thermal/"
            "thermal_zone[0-9]*"
        )
    )

    for caminho in caminhos:

        tipo = ler_texto(
            os.path.join(
                caminho,
                "type",
            )
        )

        valor = ler_inteiro(
            os.path.join(
                caminho,
                "temp",
            )
        )

        if (
            tipo is None
            or valor is None
        ):
            continue

        temperatura = round(
            valor / 1000,
            2,
        )

        resultados.append(
            {
                "zona": os.path.basename(
                    caminho.rstrip("/")
                ),

                "tipo": tipo,

                "temperatura_c": (
                    temperatura
                ),

                "estado": (
                    classificar_temperatura(
                        temperatura
                    )
                ),
            }
        )

    return resultados


# ============================================================
# ARMAZENAMENTO
# ============================================================

def ler_armazenamento():

    uso = shutil.disk_usage(
        "/"
    )

    total = uso.total

    usado = uso.used

    livre = uso.free

    percentual = (
        usado
        / total
    ) * 100

    return {
        "ponto": "/",

        "total_gb": round(
            total
            / 1024
            / 1024
            / 1024,
            2,
        ),

        "usado_gb": round(
            usado
            / 1024
            / 1024
            / 1024,
            2,
        ),

        "livre_gb": round(
            livre
            / 1024
            / 1024
            / 1024,
            2,
        ),

        "uso_percentual": round(
            percentual,
            2,
        ),

        "estado": (
            classificar_armazenamento(
                percentual
            )
        ),
    }


def classificar_armazenamento(
    uso,
):

    if uso < 70:
        return "normal"

    if uso < 85:
        return "ocupado"

    if uso < 95:
        return "muito_ocupado"

    return "critico"


# ============================================================
# PROCESSOS
# ============================================================

def contar_processos():

    processos = glob.glob(
        "/proc/[0-9]*"
    )

    total = 0

    for caminho in processos:

        nome = os.path.basename(
            caminho
        )

        if nome.isdigit():
            total += 1

    return total


# ============================================================
# UPTIME
# ============================================================

def ler_uptime():

    texto = ler_texto(
        "/proc/uptime"
    )

    if not texto:
        return None

    try:

        return round(
            float(
                texto.split()[0]
            ),
            2,
        )

    except (
        ValueError,
        IndexError,
    ):

        return None


# ============================================================
# PERCEPÇÃO CORPORAL
# ============================================================

def perceber_corpo(
    cpu_anterior=None,
):

    cpu_atual = ler_cpu()

    uso_cpu = (
        calcular_uso_cpu(
            cpu_anterior,
            cpu_atual,
        )
        if cpu_anterior is not None
        else None
    )

    estado = {
        "identidade": {
            "nome": NOME,
        },

        "corpo": {
            "cpu": {
                "uso_percentual": uso_cpu,

                "estado": (
                    classificar_cpu(
                        uso_cpu
                    )
                ),

                "calibrada": (
                    uso_cpu is not None
                ),
            },

            "memoria": ler_memoria(),

            "temperaturas_gerais": (
                ler_temperaturas()
            ),

            "gpu": (
                listar_gpus_reais()
            ),

            "armazenamento": (
                ler_armazenamento()
            ),

            "processos": (
                contar_processos()
            ),

            "uptime_segundos": (
                ler_uptime()
            ),
        },

        "percepcao": {
            "timestamp": agora_iso(),
        },
    }

    return (
        estado,
        cpu_atual,
    )


# ============================================================
# COMPARAÇÃO DE ESTADOS
# ============================================================

def comparar_valor(
    caminho,
    anterior,
    atual,
    mudancas,
):

    if anterior == atual:
        return

    mudancas.append(
        {
            "caminho": caminho,
            "anterior": anterior,
            "atual": atual,
        }
    )


def comparar_estados(
    anterior,
    atual,
):

    mudancas = []

    if anterior is None:

        return [
            {
                "tipo": "primeira_percepcao",
                "caminho": "corpo",
                "anterior": None,
                "atual": "observado",
            }
        ]

    corpo_anterior = anterior.get(
        "corpo",
        {}
    )

    corpo_atual = atual.get(
        "corpo",
        {}
    )

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu_anterior = (
        corpo_anterior.get(
            "cpu",
            {}
        )
    )

    cpu_atual = (
        corpo_atual.get(
            "cpu",
            {}
        )
    )

    comparar_valor(
        "cpu.estado",
        cpu_anterior.get(
            "estado"
        ),
        cpu_atual.get(
            "estado"
        ),
        mudancas,
    )

    comparar_valor(
        "cpu.uso_percentual",
        cpu_anterior.get(
            "uso_percentual"
        ),
        cpu_atual.get(
            "uso_percentual"
        ),
        mudancas,
    )

    # --------------------------------------------------------
    # MEMÓRIA
    # --------------------------------------------------------

    memoria_anterior = (
        corpo_anterior.get(
            "memoria"
        )
        or {}
    )

    memoria_atual = (
        corpo_atual.get(
            "memoria"
        )
        or {}
    )

    comparar_valor(
        "memoria.estado",
        memoria_anterior.get(
            "estado"
        ),
        memoria_atual.get(
            "estado"
        ),
        mudancas,
    )

    comparar_valor(
        "memoria.uso_percentual",
        memoria_anterior.get(
            "uso_percentual"
        ),
        memoria_atual.get(
            "uso_percentual"
        ),
        mudancas,
    )

    # --------------------------------------------------------
    # DISCO
    # --------------------------------------------------------

    armazenamento_anterior = (
        corpo_anterior.get(
            "armazenamento"
        )
        or {}
    )

    armazenamento_atual = (
        corpo_atual.get(
            "armazenamento"
        )
        or {}
    )

    comparar_valor(
        "armazenamento.estado",
        armazenamento_anterior.get(
            "estado"
        ),
        armazenamento_atual.get(
            "estado"
        ),
        mudancas,
    )

    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    gpus_anterior = (
        corpo_anterior.get(
            "gpu",
            []
        )
    )

    gpus_atual = (
        corpo_atual.get(
            "gpu",
            []
        )
    )

    if (
        gpus_anterior
        and gpus_atual
    ):

        gpu_anterior = (
            gpus_anterior[0]
        )

        gpu_atual = (
            gpus_atual[0]
        )

        comparar_valor(
            "gpu.estado_uso",
            gpu_anterior.get(
                "estado_uso"
            ),
            gpu_atual.get(
                "estado_uso"
            ),
            mudancas,
        )

        comparar_valor(
            "gpu.uso_percentual",
            gpu_anterior.get(
                "uso_percentual"
            ),
            gpu_atual.get(
                "uso_percentual"
            ),
            mudancas,
        )

        temperaturas_anterior = (
            gpu_anterior.get(
                "temperaturas",
                []
            )
        )

        temperaturas_atual = (
            gpu_atual.get(
                "temperaturas",
                []
            )
        )

        limite = min(
            len(
                temperaturas_anterior
            ),
            len(
                temperaturas_atual
            ),
        )

        for indice in range(
            limite
        ):

            antiga = (
                temperaturas_anterior[
                    indice
                ]
            )

            nova = (
                temperaturas_atual[
                    indice
                ]
            )

            comparar_valor(
                (
                    "gpu.temperaturas."
                    f"{indice}.estado"
                ),
                antiga.get(
                    "estado"
                ),
                nova.get(
                    "estado"
                ),
                mudancas,
            )

            comparar_valor(
                (
                    "gpu.temperaturas."
                    f"{indice}.temperatura_c"
                ),
                antiga.get(
                    "temperatura_c"
                ),
                nova.get(
                    "temperatura_c"
                ),
                mudancas,
            )

    return mudancas


# ============================================================
# EVENTOS SIGNIFICATIVOS
# ============================================================

def criar_evento(
    caminho,
    anterior,
    atual,
    motivo,
):

    return {
        "timestamp": agora_iso(),

        "tipo": "mudanca_corporal",

        "caminho": caminho,

        "anterior": anterior,

        "atual": atual,

        "delta": round(
            atual - anterior,
            2,
        ),

        "motivo": motivo,
    }


def detectar_eventos_significativos(
    estado_anterior,
    estado_atual,
):

    eventos = []

    if (
        estado_anterior is None
        or estado_atual is None
    ):
        return eventos

    corpo_anterior = (
        estado_anterior.get(
            "corpo",
            {}
        )
    )

    corpo_atual = (
        estado_atual.get(
            "corpo",
            {}
        )
    )

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu_anterior = (
        corpo_anterior.get(
            "cpu",
            {}
        )
        or {}
    )

    cpu_atual = (
        corpo_atual.get(
            "cpu",
            {}
        )
        or {}
    )

    valor_anterior = (
        cpu_anterior.get(
            "uso_percentual"
        )
    )

    valor_atual = (
        cpu_atual.get(
            "uso_percentual"
        )
    )

    if (
        isinstance(
            valor_anterior,
            (int, float),
        )
        and
        isinstance(
            valor_atual,
            (int, float),
        )
    ):

        delta = abs(
            valor_atual
            - valor_anterior
        )

        if delta >= LIMITE_CPU:

            direcao = (
                "aumento"
                if valor_atual > valor_anterior
                else "redução"
            )

            eventos.append(
                criar_evento(
                    "cpu.uso_percentual",
                    valor_anterior,
                    valor_atual,
                    (
                        f"mudança significativa "
                        f"de CPU ({direcao})"
                    ),
                )
            )

    # --------------------------------------------------------
    # MEMÓRIA
    # --------------------------------------------------------

    memoria_anterior = (
        corpo_anterior.get(
            "memoria"
        )
        or {}
    )

    memoria_atual = (
        corpo_atual.get(
            "memoria"
        )
        or {}
    )

    valor_anterior = (
        memoria_anterior.get(
            "uso_percentual"
        )
    )

    valor_atual = (
        memoria_atual.get(
            "uso_percentual"
        )
    )

    if (
        isinstance(
            valor_anterior,
            (int, float),
        )
        and
        isinstance(
            valor_atual,
            (int, float),
        )
    ):

        delta = abs(
            valor_atual
            - valor_anterior
        )

        if delta >= LIMITE_RAM:

            direcao = (
                "aumento"
                if valor_atual > valor_anterior
                else "redução"
            )

            eventos.append(
                criar_evento(
                    "memoria.uso_percentual",
                    valor_anterior,
                    valor_atual,
                    (
                        f"mudança significativa "
                        f"de memória ({direcao})"
                    ),
                )
            )

    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    gpus_anterior = (
        corpo_anterior.get(
            "gpu",
            []
        )
    )

    gpus_atual = (
        corpo_atual.get(
            "gpu",
            []
        )
    )

    if (
        gpus_anterior
        and gpus_atual
    ):

        gpu_anterior = (
            gpus_anterior[0]
        )

        gpu_atual = (
            gpus_atual[0]
        )

        valor_anterior = (
            gpu_anterior.get(
                "uso_percentual"
            )
        )

        valor_atual = (
            gpu_atual.get(
                "uso_percentual"
            )
        )

        if (
            isinstance(
                valor_anterior,
                (int, float),
            )
            and
            isinstance(
                valor_atual,
                (int, float),
            )
        ):

            delta = abs(
                valor_atual
                - valor_anterior
            )

            if delta >= LIMITE_GPU:

                direcao = (
                    "aumento"
                    if valor_atual
                    > valor_anterior
                    else "redução"
                )

                eventos.append(
                    criar_evento(
                        "gpu.uso_percentual",
                        valor_anterior,
                        valor_atual,
                        (
                            f"mudança significativa "
                            f"de GPU ({direcao})"
                        ),
                    )
                )

        # ----------------------------------------------------
        # TEMPERATURAS GPU
        # ----------------------------------------------------

        temperaturas_anterior = (
            gpu_anterior.get(
                "temperaturas",
                []
            )
        )

        temperaturas_atual = (
            gpu_atual.get(
                "temperaturas",
                []
            )
        )

        limite = min(
            len(
                temperaturas_anterior
            ),
            len(
                temperaturas_atual
            ),
        )

        for indice in range(
            limite
        ):

            antiga = (
                temperaturas_anterior[
                    indice
                ]
            )

            nova = (
                temperaturas_atual[
                    indice
                ]
            )

            valor_anterior = antiga.get(
                "temperatura_c"
            )

            valor_atual = nova.get(
                "temperatura_c"
            )

            if not (
                isinstance(
                    valor_anterior,
                    (int, float),
                )
                and
                isinstance(
                    valor_atual,
                    (int, float),
                )
            ):
                continue

            delta = abs(
                valor_atual
                - valor_anterior
            )

            if delta >= LIMITE_TEMPERATURA:

                rotulo = (
                    nova.get(
                        "rotulo"
                    )
                    or nova.get(
                        "sensor"
                    )
                    or f"sensor_{indice}"
                )

                direcao = (
                    "aumento"
                    if valor_atual
                    > valor_anterior
                    else "redução"
                )

                eventos.append(
                    criar_evento(
                        (
                            "gpu.temperaturas."
                            f"{rotulo}"
                        ),
                        valor_anterior,
                        valor_atual,
                        (
                            f"mudança significativa "
                            f"de temperatura ({direcao})"
                        ),
                    )
                )

    return eventos


# ============================================================
# MEMÓRIA CORPORAL
# ============================================================

def carregar_memoria_corporal():

    if not os.path.exists(
        ARQUIVO_MEMORIA_CORPORAL
    ):
        return {
            "identidade": {
                "nome": NOME
            },

            "sessao": {
                "iniciada_em": agora_iso(),

                "ciclos": 0,

                "eventos": [],
            },
        }

    try:

        with open(
            ARQUIVO_MEMORIA_CORPORAL,
            "r",
            encoding="utf-8",
        ) as arquivo:

            memoria = json.load(
                arquivo
            )

        if not isinstance(
            memoria,
            dict,
        ):
            raise ValueError

        memoria.setdefault(
            "identidade",
            {
                "nome": NOME
            },
        )

        memoria.setdefault(
            "sessao",
            {},
        )

        memoria[
            "sessao"
        ].setdefault(
            "ciclos",
            0,
        )

        memoria[
            "sessao"
        ].setdefault(
            "eventos",
            [],
        )

        return memoria

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ):

        return {
            "identidade": {
                "nome": NOME
            },

            "sessao": {
                "iniciada_em": agora_iso(),

                "ciclos": 0,

                "eventos": [],
            },
        }


def salvar_memoria_corporal(
    memoria,
):

    temporario = (
        ARQUIVO_MEMORIA_CORPORAL
        + ".tmp"
    )

    with open(
        temporario,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            memoria,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporario,
        ARQUIVO_MEMORIA_CORPORAL,
    )


# ============================================================
# ESTADO CORPORAL PERSISTENTE
# ============================================================

def salvar_estado_corpo(
    estado,
):

    temporario = (
        ARQUIVO_ESTADO_CORPO
        + ".tmp"
    )

    with open(
        temporario,
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            estado,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporario,
        ARQUIVO_ESTADO_CORPO,
    )


# ============================================================
# EXIBIÇÃO
# ============================================================

def mostrar_percepcao(
    estado,
    mudancas,
    eventos,
):

    corpo = estado[
        "corpo"
    ]

    print(
        "----------------------------------------------"
    )

    print(
        f"[Nixal] percepção "
        f"{estado['percepcao']['timestamp']}"
    )

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu = corpo[
        "cpu"
    ]

    if not cpu[
        "calibrada"
    ]:

        print(
            "CPU: calibrando..."
        )

    else:

        print(
            f"CPU: "
            f"{cpu['uso_percentual']:.2f}% "
            f"| estado="
            f"{cpu['estado']}"
        )

    # --------------------------------------------------------
    # RAM
    # --------------------------------------------------------

    memoria = corpo[
        "memoria"
    ]

    if memoria is None:

        print(
            "RAM: indisponível"
        )

    else:

        print(
            f"RAM: "
            f"{memoria['uso_percentual']:.2f}% "
            f"("
            f"{memoria['usado_gb']:.2f}/"
            f"{memoria['total_gb']:.2f} GB"
            f") "
            f"| estado="
            f"{memoria['estado']}"
        )

    # --------------------------------------------------------
    # TEMPERATURAS
    # --------------------------------------------------------

    temperaturas = corpo[
        "temperaturas_gerais"
    ]

    if temperaturas:

        for temperatura in temperaturas:

            print(
                f"Temperatura "
                f"{temperatura['tipo']}: "
                f"{temperatura['temperatura_c']:.2f}°C "
                f"| estado="
                f"{temperatura['estado']}"
            )

    else:

        print(
            "Temperaturas gerais: "
            "nenhuma zona detectada"
        )

    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    gpus = corpo[
        "gpu"
    ]

    if gpus:

        for gpu in gpus:

            identidade = gpu[
                "identidade"
            ]

            print(
                f"GPU real: "
                f"{gpu['dispositivo']} "
                f"| vendor="
                f"{identidade['vendor']} "
                f"| uso="
                f"{gpu['uso_percentual']} "
                f"| estado="
                f"{gpu['estado_uso']}"
            )

            print(
                f"  driver: "
                f"{identidade['driver']}"
            )

            print(
                f"  pci_id: "
                f"{identidade['pci_id']}"
            )

            print(
                f"  slot: "
                f"{identidade['pci_slot']}"
            )

            for sensor in gpu[
                "temperaturas"
            ]:

                rotulo = (
                    sensor["rotulo"]
                    or sensor["sensor"]
                )

                print(
                    f"  {rotulo}: "
                    f"{sensor['temperatura_c']:.2f}°C "
                    f"| estado="
                    f"{sensor['estado']}"
                )

    else:

        print(
            "GPU real: nenhuma detectada"
        )

    # --------------------------------------------------------
    # DISCO
    # --------------------------------------------------------

    armazenamento = corpo[
        "armazenamento"
    ]

    print(
        f"Disco /: "
        f"{armazenamento['uso_percentual']:.2f}% "
        f"usado "
        f"| estado="
        f"{armazenamento['estado']}"
    )

    print(
        f"Processos: "
        f"{corpo['processos']}"
    )

    print(
        f"Uptime: "
        f"{corpo['uptime_segundos']} s"
    )

    # --------------------------------------------------------
    # MUDANÇAS
    # --------------------------------------------------------

    if mudancas:

        print(
            "Mudanças observadas:"
        )

        for mudanca in mudancas:

            print(
                f"  {mudanca['caminho']}: "
                f"{mudanca['anterior']} "
                f"-> "
                f"{mudanca['atual']}"
            )

    else:

        print(
            "Mudanças observadas: nenhuma"
        )

    # --------------------------------------------------------
    # EVENTOS SIGNIFICATIVOS
    # --------------------------------------------------------

    if eventos:

        print(
            "EVENTOS CORPORAIS:"
        )

        for evento in eventos:

            print(
                f"  {evento['caminho']}: "
                f"{evento['anterior']} "
                f"-> "
                f"{evento['atual']} "
                f"({evento['motivo']})"
            )

    else:

        print(
            "Eventos corporais: nenhum"
        )


# ============================================================
# PRINCIPAL
# ============================================================

def main():

    print()
    print(
        "=============================================="
    )
    print(
        "NIXAL"
    )
    print(
        "MICROETAPA 52.3 — MEMÓRIA CORPORAL"
    )
    print(
        "=============================================="
    )
    print()

    print(
        "Modo: SOMENTE LEITURA"
    )

    print(
        "Controle de hardware: DESATIVADO"
    )

    print(
        "Comparação temporal: ATIVADA"
    )

    print(
        "Eventos corporais: ATIVADOS"
    )

    print()

    # --------------------------------------------------------
    # IMPORTANTE
    #
    # O estado persistente anterior NÃO será usado como
    # comparação temporal da nova sessão.
    #
    # A sessão começa com uma nova linha de base.
    # --------------------------------------------------------

    cpu_anterior = None

    estado_anterior = None

    memoria = (
        carregar_memoria_corporal()
    )

    memoria[
        "sessao"
    ] = {
        "iniciada_em": agora_iso(),

        "ciclos": 0,

        "eventos": [],
    }

    while True:

        estado_atual, cpu_atual = (
            perceber_corpo(
                cpu_anterior
            )
        )

        # ----------------------------------------------------
        # COMPARAÇÃO
        # ----------------------------------------------------

        mudancas = comparar_estados(
            estado_anterior,
            estado_atual,
        )

        # ----------------------------------------------------
        # EVENTOS
        # ----------------------------------------------------

        eventos = (
            detectar_eventos_significativos(
                estado_anterior,
                estado_atual,
            )
        )

        # ----------------------------------------------------
        # MEMÓRIA
        # ----------------------------------------------------

        memoria[
            "sessao"
        ][
            "ciclos"
        ] += 1

        if eventos:

            memoria[
                "sessao"
            ][
                "eventos"
            ].extend(
                eventos
            )

            memoria[
                "sessao"
            ][
                "eventos"
            ] = memoria[
                "sessao"
            ][
                "eventos"
            ][-MAX_EVENTOS:]

        # ----------------------------------------------------
        # PERSISTÊNCIA
        # ----------------------------------------------------

        salvar_estado_corpo(
            estado_atual
        )

        salvar_memoria_corporal(
            memoria
        )

        # ----------------------------------------------------
        # EXIBIÇÃO
        # ----------------------------------------------------

        mostrar_percepcao(
            estado_atual,
            mudancas,
            eventos,
        )

        # ----------------------------------------------------
        # PREPARAR PRÓXIMO CICLO
        # ----------------------------------------------------

        estado_anterior = (
            estado_atual
        )

        cpu_anterior = cpu_atual

        time.sleep(
            INTERVALO_CICLO
        )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "[Nixal] memória corporal encerrada."
        )
