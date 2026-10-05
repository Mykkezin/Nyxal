from __future__ import annotations
from typing import Any
import copy

class FechamentoLLC:
    FONTE="llc_fechamento"
    VERSAO="LLC.10.0.0"
    INVARIANTES={"autorizacao_explicita":False,"integracao_executada":False,"stable_modificada":False,"arquitetura_modificada":False,"conhecimento_permanente":False,"execucao_local":False,"treinamento_automatico":False,"implantacao_automatica":False,"causalidade_ambiental_comprovada":False}

    @classmethod
    def validar(cls, *, decisao_inicial:dict[str,Any], decisao_reutilizada:dict[str,Any], aprendizado:dict[str,Any], evidencia_final:dict[str,Any])->dict[str,Any]:
        erros=[]
        for nome,obj in (("decisao_inicial",decisao_inicial),("decisao_reutilizada",decisao_reutilizada),("aprendizado",aprendizado),("evidencia_final",evidencia_final)):
            if not isinstance(obj,dict): erros.append(f"{nome}_invalida")
        if isinstance(aprendizado,dict) and aprendizado.get("aprendizado_auditavel") is not True: erros.append("aprendizado_nao_auditavel")
        if isinstance(evidencia_final,dict) and evidencia_final.get("escopo_validado") is not True: erros.append("escopo_final_nao_validado")
        influencia=isinstance(aprendizado,dict) and isinstance(decisao_inicial,dict) and isinstance(decisao_reutilizada,dict) and aprendizado.get("aprendizado_id") is not None and decisao_inicial.get("acao")!=decisao_reutilizada.get("acao")
        if not influencia: erros.append("aprendizado_nao_influenciou_reutilizacao")
        valido=not erros
        return {"sucesso":True,"estado":"llc_fechado" if valido else "llc_fechamento_inconclusivo","origem":cls.FONTE,"versao":cls.VERSAO,"ciclo_fechado":valido,"influencia_reutilizacao_comprovada":influencia,"erros":erros,**copy.deepcopy(cls.INVARIANTES)}
