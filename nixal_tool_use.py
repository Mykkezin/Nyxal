#!/usr/bin/env python3
"""Ferramentas operacionais limitadas da Nyxal, integradas ao registro existente.

Este módulo não cria um segundo executor ou sistema de memória geral. Ele
adiciona adaptadores opcionais ao GerenciadorCapacidades já usado pelo Core,
pelo diálogo local e pelo servidor MCP.
"""
from __future__ import annotations

import ipaddress
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_DIR = Path(__file__).resolve().parent
HOME = Path.home()
MAX_JSON_BYTES = 1_000_000
MAX_AISWEB_BYTES = 2_000_000
DEFAULT_USER_DATA_DIR = Path(
    os.environ.get("NYXAL_USER_DATA_DIR", str(HOME / ".local" / "share" / "nyxal"))
).expanduser()
ARQUIVO_NOTAS_LEMBRETES = DEFAULT_USER_DATA_DIR / "notas_lembretes.json"

_PARTES_SENSIVEIS = {
    ".git", ".venv", "venv", "node_modules", ".ssh", ".gnupg", ".aws",
    ".config", ".pki", ".hermes", "keyrings", "secrets", "secret",
    "credentials", "credential", "tokens", "token",
}
_NOMES_SENSIVEIS = {
    ".env", ".env.local", ".env.production", ".bashrc", ".profile",
    "id_rsa", "id_ed25519", "authorized_keys", "known_hosts",
    "credentials.json", "token.json",
}
_EXTENSOES_SENSIVEIS = {".pem", ".key", ".p12", ".pfx", ".kdbx"}


def _texto(valor: Any, limite: int = 4000) -> str:
    return valor.strip()[:limite] if isinstance(valor, str) else ""


def _limite(valor: Any, padrao: int, minimo: int, maximo: int) -> int:
    if isinstance(valor, bool):
        return padrao
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return padrao
    return max(minimo, min(maximo, numero))


def _caminho_sensivel(caminho: Path) -> bool:
    partes = [p.lower() for p in caminho.parts]
    nome = caminho.name.lower()
    if any(p in _PARTES_SENSIVEIS or p.startswith(".env") for p in partes):
        return True
    if nome in _NOMES_SENSIVEIS or nome.startswith(".env"):
        return True
    if caminho.suffix.lower() in _EXTENSOES_SENSIVEIS:
        return True
    return any(
        marcador in nome
        for marcador in ("secret", "credential", "private_key", "access_token", "refresh_token")
    )


class _SemRedirecionamento(HTTPRedirectHandler):
    """Impede que uma resposta redirecione consultas ou credenciais para outro host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_get_json(url: str, *, timeout: float = 8.0) -> Any:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Nyxal/1.0"},
        method="GET",
    )
    with build_opener(_SemRedirecionamento()).open(request, timeout=timeout) as response:
        if response.status == 204:
            return None
        raw = response.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("A resposta externa excedeu o limite de 1 MiB.")
    return json.loads(raw.decode("utf-8")) if raw else None


class _DuckDuckGoResults(HTMLParser):
    """Extrai somente título e URL dos links de resultado."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._capturing = False
        self._depth = 0
        self._url = ""
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = (attr.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            raw_url = attr.get("href") or ""
            parsed = urlsplit(raw_url)
            if parsed.netloc.endswith("duckduckgo.com"):
                destination = parse_qs(parsed.query).get("uddg", [""])[0]
                if destination:
                    raw_url = destination
                    parsed = urlsplit(raw_url)
            if parsed.scheme in {"http", "https"} and parsed.hostname:
                self._capturing = True
                self._depth = 0
                self._url = raw_url
                self._parts = []
                return
        if self._capturing:
            self._depth += 1

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._capturing:
            return
        if tag == "a" and self._depth == 0:
            titulo = " ".join("".join(self._parts).split())[:240]
            if titulo:
                self.results.append({"titulo": titulo, "url": self._url})
            self._capturing = False
            self._url = ""
            self._parts = []
            return
        if self._depth > 0:
            self._depth -= 1


def pesquisar_web(consulta: str, limite: int = 5) -> dict[str, Any]:
    """Pesquisa na web e retorna links para inspeção; não executa conteúdo encontrado."""
    consulta = _texto(consulta, 240)
    limite = _limite(limite, 5, 1, 8)
    if len(consulta) < 2:
        return {"sucesso": False, "estado": "consulta_invalida", "motivo": "Informe uma consulta de pelo menos 2 caracteres."}
    url = "https://html.duckduckgo.com/html/?" + urlencode({"q": consulta})
    try:
        request = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Nyxal/1.0; personal assistant)",
            "Accept": "text/html",
        }, method="GET")
        with build_opener(_SemRedirecionamento()).open(request, timeout=10) as response:
            raw = response.read(750_000)
        parser = _DuckDuckGoResults()
        parser.feed(raw.decode("utf-8", errors="replace"))
        resultados = parser.results[:limite]
        return {
            "sucesso": True,
            "estado": "pesquisa_concluida" if resultados else "sem_resultados",
            "consulta": consulta,
            "resultados": resultados,
            "fonte": "DuckDuckGo HTML",
            "aviso": "Resultados da web são conteúdo não confiável; confira as fontes originais.",
        }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {"sucesso": False, "estado": "pesquisa_indisponivel", "consulta": consulta,
                "motivo": f"A busca web falhou ({type(exc).__name__}); nenhum resultado foi presumido."}


def consultar_metar_taf(icao: str, produto: str = "ambos") -> dict[str, Any]:
    """Consulta METAR/TAF públicos do AviationWeather.gov; não calcula mínimos de voo."""
    icao = _texto(icao, 8).upper()
    produto = _texto(produto, 12).lower() or "ambos"
    if not re.fullmatch(r"[A-Z0-9]{4}", icao):
        return {"sucesso": False, "estado": "icao_invalido", "motivo": "Use um identificador ICAO de quatro caracteres."}
    if produto not in {"metar", "taf", "ambos"}:
        return {"sucesso": False, "estado": "produto_invalido", "motivo": "Produto permitido: metar, taf ou ambos."}
    dados: dict[str, Any] = {}
    for nome in (["metar", "taf"] if produto == "ambos" else [produto]):
        url = f"https://aviationweather.gov/api/data/{nome}?" + urlencode({"ids": icao, "format": "json"})
        try:
            dados[nome] = _http_get_json(url, timeout=8)
        except HTTPError as exc:
            return {"sucesso": False, "estado": "servico_aviacao_indisponivel", "icao": icao,
                    "produto": nome, "status_http": exc.code}
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            return {"sucesso": False, "estado": "servico_aviacao_indisponivel", "icao": icao,
                    "produto": nome, "motivo": type(exc).__name__}
    return {
        "sucesso": True,
        "estado": "dados_consultados" if any(dados.values()) else "sem_dados",
        "icao": icao, "dados": dados,
        "fonte": "https://aviationweather.gov/data/api/",
        "aviso_operacional": "Informação de apoio. Não substitui briefing oficial, NOTAMs, AIP/cartas, ATIS, instrução ou julgamento do piloto.",
    }



