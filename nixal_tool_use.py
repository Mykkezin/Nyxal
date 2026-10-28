#!/usr/bin/env python3
"""Ferramentas operacionais limitadas da Nyxal, integradas ao registro existente.

Este módulo não cria um segundo executor ou sistema de memória geral. Ele
adiciona adaptadores opcionais ao GerenciadorCapacidades já usado pelo Core,
pelo diálogo local e pelo servidor MCP.
"""
from __future__ import annotations

import difflib
import hashlib
import ipaddress
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import time
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
# Compartilhado entre instâncias da loja no mesmo processo (API, Core e serviço de lembretes).
_NOTAS_LOCK = threading.RLock()

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
    permitidos = {
        "notam": {"icaoCode", "fir"},
        "cartas": {"especie", "tipo", "icaoCode", "name", "dt", "use"},
    }
    if area not in permitidos or set(parametros) - permitidos[area]:
        return {"sucesso": False, "estado": "consulta_invalida", "motivo": "Área ou filtro não permitido."}
    params = {"apiKey": api_key, "apiPass": api_pass, "area": area}
    params.update({k: v for k, v in parametros.items() if isinstance(v, str) and v})
    url = "https://api.decea.mil.br/aisweb/?" + urlencode(params)
    request = Request(url, headers={"Accept": "application/xml, text/xml", "User-Agent": "Nyxal/1.0"}, method="GET")
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
        return {
            "sucesso": True,
            "estado": "consulta_concluida",
            "area": area,
            "dados": _aisweb_xml_para_obj(raiz, _limite(limite, 20, 1, 50)),
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
    """Consulta NOTAM pelo AISWEB/DECEA; não substitui briefing oficial pré-voo."""
    codigo_texto = _texto(localidades, 80).upper().replace(" ", "")
    codigos = [x for x in codigo_texto.split(",") if x]
    if not codigos or len(codigos) > 10 or any(not re.fullmatch(r"[A-Z]{4}", x) for x in codigos):
        return {"sucesso": False, "estado": "icao_invalido", "motivo": "Informe de 1 a 10 códigos ICAO de quatro letras, separados por vírgula."}
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
    icao: str = "", especie: str = "", tipo: str = "", nome: str = "", dt: str = "", limite: int = 20,
) -> dict[str, Any]:
    """Pesquisa metadados/links de cartas aeronáuticas oficiais ostensivas."""
    tipos = {
        "IFR": {"ADC", "AOC", "ARC", "ATCSMAC", "GMC", "IAC", "LC", "OTR", "PATC", "PDC", "SID", "STAR", "VAC"},
        "VFR": {"CAP", "CIAP", "CINAV", "CNAV", "CV", "REA", "REAST", "REH", "REUL", "WAC"},
        "ROTA": {"ENRC"},
    }
    especie = _texto(especie, 8).upper()
    tipo = _texto(tipo, 12).upper()
    nome = _texto(nome, 120)
    dt = _texto(dt, 10).lower()
    codigo_texto = _texto(icao, 80).upper().replace(" ", "")
    codigos = [x for x in codigo_texto.split(",") if x]
    if codigos and (len(codigos) > 10 or any(not re.fullmatch(r"[A-Z]{4}", x) for x in codigos)):
        return {"sucesso": False, "estado": "icao_invalido", "motivo": "Informe até dez códigos ICAO de quatro letras."}
    if not especie:
        return {"sucesso": False, "estado": "especie_obrigatoria", "motivo": "Informe IFR, VFR ou ROTA para evitar o padrão implícito da API."}
    if especie not in tipos:
        return {"sucesso": False, "estado": "especie_invalida", "permitidas": sorted(tipos)}
    if not tipo:
        return {"sucesso": False, "estado": "tipo_obrigatorio", "motivo": "Informe o tipo de carta para a espécie selecionada."}
    if tipo not in tipos[especie]:
        return {"sucesso": False, "estado": "tipo_invalido", "motivo": "O tipo precisa ser compatível com a espécie IFR, VFR ou ROTA."}
    if dt and dt != "last_amdt":
        try:
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            return {"sucesso": False, "estado": "data_invalida", "motivo": "Use uma data válida no formato AAAA-MM-DD ou last_amdt."}
    if not (codigos or nome or dt):
        return {"sucesso": False, "estado": "filtro_obrigatorio", "motivo": "Informe um ICAO, nome ou ciclo AIRAC além da espécie/tipo para limitar a pesquisa."}
    limite = _limite(limite, 20, 1, 50)
    params = {"especie": especie, "tipo": tipo, "use": "0"}
    if codigos:
        params["icaoCode"] = ",".join(codigos)
    if nome:
        params["name"] = nome
    if dt:
        params["dt"] = dt
    resultado = _aisweb_consultar("cartas", params, limite)
    resultado.update({
        "consulta": {"icao": codigos, "especie": especie, "tipo": tipo, "nome": nome or None, "dt": dt or "ciclo vigente", "uso": "ostensivo"},
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
            "proximo_passo": "Configure a URL local e as credenciais do Home Assistant no ambiente do processo; não coloque segredos no repositório.",
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
        self._lock = _NOTAS_LOCK

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


# Edição de workspace em duas etapas: preparar diff e aplicar com confirmação separada.
MAX_WORKSPACE_EDIT_BYTES = 12_000
_WORKSPACE_PLAN_TTL_SECONDS = 900
_WORKSPACE_PLAN_LIMIT = 8
_WORKSPACE_DIFF_REVIEW_LIMIT = 4_500
_WORKSPACE_PLANS: dict[str, dict[str, Any]] = {}
_WORKSPACE_PLAN_LOCK = threading.RLock()

_WORKSPACE_ALLOWED_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".jsx", ".html", ".css", ".svg", ".xml", ".sql", ".csv", ".properties",
    ".service", ".desktop",
}
_WORKSPACE_ALLOWED_NAMES = {
    "readme", "license", "makefile", "dockerfile", ".gitignore", ".dockerignore",
}
_WORKSPACE_PROTECTED_NAMES = {
    # Estado, filas, logs e memórias operacionais: não editáveis pela ferramenta.
    "estado_corpo_nixal.json", "estado_nixal.json", "estado_nyxal_runtime.json",
    "estado_nyxos_operacional.json", "eventos_delta_nyxos.json",
    "auditoria_atuacao_nyxos.jsonl", "log_nyxal_residente.json",
    "log_capacidades_nixal.json", "log_nyxal_runtime.json",
    "log_nyxal_runtime.json.tmp", "fila_tarefas_nixal.json",
    "memoria_investigacao_nixal.json", "memoria_conhecimento_nixal.json",
    "memoria_aprendizado_nixal.json", "fisiologia_operacional_nyxos.json",
    "gateway_atuacao_nyxos.json", "presenca_maquina_nyxos.json",
    "plano_central_controle_nyxos.json",
}


def _workspace_edicao_habilitada() -> bool:
    """Defesa em profundidade: ambos os opt-ins devem estar ativos no próprio processo."""
    def ativo(nome: str) -> bool:
        return os.environ.get(nome, "").strip().casefold() in {"1", "true", "yes", "on"}
    return ativo("NYXAL_ENABLE_MUTABLE_TOOLS") and ativo("NYXAL_ENABLE_WORKSPACE_WRITE")


def _workspace_tem_componente_simbolico(caminho: Path) -> bool:
    """Detecta symlinks em um caminho de persistência auxiliar, inclusive ancestrais."""
    candidato = Path(caminho)
    while True:
        try:
            if candidato.is_symlink():
                return True
        except OSError:
            return True
        if candidato.parent == candidato:
            return False
        candidato = candidato.parent


def _workspace_root() -> Path:
    """Raiz explicitamente configurada; por padrão, o próprio repositório Nyxal."""
    valor = os.environ.get("NYXAL_WORKSPACE_WRITE_ROOT", str(BASE_DIR)).strip()
    if not valor:
        raise ValueError("workspace_nao_configurado")
    raiz = Path(valor).expanduser().resolve(strict=True)
    if not raiz.is_dir():
        raise ValueError("workspace_nao_e_diretorio")
    return raiz


def _workspace_target(caminho: Any) -> tuple[Path, Path, str]:
    """Resolve somente caminhos relativos, textuais e dentro de uma raiz permitida."""
    if not isinstance(caminho, str) or not caminho.strip() or len(caminho) > 240:
        raise ValueError("caminho_invalido")
    caminho = caminho.strip()
    if "\x00" in caminho or "\\" in caminho or caminho.startswith(("/", "~")):
        raise ValueError("somente_caminho_relativo_posix")
    partes_brutas = caminho.split("/")
    if any(parte in {"", ".", ".."} for parte in partes_brutas):
        raise ValueError("caminho_nao_normalizado")
    caminho_relativo = Path(*partes_brutas)
    if caminho_relativo.is_absolute() or not caminho_relativo.parts:
        raise ValueError("caminho_absoluto_bloqueado")

    partes_normalizadas = [parte.casefold() for parte in partes_brutas]
    if any(
        parte in _PARTES_SENSIVEIS
        or parte.startswith(".env")
        or parte.startswith("backup_")
        or parte in {"backups", "voices", "memoria"}
        for parte in partes_normalizadas
    ):
        raise ValueError("diretorio_sensivel_bloqueado")
    nome = caminho_relativo.name.casefold()
    sufixo = caminho_relativo.suffix.casefold()
    nomes_sensivel_por_padrao = (
        "credential", "credentials", "secret", "secrets", "token", "tokens",
        "password", "passwd", "private_key", "private-key", "api_key", "api-key",
        "apikey", "auth", "oauth", "client_secret",
    )
    if (
        nome in _NOMES_SENSIVEIS
        or nome in _WORKSPACE_PROTECTED_NAMES
        or any(parte in nome for parte in nomes_sensivel_por_padrao)
    ):
        raise ValueError("arquivo_sensivel_ou_operacional_bloqueado")
    if sufixo in _EXTENSOES_SENSIVEIS:
        raise ValueError("extensao_sensivel_bloqueada")
    if nome not in _WORKSPACE_ALLOWED_NAMES and sufixo not in _WORKSPACE_ALLOWED_SUFFIXES:
        raise ValueError("tipo_de_arquivo_nao_permitido")

    raiz = _workspace_root()
    alvo = raiz.joinpath(*partes_brutas)
    atual = raiz
    for parte in partes_brutas[:-1]:
        atual = atual / parte
        if atual.is_symlink():
            raise ValueError("symlink_no_caminho_bloqueado")
        if not atual.exists():
            raise ValueError("diretorio_pai_inexistente")
        if not atual.is_dir():
            raise ValueError("componente_do_caminho_nao_e_diretorio")
    if alvo.is_symlink():
        raise ValueError("symlink_de_destino_bloqueado")
    resolvido = alvo.resolve(strict=False)
    if resolvido == raiz or raiz not in resolvido.parents:
        raise ValueError("destino_fora_do_workspace")
    if alvo.exists() and not alvo.is_file():
        raise ValueError("destino_nao_e_arquivo_regular")
    if not alvo.parent.exists() or not alvo.parent.is_dir():
        raise ValueError("diretorio_pai_inexistente")
    return raiz, alvo, caminho_relativo.as_posix()


def _redigir_preview_workspace(texto: str) -> str:
    """Redige credenciais em formatos KEY=value, YAML e JSON antes de expor o diff."""
    texto = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", texto)
    padrao = re.compile(
        r"""(?i)(["']?[a-z0-9_-]*(?:api[_ -]?key|api[_ -]?token|access[_ -]?token|refresh[_ -]?token|session[_ -]?token|id[_ -]?token|token|authorization|password|senha|secret|credential)[a-z0-9_-]*["']?\s*[:=]\s*)("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^,\s;}\]]+)"""
    )

    def redigir_valor(m: re.Match[str]) -> str:
        valor = m.group(2)
        if len(valor) >= 2 and valor[0] in {"'", '"'} and valor[-1] == valor[0]:
            aspas = valor[0]
            return f"{m.group(1)}{aspas}[REDACTED]{aspas}"
        return f"{m.group(1)}[REDACTED]"

    return padrao.sub(redigir_valor, texto)


def preparar_edicao_workspace(caminho: str, conteudo: str) -> dict[str, Any]:
    """Prepara uma proposta limitada; não modifica o arquivo alvo."""
    if not _workspace_edicao_habilitada():
        return {"sucesso": False, "estado": "workspace_edicao_desativada", "aplicado": False}
    try:
        raiz, alvo, relativo = _workspace_target(caminho)
        if not isinstance(conteudo, str):
            return {"sucesso": False, "estado": "conteudo_invalido", "aplicado": False}
        if "\x00" in conteudo:
            return {"sucesso": False, "estado": "conteudo_binario_bloqueado", "aplicado": False}
        bytes_novos = conteudo.encode("utf-8")
        if len(bytes_novos) > MAX_WORKSPACE_EDIT_BYTES:
            return {
                "sucesso": False,
                "estado": "conteudo_excede_limite",
                "limite_bytes": MAX_WORKSPACE_EDIT_BYTES,
                "aplicado": False,
            }
        existe = alvo.exists()
        bytes_antigos = b""
        modo_original = None
        if existe:
            bytes_antigos = alvo.read_bytes()
            if len(bytes_antigos) > MAX_WORKSPACE_EDIT_BYTES:
                return {"sucesso": False, "estado": "arquivo_original_excede_limite", "aplicado": False}
            if b"\x00" in bytes_antigos:
                return {"sucesso": False, "estado": "arquivo_binario_bloqueado", "aplicado": False}
            try:
                texto_antigo = bytes_antigos.decode("utf-8")
            except UnicodeDecodeError:
                return {"sucesso": False, "estado": "arquivo_nao_utf8_bloqueado", "aplicado": False}
            modo_original = stat.S_IMODE(alvo.stat().st_mode)
        else:
            texto_antigo = ""
        if texto_antigo == conteudo:
            return {
                "sucesso": True,
                "estado": "sem_alteracoes",
                "caminho": relativo,
                "aplicado": False,
                "mensagem": "O conteúdo proposto é idêntico ao arquivo atual.",
            }

        diff = "".join(difflib.unified_diff(
            texto_antigo.splitlines(keepends=True),
            conteudo.splitlines(keepends=True),
            fromfile=f"a/{relativo}" if existe else "/dev/null",
            tofile=f"b/{relativo}",
            n=3,
        ))
        diff_preview = _redigir_preview_workspace(diff)
        if len(diff_preview) > _WORKSPACE_DIFF_REVIEW_LIMIT:
            return {
                "sucesso": False,
                "estado": "diff_excede_limite_de_revisao",
                "limite_diff_chars": _WORKSPACE_DIFF_REVIEW_LIMIT,
                "aplicado": False,
                "orientacao": "Divida a alteração em propostas menores para que o diff completo possa ser revisado antes da confirmação.",
            }
        plano_id = uuid.uuid4().hex[:12]
        agora = time.time()
        plano = {
            "plano_id": plano_id,
            "raiz": str(raiz),
            "caminho": relativo,
            "sha256_original": hashlib.sha256(bytes_antigos).hexdigest() if existe else None,
            "sha256_proposto": hashlib.sha256(bytes_novos).hexdigest(),
            "conteudo_novo": conteudo,
            "modo_original": modo_original,
            "criado_em": agora,
            "expira_em": agora + _WORKSPACE_PLAN_TTL_SECONDS,
        }
        with _WORKSPACE_PLAN_LOCK:
            for chave, valor in list(_WORKSPACE_PLANS.items()):
                if valor.get("expira_em", 0) <= agora:
                    _WORKSPACE_PLANS.pop(chave, None)
            if len(_WORKSPACE_PLANS) >= _WORKSPACE_PLAN_LIMIT:
                return {
                    "sucesso": False,
                    "estado": "limite_de_planos_pendentes",
                    "limite": _WORKSPACE_PLAN_LIMIT,
                    "aplicado": False,
                }
            _WORKSPACE_PLANS[plano_id] = plano
        return {
            "sucesso": True,
            "estado": "plano_preparado",
            "plano_id": plano_id,
            "caminho": relativo,
            "acao_proposta": "atualizar" if existe else "criar",
            "sha256_original": plano["sha256_original"],
            "sha256_proposto": plano["sha256_proposto"],
            "expira_em_segundos": _WORKSPACE_PLAN_TTL_SECONDS,
            "diff": diff_preview,
            "diff_truncado": False,
            "aplicado": False,
            "confirmacao_exata": f"CONFIRMO APLICACAO {plano_id}",
            "aviso": "Nada foi escrito. Aplique apenas em outra mensagem após revisar o diff e enviar a confirmação exata.",
        }
    except (OSError, ValueError, UnicodeError) as erro:
        motivo = str(erro) if str(erro) else type(erro).__name__
        return {"sucesso": False, "estado": motivo[:100], "aplicado": False}


def aplicar_edicao_workspace(plano_id: str, confirmacao_exata: str) -> dict[str, Any]:
    """Aplica apenas o plano em RAM, se a confirmação e o hash do alvo ainda coincidirem."""
    if not _workspace_edicao_habilitada():
        return {"sucesso": False, "estado": "workspace_edicao_desativada", "aplicado": False}
    if not isinstance(plano_id, str) or not re.fullmatch(r"[0-9a-f]{12}", plano_id):
        return {"sucesso": False, "estado": "plano_id_invalido", "aplicado": False}
    token_esperado = f"CONFIRMO APLICACAO {plano_id}"
    if not isinstance(confirmacao_exata, str) or confirmacao_exata.strip().casefold() != token_esperado.casefold():
        return {"sucesso": False, "estado": "confirmacao_exata_necessaria", "aplicado": False}

    with _WORKSPACE_PLAN_LOCK:
        plano = _WORKSPACE_PLANS.get(plano_id)
        if not isinstance(plano, dict):
            return {"sucesso": False, "estado": "plano_inexistente_ou_expirado", "aplicado": False}
        if plano.get("expira_em", 0) <= time.time():
            _WORKSPACE_PLANS.pop(plano_id, None)
            return {"sucesso": False, "estado": "plano_expirado", "aplicado": False}

        try:
            raiz, alvo, relativo = _workspace_target(plano.get("caminho"))
            if str(raiz) != plano.get("raiz"):
                return {"sucesso": False, "estado": "workspace_mudou_desde_o_plano", "aplicado": False}
            bytes_atuais = alvo.read_bytes() if alvo.exists() else None
            sha_atual = hashlib.sha256(bytes_atuais).hexdigest() if bytes_atuais is not None else None
            if sha_atual != plano.get("sha256_original"):
                return {
                    "sucesso": False,
                    "estado": "arquivo_alterado_desde_o_plano",
                    "caminho": relativo,
                    "aplicado": False,
                }
            bytes_novos = plano["conteudo_novo"].encode("utf-8")
            if hashlib.sha256(bytes_novos).hexdigest() != plano.get("sha256_proposto"):
                return {"sucesso": False, "estado": "hash_do_plano_invalido", "aplicado": False}

            backup_id = None
            if bytes_atuais is not None:
                pasta_backup = DEFAULT_USER_DATA_DIR / "workspace-backups"
                if (
                    _workspace_tem_componente_simbolico(DEFAULT_USER_DATA_DIR)
                    or _workspace_tem_componente_simbolico(pasta_backup)
                ):
                    return {
                        "sucesso": False,
                        "estado": "diretorio_backup_com_link_simbolico",
                        "aplicado": False,
                    }
                pasta_backup.mkdir(parents=True, exist_ok=True, mode=0o700)
                if _workspace_tem_componente_simbolico(pasta_backup) or not pasta_backup.is_dir():
                    return {
                        "sucesso": False,
                        "estado": "diretorio_backup_inseguro",
                        "aplicado": False,
                    }
                os.chmod(pasta_backup, 0o700)
                caminho_backup = pasta_backup / f"{plano_id}.bak"
                if _workspace_tem_componente_simbolico(caminho_backup):
                    return {
                        "sucesso": False,
                        "estado": "arquivo_backup_com_link_simbolico",
                        "aplicado": False,
                    }
                fd_backup, temporario_backup = tempfile.mkstemp(prefix=f".{plano_id}-", dir=pasta_backup)
                try:
                    with os.fdopen(fd_backup, "wb") as arquivo_backup:
                        os.fchmod(arquivo_backup.fileno(), 0o600)
                        arquivo_backup.write(bytes_atuais)
                        arquivo_backup.flush()
                        os.fsync(arquivo_backup.fileno())
                    os.replace(temporario_backup, caminho_backup)
                finally:
                    if os.path.exists(temporario_backup):
                        os.unlink(temporario_backup)
                backup_id = plano_id

            modo = plano.get("modo_original")
            modo = modo if isinstance(modo, int) else 0o600
            fd, temporario = tempfile.mkstemp(prefix=".nyxal-edit-", dir=alvo.parent)
            try:
                with os.fdopen(fd, "wb") as arquivo_temporario:
                    os.fchmod(arquivo_temporario.fileno(), modo)
                    arquivo_temporario.write(bytes_novos)
                    arquivo_temporario.flush()
                    os.fsync(arquivo_temporario.fileno())
                # Segunda verificação estreita a janela de concorrência externa.
                atuais_para_verificar = alvo.read_bytes() if alvo.exists() else None
                sha_verificado = (
                    hashlib.sha256(atuais_para_verificar).hexdigest()
                    if atuais_para_verificar is not None else None
                )
                if sha_verificado != plano.get("sha256_original"):
                    return {
                        "sucesso": False,
                        "estado": "arquivo_alterado_durante_aplicacao",
                        "caminho": relativo,
                        "aplicado": False,
                        "backup_id": backup_id,
                    }
                os.replace(temporario, alvo)
                try:
                    descritor_pasta = os.open(alvo.parent, os.O_RDONLY)
                    try:
                        os.fsync(descritor_pasta)
                    finally:
                        os.close(descritor_pasta)
                except OSError:
                    pass
            finally:
                if os.path.exists(temporario):
                    os.unlink(temporario)
            _WORKSPACE_PLANS.pop(plano_id, None)
            return {
                "sucesso": True,
                "estado": "arquivo_atualizado" if bytes_atuais is not None else "arquivo_criado",
                "caminho": relativo,
                "sha256_original": plano.get("sha256_original"),
                "sha256_final": plano.get("sha256_proposto"),
                "backup_id": backup_id,
                "aplicado": True,
                "shell_executado": False,
            }
        except (OSError, ValueError, KeyError, UnicodeError) as erro:
            return {
                "sucesso": False,
                "estado": (str(erro) or type(erro).__name__)[:100],
                "aplicado": False,
            }


def registrar_capacidades_operacionais(
    capacidades: Any,
    *,
    incluir_acoes: bool = False,
    incluir_dados_privados: bool = False,
    incluir_edicao_workspace: bool = False,
    store: NotasLembretesNixOS | None = None,
) -> None:
    """Registra ferramentas operacionais com escopo conservador.

    Por padrão, só registra pesquisa pública, consulta METAR/TAF e
    diagnósticos locais de leitura. Capacidades que acessam arquivos,
    e-mail, agenda, notas ou sensores da casa exigem opt-in explícito.

    Leituras privadas e ações mutáveis são opt-in independentes. Ações que
    alteram estado recebem política explícita no registro de capacidades e o
    executor exige autorização explícita antes de chamar a função.
    """
    if not hasattr(capacidades, "registrar") or not hasattr(capacidades, "capacidades"):
        raise TypeError("É necessário fornecer o GerenciadorCapacidades existente.")
    if not isinstance(incluir_acoes, bool):
        raise TypeError("incluir_acoes precisa ser booleano.")
    if not isinstance(incluir_dados_privados, bool):
        raise TypeError("incluir_dados_privados precisa ser booleano.")
    if not isinstance(incluir_edicao_workspace, bool):
        raise TypeError("incluir_edicao_workspace precisa ser booleano.")
    if incluir_edicao_workspace and not incluir_acoes:
        raise ValueError("Edição de workspace exige o opt-in de ações mutáveis.")
    notas = store or NotasLembretesNixOS()

    def adicionar(
        nome: str,
        descricao: str,
        objetivo: str,
        exemplos: list[str],
        funcao: Any,
        argumentos: dict[str, dict[str, Any]],
        dominio: str,
        evidencias: list[str],
        politica: str = "somente_leitura",
    ) -> None:
        if nome in capacidades.capacidades:
            return
        capacidades.registrar(
            nome=nome,
            descricao=descricao,
            objetivo=objetivo,
            exemplos=exemplos,
            funcao=funcao,
            argumentos=argumentos,
            dominios=[dominio],
            evidencias_dominio=evidencias,
            politica=politica,
        )

    # Ferramentas de baixo impacto; não recebem credenciais nem alteram estado.
    adicionar(
        "pesquisar_web",
        "Busca resultados na web e retorna títulos/URLs; não executa páginas.",
        "Encontrar fontes externas para uma pergunta.",
        ["Pesquise a documentação oficial do Ollama", "Encontre fontes sobre METAR"],
        pesquisar_web,
        {
            "consulta": {"tipo": "string", "obrigatorio": True, "descricao": "Consulta"},
            "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Número de resultados", "minimo": 1, "maximo": 8},
        },
        "web",
        ["pesquisar na web", "buscar na internet", "pesquisar online", "fontes web"],
    )
    adicionar(
        "consultar_notam_aisweb",
        "Consulta NOTAM no AISWEB/DECEA por ICAO/FIR; briefing oficial continua obrigatório.",
        "Consultar avisos aeronáuticos publicados para planejamento.",
        ["Consulte os NOTAMs de SBSP", "NOTAM de SBGR e SBGL"],
        consultar_notam_aisweb,
        {
            "localidades": {"tipo": "string", "obrigatorio": True, "descricao": "Um a dez códigos ICAO separados por vírgula", "max_length": 49},
            "fir": {"tipo": "string", "obrigatorio": False, "descricao": "Código FIR opcional", "max_length": 4},
            "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Limite de registros", "minimo": 1, "maximo": 50},
        },
        "aviacao",
        ["notam", "avisos aeronáuticos", "briefing", "AISWEB"],
    )
    adicionar(
        "consultar_cartas_aisweb",
        "Pesquisa metadados e links de cartas ostensivas do AISWEB/DECEA.",
        "Localizar cartas IFR, VFR ou de rota e links oficiais.",
        ["Encontre a carta IAC de SBSP", "Busque cartas WAC de um aeródromo"],
        consultar_cartas_aisweb,
        {
            "icao": {"tipo": "string", "obrigatorio": False, "descricao": "Até dez códigos ICAO separados por vírgula", "max_length": 49},
            "especie": {"tipo": "string", "obrigatorio": True, "descricao": "IFR, VFR ou ROTA", "enum": ["IFR", "VFR", "ROTA"]},
            "tipo": {"tipo": "string", "obrigatorio": True, "descricao": "Tipo de carta compatível com a espécie", "max_length": 12},
            "nome": {"tipo": "string", "obrigatorio": False, "descricao": "Nome parcial da carta", "max_length": 120},
            "dt": {"tipo": "string", "obrigatorio": False, "descricao": "Data AAAA-MM-DD ou last_amdt", "max_length": 10},
            "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Limite de registros", "minimo": 1, "maximo": 50},
        },
        "aviacao",
        ["cartas aeronáuticas", "carta IFR", "carta VFR", "AISWEB"],
    )
    adicionar(
        "consultar_metar_taf",
        "Consulta METAR/TAF públicos por ICAO; apoio, não substitui briefing oficial.",
        "Consultar observação e previsão meteorológica de aeródromo.",
        ["METAR e TAF de SBGR", "Consulte o METAR SBSP"],
        consultar_metar_taf,
        {
            "icao": {"tipo": "string", "obrigatorio": True, "descricao": "ICAO com quatro caracteres"},
            "produto": {"tipo": "string", "obrigatorio": False, "descricao": "metar, taf ou ambos", "enum": ["metar", "taf", "ambos"]},
        },
        "aviacao",
        ["metar", "taf", "meteorologia aeronáutica", "aeroporto ICAO"],
    )
    adicionar(
        "executar_diagnostico",
        "Verifica git status ou lista unidades de serviço de usuário com falha; sem shell livre.",
        "Diagnosticar o estado do Git ou serviços Nyxal com falha.",
        ["Verifique o git status", "Liste os serviços de usuário que falharam"],
        executar_diagnostico,
        {
            "tipo": {"tipo": "string", "obrigatorio": True, "descricao": "Use git_status ou servicos_nyxal", "enum": ["git_status", "servicos_nyxal"]},
        },
        "diagnostico_local",
        ["diagnóstico de serviço", "serviço falhou", "serviços falhados", "git status", "unidades systemd"],
    )

    if incluir_dados_privados:
        # Dados pessoais/locais não entram no espaço de ferramentas sem opt-in.
        adicionar(
            "buscar_arquivos",
            "Busca arquivos por nome em pastas permitidas; ignora caminhos sensíveis.",
            "Encontrar arquivos locais sem executar seu conteúdo.",
            ["Encontre o arquivo orçamento", "Busque o PDF de aviação"],
            buscar_arquivos,
            {
                "termo": {"tipo": "string", "obrigatorio": True, "descricao": "Termo de busca"},
                "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Máximo de resultados", "minimo": 1, "maximo": 20},
            },
            "arquivos_locais",
            ["buscar arquivo", "encontrar arquivo", "localizar arquivo"],
        )
        adicionar(
            "ler_arquivo_usuario",
            "Lê texto de arquivo em pastas permitidas; bloqueia credenciais e arquivos grandes.",
            "Ler um documento local solicitado.",
            ["Leia o documento em Downloads", "Abra o README do projeto"],
            ler_arquivo_usuario,
            {"caminho": {"tipo": "string", "obrigatorio": True, "descricao": "Caminho relativo permitido"}},
            "arquivos_locais",
            ["ler arquivo", "ler documento", "conteúdo do arquivo"],
        )
        adicionar(
            "consultar_emails_google",
            "Busca mensagens Gmail via OAuth, somente leitura.",
            "Consultar mensagens autorizadas pelo operador.",
            ["Veja meus e-mails não lidos", "Busque e-mails sobre a reunião"],
            consultar_emails_google,
            {
                "consulta": {"tipo": "string", "obrigatorio": False, "descricao": "Consulta Gmail"},
                "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Máximo de mensagens", "minimo": 1, "maximo": 20},
            },
            "google_workspace",
            ["gmail", "e-mail", "email", "mensagens"],
        )
        adicionar(
            "ler_email_google",
            "Lê texto de um e-mail pelo ID exato; não altera a conta.",
            "Abrir conteúdo de mensagem previamente selecionada.",
            ["Leia o e-mail de ID ...", "Resuma esta mensagem"],
            ler_email_google,
            {"message_id": {"tipo": "string", "obrigatorio": True, "descricao": "ID exato retornado pela busca Gmail"}},
            "google_workspace",
            ["ler e-mail", "abrir mensagem", "corpo do e-mail"],
        )
        adicionar(
            "consultar_agenda_google",
            "Consulta eventos Google Calendar em janela limitada, somente leitura.",
            "Responder perguntas sobre compromissos existentes.",
            ["O que tenho na agenda?", "Quais eventos tenho esta semana?"],
            consultar_agenda_google,
            {
                "dias": {"tipo": "integer", "obrigatorio": False, "descricao": "Janela em dias", "minimo": 1, "maximo": 31},
                "limite": {"tipo": "integer", "obrigatorio": False, "descricao": "Máximo de eventos", "minimo": 1, "maximo": 50},
            },
            "google_workspace",
            ["agenda", "calendário", "compromisso", "evento"],
        )
        adicionar(
            "consultar_home_assistant",
            "Consulta estados Home Assistant por entidade/domínio, apenas HTTP GET.",
            "Consultar dispositivos autorizados sem acioná-los.",
            ["Quais luzes estão ligadas?", "Consulte o sensor de temperatura da casa"],
            consultar_home_assistant,
            {
                "entidade_id": {"tipo": "string", "obrigatorio": False, "descricao": "ID como light.sala"},
                "dominio": {"tipo": "string", "obrigatorio": False, "descricao": "Filtro", "enum": ["seguro", "luz", "interruptor", "sensor", "clima", "midia", "todos"]},
            },
            "casa_inteligente",
            ["home assistant", "dispositivos", "luzes", "sensor de casa"],
        )
        adicionar(
            "listar_notas_lembretes",
            "Lista notas e lembretes locais sem alterar registros.",
            "Ver notas e lembretes registrados pelo operador.",
            ["Liste minhas notas", "Quais lembretes tenho?"],
            notas.listar,
            {"tipo": {"tipo": "string", "obrigatorio": False, "descricao": "notas, lembretes ou todos", "enum": ["notas", "lembretes", "todos"]}},
            "produtividade",
            ["notas", "lembretes", "anotações", "tarefas futuras"],
        )

    if incluir_acoes:
        adicionar(
            "salvar_nota",
            "Salva uma nota local persistente apenas após pedido explícito do operador.",
            "Guardar informação expressamente solicitada.",
            ["Anote que a reunião mudou para sexta", "Salve esta nota"],
            notas.salvar_nota,
            {
                "titulo": {"tipo": "string", "obrigatorio": True, "descricao": "Título", "max_length": 120},
                "conteudo": {"tipo": "string", "obrigatorio": True, "descricao": "Conteúdo", "max_length": 4000},
            },
            "produtividade",
            ["anotar", "salvar nota", "registrar nota", "guardar"],
            "acao_com_pedido_explicito",
        )
        adicionar(
            "criar_lembrete",
            "Cria um lembrete local com data/hora ISO 8601 após pedido explícito.",
            "Agendar uma notificação local solicitada pelo operador.",
            ["Me lembre às 19h de estudar", "Crie um lembrete para amanhã"],
            notas.criar_lembrete,
            {
                "texto": {"tipo": "string", "obrigatorio": True, "descricao": "O que lembrar", "max_length": 500},
                "data_hora": {"tipo": "string", "obrigatorio": True, "descricao": "ISO 8601 com fuso quando possível", "max_length": 80},
            },
            "produtividade",
            ["me lembre", "lembrete", "recordar", "avisar depois"],
            "acao_com_pedido_explicito",
        )
        adicionar(
            "abrir_aplicativo",
            "Abre somente um aplicativo permitido após pedido explícito.",
            "Abrir navegador, gestor de arquivos, terminal ou calculadora.",
            ["Abra o navegador", "Abra a calculadora"],
            abrir_aplicativo,
            {
                "aplicativo": {"tipo": "string", "obrigatorio": True, "descricao": "Nome permitido",
                    "enum": ["navegador", "arquivos", "terminal", "calculadora"]},
            },
            "controle_local",
            ["abrir aplicativo", "iniciar aplicativo", "abrir navegador", "abrir terminal"],
            "acao_com_pedido_explicito",
        )


    if incluir_edicao_workspace:
        # A ferramenta de proposta nunca grava no destino; a aplicação é outra chamada
        # e exige uma confirmação de usuário, com identificador vinculado ao hash do alvo.
        adicionar(
            "preparar_edicao_workspace",
            "Prepara um diff pequeno para um arquivo textual permitido dentro do workspace configurado. Não aplica mudanças; devolve um ID e um token de confirmação para outro turno.",
            "Propor uma pequena alteração revisável a um arquivo de projeto autorizado.",
            ["Prepare uma proposta pequena para corrigir README.md", "Mostre um diff curto para atualizar um módulo Python"],
            preparar_edicao_workspace,
            {
                "caminho": {
                    "tipo": "string", "obrigatorio": True,
                    "descricao": "Caminho relativo do workspace; não use caminho absoluto",
                    "max_length": 240,
                },
                "conteudo": {
                    "tipo": "string", "obrigatorio": True,
                    "descricao": "Conteúdo textual completo de uma pequena edição, até 3.000 caracteres",
                    "max_length": 3000,
                },
            },
            "workspace_edicao",
            ["prepare uma edição", "proponha alteração de arquivo", "gere diff de arquivo"],
            "acao_com_pedido_explicito",
        )
        adicionar(
            "aplicar_edicao_workspace",
            "Aplica um plano pendente de edição do workspace após a confirmação exata em um turno separado. Revalida hash e cria backup local antes de substituir o arquivo.",
            "Aplicar uma proposta de arquivo que o operador revisou e confirmou explicitamente.",
            ["Aplicar a edição depois de confirmar o ID exato do plano"],
            aplicar_edicao_workspace,
            {
                "plano_id": {
                    "tipo": "string", "obrigatorio": True,
                    "descricao": "ID de 12 caracteres recebido na proposta",
                    "max_length": 12,
                },
                "confirmacao_exata": {
                    "tipo": "string", "obrigatorio": True,
                    "descricao": "Repita exatamente CONFIRMO APLICACAO <PLANO_ID>",
                    "max_length": 40,
                },
            },
            "workspace_edicao",
            ["confirmar aplicação de plano", "aplicar edição confirmada"],
            "acao_com_pedido_explicito",
        )

__all__ = [
    "NotasLembretesNixOS", "ServicoLembretesNixOS", "registrar_capacidades_operacionais",
    "pesquisar_web", "consultar_metar_taf", "consultar_notam_aisweb", "consultar_cartas_aisweb",
    "consultar_home_assistant",
    "buscar_arquivos", "ler_arquivo_usuario", "consultar_emails_google",
    "ler_email_google", "consultar_agenda_google", "abrir_aplicativo", "executar_diagnostico",
    "preparar_edicao_workspace", "aplicar_edicao_workspace",
]
