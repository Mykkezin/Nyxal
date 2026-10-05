from __future__ import annotations
from typing import Any
import copy

class ReplicacaoLLC:
    FONTE="llc_replicacao"
    VERSAO="LLC.7.0.0"
    MIN_REPLICACOES=2
    INVARIANTES={"autorizacao_explicita":False,"integracao_executada":False,"stable_modificada":False,"arquitetura_modificada":False,"conhecimento_permanente":False,"execucao_local":False,"treinamento_automatico":False,"implantacao_automatica":False,"causalidade_ambiental_comprovada":False}

    @classmethod
    def avaliar(cls, *, evidencias:list[dict[str,Any]], metrica:dict[str,Any], acao_esperada:str)->dict[str,Any]:
        erros=[]; ids=set(); efeitos=[]
        if not isinstance(evidencias,list) or len(evidencias)<cls.MIN_REPLICACOES: erros.append("replicacoes_insuficientes")
        for item in evidencias if isinstance(evidencias,list) else []:
            if not isinstance(item,dict): erros.append("replicacao_invalida"); continue
            rid=item.get("replicacao_id")
            if not isinstance(rid,str) or not rid.strip(): erros.append("replicacao_id_invalido")
            elif rid in ids: erros.append("replicacao_id_duplicado")
            else: ids.add(rid)
            if item.get("acao")!=acao_esperada: erros.append("acao_divergente")
            if item.get("metrica")!=metrica: erros.append("metrica_divergente")
            if item.get("proveniencia_evidencia_valida") is not True: erros.append("proveniencia_invalida")
            efeito=item.get("efeito_medio_contrafactual")
            if not isinstance(efeito,(int,float)) or isinstance(efeito,bool): erros.append("efeito_invalido")
            else: efeitos.append(float(efeito))
        direcao=metrica.get("direcao_melhor") if isinstance(metrica,dict) else None
        consistente=bool(efeitos) and all((e>0 if direcao=="maior" else e<0) for e in efeitos) if direcao in {"maior","menor"} else False
        valido=not erros and len(ids)>=cls.MIN_REPLICACOES and consistente
        return {"sucesso":True,"estado":"replicacao_independente_consistente" if valido else "replicacao_inconclusiva","origem":cls.FONTE,"versao":cls.VERSAO,"replicacoes_distintas":len(ids),"efeitos":efeitos,"consistencia_direcional":consistente,"replicacao_independente_comprovada":valido,"erros":erros,**copy.deepcopy(cls.INVARIANTES)}