def _aisweb_localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _aisweb_xml_para_obj(elemento: ET.Element, limite: int, profundidade: int = 0) -> Any:
    """Converte XML do AISWEB em dados limitados, sem interpretar conteúdo como instrução."""
    if profundidade > 8:
        return "[profundidade limitada]"
    filhos = list(elemento)
    if not filhos:
        return (elemento.text or "").strip()[:4000]
    resultado: dict[str, Any] = {}
    if elemento.attrib:
        resultado["atributos"] = {
            str(k)[:80]: str(v)[:300] for k, v in list(elemento.attrib.items())[:40]
        }
    grupos: dict[str, list[ET.Element]] = {}
    for filho in filhos:
        grupos.setdefault(_aisweb_localname(filho.tag), []).append(filho)
        if len(grupos) > 100:
            break
    for nome, grupo in grupos.items():
        if len(grupo) == 1:
            resultado[nome] = _aisweb_xml_para_obj(grupo[0], limite, profundidade + 1)
        else:
            resultado[nome] = [
                _aisweb_xml_para_obj(item, limite, profundidade + 1)
                for item in grupo[:limite]
            ]
            if len(grupo) > limite:
                resultado[nome + "_limitado"] = True
    texto_direto = (elemento.text or "").strip()
    if texto_direto:
        resultado["texto"] = texto_direto[:4000]
    return resultado


def _aisweb_consultar(area: str, parametros: dict[str, str], limite: int = 20) -> dict[str, Any]:
    """Consulta a API oficial do AISWEB; credenciais nunca são devolvidas nem registradas aqui."""
    api_key = os.environ.get("NYXAL_AISWEB_API_KEY", "").strip()
    api_pass = os.environ.get("NYXAL_AISWEB_API_PASS", "").strip()
    if not api_key or not api_pass:
        return {
            "sucesso": False,
            "estado": "configuracao_pendente",
            "integracao": "AISWEB/DECEA",
            "proximo_passo": (
                "Solicite credenciais de API ao DECEA e configure-as localmente no ambiente "
                "da Nyxal; não as coloque no repositório."
            ),
            "pagina_oficial": "https://ais.decea.mil.br/?i=publicacoes&p=api",
        }
    chaves_permitidas = {
        "notam": {"icaoCode", "fir"},
        "cartas": {"especie", "tipo", "icaoCode", "name", "dt", "use"},
    }
    if area not in chaves_permitidas or set(parametros) - chaves_permitidas[area]:
        return {"sucesso": False, "estado": "consulta_invalida", "motivo": "Área ou filtro não permitido."}
    params = {"apiKey": api_key, "apiPass": api_pass, "area": area}
    params.update({k: v for k, v in parametros.items() if isinstance(v, str) and v})
    url = "https://api.decea.mil.br/aisweb/?" + urlencode(params)
    request = Request(
        url,
        headers={"Accept": "application/xml, text/xml", "User-Agent": "Nyxal/1.0"},
        method="GET",
    )
    try:
        with build_opener(_SemRedirecionamento()).open(request, timeout=10) as response:
            raw = response.read(MAX_AISWEB_BYTES + 1)
        if len(raw) > MAX_AISWEB_BYTES:
            return {"sucesso": False, "estado": "resposta_muito_grande", "limite_bytes": MAX_AISWEB_BYTES}
        texto = raw.decode("utf-8-sig")
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", texto, re.IGNORECASE):
            return {"sucesso": False, "estado": "xml_nao_permitido", "motivo": "A resposta XML contém declarações não permitidas."}
        raiz = ET.fromstring(texto)
        if any(_aisweb_localname(node.tag).casefold() in {"error", "erro"} for node in raiz.iter()):
            return {"sucesso": False, "estado": "erro_da_api", "motivo": "O AISWEB retornou um erro estruturado."}
        dados = _aisweb_xml_para_obj(raiz, _limite(limite, 20, 1, 50))
        return {
            "sucesso": True,
            "estado": "consulta_concluida",
            "area": area,
            "dados": dados,
            "fonte": "https://ais.decea.mil.br/",
            "limite_resultados_por_lista": _limite(limite, 20, 1, 50),
        }
    except HTTPError as exc:
        return {
            "sucesso": False,
            "estado": "credenciais_rejeitadas" if exc.code in {401, 403} else "servico_indisponivel",
            "status_http": exc.code,
        }
    except (URLError, TimeoutError, OSError):
        return {"sucesso": False, "estado": "servico_indisponivel", "motivo": "Não foi possível contatar o AISWEB."}
    except (ET.ParseError, UnicodeError, ValueError):
        return {"sucesso": False, "estado": "resposta_invalida", "motivo": "A resposta do AISWEB não pôde ser validada."}


def consultar_notam_aisweb(localidades: str, fir: str = "", limite: int = 20) -> dict[str, Any]:
    """Consulta NOTAM pelo AISWEB/DECEA. É apoio e não substitui briefing oficial pré-voo."""
    texto_localidades = _texto(localidades, 80).upper().replace(" ", "")
    codigos = [x for x in texto_localidades.split(",") if x]
    if not codigos or len(codigos) > 10 or any(not re.fullmatch(r"[A-Z]{4}", x) for x in codigos):
        return {
            "sucesso": False, "estado": "icao_invalido",
            "motivo": "Informe de 1 a 10 códigos ICAO de quatro letras, separados por vírgula.",
        }
    fir = _texto(fir, 4).upper()
    if fir and not re.fullmatch(r"[A-Z]{4}", fir):
        return {"sucesso": False, "estado": "fir_invalida", "motivo": "O código FIR deve conter quatro letras."}
    limite = _limite(limite, 20, 1, 50)
    parametros = {"icaoCode": ",".join(codigos)}
    if fir:
        parametros["fir"] = fir
    resultado = _aisweb_consultar("notam", parametros, limite)
    resultado.update({
        "consulta": {"localidades": codigos, "fir": fir or None},
        "aviso_operacional": (
            "Confirme os NOTAMs na fonte oficial e no briefing pré-voo vigente. "
            "Esta consulta de apoio não substitui briefing AIS, AIP, cartas ou julgamento do piloto."
        ),
    })
    return resultado


