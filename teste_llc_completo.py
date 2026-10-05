#!/usr/bin/env python3
from nixal_replicacao_llc import ReplicacaoLLC
from nixal_escopo_llc import EscopoLLC
from nixal_aprendizado_llc import AprendizadoLLC
from nixal_fechamento_llc import FechamentoLLC

def main():
    metrica={"nome":"cpu_uso","caminho":"recursos.cpu.uso_percentual","unidade":"%","fonte":"habitat_nyxos","direcao_melhor":"menor"}
    reps=[
        {"replicacao_id":"r1","execucao_id":"exec-1","serie_id":"serie-1","acao":"registrar_estado_corpo","metrica":metrica,"proveniencia_evidencia_valida":True,"efeito_medio_contrafactual":-3.0},
        {"replicacao_id":"r2","execucao_id":"exec-2","serie_id":"serie-2","acao":"registrar_estado_corpo","metrica":metrica,"proveniencia_evidencia_valida":True,"efeito_medio_contrafactual":-2.0},
    ]
    r7=ReplicacaoLLC.avaliar(evidencias=reps,metrica=metrica,acao_esperada="registrar_estado_corpo")
    assert r7["replicacao_distinta_validada"] is True
    assert r7["independencia_real_comprovada"] is False

    escopo={"habitat":"habitat_nyxos","metrica":"recursos.cpu.uso_percentual","acao":"registrar_estado_corpo","universal":False}
    r8=EscopoLLC.validar(evidencia=r7,escopo_observado=escopo,escopo_declarado=escopo)
    assert r8["escopo_validado"] is True

    r9=AprendizadoLLC.cristalizar(evidencia=r8,escopo=escopo,regra="preferir registrar_estado_corpo dentro do escopo validado")
    assert r9["aprendizado_auditavel"] is True
    assert r9["aprendizado_id"]

    r10=FechamentoLLC.validar(decisao_inicial={"acao":"observar_sem_atuar"},decisao_reutilizada={"acao":"registrar_estado_corpo"},aprendizado=r9,evidencia_final=r8)
    assert r10["ciclo_fechado"] is True

    # gates negativos
    assert ReplicacaoLLC.avaliar(evidencias=reps[:1],metrica=metrica,acao_esperada="registrar_estado_corpo")["replicacao_distinta_validada"] is False
    duplicado=[{**reps[1],"execucao_id":"exec-1"}]
    assert ReplicacaoLLC.avaliar(evidencias=reps[:1]+duplicado,metrica=metrica,acao_esperada="registrar_estado_corpo")["replicacao_distinta_validada"] is False
    universal=EscopoLLC.validar(evidencia=r7,escopo_observado=escopo,escopo_declarado={**escopo,"universal":True})
    assert universal["escopo_validado"] is False
    assert AprendizadoLLC.cristalizar(evidencia=universal,escopo=escopo,regra="x")["aprendizado_auditavel"] is False
    fechado=FechamentoLLC.validar(decisao_inicial={"acao":"a"},decisao_reutilizada={"acao":"a"},aprendizado=r9,evidencia_final=r8)
    assert fechado["ciclo_fechado"] is False

    print("TESTE_LLC_COMPLETO_OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
