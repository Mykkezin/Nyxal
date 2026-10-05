from __future__ import annotations
from typing import Any
import copy,hashlib,json

class AprendizadoLLC:
    FONTE="llc_aprendizado"
    VERSAO="LLC.9.0.0"
    INVARIANTES={"autorizacao_explicita":False,"integracao_executada":False,"stable_modificada":False,"arquitetura_modificada":False,"conhecimento_permanente":False,"execucao_local":False,"treinamento_automatico":False,"implantacao_automatica":False,"causalidade_ambiental_comprovada":False}

    @staticmethod
    def _hash(d:Any)->str:
        return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()[:24]

    @classmethod
    def cristalizar(cls, *, evidencia:dict[str,Any], escopo:dict[str,Any], regra:str)->dict[str,Any]:
        erros=[]
        if not isinstance(evidencia,dict) or evidencia.get("escopo_validado") is not True: erros.append("escopo_nao_validado")
        if not isinstance(escopo,dict) or not escopo: erros.append("escopo_invalido")
        if not isinstance(regra,str) or not regra.strip(): erros.append("regra_invalida")
        payload={"regra":regra.strip(),"escopo":escopo,"origem":evidencia.get("origem") if isinstance(evidencia,dict) else None,"versao_origem":evidencia.get("versao") if isinstance(evidencia,dict) else None}
        aid=cls._hash(payload) if not erros else None
        valido=not erros
        return {"sucesso":True,"estado":"aprendizado_auditavel" if valido else "aprendizado_inconclusivo","origem":cls.FONTE,"versao":cls.VERSAO,"aprendizado_auditavel":valido,"aprendizado_id":aid,"regra":regra.strip() if isinstance(regra,str) else None,"escopo":copy.deepcopy(escopo) if isinstance(escopo,dict) else None,"proveniencia":copy.deepcopy(evidencia) if isinstance(evidencia,dict) else None,"erros":erros,**copy.deepcopy(cls.INVARIANTES)}