def consultar_cartas_aisweb(
    icao: str = "",
    especie: str = "",
    tipo: str = "",
    nome: str = "",
    dt: str = "",
    limite: int = 20,
) -> dict[str, Any]:
    """Pesquisa metadados/links de cartas do AISWEB; não baixa nem interpreta a carta."""
    especies_tipos = {
        "IFR": {"ADC", "AOC", "ARC", "ATCSMAC", "GMC", "IAC", "LC", "OTR", "PATC", "PDC", "SID", "STAR", "VAC"},
        "VFR": {"CAP", "CIAP", "CINAV", "CNAV", "CV", "REA", "REAST", "REH", "REUL", "WAC"},
        "ROTA": {"ENRC"},
    }
    especie = _texto(especie, 8).upper()
    tipo = _texto(tipo, 12).upper()
    nome = _texto(nome, 120)
    dt = _texto(dt, 10).lower()
    texto_icao = _texto(icao, 80).upper().replace(" ", "")
    codigos = [x for x in texto_icao.split(",") if x]
    if codigos and (len(codigos) > 10 or any(not re.fullmatch(r"[A-Z]{4}", x) for x in codigos)):
        return {"sucesso": False, "estado": "icao_invalido", "motivo": "Informe até 10 códigos ICAO de quatro letras."}
    if not especie:
        return {"sucesso": False, "estado": "especie_obrigatoria", "motivo": "Informe IFR, VFR ou ROTA para evitar o padrão implícito da API."}
    if especie not in especies_tipos:
        return {"sucesso": False, "estado": "especie_invalida", "permitidas": sorted(especies_tipos)}
    if not tipo:
        return {"sucesso": False, "estado": "tipo_obrigatorio", "motivo": "Informe o tipo de carta para a espécie selecionada."}
    if tipo not in especies_tipos[especie]:
        return {
            "sucesso": False, "estado": "tipo_invalido",
            "motivo": "O tipo precisa ser compatível com a espécie IFR, VFR ou ROTA.",
        }
    if dt and dt != "last_amdt":
        try:
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            return {"sucesso": False, "estado": "data_invalida", "motivo": "Use uma data válida no formato AAAA-MM-DD ou last_amdt."}
    if not (codigos or nome or dt):
        return {
            "sucesso": False, "estado": "filtro_obrigatorio",
            "motivo": "Informe um ICAO, nome ou ciclo AIRAC além da espécie/tipo para limitar a pesquisa.",
        }
    limite = _limite(limite, 20, 1, 50)
    parametros = {"use": "0"}
    if codigos:
        parametros["icaoCode"] = ",".join(codigos)
    if especie:
        parametros["especie"] = especie
    if tipo:
        parametros["tipo"] = tipo
    if nome:
        parametros["name"] = nome
    if dt:
        parametros["dt"] = "last_amdt" if dt == "last_amdt" else dt
    resultado = _aisweb_consultar("cartas", parametros, limite)
    resultado.update({
        "consulta": {
            "icao": codigos, "especie": especie or None, "tipo": tipo or None,
            "nome": nome or None, "dt": dt or "ciclo vigente", "uso": "ostensivo",
        },
        "aviso_operacional": (
            "Abra e confirme a vigência da carta na fonte oficial antes do uso operacional. "
            "A Nyxal retorna metadados e links, não substitui leitura da carta nem briefing pré-voo."
        ),
    })
    return resultado


def _url_home_assistant() -> tuple[str, str] | None:
    base = os.environ.get("NYXAL_HOME_ASSISTANT_URL", "").strip().rstrip("/")
    token = os.environ.get("NYXAL_HOME_ASSISTANT_TOKEN", "").strip()
    if not base or not token:
        return None
    try:
        parsed = urlsplit(base)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        return None
    local_or_private = host in {"localhost", "homeassistant"} or host.endswith(".local")
    try:
        addr = ipaddress.ip_address(host)
        local_or_private = local_or_private or addr.is_private or addr.is_loopback
    except ValueError:
        pass
    if parsed.scheme == "http" and not local_or_private:
        return None
    if port is not None and not 1 <= port <= 65535:
        return None
    return base, token


