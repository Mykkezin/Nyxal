#!/usr/bin/env python3
"""NYXAL — Learning Loop Causal (LLC).

LLC.1: influencia decisoria por contraste sem/com aprendizado.
LLC.2: decisao -> acao -> resultado -> feedback operacional -> aprendizado.
LLC.3: evidencia causal por metrica externa + controle + contrafactual.

LLC.3 nao transforma simples pre/post em causalidade e nao treina,
implanta, autoriza integracao ou altera arquitetura.
"""

from __future__ import annotations

import copy
from typing import Any


class LearningLoopCausalNixal:
    FONTE = "learning_loop_causal_nixal"
    VERSAO = "LLC.3.0.0"
    POLITICA = "repetir_sucesso_evitar_falha"
    DESENHO_CAUSAL = "contraste_controlado_did"

    CANDIDATAS = (
        {"estrategia": "persistir_estado", "acao": "registrar_estado_corpo", "pontuacao_base": 1.0},
        {"estrategia": "somente_observar", "acao": "observar_sem_atuar", "pontuacao_base": 0.0},
    )

    INVARIANTES = {
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
        "execucao_local": False,
        "treinamento_automatico": False,
        "implantacao_automatica": False,
    }

    @staticmethod
    def _numero(valor: Any) -> float | None:
        if isinstance(valor, bool):
            return None
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        return numero if numero == numero and abs(numero) != float("inf") else None

    @classmethod
    def _opcao_por_acao(cls, acao: str) -> dict[str, Any] | None:
        return next(
            (copy.deepcopy(item) for item in cls.CANDIDATAS if item["acao"] == acao),
            None,
        )

    @classmethod
    def _sinal_aprendizado(cls, aprendizado_anterior: dict[str, Any] | None):
        if not isinstance(aprendizado_anterior, dict):
            return None
        if aprendizado_anterior.get("disponivel") is not True:
            return None
        experiencia = aprendizado_anterior.get("experiencia_anterior")
        avaliacao = aprendizado_anterior.get("avaliacao_anterior")
        if not isinstance(experiencia, dict) or not isinstance(avaliacao, dict):
            return None
        acao = experiencia.get("acao")
        avaliacao_nome = avaliacao.get("avaliacao")
        if not isinstance(acao, str) or avaliacao_nome not in {"sucesso", "falha"}:
            return None
        if cls._opcao_por_acao(acao) is None:
            return None
        return {
            "aprendizado_id": aprendizado_anterior.get("aprendizado_id"),
            "ciclo_origem": aprendizado_anterior.get("ciclo_origem"),
            "acao_anterior": acao,
            "avaliacao_anterior": avaliacao_nome,
            "aplicado_no_ciclo_atual": bool(aprendizado_anterior.get("aplicado_no_ciclo_atual")),
        }

    @classmethod
    def _pontuar_sem_aprendizado(cls):
        return [
            {**copy.deepcopy(item), "pontuacao": float(item["pontuacao_base"])}
            for item in cls.CANDIDATAS
        ]

    @classmethod
    def _pontuar_com_aprendizado(cls, sinal):
        pontuacoes = cls._pontuar_sem_aprendizado()
        if sinal is None:
            return pontuacoes
        for item in pontuacoes:
            if sinal["avaliacao_anterior"] == "sucesso" and item["acao"] == sinal["acao_anterior"]:
                item["pontuacao"] += 1.0
            elif sinal["avaliacao_anterior"] == "falha":
                item["pontuacao"] += -2.0 if item["acao"] == sinal["acao_anterior"] else 1.0
        return pontuacoes

    @staticmethod
    def _selecionar(pontuacoes):
        return copy.deepcopy(sorted(
            pontuacoes,
            key=lambda item: (-float(item.get("pontuacao", 0.0)), str(item.get("acao", ""))),
        )[0])

    @classmethod
    def selecionar(cls, *, estado_corpo, prioridades, aprendizado_anterior):
        if not isinstance(estado_corpo, dict):
            return {
                "sucesso": False, "estado": "llc_estado_invalido",
                "origem": cls.FONTE, "versao": cls.VERSAO,
                "motivo": "O estado corporal precisa ser um objeto.",
                **cls.INVARIANTES, "causalidade_ambiental_comprovada": False,
            }
        if not isinstance(prioridades, dict):
            return {
                "sucesso": False, "estado": "llc_prioridades_invalidas",
                "origem": cls.FONTE, "versao": cls.VERSAO,
                "motivo": "As prioridades precisam ser um objeto.",
                **cls.INVARIANTES, "causalidade_ambiental_comprovada": False,
            }
        sinal = cls._sinal_aprendizado(aprendizado_anterior)
        sem = cls._selecionar(cls._pontuar_sem_aprendizado())
        com = cls._selecionar(cls._pontuar_com_aprendizado(sinal))
        mudou = sem["acao"] != com["acao"]
        influencia = bool(
            sinal is not None
            and isinstance(aprendizado_anterior, dict)
            and aprendizado_anterior.get("aplicado_no_ciclo_atual") is True
            and mudou
        )
        motivo = (
            "O sinal de aprendizado alterou a escolha entre as alternativas."
            if influencia
            else "O aprendizado foi considerado, mas nao alterou a escolha."
            if sinal is not None
            else "Nao existe sinal de aprendizado estruturado valido."
        )
        return {
            "sucesso": True, "estado": "decisao_llc", "origem": cls.FONTE,
            "versao": cls.VERSAO, "tipo": "acao_controlada",
            "acao": com["acao"], "estrategia": com["estrategia"], "motivo": motivo,
            "necessidade_prioritaria": copy.deepcopy(prioridades.get("selecionada")),
            "aprendizado_considerado": copy.deepcopy(aprendizado_anterior),
            "llc": {
                "politica": cls.POLITICA, "sinal_valido": sinal is not None,
                "decisao_sem_aprendizado": sem, "decisao_com_aprendizado": com,
                "influencia_decisoria_comprovada": influencia,
                "mudou_escolha": mudou, "causalidade_ambiental_comprovada": False,
            },
            **cls.INVARIANTES, "causalidade_ambiental_comprovada": False,
        }

    @classmethod
    def avaliar_resultado(cls, *, decisao, acao_resultado, resultado_observado):
        if not isinstance(decisao, dict):
            return {"sucesso": False, "estado": "llc2_decisao_invalida",
                    "motivo": "A decisao precisa ser um objeto.", **cls.INVARIANTES,
                    "causalidade_ambiental_comprovada": False}
        if not isinstance(acao_resultado, dict):
            return {"sucesso": False, "estado": "llc2_acao_invalida",
                    "motivo": "O resultado da acao precisa ser um objeto.", **cls.INVARIANTES,
                    "causalidade_ambiental_comprovada": False}
        if not isinstance(resultado_observado, dict):
            return {"sucesso": False, "estado": "llc2_resultado_invalido",
                    "motivo": "O resultado observado precisa ser um objeto.", **cls.INVARIANTES,
                    "causalidade_ambiental_comprovada": False}
        acao = decisao.get("acao")
        acao_sucesso = bool(acao_resultado.get("sucesso"))
        resultado_sucesso = bool(resultado_observado.get("sucesso"))
        if not acao_sucesso or not resultado_sucesso:
            ganho, classificacao = -1.0, "perda_operacional"
        elif acao == "observar_sem_atuar":
            ganho, classificacao = 0.0, "neutro_operacional"
        else:
            ganho, classificacao = 1.0, "ganho_operacional"
        return {
            "sucesso": True, "estado": "feedback_operacional_calculado",
            "origem": cls.FONTE, "versao": cls.VERSAO,
            "ganho_perda_operacional": ganho, "classificacao": classificacao,
            "base": "sucesso_da_acao_e_do_resultado_observado", "acao": acao,
            "acao_sucesso": acao_sucesso, "resultado_sucesso": resultado_sucesso,
            "influencia_decisoria_comprovada": bool(
                (decisao.get("llc") or {}).get("influencia_decisoria_comprovada") is True
            ),
            "causalidade_ambiental_comprovada": False, **cls.INVARIANTES,
        }

    @classmethod
    def _avaliar_contraste(cls, *, observacao, direcao_melhor, tolerancia):
        if not isinstance(observacao, dict):
            return None
        if observacao.get("contrafactual_validado") is not True:
            return None
        if observacao.get("controle_valido") is not True:
            return None
        confundidores = observacao.get("confundidores_detectados", [])
        if not isinstance(confundidores, list) or confundidores:
            return None
        valores = tuple(cls._numero(observacao.get(k)) for k in (
            "intervencao_antes", "intervencao_depois", "controle_antes", "controle_depois"
        ))
        if any(v is None for v in valores):
            return None
        tratamento_antes, tratamento_depois, controle_antes, controle_depois = valores
        delta_tratamento = tratamento_depois - tratamento_antes
        delta_controle = controle_depois - controle_antes
        efeito = delta_tratamento - delta_controle
        melhoria = (
            efeito > tolerancia if direcao_melhor == "maior"
            else efeito < -tolerancia
        )
        return {
            "id": observacao.get("id"),
            "delta_intervencao": delta_tratamento,
            "delta_controle": delta_controle,
            "efeito_contrafactual": efeito,
            "melhoria": bool(melhoria),
            "contrafactual_validado": True,
            "controle_valido": True,
            "confundidores_detectados": [],
        }

    @classmethod
    def avaliar_consequencia_controlada(
        cls, *, decisao, acao_resultado, resultado_observado, metrica, observacoes
    ):
        """Avalia evidencia causal por contraste controlado.

        Exige metrica externa declarada, desenho suportado, controle valido,
        pelo menos 3 contrastes e consistencia da direcao de melhoria.
        """
        erros = []
        for nome, valor in (
            ("decisao", decisao), ("acao_resultado", acao_resultado),
            ("resultado_observado", resultado_observado), ("metrica", metrica),
        ):
            if not isinstance(valor, dict):
                erros.append(f"{nome}_invalido")
        if not isinstance(observacoes, list):
            erros.append("observacoes_invalido")
        if erros:
            return {
                "sucesso": False, "estado": "llc3_entrada_invalida",
                "erros": erros, "desenho_experimental": cls.DESENHO_CAUSAL,
                "evidencia_causal_controlada": False,
                "causalidade_ambiental_comprovada": False, **cls.INVARIANTES,
            }

        influencia = bool(
            (decisao.get("llc") or {}).get("influencia_decisoria_comprovada") is True
        )
        if not influencia:
            erros.append("influencia_decisoria_nao_comprovada")
        if decisao.get("acao") == "observar_sem_atuar":
            erros.append("acao_sem_atuacao_nao_produz_intervencao")
        if acao_resultado.get("acao") != decisao.get("acao"):
            erros.append("acao_resultado_diverge_da_decisao")
        if acao_resultado.get("sucesso") is not True:
            erros.append("acao_nao_sucesso")
        if resultado_observado.get("sucesso") is not True:
            erros.append("resultado_nao_sucesso")

        nome = metrica.get("nome")
        unidade = metrica.get("unidade")
        fonte = metrica.get("fonte")
        direcao = metrica.get("direcao_melhor")
        tolerancia = cls._numero(metrica.get("tolerancia", 0.0))
        desenho = metrica.get("desenho_experimental", cls.DESENHO_CAUSAL)

        if not isinstance(nome, str) or not nome.strip():
            erros.append("metrica_sem_nome")
        if not isinstance(unidade, str) or not unidade.strip():
            erros.append("metrica_sem_unidade")
        if not isinstance(fonte, str) or not fonte.strip():
            erros.append("metrica_sem_fonte")
        if direcao not in {"maior", "menor"}:
            erros.append("direcao_melhor_invalida")
        if tolerancia is None or tolerancia < 0:
            erros.append("tolerancia_invalida")
        if desenho != cls.DESENHO_CAUSAL:
            erros.append("desenho_experimental_nao_suportado")
        if len(observacoes) < 3:
            erros.append("repeticoes_insuficientes")

        contrastes = []
        if not erros:
            for observacao in observacoes:
                contraste = cls._avaliar_contraste(
                    observacao=observacao, direcao_melhor=direcao, tolerancia=tolerancia
                )
                if contraste is None:
                    erros.append("contraste_invalido")
                else:
                    contrastes.append(contraste)

        efeitos = [float(item["efeito_contrafactual"]) for item in contrastes]
        efeito_medio = sum(efeitos) / len(efeitos) if efeitos else None
        todas_melhoraram = bool(contrastes) and all(item["melhoria"] for item in contrastes)
        consistente = bool(
            contrastes and efeito_medio is not None and all(
                efeito > tolerancia if direcao == "maior" else efeito < -tolerancia
                for efeito in efeitos
            )
        )
        evidencia = bool(not erros and len(contrastes) >= 3 and todas_melhoraram and consistente)

        return {
            "sucesso": True,
            "estado": "evidencia_causal_controlada" if evidencia else "evidencia_causal_inconclusiva",
            "origem": cls.FONTE, "versao": cls.VERSAO,
            "desenho_experimental": cls.DESENHO_CAUSAL,
            "metrica": {
                "nome": nome, "unidade": unidade, "fonte": fonte,
                "direcao_melhor": direcao, "tolerancia": tolerancia,
            },
            "repeticoes": len(contrastes), "contrastes": contrastes,
            "efeito_medio_contrafactual": efeito_medio,
            "todas_melhoraram": todas_melhoraram,
            "consistencia": consistente, "erros": erros,
            "evidencia_causal_controlada": evidencia,
            "causalidade_ambiental_comprovada": evidencia,
            "observacao_critica": (
                "Evidencia causal valida dentro do protocolo declarado; "
                "nao constitui prova universal fora do desenho experimental."
            ),
            **cls.INVARIANTES,
        }

    @classmethod
    def fechar_transicao(
        cls, *, aprendizado_anterior, decisao, acao_resultado,
        resultado_observado, avaliacao, aprendizado_novo, evidencia_causal=None
    ):
        feedback = avaliacao.get("llc2") if isinstance(avaliacao, dict) else None
        if not isinstance(feedback, dict):
            feedback = {}
        novo_valor = aprendizado_novo.get("valor") if isinstance(aprendizado_novo, dict) else None
        novo_id = novo_valor.get("id") if isinstance(novo_valor, dict) else None
        anterior_id = aprendizado_anterior.get("aprendizado_id") if isinstance(aprendizado_anterior, dict) else None
        comprovada = bool(
            isinstance(evidencia_causal, dict)
            and evidencia_causal.get("causalidade_ambiental_comprovada") is True
        )
        return {
            "versao": cls.VERSAO,
            "estado": "transicao_llc3_fechada" if evidencia_causal is not None else "transicao_llc2_fechada",
            "aprendizado_anterior_id": anterior_id,
            "decisao": {
                "acao": decisao.get("acao"), "estrategia": decisao.get("estrategia"),
                "influencia_decisoria_comprovada": bool(
                    (decisao.get("llc") or {}).get("influencia_decisoria_comprovada") is True
                ),
                "mudou_escolha": bool((decisao.get("llc") or {}).get("mudou_escolha") is True),
            },
            "acao": copy.deepcopy(acao_resultado),
            "resultado": copy.deepcopy(resultado_observado),
            "feedback_operacional": copy.deepcopy(feedback),
            "avaliacao": copy.deepcopy(avaliacao),
            "evidencia_causal": copy.deepcopy(evidencia_causal),
            "aprendizado_novo_id": novo_id,
            "ciclo_fechado": True,
            "causalidade_ambiental_comprovada": comprovada,
            **cls.INVARIANTES,
        }

    @classmethod
    def contexto(cls):
        return {
            "sucesso": True, "estado": "llc_disponivel",
            "origem": cls.FONTE, "versao": cls.VERSAO,
            "politica": cls.POLITICA, "feedback_operacional": True,
            "transicao_completa": True, "protocolo_causal_controlado": True,
            "alternativas": [copy.deepcopy(item) for item in cls.CANDIDATAS],
            "execucao_de_acao": False, "treinamento_automatico": False,
            "implantacao_automatica": False, "influencia_decisoria": True,
            "causalidade_ambiental": False,
            "invariantes": {
                **copy.deepcopy(cls.INVARIANTES),
                "causalidade_ambiental_comprovada": False,
            },
        }


__all__ = ["LearningLoopCausalNixal"]
