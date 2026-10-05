from __future__ import annotations
from typing import Any
import copy

class EscopoLLC:
    FONTE="llc_escopo"
    VERSAO="LLC.8.0.0"
    INVARIANTES={"autorizacao_explicita":False,"integracao_executada":False,"stable_modificada":False,"arquitetura_modificada":False,"conhecimento_permanente":False,"execucao_local":False,"treinamento_automatico":False,"implantacao_automatica":False,"causalidade_ambiental_comprovada":False}

    @classmethod
    def validar(cls, *, evidencia:dict[str,Any], escopo_observado:dict[str,Any], escopo_declarado:dict[str,Any])->dict[str,Any]:
        erros=[]
        if not isinstance(evidencia,dict) or evidencia.get("replicacao_independente_comprovada") is not True: erros.append("replicacao_nao_comprovada")
        if not isinstance(escopo_observado,dict) or not isinstance(escopo_declarado,dict): erros.append("escopo_invalido")
        if isinstance(escopo_observado,dict) and isinstance(escopo_declarado,dict) and escopo_observado!=escopo_declarado: erros.append("escopo_declarado_excede_observado")
        if isinstance(escopo_declarado,dict) and escopo_declarado.get("universal") is True: erros.append("generalizacao_universal_proibida")
        valido=not erros
        return {"sucesso":True,"estado":"escopo_validado" if valido else "escopo_inconclusivo","origem":cls.FONTE,"versao":cls.VERSAO,"escopo_validado":valido,"escopo":copy.deepcopy(escopo_declarado) if isinstance(escopo_declarado,dict) else None,"erros":erros,**copy.deepcopy(cls.INVARIANTES)}