def consultar_home_assistant(entidade_id: str = "", dominio: str = "seguro") -> dict[str, Any]:
    """Consulta estado Home Assistant; nenhuma ferramenta de controle físico é registrada."""
    config = _url_home_assistant()
    if config is None:
        return {
            "sucesso": True, "estado": "configuracao_pendente",
            "integracao": "Home Assistant", "modo": "somente_leitura",
            "proximo_passo": "Configure a URL-base e uma credencial de acesso no ambiente do serviço local; nunca a grave no repositório.",
            "acoes_fisicas_habilitadas": False,
        }
    base, token = config
    entidade_id = _texto(entidade_id, 160).lower()
    dominio = _texto(dominio, 24).lower() or "seguro"
    if entidade_id and not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", entidade_id):
        return {"sucesso": False, "estado": "entidade_invalida", "motivo": "O identificador deve ter formato dominio.entidade."}
    dominios = {
        "seguro": {"light", "switch", "sensor", "binary_sensor", "climate", "weather", "media_player"},
        "luz": {"light"}, "interruptor": {"switch"}, "sensor": {"sensor", "binary_sensor"},
        "clima": {"climate", "weather"}, "midia": {"media_player"},
        "todos": {"light", "switch", "sensor", "binary_sensor", "climate", "weather", "media_player"},
    }
    if dominio not in dominios:
        return {"sucesso": False, "estado": "dominio_invalido", "motivo": "Use seguro, luz, interruptor, sensor, clima, midia ou todos."}
    url = f"{base}/api/states/{quote(entidade_id, safe='.')}" if entidade_id else f"{base}/api/states"
    try:
        request = Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json"}, method="GET")
        with build_opener(_SemRedirecionamento()).open(request, timeout=6) as response:
            raw = response.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            return {"sucesso": False, "estado": "resposta_muito_grande"}
        body = json.loads(raw.decode("utf-8")) if raw else None
        items = [body] if entidade_id and isinstance(body, dict) else (body if not entidade_id and isinstance(body, list) else [])
        safe_states = []
        allowed_attrs = {"friendly_name", "unit_of_measurement", "device_class", "icon", "temperature", "current_temperature", "current_humidity", "hvac_mode", "brightness"}
        for item in items:
            if not isinstance(item, dict):
                continue
            entity = item.get("entity_id")
            if not isinstance(entity, str) or "." not in entity:
                continue
            if not entidade_id and entity.split(".", 1)[0] not in dominios[dominio]:
                continue
            attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
            safe_states.append({
                "entity_id": entity[:160], "state": str(item.get("state", "unknown"))[:120],
                "attributes": {k: attrs[k] for k in allowed_attrs if k in attrs and isinstance(attrs[k], (str, int, float, bool))},
                "last_changed": str(item.get("last_changed", ""))[:40],
            })
            if len(safe_states) >= 30:
                break
        return {"sucesso": True, "estado": "estado_consultado" if safe_states else "sem_resultados",
                "modo": "somente_leitura", "entidades": safe_states, "acoes_fisicas_habilitadas": False}
    except HTTPError as exc:
        return {"sucesso": False, "estado": "home_assistant_indisponivel", "status_http": exc.code,
                "motivo": "A API rejeitou a consulta; o token não foi incluído no resultado."}
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {"sucesso": False, "estado": "home_assistant_indisponivel", "motivo": type(exc).__name__}


class NotasLembretesNixOS:
    """Notas e lembretes locais, distintos da memória conversacional."""
    VERSAO = 1

    def __init__(self, arquivo: Path | None = None) -> None:
        self.arquivo = Path(arquivo) if arquivo else ARQUIVO_NOTAS_LEMBRETES
        self._lock = threading.RLock()

    def _vazio(self) -> dict[str, Any]:
        return {"versao": self.VERSAO, "notas": [], "lembretes": []}

    def _ler(self) -> dict[str, Any]:
        if not self.arquivo.exists():
            return self._vazio()
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("O arquivo local de notas/lembretes não pôde ser lido; nenhum dado foi substituído.") from exc
        if not isinstance(dados, dict) or dados.get("versao") != self.VERSAO or not isinstance(dados.get("notas"), list) or not isinstance(dados.get("lembretes"), list):
            raise RuntimeError("Formato local de notas/lembretes inválido; nenhum dado foi substituído.")
        return dados

    def _salvar(self, dados: dict[str, Any]) -> None:
        self.arquivo.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.arquivo.parent, 0o700)
        except OSError:
            pass
        temporario: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.arquivo.parent,
                    prefix=".nyxal-notas-", suffix=".tmp", delete=False) as handle:
                temporario = Path(handle.name)
                try:
                    os.fchmod(handle.fileno(), 0o600)
                except OSError:
                    pass
                handle.write(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporario, self.arquivo)
            temporario = None
            try:
                os.chmod(self.arquivo, 0o600)
            except OSError:
                pass
        finally:
            if temporario is not None:
                try:
                    temporario.unlink(missing_ok=True)
                except OSError:
                    pass

    def salvar_nota(self, titulo: str, conteudo: str) -> dict[str, Any]:
        titulo, conteudo = _texto(titulo, 120), _texto(conteudo, 4000)
        if not titulo or not conteudo:
            return {"sucesso": False, "estado": "entrada_invalida", "motivo": "Título e conteúdo são obrigatórios."}
        with self._lock:
            dados = self._ler()
            if len(dados["notas"]) >= 500:
                return {"sucesso": False, "estado": "limite_atingido", "motivo": "Limite de 500 notas atingido."}
            nota = {"id": uuid.uuid4().hex, "titulo": titulo, "conteudo": conteudo,
                    "criada_em": datetime.now().astimezone().isoformat(timespec="seconds")}
            dados["notas"].append(nota)
            self._salvar(dados)
        return {"sucesso": True, "estado": "nota_salva", "nota": nota, "local": str(self.arquivo)}

    def criar_lembrete(self, texto: str, data_hora: str) -> dict[str, Any]:
        texto, data_hora = _texto(texto, 500), _texto(data_hora, 80)
        if not texto or not data_hora:
            return {"sucesso": False, "estado": "entrada_invalida", "motivo": "Texto e data_hora ISO 8601 são obrigatórios."}
        try:
            quando = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
            if quando.tzinfo is None:
                quando = quando.replace(tzinfo=datetime.now().astimezone().tzinfo)
            quando = quando.astimezone()
        except (ValueError, OverflowError):
            return {"sucesso": False, "estado": "data_hora_invalida", "motivo": "Use data/hora ISO 8601 com fuso quando possível."}
        agora = datetime.now().astimezone()
        if quando <= agora:
            return {"sucesso": False, "estado": "data_hora_no_passado", "motivo": "O lembrete precisa estar no futuro."}
        if quando > agora + timedelta(days=365 * 5):
            return {"sucesso": False, "estado": "data_hora_fora_do_limite", "motivo": "O lembrete não pode passar de cinco anos."}
        with self._lock:
            dados = self._ler()
            pendentes = [x for x in dados["lembretes"] if isinstance(x, dict) and x.get("notificado_em") is None]
            if len(pendentes) >= 500:
                return {"sucesso": False, "estado": "limite_atingido", "motivo": "Limite de 500 lembretes pendentes atingido."}
            lembrete = {"id": uuid.uuid4().hex, "texto": texto, "data_hora": quando.isoformat(timespec="seconds"),
                        "estado": "pendente", "criado_em": agora.isoformat(timespec="seconds"), "notificado_em": None}
            dados["lembretes"].append(lembrete)
            self._salvar(dados)
        return {"sucesso": True, "estado": "lembrete_criado", "lembrete": lembrete,
                "notificacoes": "A API local verifica vencimentos enquanto o serviço estiver em execução."}

    def listar(self, tipo: str = "todos") -> dict[str, Any]:
        if tipo not in {"notas", "lembretes", "todos"}:
            return {"sucesso": False, "estado": "tipo_invalido", "motivo": "Use notas, lembretes ou todos."}
        with self._lock:
            dados = self._ler()
        notas = dados["notas"][-30:]
        lembretes = sorted(dados["lembretes"], key=lambda x: str(x.get("data_hora", "")) if isinstance(x, dict) else "")[:50]
        return {"sucesso": True, "estado": "consulta_concluida",
                "notas": notas if tipo in {"notas", "todos"} else [],
                "lembretes": lembretes if tipo in {"lembretes", "todos"} else [],
                "limites": {"notas_retornadas": 30, "lembretes_retornados": 50}}

    def lembretes_vencidos(self) -> list[dict[str, Any]]:
        agora = datetime.now().astimezone()
        with self._lock:
            dados = self._ler()
        vencidos = []
        for item in dados["lembretes"]:
            if not isinstance(item, dict) or item.get("notificado_em") is not None:
                continue
            try:
                quando = datetime.fromisoformat(str(item.get("data_hora", "")).replace("Z", "+00:00"))
                if quando.tzinfo is None:
                    quando = quando.replace(tzinfo=agora.tzinfo)
                if quando.astimezone() <= agora:
                    vencidos.append(dict(item))
            except (ValueError, TypeError, OverflowError):
                continue
        return vencidos[:20]

    def marcar_notificado(self, lembrete_id: str) -> bool:
        with self._lock:
            dados = self._ler()
            for item in dados["lembretes"]:
                if isinstance(item, dict) and item.get("id") == lembrete_id and item.get("notificado_em") is None:
                    item["notificado_em"] = datetime.now().astimezone().isoformat(timespec="seconds")
                    item["estado"] = "notificado"
                    self._salvar(dados)
                    return True
        return False


