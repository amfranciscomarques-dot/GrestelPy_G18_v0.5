"""
Módulo: engine/statements/dr.py — Demonstração de Resultados Consolidada (2024-2029)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Este módulo constrói a Demonstração de Resultados (DR), que evidencia:
  - Receita de vendas (produto e mercadorias)
  - Custos operacionais (CMVMC, Pessoal, FSE)
  - Resultados operacionais (EBIT = EBITDA - Depreciação)
  - Resultados financeiros (juros, subsídios, outros rendimentos)
  - Resultado antes e depois de impostos (RAI, Resultado Líquido)

ESTRUTURA DA DR (Fluxo de Cálculo):
  1. RECEITAS OPERACIONAIS:
     - Vendas Produtos: calculadas por produto com crescimento volume × crescimento preço
     - Vendas Mercadorias: vendidas a margens definidas por categoria

  2. CUSTOS OPERACIONAIS:
     - CMVMC (Custo de Mercadorias Vendidas e Matérias-Primas): % da receita
     - Pessoal: base + crescimento de headcount
     - FSE (Fornecimentos e Serviços Externos): base + crescimento e detalhe por rubrica
     - Depreciação: do plano plurianual de investimento
     - Imparidades: 0,5% dos saldos de clientes (estimativa de crédito duvidoso)

  3. RESULTADOS OPERACIONAIS:
     - EBITDA = Receita - CMVMC - Pessoal - FSE
     - EBIT = EBITDA - Depreciação

  4. RESULTADOS FINANCEIROS:
     - Juros (carga financeira): do plano de financiamento
     - Subsídios: se houver (ex: Hub Logístico)
     - Outros Rendimentos: cedência de pessoal, equivalência patrimonial, câmbio

  5. RESULTADO ANTES DE IMPOSTOS (RAI):
     - RAI = EBIT + (Juros) + (Outros Rendimentos) + (Outros Gastos) + (Imparidades)

  6. IMPOSTO SOBRE RENDIMENTO (IRC):
     - ICE (art. 41.º-A EBF): dedução à matéria coletável (~342k€ em 2024, cresce 3%/ano)
     - Taxa geral: 21% (2024) / 20% (2025+) — Grestel é grande empresa
     - Derrama Municipal: 1,5%
     - Derrama Estadual: 3% se lucro tributável > 1,5M€
     - SIFIDE II (CFI): crédito 380k€ em 2025 (ANI) + ~130k€/ano a partir de 2026
     - Tributação Autónoma (art. 88.º CIRC): ~22k€ em 2024, indexado 3%/ano

  7. RESULTADO LÍQUIDO:
     - = RAI - IRC

LÓGICA FINANCEIRA CRÍTICA:
  - 2024: dados reais (input de Base2024), não projetado
  - 2025: período PARCIAL (janeiro-setembro, 9 meses) — vendas/custos escalados 9/12
  - 2026-2029: períodos completos (12 meses)
  - Crescimentos cumulativos aplicados ano a ano
  - Imparidades crescem com saldo de clientes (indica risco de crédito)
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS, YEARS
from ..operacional import vendas
from ..operacional import fse
from ..operacional import pessoal
from ..investimento import investimento
from ..financiamento import financiamento
from ..operacional import cmvmc
from ..operacional import clientes as conta_clientes
from ..operacional import inventarios
from ..projetos import ecogres as ecogres_mod


def _get_dr_2024_value(base: Base2024, key: str, default: float = 0.0) -> float:
    """Lê uma rubrica da DR real 2024 a partir de base.raw, com fallback."""
    try:
        return float(base.raw["dr_2024_real"][key])
    except (AttributeError, KeyError, TypeError, ValueError):
        return float(default)


def _load_hub_dr(a: Assumptions) -> dict[int, dict] | None:
    """Carrega os impactos do Hub na DR, ou None se o Hub estiver desativado."""
    try:
        hub_raw = a.raw.get("hub_logistico", {})
        if not hub_raw.get("incluir_hub", False):
            return None

        from ..projetos import hub_logistico as hub_mod

        return hub_mod.hub_dr_impact(hub_raw)
    except Exception:
        return None


def _load_ecogres() -> dict | None:
    """Carrega os pressupostos da Ecogres apenas se ativa."""
    try:
        eco = ecogres_mod.load()
        if not eco or not eco.get("incluir_ecogres", False):
            return None
        return eco
    except Exception:
        return None


def _outros_rendimentos(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_inv: pd.DataFrame | None = None,
    hub_dr: dict[int, dict] | None = None,
    eco: dict | None = None,
) -> tuple[dict, dict]:
    """
    Calcula Outros Rendimentos e Ganhos (receitas não operacionais).

    COMPONENTES:
      1. Cedência de Locações: aluguel de imóveis/espaços físicos (receita passiva)
      2. Cedência de Pessoal: faturação de funcionários cedidos a terceiros
      3. Equivalência Patrimonial: resultado proporcional de associadas/joint ventures
      4. Subsídios e Contribuições: Gov., programas (investimento, R&D, emprego)
      5. Ganhos de Câmbio: variações cambiais (se transações em moeda estrangeira)
      6. Subsídio Hub: se Hub Logístico ativo (subsídio específico)

    LÓGICA TEMPORAL:
      - 2024: usa valor real (input base.outros_rendimentos)
      - 2025: mescla componentes: cedências + equivalência + subsídios gov.
      - 2026-2029: crescimento estruturado (cedências sobem com inflação,
                    equivalência com investimento, subsídios estáveis)

    CRESCIMENTO (Plurianual):
      - Cedências: crescimento moderado (2,5% a 2,5%, depende de pressupostos)
      - Equivalência: depende de resultado investido em associadas
      - Subsídios: assumem constância (Gov. mantém programas)

    RETORNA:
      - (res, breakdown): dict anual + dict com detalhe por componente
        Permite rastreabilidade de origem de cada rendimento
    """
    ab = sched.plurianual_AB

    g = [
        ab.get("AB74", 0.02),
        ab.get("AB84", 0.025),
        ab.get("AB93", 0.025),
        ab.get("AB94", 0.025),
    ]

    outros_rend_2024 = _get_dr_2024_value(base, "outros_rend", 0.0)

    if df_inv is not None:
        req_2025 = float(
            df_inv[df_inv.ano == 2025]["rend_equiv_patrimonial"].iloc[0]
        )
    else:
        req_2025 = sched.investimento["rend_equiv_patrimonial"][2025]

    if eco is not None:
        df_ced = ecogres_mod.cedencia_pessoal_anual(eco)
        cedencia_map = dict(zip(df_ced["ano"], df_ced["cedencia_pessoal"]))
    else:
        cedencia_map = {y: 0.0 for y in ALL_YEARS}

    ced_pessoal_2025 = cedencia_map.get(2025, 0.0)
    ced_pessoal_2024 = cedencia_map.get(2024, 0.0)

    cedencia_loc_base = (
        base.outros_rendimentos["Cedencia_locacoes"]
        - ced_pessoal_2024
    )

    subs_cambio_base = (
        base.outros_rendimentos["Subs_Investimento"]
        + base.outros_rendimentos["Subs_Exploracao"]
        + float(base.outros_rendimentos.get("Cambio_Outros_base", 0.0))
    )

    hub_subsidio_2025 = (
        hub_dr[2025].get("outros_rend_subsidio", 0.0)
        if hub_dr
        else 0.0
    )

    base_2025 = (
        cedencia_loc_base
        + ced_pessoal_2025
        + req_2025
        + subs_cambio_base
        + hub_subsidio_2025
    )

    res = {
        2024: outros_rend_2024,
        2025: base_2025,
    }

    base_loc_subs = cedencia_loc_base + subs_cambio_base
    frac_loc = cedencia_loc_base / base_loc_subs if base_loc_subs > 0 else 0.5

    equiv_2024 = base.outros_rendimentos["Equivalencia_patrimonial"]
    ced_loc_2024 = cedencia_loc_base

    subs_2024 = (
        outros_rend_2024
        - ced_loc_2024
        - ced_pessoal_2024
        - equiv_2024
    )

    breakdown: dict[int, dict] = {
        2024: {
            "outros_rend_ced_loc": ced_loc_2024,
            "outros_rend_ced_pessoal": ced_pessoal_2024,
            "outros_rend_equiv_patr": equiv_2024,
            "outros_rend_subs_cambio": subs_2024,
        },
        2025: {
            "outros_rend_ced_loc": cedencia_loc_base,
            "outros_rend_ced_pessoal": ced_pessoal_2025,
            "outros_rend_equiv_patr": req_2025,
            "outros_rend_subs_cambio": subs_cambio_base + hub_subsidio_2025,
        },
    }

    if df_inv is not None:
        base_no_req_ced = (
            base_2025
            - req_2025
            - hub_subsidio_2025
            - ced_pessoal_2025
        )

        for i, y in enumerate(YEARS[1:]):
            req_y = float(
                df_inv[df_inv.ano == y]["rend_equiv_patrimonial"].iloc[0]
            )
            ced_p_y = cedencia_map.get(y, 0.0)

            hub_sub_y = (
                hub_dr[y].get("outros_rend_subsidio", 0.0)
                if hub_dr and y in hub_dr
                else 0.0
            )

            grown = base_no_req_ced * (1 + g[i]) ** (i + 1)

            res[y] = grown + req_y + ced_p_y + hub_sub_y

            breakdown[y] = {
                "outros_rend_ced_loc": grown * frac_loc,
                "outros_rend_ced_pessoal": ced_p_y,
                "outros_rend_equiv_patr": req_y,
                "outros_rend_subs_cambio": grown * (1 - frac_loc) + hub_sub_y,
            }
    else:
        cur = base_2025 - ced_pessoal_2025 - hub_subsidio_2025

        for i, y in enumerate(YEARS[1:]):
            ced_p_y = cedencia_map.get(y, 0.0)

            hub_sub_y = (
                hub_dr[y].get("outros_rend_subsidio", 0.0)
                if hub_dr and y in hub_dr
                else 0.0
            )

            cur = cur * (1 + g[i])

            res[y] = cur + ced_p_y + hub_sub_y

            breakdown[y] = {
                "outros_rend_ced_loc": cur * frac_loc,
                "outros_rend_ced_pessoal": ced_p_y,
                "outros_rend_equiv_patr": cur * (1 - frac_loc),
                "outros_rend_subs_cambio": hub_sub_y,
            }

    return res, breakdown


def _outros_gastos(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> dict:
    """Outros gastos e perdas — crescem com inflação/pressupostos plurianuais."""
    ab = sched.plurianual_AB

    inflacao_raw = a.macro.get("inflacao", {})

    if isinstance(inflacao_raw, dict):
        inflacao = inflacao_raw.get(
            2025,
            inflacao_raw.get("anual", {}).get(2025, a.inflacao_anual(2025)),
        )
    else:
        inflacao = 0.023

    val_2024 = _get_dr_2024_value(base, "outros_gastos", 0.0)
    val_2025 = val_2024 * (1 + inflacao)

    res = {
        2024: val_2024,
        2025: val_2025,
    }

    g = [
        ab.get("AB68", 0.05),
        ab.get("AB84", 0.025),
        ab.get("AB93", 0.025),
        ab.get("AB94", 0.025),
    ]

    cur = val_2025

    for i, y in enumerate(YEARS[1:]):
        cur = cur * (1 + g[i])
        res[y] = cur

    return res


def _imparidades(
    df_clientes: pd.DataFrame,
    base: Base2024,
) -> dict:
    """
    Calcula Imparidades de Clientes (Provisão para Crédito Duvidoso).

    CONCEITO CONTABILÍSTICO (IAS 39 / IFRS 9):
      Uma imparidade é uma redução de valor estimada para cobrir o risco de
      que clientes não paguem as suas dívidas. É uma provisão prudencial.

    METODOLOGIA (Abordagem Simplificada):
      - Imparidade = 0,5% do saldo de clientes em carteira
      - Presunção: em cada €1.000 de crédito, ~€5 é cobrado como perda
      - Conservadora: % fixo não diferencia por risco (simplifica, mantém prudência)

    EVOLUÇÃO TEMPORAL:
      - 2024: usa valor real de imparidades (input)
      - 2025-2029: evolui com saldo de clientes projetado
      - Crescimento de clientes → crescimento de imparidades (risco proporcional)

    IMPACTO NA DR:
      - Linha de "Imparidades" (negativa): reduz resultado operacional
      - Efeito: reduz lucro antes de impostos (RAI)
      - Racional: contingência prudencial para riscos de cobrança

    EXEMPLO:
      Saldo de Clientes em 2025: €5.000.000
      Imparidade = €5.000.000 × 0,5% = €25.000 (provisão para perdas estimadas)
    """
    imparidades_2024 = _get_dr_2024_value(base, "imparidades", 0.0)

    res = {
        2024: imparidades_2024,
    }

    # Calcula imparidades para cada ano baseadas no saldo de clientes
    for _, r in df_clientes.iterrows():
        if r["ano"] >= 2025:
            res[r["ano"]] = r["saldo_clientes"] * 0.005

    return res


def _irc(
    rai: dict,
    a: Assumptions,
    base: Base2024,
) -> dict:
    """
    Calcula o IRC (Imposto sobre o Rendimento das Pessoas Coletivas).

    SEQUÊNCIA DE CÁLCULO (por ano de projeção):
      1. ICE — Incentivo à Capitalização das Empresas (art. 41.º-A EBF):
         Dedução à matéria coletável = ICE_valor_base × (1 + g)^(ano-2024).
         Reduz o lucro tributável antes de aplicar qualquer taxa.

      2. COLETA BASE (sobre lucro tributável = RAI − ICE):
         - Taxa geral (Grestel = grande empresa → aplica-se desde o 1.º euro)
         - Derrama Municipal: 1,5% sobre lucro tributável
         - Derrama Estadual: 3% sobre a parcela acima de €1,5M
         - Deduções fiscais (standard)

      3. SIFIDE II — crédito de imposto (art. 35.º do CFI):
         Deduzido à coleta calculada em (2).
         Inclui crédito pontual (pendente ANI) e crédito recorrente (I&D anual).
         Nunca reduz a coleta abaixo de zero.

      4. TRIBUTAÇÃO AUTÓNOMA (art. 88.º CIRC):
         Acrescida ao IRC final. Incide sobre despesas não dedutíveis
         (viaturas, representação). Valor base 2024 indexado à inflação.

    Nota: 2024 é lido do histórico auditado (taxa efetiva real = 8%).
    """
    irc_2024 = _get_dr_2024_value(base, "irc", 0.0)
    res = {2024: irc_2024}

    imp = a.impostos
    taxa_geral_ano  = imp.get("IRC_taxa_geral_ano", {})
    taxa_red_ano    = imp.get("IRC_taxa_reduzida_ano", {})
    der_est         = imp.get("Derrama_Estadual", 0.03)
    der_est_limiar  = imp.get("Derrama_Estadual_limiar", 1_500_000)

    # ICE
    ice_base = float(imp.get("ICE_valor_base", 0.0))
    ice_g    = float(imp.get("ICE_taxa_crescimento", 0.03))

    # SIFIDE II
    sifide_credito_ano = {int(k): float(v) for k, v in imp.get("SIFIDE_credito_coleta_ano", {}).items()}
    sifide_despesas    = float(imp.get("SIFIDE_despesas_anuais", 0.0))
    sifide_taxa        = float(imp.get("SIFIDE_taxa_credito", 0.325))
    sifide_recorrente  = int(imp.get("SIFIDE_ano_inicio_recorrente", 9999))

    # Tributação Autónoma
    ta_base = float(imp.get("Tributacao_Autonoma_valor_2024", 0.0))
    ta_g    = float(imp.get("Tributacao_Autonoma_crescimento", 0.03))

    for y, r in rai.items():
        if y == 2024 or r is None:
            continue

        taxa_geral = taxa_geral_ano.get(y, imp["IRC_taxa_geral"])
        taxa_red   = taxa_red_ano.get(y, imp["IRC_taxa_reduzida"])

        # 1. ICE: dedução à matéria coletável
        ice_ded = ice_base * (1.0 + ice_g) ** (y - 2024) if ice_base > 0 else 0.0
        r_tributavel = max(0.0, r - ice_ded)

        # 2. Coleta base sobre lucro tributável
        coleta = max(
            0.0,
            min(r_tributavel, 50_000) * taxa_red
            + max(0.0, r_tributavel - 50_000) * taxa_geral
            + r_tributavel * imp["Derrama_Municipal"]
            + max(0.0, r_tributavel - der_est_limiar) * der_est
            - imp["Deducoes_Fiscais"],
        )

        # 3. SIFIDE II: crédito pontual + crédito recorrente
        sifide_c = float(sifide_credito_ano.get(y, 0.0))
        if sifide_despesas > 0 and y >= sifide_recorrente:
            sifide_c += sifide_despesas * sifide_taxa
        coleta = max(0.0, coleta - sifide_c)

        # 4. Tributação autónoma (acrescenta ao IRC final)
        ta = ta_base * (1.0 + ta_g) ** (y - 2024) if ta_base > 0 else 0.0

        res[y] = coleta + ta

    return res


def build_dr(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_prod: "pd.DataFrame | None" = None,
    df_merc: "pd.DataFrame | None" = None,
    df_total: "pd.DataFrame | None" = None,
) -> pd.DataFrame:
    """
    Constrói a Demonstração de Resultados Completa (2024-2029).

    FLUXO INTERNO (11 etapas sequenciais):
      1. Calcula vendas anuais: produtos + mercadorias → receita bruta
      2. Calcula FSE (custos operacionais): base + crescimento, detalha por rubrica
      3. Calcula pessoal: salários, contribuições sociais
      4. Calcula depreciação: do plano de investimento
      5. Calcula financiamento: juros e encargos da dívida
      6. Calcula CMVMC: custo de mercadorias e matérias primas (% da receita)
      7. Calcula inventário: variação do stock (acréscimo ou libertação de caixa)
      8. Calcula clientes: saldos a receber (para imparidades)
      9. Calcula outros rendimentos: equivalência patrimonial, cedência pessoal, subsídios
     10. Calcula outros gastos: gastos não operacionais
     11. Calcula impostos (IRC): taxa progressiva + derramas

    SAÍDA:
      DataFrame com 40+ colunas:
        - receitas: vn (vendas líquidas)
        - custos operacionais: cmvmc, fse (detalhe por rubrica), pessoal, imparidades
        - resultados operacionais: ebitda, ebit
        - resultados financeiros: juros, subsídios, outros_rend
        - resultado antes/depois impostos: rai, irc, resultado_liquido

    PRINCÍPIOS CONTABILÍSTICOS RESPEITADOS:
      - Acuidade: reconhecimento de receita ao momento da venda
      - Prudência: imparidades de clientes (0,5% do saldo) e riscos
      - Consistência: mesmos pressupostos ano a ano, com crescimentos aplicados
      - Materialidade: omissão de rubricas imateriais (rounding a 0,01€)
    """
    # ===== ETAPA 1: CÁLCULO DE VENDAS ANUAIS =====
    if df_prod is None:
        df_prod = vendas.vendas_anuais(a, base, sched)
    if df_merc is None:
        df_merc = vendas.vendas_mercadorias_anuais(a, base)
    if df_total is None:
        df_total = vendas.resumo_anual(df_prod, df_merc)

    # FATOR DE ESCALA 2025: O ano 2025 tem apenas 9 meses (jan-set)
    # Logo, o crescimento de vendas de 2024 para 2025 é reduzido proporcionalmente
    # Este factor é usado para escalar FSE, pessoal, etc. para o período parcial
    vn_2024 = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])
    factor_2025 = vn_2025 / vn_2024 if vn_2024 else 1.0

    # ===== ETAPA 2: CÁLCULO DE FSE (Fornecimentos e Serviços Externos) =====
    # FSE: custos operacionais variáveis (eletricidade, água, comunicações, limpeza, etc.)
    # Cresce com base + crescimento definido em assumptions (redução custo, eficiência, etc.)
    # O factor_2025 ajusta para o período parcial (9 meses)
    df_fse = fse.fse_anual(a, base, factor_2025)

    # FSE DETALHADO: desagregação por rubrica (categoria)
    # Necessário para dashboard/reporting detalhado (ex: eletricidade, gás, comunicações)
    # Cada rubrica cresce independentemente (modelo não agregado)
    df_fse_det = fse.fse_detalhe_anual(a, base, factor_2025)
    fse_det_by_year: dict[int, dict[str, float]] = {}
    for _, r in df_fse_det.iterrows():
        y = int(r["ano"])
        rub = str(r["rubrica"])
        fse_det_by_year.setdefault(y, {})[rub] = float(r["valor"])

    fse_cols_by_rubrica = fse.FSE_DETALHE_KEYS

    # RECONCILIAÇÃO FSE: as rubricas detalhadas devem somar exatamente o total
    # Este bloco aplica um factor de escala para garantir fechamento (evita rounding errors)
    for y in ALL_YEARS:
        total_fse_y = float(df_fse[df_fse.ano == y]["fse"].iloc[0]) if not df_fse.empty else 0.0
        rub_sum = sum(
            float(fse_det_by_year.get(y, {}).get(rub, 0.0))
            for rub in fse_cols_by_rubrica.keys()
        )
        if rub_sum > 0:
            scale = total_fse_y / rub_sum
            for rub in fse_cols_by_rubrica.keys():
                fse_det_by_year.setdefault(y, {})[rub] = float(
                    fse_det_by_year.get(y, {}).get(rub, 0.0) * scale
                )

    # ===== ETAPA 3: CÁLCULO DE PESSOAL =====
    # Gastos com pessoal: salários, contribuições patronais, impostos sobre remunerações
    # Cresce com inflação + crescimento de headcount (evolução de efectivos)
    df_pessoal = pessoal.pessoal_anual(a, base, df_total)

    # ===== ETAPA 4: CÁLCULO DE DEPRECIAÇÃO =====
    # Depreciação: redução de valor dos ativos imobilizados (máquinas, instalações, software)
    # Segue o plano de investimento (entradas e saídas de ativos)
    df_inv = investimento.investimento_anual(a, base, sched, df_vn=df_total)

    # ===== ETAPA 5: CÁLCULO DE FINANCIAMENTO =====
    # Juros e encargos de dívida: capital emprestado ao banco × taxa de juro
    # Decresce com amortizações do empréstimo
    df_fin = financiamento.financiamento_anual(sched, a)

    # ===== ETAPA 6: CÁLCULO DE CMVMC =====
    # CMVMC: Custo de Mercadorias Vendidas e Matérias-Primas Consumidas
    # Inclui: custo direto de produto vendido + consumo de matérias-primas
    # Expressa como % da receita (margem bruta = receita - CMVMC)
    df_cmvmc = cmvmc.cmvmc_anual(a, base, df_prod, df_merc)

    # ===== ETAPA 7: CÁLCULO DE INVENTÁRIO =====
    # Inventário (Stock): quantidade de mercadorias em armazém
    # Variação do inventário: acréscimo (caixa negativa) ou venda (caixa positiva)
    # Na DR: variação de inventários = -ΔStock (se stock sobe, caixa desce)
    df_inv_st = inventarios.inventarios_anual(a, base, df_cmvmc)

    # ===== ETAPA 8: CÁLCULO DE CLIENTES =====
    # Saldo de Clientes (Contas a Receber): crédito concedido aos clientes
    # Base para cálculo de imparidades (0,5% de crédito duvidoso estimado)
    df_cli = conta_clientes.clientes_anual(a, base, df_total)

    # ===== ETAPA 9: CARREGAMENTO DE SUBSIDIÁRIAS (Opcional) =====
    # Hub Logístico M6: se ativo, contribui com rendimentos (subsídios) e custos (pessoal, FSE)
    hub_dr = _load_hub_dr(a)

    # Ecogres: se ativa, afeta CMVMC (redução, maior eficiência) e pessoal (cedência)
    eco = _load_ecogres()

    if eco is not None:
        # Subcontratação Ecogres: redução de CMVMC (outsourcing de produção)
        df_subc = ecogres_mod.subcontratacao_anual(eco)
        subc_map = dict(zip(df_subc["ano"], df_subc["subcontratacao_ecogres"]))

        # Redução de CMVMC pela eficiência de Ecogres
        eco_mpsc_red = ecogres_mod.reducao_mpsc(eco)
    else:
        subc_map = {y: 0.0 for y in ALL_YEARS}
        eco_mpsc_red = {y: 0.0 for y in ALL_YEARS}

    # ===== ETAPA 10: CÁLCULO DE OUTROS RENDIMENTOS =====
    # Outros Rendimentos: receitas não operacionais
    #   - Equivalência Patrimonial: resultado de participações em associadas
    #   - Cedência de Pessoal: faturação de pessoal cedido a terceiros
    #   - Subsídios (Gov./Programas): investimento, exploração, investigação
    #   - Ganhos de câmbio: variações cambiais (se ativo em moeda estrangeira)
    outros_rend, outros_rend_bk = _outros_rendimentos(
        a,
        base,
        sched,
        df_inv,
        hub_dr,
        eco,
    )

    # ===== ETAPA 11: CÁLCULO DE IMPOSTOS E GASTOS EXTRAORDINÁRIOS =====
    # Outros Gastos: despesas não operacionais (ajustes, perdas, penalidades)
    outros_gastos = _outros_gastos(a, base, sched)

    # Imparidades: provisões para crédito duvidoso (estimativa contabilística de risco)
    # Calculadas como % do saldo de clientes (0,5% standard)
    imparidades = _imparidades(df_cli, base)

    rows = []
    rai_dict = {}

    r24 = base.raw["dr_2024_real"]

    rai_dict[2024] = r24["rai"]
    bk24 = outros_rend_bk[2024]

    rows.append(
        {
            "ano": 2024,
            "vn": r24["vn"],
            "var_inventarios": r24["var_inventarios"],
            "outros_rend": r24["outros_rend"],
            "cmvmc": -r24["cmvmc"],
            "fse": -r24["fse"],
            # detalhe FSE por rubrica (custos negativos na DR)
            **{
                fse_cols_by_rubrica[rub]: -fse_det_by_year.get(2024, {}).get(rub, 0.0)
                for rub in fse_cols_by_rubrica.keys()
            },
            "gastos_pessoal": -r24["gastos_pessoal"],
            "imparidades": -r24["imparidades"],
            "outros_gastos": -r24["outros_gastos"],
            "ebitda": r24["ebitda"],
            "depreciacoes": -r24["depreciacoes"],
            "ebit": r24["ebit"],
            "juros": -r24["juros"],
            "rend_financeiros": r24["rend_financeiros"],
            "rai": r24["rai"],
            "irc": -r24["irc"],
            "rl": r24["rl"],
            "hub_pessoal_reducao": 0.0,
            "hub_fse_reducao": 0.0,
            "hub_cmvmc_reducao": 0.0,
            "hub_fse_opex": 0.0,
            "hub_vn_incremental": 0.0,
            "hub_cmvmc_incremental": 0.0,
            "hub_outros_rend_subsidio": 0.0,
            "fse_subcontratacao_ecogres": subc_map.get(2024, 0.0),
            "ecogres_reducao_mpsc": 0.0,
            "outros_rend_ced_loc": bk24["outros_rend_ced_loc"],
            "outros_rend_ced_pessoal": bk24["outros_rend_ced_pessoal"],
            "outros_rend_equiv_patr": bk24["outros_rend_equiv_patr"],
            "outros_rend_subs_cambio": bk24["outros_rend_subs_cambio"],
        }
    )

    for y in YEARS:
        vn = float(df_total[df_total.ano == y]["vn_total"].iloc[0])
        f_base = float(df_fse[df_fse.ano == y]["fse"].iloc[0])
        p_base = float(
            df_pessoal[df_pessoal.ano == y]["gastos_pessoal"].iloc[0]
        )
        c_base = float(df_cmvmc[df_cmvmc.ano == y]["cmvmc"].iloc[0])
        d = float(df_inv[df_inv.ano == y]["total_dep_amort"].iloc[0])
        j = float(df_fin[df_fin.ano == y]["juros_total"].iloc[0])

        inv_ef = float(df_inv_st[df_inv_st.ano == y]["inventarios"].iloc[0])
        inv_ei = float(df_inv_st[df_inv_st.ano == y - 1]["inventarios"].iloc[0])
        var_inv = inv_ef - inv_ei

        out_rend = outros_rend[y]
        out_gast = outros_gastos[y]
        imp = imparidades.get(y, 0.0)

        rend_fin = float(base.outros_rendimentos.get("Rendimentos_Financeiros", 60_000))

        ecogres_subc = subc_map.get(y, 0.0)

        c_adj = c_base + ecogres_subc
        f_adj = f_base - ecogres_subc

        hub_pessoal_red = 0.0
        hub_fse_red = 0.0
        hub_cmvmc_red = 0.0
        hub_fse_opex = 0.0
        hub_vn_inc = 0.0
        hub_cmvmc_inc = 0.0
        hub_outros_rend = 0.0

        if hub_dr and y in hub_dr:
            h = hub_dr[y]
            hub_pessoal_red = h.get("pessoal_reducao", 0.0)
            hub_fse_red = h.get("fse_reducao", 0.0)
            hub_cmvmc_red = h.get("cmvmc_reducao", 0.0)
            hub_fse_opex = h.get("fse_opex_hub", 0.0)
            hub_vn_inc = h.get("vn_incremental", 0.0)
            hub_cmvmc_inc = h.get("cmvmc_incremental", 0.0)
            hub_outros_rend = h.get("outros_rend_subsidio", 0.0)

        vn = vn + hub_vn_inc
        out_rend = out_rend + hub_outros_rend
        p = p_base - hub_pessoal_red
        f = f_adj - hub_fse_red + hub_fse_opex
        c = c_adj - hub_cmvmc_red - eco_mpsc_red.get(y, 0.0) + hub_cmvmc_inc

        ebitda = vn + var_inv + out_rend - c - f - p - imp - out_gast
        ebit = ebitda - d
        rai = ebit - j + rend_fin

        rai_dict[y] = rai
        bky = outros_rend_bk[y]

        rows.append(
            {
                "ano": y,
                "vn": vn,
                "var_inventarios": var_inv,
                "outros_rend": out_rend,
                "cmvmc": -c,
                "fse": -f,
                # detalhe FSE por rubrica (custos negativos na DR)
                **{
                    fse_cols_by_rubrica[rub]: -fse_det_by_year.get(y, {}).get(rub, 0.0)
                    for rub in fse_cols_by_rubrica.keys()
                },
                "gastos_pessoal": -p,
                "imparidades": -imp,
                "outros_gastos": -out_gast,
                "ebitda": ebitda,
                "depreciacoes": -d,
                "ebit": ebit,
                "juros": -j,
                "rend_financeiros": rend_fin,
                "rai": rai,
                "hub_pessoal_reducao": hub_pessoal_red,
                "hub_fse_reducao": hub_fse_red,
                "hub_cmvmc_reducao": hub_cmvmc_red,
                "hub_fse_opex": hub_fse_opex,
                "hub_vn_incremental": hub_vn_inc,
                "hub_cmvmc_incremental": hub_cmvmc_inc,
                "hub_outros_rend_subsidio": hub_outros_rend,
                "fse_subcontratacao_ecogres": ecogres_subc,
                "ecogres_reducao_mpsc": eco_mpsc_red.get(y, 0.0),
                "outros_rend_ced_loc": bky["outros_rend_ced_loc"],
                "outros_rend_ced_pessoal": bky["outros_rend_ced_pessoal"],
                "outros_rend_equiv_patr": bky["outros_rend_equiv_patr"],
                "outros_rend_subs_cambio": bky["outros_rend_subs_cambio"],
            }
        )

    irc = _irc(rai_dict, a, base)

    for r in rows:
        if r["ano"] != 2024:
            r["irc"] = -irc.get(r["ano"], 0.0)
            r["rl"] = r["rai"] + r["irc"]

    return pd.DataFrame(rows)
