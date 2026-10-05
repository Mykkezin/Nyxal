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
        erros=[]; ids=set(); execucoes=set(); series=set(); efeitos=[]
        if not isinstance(evidencias,list) or len(evidencias)<cls.MIN_REPLICACOES: erros.append("replicacoes_insuficientes")
        for item in evidencias if isinstance(evidencias,list) else []:
            if not isinstance(item,dict): erros.append("replicacao_invalida"); continue
            rid=item.get("replicacao_id"); eid=item.get("execucao_id"); sid=item.get("serie_id")
            if not isinstance(rid,str) or not rid.strip(): erros.append("replicacao_id_invalido")
            elif rid in ids: erros.append("replicacao_id_duplicado")
            else: ids.add(rid)
            if not isinstance(eid,str) or not eid.strip(): erros.append("execucao_id_invalido")
            elif eid in execucoes: erros.append("execucao_id_duplicado")
            else: execucoes.add(eid)
            if not isinstance(sid,str) or not sid.strip(): erros.append("serie_id_invalido")
            elif sid in series: erros.append("serie_id_duplicado")
            else: series.add(sid)
            if item.get("acao")!=acao_esperada: erros.append("acao_divergente")
            if item.get("metrica")!=metrica: erros.append("metrica_divergente")
            if item.get("proveniencia_evidencia_valida") is not True: erros.append("proveniencia_invalida")
            efeito=item.get("efeito_medio_contrafactual")
            if not isinstance(efeito,(int,float)) or isinstance(efeito,bool): erros.append("efeito_invalido")
            else: efeitos.append(float(efeito))
        direcao=metrica.get("direcao_melhor") if isinstance(metrica,dict) else None
        consistente=bool(efeitos) and all((e>0 if direcao=="maior" else e<0) for e in efeitos) if direcao in {"maior","menor"} else False
        distinta=len(ids)>=cls.MIN_REPLICACOES and len(execucoes)>=cls.MIN_REPLICACOES and len(series)>=cls.MIN_REPLICACOES
        valido=not erros and distinta and consistente
        return {"sucesso":True,"estado":"replicacao_distinta_consistente" if valido else "replicacao_inconclusiva","origem":cls.FONTE,"versao":cls.VERSAO,"replicacoes_distintas":len(ids),"execucoes_distintas":len(execucoes),"series_distintas":len(series),"efeitos":efeitos,"consistencia_direcional":consistente,"replicacao_distinta_validada":valido,"independencia_real_comprovada":False,"erros":erros,**copy.deepcopy(cls.INVARIANTES)}