class ServicoLembretesNixOS:
    """Verifica lembretes e entrega notificações de desktop sem shell."""
    def __init__(self, store: NotasLembretesNixOS | None = None, intervalo: float = 20.0) -> None:
        self.store = store or NotasLembretesNixOS()
        self.intervalo = max(5.0, float(intervalo))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="nyxal-lembretes", daemon=True)
        self._thread.start()
        return True

    def parar(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(0.0, timeout))

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.processar_vencidos()
            except Exception:
                pass
            self._stop.wait(self.intervalo)

    def processar_vencidos(self) -> dict[str, int]:
        notify = shutil.which("notify-send")
        if not notify or not any(os.environ.get(k) for k in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS")):
            return {"vencidos": 0, "notificados": 0, "ambiente_indisponivel": 1}
        vencidos = self.store.lembretes_vencidos()
        enviados = 0
        for item in vencidos:
            texto = _texto(item.get("texto"), 500)
            if not texto:
                continue
            try:
                result = subprocess.run([notify, "Nyxal — Lembrete", texto],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=4, check=False)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if result.returncode == 0 and self.store.marcar_notificado(str(item.get("id", ""))):
                enviados += 1
        return {"vencidos": len(vencidos), "notificados": enviados, "ambiente_indisponivel": 0}


def buscar_arquivos(termo: str, limite: int = 10) -> dict[str, Any]:
    termo, limite = _texto(termo, 160).casefold(), _limite(limite, 10, 1, 20)
    if len(termo) < 2:
        return {"sucesso": False, "estado": "consulta_invalida", "motivo": "O termo precisa conter ao menos 2 caracteres."}
    roots = [BASE_DIR, HOME / "Documents", HOME / "Downloads", HOME / "Desktop"]
    roots = [p.resolve() for p in roots if p.exists() and p.is_dir()]
    encontrados: list[dict[str, Any]] = []
    examinados = 0
    ignorar = set(_PARTES_SENSIVEIS) | {".cache", "__pycache__", "dist", "build"}
    for root in roots:
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d.lower() not in ignorar)
            for nome in files:
                examinados += 1
                if examinados > 12000:
                    break
                caminho = Path(current) / nome
                if _caminho_sensivel(caminho):
                    continue
                if termo not in nome.casefold() and termo not in str(caminho.parent).casefold():
                    continue
                try:
                    st = caminho.stat()
                except OSError:
                    continue
                if caminho.is_file():
                    encontrados.append({"caminho": str(caminho)[:600], "tamanho_bytes": st.st_size,
                        "modificado_em": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")})
                if len(encontrados) >= limite:
                    break
            if len(encontrados) >= limite or examinados > 12000:
                break
        if len(encontrados) >= limite or examinados > 12000:
            break
    return {"sucesso": True, "estado": "busca_concluida" if encontrados else "sem_resultados",
            "termo": termo, "resultados": encontrados, "arquivos_examinados": examinados, "limite_busca": 12000}


def ler_arquivo_usuario(caminho: str) -> dict[str, Any]:
    caminho = _texto(caminho, 500)
    if not caminho:
        return {"sucesso": False, "estado": "caminho_invalido"}
    rel = Path(caminho).expanduser()
    if rel.is_absolute() or ".." in rel.parts or any(parte.startswith(".") for parte in rel.parts):
        return {"sucesso": False, "estado": "caminho_bloqueado", "motivo": "Use um caminho relativo, sem componentes ocultos ou '..', dentro das pastas permitidas."}
    roots = [BASE_DIR.resolve(), (HOME / "Documents").resolve(), (HOME / "Downloads").resolve(), (HOME / "Desktop").resolve()]
    destino = None
    for root in roots:
        candidato = (root / rel).resolve()
        if (candidato == root or root in candidato.parents) and candidato.is_file():
            destino = candidato
            break
    if destino is None:
        return {"sucesso": False, "estado": "arquivo_nao_encontrado", "motivo": "O arquivo não existe em uma das pastas permitidas."}
    if _caminho_sensivel(destino):
        return {"sucesso": False, "estado": "arquivo_protegido", "motivo": "A leitura foi bloqueada pela política de proteção de credenciais."}
    try:
        if destino.stat().st_size > 1_000_000:
            return {"sucesso": False, "estado": "arquivo_muito_grande", "limite_bytes": 1_000_000}
        conteudo = destino.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {"sucesso": False, "estado": "arquivo_indisponivel", "motivo": type(exc).__name__}
    return {"sucesso": True, "estado": "arquivo_lido", "caminho": str(destino),
            "conteudo": conteudo[:20000], "truncado": len(conteudo) > 20000}


def consultar_emails_google(consulta: str = "is:unread newer_than:7d", limite: int = 10) -> dict[str, Any]:
    from nixal_integracao_gmail import IntegracaoGmailNixOS
    consulta, limite = _texto(consulta, 500) or "is:unread newer_than:7d", _limite(limite, 10, 1, 20)
    google = IntegracaoGmailNixOS()
    status = google.status()
    if status.get("estado") != "configurado" or not status.get("servicos_disponiveis", {}).get("gmail"):
        return {"sucesso": False, "estado": "gmail_nao_configurado", "somente_leitura": True, "integracao": status}
    return google.listar_mensagens(query=consulta, limite=limite)


def ler_email_google(message_id: str) -> dict[str, Any]:
    from nixal_integracao_gmail import IntegracaoGmailNixOS
    message_id = _texto(message_id, 200)
    if not message_id or not re.fullmatch(r"[A-Za-z0-9_-]+", message_id):
        return {"sucesso": False, "estado": "id_email_invalido"}
    google = IntegracaoGmailNixOS()
    status = google.status()
    if status.get("estado") != "configurado" or not status.get("servicos_disponiveis", {}).get("gmail"):
        return {"sucesso": False, "estado": "gmail_nao_configurado", "somente_leitura": True}
    resultado = google.obter_mensagem(message_id)
    if isinstance(resultado, dict) and isinstance(resultado.get("corpo_texto"), str):
        corpo = resultado["corpo_texto"]
        resultado["corpo_texto"] = corpo[:8000]
        resultado["corpo_truncado"] = len(corpo) > 8000
    return resultado


def consultar_agenda_google(dias: int = 14, limite: int = 20) -> dict[str, Any]:
    from nixal_integracao_gmail import IntegracaoGmailNixOS
    dias, limite = _limite(dias, 14, 1, 31), _limite(limite, 20, 1, 50)
    google = IntegracaoGmailNixOS()
    status = google.status()
    if status.get("estado") != "configurado" or not status.get("servicos_disponiveis", {}).get("agenda"):
        return {"sucesso": False, "estado": "agenda_nao_configurada", "somente_leitura": True, "integracao": status}
    return google.listar_eventos(limite=limite, dias=dias)


def abrir_aplicativo(aplicativo: str) -> dict[str, Any]:
    """Abre um nome de aplicativo da lista fixa; não executa texto como comando."""
    aplicativo = _texto(aplicativo, 40).lower()
    mapa = {
        "navegador": [["firefox"], ["chromium"], ["chromium-browser"], ["google-chrome"], ["xdg-open", "about:blank"]],
        "arquivos": [["xdg-open", str(HOME)]],
        "terminal": [["x-terminal-emulator"], ["gnome-terminal"], ["konsole"], ["kgx"], ["xterm"]],
        "calculadora": [["gnome-calculator"], ["kcalc"], ["qalculate-gtk"], ["mate-calc"]],
    }
    if aplicativo not in mapa:
        return {"sucesso": False, "estado": "aplicativo_nao_permitido", "permitidos": sorted(mapa)}
    for comando in mapa[aplicativo]:
        executable = shutil.which(comando[0])
        if not executable:
            continue
        try:
            processo = subprocess.Popen([executable, *comando[1:]], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            return {"sucesso": True, "estado": "aplicativo_aberto", "aplicativo": aplicativo,
                    "pid": processo.pid, "comando_permitido": comando[0]}
        except OSError:
            continue
    return {"sucesso": False, "estado": "aplicativo_indisponivel", "aplicativo": aplicativo,
            "motivo": "Executável permitido não encontrado ou ambiente gráfico indisponível."}


def executar_diagnostico(tipo: str) -> dict[str, Any]:
    """Executa apenas diagnósticos fixos, de leitura, sem shell fornecido pelo usuário."""
    tipo = _texto(tipo, 40).lower()
    if tipo == "git_status":
        comando, cwd = ["git", "status", "--short", "--branch"], BASE_DIR
        try:
            result = subprocess.run(comando, cwd=cwd, capture_output=True, text=True, timeout=5, check=False)
            return {"sucesso": result.returncode == 0, "tipo": tipo, "codigo_saida": result.returncode,
                    "saida": result.stdout[:6000], "erro": result.stderr[:1000]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"sucesso": False, "tipo": tipo, "estado": "diagnostico_indisponivel", "motivo": type(exc).__name__}
    if tipo == "servicos_nyxal":
        try:
            result = subprocess.run(["systemctl", "--user", "--no-pager", "--plain", "--state=failed", "list-units"],
                capture_output=True, text=True, timeout=5, check=False)
            return {"sucesso": result.returncode == 0, "tipo": tipo, "codigo_saida": result.returncode,
                    "saida": result.stdout[:6000], "erro": result.stderr[:1000]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"sucesso": False, "tipo": tipo, "estado": "diagnostico_indisponivel", "motivo": type(exc).__name__}
    if tipo in {"sistema", "processos", "disco", "memoria"}:
        from nixal_observabilidade_sistema import ObservabilidadeSistemaNixOS
        snap = ObservabilidadeSistemaNixOS().snapshot()
        chaves = {
            "sistema": ("host", "cpu", "memoria", "armazenamento_home", "temperaturas", "gpu", "governanca"),
            "processos": ("processos",), "disco": ("armazenamento_home",), "memoria": ("memoria",),
        }[tipo]
        return {"sucesso": bool(snap.get("sucesso")), "tipo": tipo, "modo": "somente_leitura",
                **{key: snap.get(key) for key in chaves}}
    return {"sucesso": False, "estado": "diagnostico_nao_permitido",
            "permitidos": ["git_status", "servicos_nyxal", "sistema", "processos", "disco", "memoria"],
            "comandos_arbitrarios_habilitados": False}


def registrar_capacidades_operacionais(
    capacidades: Any,
    *,
    incluir_acoes: bool = False,
    incluir_dados_privados: bool = False,
    store: NotasLembretesNixOS | None = None,
) -> None:
    """Registra ferramentas com perfil seguro por padrão.

    Pesquisa pública, METAR/TAF e diagnósticos fixos ficam disponíveis por
    padrão. Arquivos pessoais, Gmail, agenda, Home Assistant e notas exigem
    opt-in; escrita/notificações/abertura de aplicativos exigem outro opt-in.
    """
    if not hasattr(capacidades, "registrar") or not hasattr(capacidades, "capacidades"):
        raise TypeError("É necessário fornecer o GerenciadorCapacidades existente.")
    if not isinstance(incluir_acoes, bool) or not isinstance(incluir_dados_privados, bool):
        raise TypeError("Os opt-ins precisam ser booleanos.")
    if os.environ.get("NYXAL_ENABLE_PRIVATE_READ_TOOLS", "").strip().lower() in {"1", "true", "yes", "on"}:
        incluir_dados_privados = True
    if os.environ.get("NYXAL_ENABLE_MUTABLE_TOOLS", "").strip().lower() in {"1", "true", "yes", "on"}:
        incluir_acoes = True

    ferramentas_privadas = {
        "buscar_arquivos",
        "ler_arquivo_usuario",
        "consultar_emails_google",
        "ler_email_google",
        "consultar_agenda_google",
        "consultar_home_assistant",
        "listar_notas_lembretes",
    }
    notas = store or NotasLembretesNixOS()

    try:
        assinatura_registrar = inspect.signature(capacidades.registrar).parameters
        assinatura_executar = inspect.signature(capacidades.executar).parameters
    except (TypeError, ValueError, AttributeError):
        assinatura_registrar, assinatura_executar = {}, {}
    possui_politica = "politica" in assinatura_registrar
    possui_guarda = "autorizacao_explicita" in assinatura_executar

    def adicionar(nome: str, descricao: str, objetivo: str, exemplos: list[str], funcao: Any,
                  argumentos: dict[str, dict[str, Any]], dominio: str, evidencias: list[str],
                  politica: str = "somente_leitura") -> None:
        if nome in capacidades.capacidades:
            return
        if nome in ferramentas_privadas and not incluir_dados_privados:
            return
        # Nunca registra escrita no registro legado que não consiga aplicar a guarda.
        if politica != "somente_leitura" and not (possui_politica and possui_guarda):
            return
        kwargs = {
            "nome": nome, "descricao": descricao, "objetivo": objetivo, "exemplos": exemplos,
            "funcao": funcao, "argumentos": argumentos, "dominios": [dominio],
            "evidencias_dominio": evidencias,
        }
        if possui_politica:
            kwargs["politica"] = politica
        capacidades.registrar(**kwargs)

    adicionar("buscar_arquivos", "Busca arquivos por nome no projeto e em Documents, Downloads e Desktop; ignora caminhos sensíveis.",
        "Encontrar arquivos locais sem executar seu conteúdo.", ["Encontre o arquivo orçamento", "Busque o PDF de aviação"],
        buscar_arquivos, {"termo": {"tipo": "string", "obrigatorio": True, "descricao": "Termo de busca"},
        "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Máximo de resultados", "minimo": 1, "maximo": 20}},
        "arquivos_locais", ["buscar arquivo", "encontrar arquivo", "localizar arquivo"])
    adicionar("ler_arquivo_usuario", "Lê texto de arquivo dentro das pastas permitidas; bloqueia credenciais e arquivos grandes.",
        "Ler um documento local solicitado.", ["Leia o documento em Downloads", "Abra o README do projeto"],
        ler_arquivo_usuario, {"caminho": {"tipo": "string", "obrigatorio": True, "descricao": "Caminho relativo permitido"}},
        "arquivos_locais", ["ler arquivo", "ler documento", "conteúdo do arquivo"])
    adicionar("consultar_emails_google", "Busca mensagens Gmail via OAuth em modo somente leitura.",
        "Consultar metadados e prévias de mensagens autorizadas.", ["Veja meus e-mails não lidos", "Busque e-mails sobre a reunião"],
        consultar_emails_google, {"consulta": {"tipo": "string", "obrigatorio": False, "descricao": "Consulta Gmail"},
        "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Máximo de mensagens", "minimo": 1, "maximo": 20}},
        "google_workspace", ["gmail", "e-mail", "email", "mensagens"])
    adicionar("ler_email_google", "Lê texto de um e-mail pelo ID exato; não altera a conta.",
        "Abrir conteúdo de mensagem previamente selecionada pelo usuário.", ["Leia o e-mail de ID ...", "Resuma esta mensagem"],
        ler_email_google, {"message_id": {"tipo": "string", "obrigatorio": True, "descricao": "ID exato retornado pela busca Gmail"}},
        "google_workspace", ["ler e-mail", "abrir mensagem", "corpo do e-mail"])
    adicionar("consultar_agenda_google", "Consulta eventos Google Calendar em janela limitada, somente leitura.",
        "Responder perguntas sobre compromissos existentes.", ["O que tenho na agenda?", "Quais eventos tenho esta semana?"],
        consultar_agenda_google, {"dias": {"tipo": "integer", "obrigatorio": False, "descricao": "Janela em dias", "minimo": 1, "maximo": 31},
        "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Máximo de eventos", "minimo": 1, "maximo": 50}},
        "google_workspace", ["agenda", "calendário", "compromisso", "evento"])
    adicionar("pesquisar_web", "Busca resultados na web e retorna títulos/URLs; não abre nem executa as páginas.",
        "Encontrar fontes externas para a pergunta.", ["Pesquise a documentação oficial do Ollama", "Encontre fontes sobre METAR"],
        pesquisar_web, {"consulta": {"tipo": "string", "obrigatorio": True, "descricao": "Consulta"},
        "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Número de resultados", "minimo": 1, "maximo": 8}},
        "web", ["pesquisar na web", "buscar na internet", "pesquisar online", "fontes web"])
    adicionar("consultar_metar_taf", "Consulta METAR/TAF públicos por ICAO; apoio e não substitui briefing oficial.",
        "Consultar observação e previsão meteorológica de aeródromo.", ["METAR e TAF de SBGR", "Consulte o METAR SBSP"],
        consultar_metar_taf, {"icao": {"tipo": "string", "obrigatorio": True, "descricao": "ICAO com quatro caracteres"},
        "produto": {"tipo": "string", "obrigatorio": False, "descricao": "metar, taf ou ambos", "enum": ["metar", "taf", "ambos"]}},
        "aviacao", ["metar", "taf", "meteorologia aeronáutica", "aeroporto ICAO"])
    adicionar("consultar_notam_aisweb", "Consulta NOTAM pelo AISWEB/DECEA para 1 a 10 localidades ICAO; briefing oficial continua obrigatório.",
        "Consultar avisos aeronáuticos publicados para planejamento.", ["Consulte os NOTAMs de SBSP", "NOTAM de SBGR e SBGL"],
        consultar_notam_aisweb, {"localidades": {"tipo": "string", "obrigatorio": True, "descricao": "Um a dez códigos ICAO separados por vírgula"},
        "fir": {"tipo": "string", "obrigatorio": False, "descricao": "Código FIR opcional"},
        "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Limite de registros", "minimo": 1, "maximo": 50}},
        "aviacao", ["notam", "avisos aeronáuticos", "briefing", "AISWEB"])
    adicionar("consultar_cartas_aisweb", "Pesquisa metadados e links de cartas aeronáuticas oficiais do AISWEB/DECEA; cartas ostensivas apenas.",
        "Localizar cartas IFR, VFR ou de rota e seus links oficiais.", ["Encontre cartas IFR de SBSP", "Cartas VFR WAC perto de SBGR"],
        consultar_cartas_aisweb, {"icao": {"tipo": "string", "obrigatorio": False, "descricao": "Até dez códigos ICAO separados por vírgula"},
        "especie": {"tipo": "string", "obrigatorio": False, "descricao": "IFR, VFR ou ROTA", "enum": ["IFR", "VFR", "ROTA"]},
        "tipo": {"tipo": "string", "obrigatorio": False, "descricao": "Tipo de carta compatível com a espécie"},
        "nome": {"tipo": "string", "obrigatorio": False, "descricao": "Nome parcial da carta"},
        "dt": {"tipo": "string", "obrigatorio": False, "descricao": "Data AAAA-MM-DD ou last_amdt"},
        "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Limite de registros", "minimo": 1, "maximo": 50}},
        "aviacao", ["cartas aeronáuticas", "carta IFR", "carta VFR", "AISWEB"])
    adicionar("consultar_home_assistant", "Consulta estados Home Assistant por entidade/domínio, apenas HTTP GET.",
        "Consultar dispositivos autorizados sem acioná-los.", ["Quais luzes estão ligadas?", "Consulte o sensor de temperatura da casa"],
        consultar_home_assistant, {"entidade_id": {"tipo": "string", "obrigatorio": False, "descricao": "ID como light.sala"},
        "dominio": {"tipo": "string", "obrigatorio": False, "descricao": "Filtro", "enum": ["seguro", "luz", "interruptor", "sensor", "clima", "midia", "todos"]}},
        "casa_inteligente", ["home assistant", "dispositivos", "luzes", "sensor de casa"])
    adicionar("listar_notas_lembretes", "Lista notas e lembretes locais sem alterar registros.",
        "Ver notas guardadas e lembretes registrados.", ["Liste minhas notas", "Quais lembretes tenho?"],
        notas.listar, {"tipo": {"tipo": "string", "obrigatorio": False, "descricao": "notas, lembretes ou todos", "enum": ["notas", "lembretes", "todos"]}},
        "produtividade", ["notas", "lembretes", "anotações", "tarefas futuras"])
    adicionar("executar_diagnostico", "Realiza diagnósticos fixos somente leitura; não aceita shell livre.",
        "Verificar estado do Git, serviços, processos, disco e memória.", ["Verifique o git status", "Confira o uso de disco"],
        executar_diagnostico, {"tipo": {"tipo": "string", "obrigatorio": True, "descricao": "Diagnóstico permitido",
        "enum": ["git_status", "servicos_nyxal", "sistema", "processos", "disco", "memoria"]}},
        "diagnostico_local", ["diagnóstico", "git status", "disco", "memória do sistema", "processos"])
    if incluir_acoes:
        adicionar("salvar_nota", "Salva nota local persistente apenas após pedido explícito do usuário.",
            "Preservar conteúdo solicitado pelo operador.", ["Anote que a reunião mudou para sexta", "Salve esta nota"],
            notas.salvar_nota, {"titulo": {"tipo": "string", "obrigatorio": True, "descricao": "Título"},
            "conteudo": {"tipo": "string", "obrigatorio": True, "descricao": "Conteúdo"}},
            "produtividade", ["anotar", "salvar nota", "registrar nota", "guardar"], "acao_com_pedido_explicito")
        adicionar("criar_lembrete", "Cria lembrete local após pedido explícito, com data/hora ISO 8601.",
            "Agendar notificação local solicitada pelo operador.", ["Me lembre às 19h de estudar", "Crie um lembrete para amanhã"],
            notas.criar_lembrete, {"texto": {"tipo": "string", "obrigatorio": True, "descricao": "O que lembrar"},
            "data_hora": {"tipo": "string", "obrigatorio": True, "descricao": "ISO 8601, com fuso quando possível"}},
            "produtividade", ["me lembre", "lembrete", "recordar", "avisar depois"], "acao_com_pedido_explicito")
        adicionar("abrir_aplicativo", "Abre um app de allowlist, sem aceitar argumentos de shell.",
            "Abrir navegador, gestor de arquivos, terminal ou calculadora, se solicitado explicitamente.",
            ["Abra o navegador", "Abra a calculadora"],
            abrir_aplicativo, {"aplicativo": {"tipo": "string", "obrigatorio": True, "descricao": "Nome permitido",
            "enum": ["navegador", "arquivos", "terminal", "calculadora"]}},
            "controle_local", ["abrir aplicativo", "iniciar aplicativo", "abrir navegador", "abrir terminal"],
            "acao_com_pedido_explicito")


__all__ = [
    "NotasLembretesNixOS", "ServicoLembretesNixOS", "registrar_capacidades_operacionais",
    "pesquisar_web", "consultar_metar_taf", "consultar_notam_aisweb", "consultar_cartas_aisweb",
    "consultar_home_assistant",
    "buscar_arquivos", "ler_arquivo_usuario", "consultar_emails_google",
    "ler_email_google", "consultar_agenda_google", "abrir_aplicativo", "executar_diagnostico",
]
