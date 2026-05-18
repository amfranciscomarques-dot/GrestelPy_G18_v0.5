"""Costa Nova Logistics Hub 4.0 — Projeto M6.

Hub logístico automatizado (ZI Vagos, Lotes 77-85) com AMR, VLM, Cobots Vision AI,
WMS integrado e Digital Twin.

Funções exportadas:
  load()                      — carrega m6_hub_assumptions.yaml
  hub_capex(hub)              — CAPEX schedule, AFT rolling e juros capitalizados (NCRF 10)
  hub_financing(hub)          — empréstimo bancário + amortizações + juros (expensed vs. capitalizados)
  hub_nfm(hub)                — ΔNFM anual do hub (stock + clientes − fornecedores)
  hub_rfai(hub)               — crédito fiscal RFAI anual (CFI art. 22.º-23.º)
  hub_dr_impact(hub)          — impacto per-line no DR da Grestel (anual, 2025-2029)
  hub_dfc_impact(hub)         — impacto nos fluxos de caixa consolidados da Grestel
  hub_fcf(hub)                — FCF livre unlevered (FCFF) para análise VAL/TIR
  mapa_servico_divida(hub)    — debt service schedule anual com DSCR do hub
  mapa_tesouraria_mensal(hub) — desdobramento mensal 2025-2026 (base M6/M3)
  viabilidade_hub(hub)        — VAL, TIR, Payback, Índice de Rendibilidade, Valor Residual
  ponto_critico_hub(driver)   — ponto crítico (break-even NPV=0) por driver
  tornado_hub(hub)            — análise de sensibilidade tornado do VAL

Notas metodológicas:
  • FCF livre = FCFF (Free Cash Flow to the Firm) — unlevered, para desconto ao WACC
  • Juros de carência (2025-2027) excluídos do FCFF; capturados na DFC consolidada
  • Juros 2025 capitalizados no AFT (NCRF 10) — aumentam base depreciável, não DR
  • ΔNFM incluído no FCFF: saída de caixa real que não transita pela DR
  • Base mensal disponível em mapa_tesouraria_mensal() para análise de liquidez M6
"""

from __future__ import annotations

import copy
from typing import Sequence

import pandas as pd
import yaml
from pathlib import Path

from ..inputs import DATA_DIR, YEARS


def _hub_assumptions_path() -> Path:
    return DATA_DIR / "subsidiarias" / "hub_logistico" / "m6_hub_assumptions.yaml"


def load() -> dict:
    """Carrega m6_hub_assumptions.yaml."""
    with open(_hub_assumptions_path(), "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# CAPEX e Depreciação por pool de ativo
# ---------------------------------------------------------------------------

def _dep_por_ano(proj: dict, year: int) -> float:
    """Depreciação total de todos os pools num dado ano.

    Cada pool deprecia montante/vida_util por ano, a partir de
    max(ano_inicio_pool, ano_inicio_beneficios) e durante vida_util anos.
    """
    pools = proj["capex"]["pools"]
    ano_inicio_op = int(proj["ano_inicio_beneficios"])
    total = 0.0
    for pool in pools.values():
        montante = float(pool["montante"])
        vida_util = int(pool["vida_util_anos"])
        ano_pool = int(pool["ano_inicio"])
        dep_pool = montante / vida_util
        ano_dep_inicio = max(ano_pool, ano_inicio_op)
        ano_dep_fim = ano_dep_inicio + vida_util - 1
        if ano_dep_inicio <= year <= ano_dep_fim:
            total += dep_pool
    return total


def _juros_capitalizados_map(hub: dict) -> dict[int, float]:
    """
    Juros capitalizados no custo do ativo por ano de construção — NCRF 10.

    Fundamento académico (NCRF 10 §8):
    «Os custos de empréstimos que sejam diretamente atribuíveis à aquisição,
    construção ou produção de um ativo qualificável devem ser capitalizados
    como parte do custo desse ativo.»

    O hub logístico qualifica como «ativo qualificável» porque o período de
    construção e instalação é substancial (≥ 12 meses — NCRF 10 §5). A
    capitalização cessa quando o ativo está substancialmente pronto para o
    uso pretendido (NCRF 10 §22), i.e., quando arranca a operação (2026).

    Impacto no modelo:
      • DR: juros capitalizados NÃO reconhecidos como gasto financeiro
      • Balanço: AFT ↑ pelo montante capitalizado → maior base depreciável
      • DFC: o juro é SEMPRE saída de caixa real (NCRF 2 §33b) — capturado
              no fluxo_financiamento, independentemente do tratamento contab.
      • FCF unlevered: exclui juros por natureza (desalavancado); efeito
              indireto via depreciação mais alta nos anos operacionais

    Retorna: {ano: montante_capitalizado} — zero nos anos fora do período.
    """
    proj = hub["projeto_hub"]
    jc_cfg = proj.get("juros_capitalizaveis", {})

    if not jc_cfg.get("capitalizar", False):
        return {y: 0.0 for y in YEARS}

    ano_ini = int(jc_cfg.get("ano_inicio_capitalizacao", 9999))
    ano_fim = int(jc_cfg.get("ano_fim_capitalizacao", 0))

    banco = proj["financiamento"]["Banco_Hub"]
    capital = float(banco["montante"])
    taxa = float(banco["taxa_juro"])
    desembolso_ano = int(banco["desembolso"])

    saldo = 0.0
    result: dict[int, float] = {}

    for y in YEARS:
        if y == desembolso_ano:
            saldo = capital

        juros_y = saldo * taxa if saldo > 0 else 0.0
        result[y] = juros_y if ano_ini <= y <= ano_fim else 0.0

    return result


def hub_capex(hub: dict) -> pd.DataFrame:
    """CAPEX schedule do Hub, AFT rolling e depreciação com juros capitalizados (NCRF 10)."""
    proj = hub["projeto_hub"]
    cron = proj["capex"]["cronograma"]

    # Juros capitalizados: aumentam o custo do AFT (NCRF 10) mas NÃO o CAPEX
    # de caixa — o desembolso real está em fluxo_financiamento (pagamento de juros)
    jc_map = _juros_capitalizados_map(hub)

    # Pool virtual para depreciação dos juros capitalizados:
    # mesma taxa que a construção civil (4 % / 25 anos), pois são parte
    # integrante do custo de construção (NCRF 10 §8 + DR 25/2009 Anexo I)
    taxa_dep_jc = float(
        proj["capex"]["pools"]["construcao_civil"]["taxa_depreciacao"]
    )
    vida_jc = int(proj["capex"]["pools"]["construcao_civil"]["vida_util_anos"])
    ano_dep_jc_inicio = int(proj["ano_inicio_beneficios"])  # depreciação inicia com o ativo

    jc_acumulado = 0.0  # total de juros capitalizados até à data
    aft = 0.0           # AFT contabilístico (inclui juros capitalizados)
    rows = []

    for y in YEARS:
        capex_y = float(cron.get(y, 0.0))

        # Depreciação dos pools base (excluindo juros cap. — base separada para
        # que pt2030_reconhecimento() não seja contaminado pelo NCRF 10)
        dep_pools = _dep_por_ano(proj, y)

        # Juros capitalizados no próprio ano → somados ao AFT neste ano
        jc_y = jc_map.get(y, 0.0)
        jc_acumulado += jc_y

        # Depreciação sobre o pool virtual dos juros capitalizados
        # Inicia em ano_dep_jc_inicio, dura vida_jc anos
        dep_jc = 0.0
        if jc_acumulado > 0 and y >= ano_dep_jc_inicio:
            anos_dep = y - ano_dep_jc_inicio
            if anos_dep < vida_jc:
                dep_jc = jc_acumulado * taxa_dep_jc

        dep_y = dep_pools + dep_jc

        # AFT contabilístico = CAPEX cronograma + juros capitalizados − depreciações
        aft = aft + capex_y + jc_y - dep_y

        rows.append(
            {
                "ano": y,
                "capex": capex_y,                # CAPEX caixa (para DFC)
                "juros_capitalizados_aft": jc_y, # acrescimo AFT por NCRF 10
                "depreciacao": dep_y,            # total = pools + virtual jc
                "dep_pools": dep_pools,          # depreciação base (para PT2030)
                "dep_juros_cap": dep_jc,         # depreciação adicional NCRF 10
                "aft_liquido_fim": max(aft, 0.0),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Financiamento Bancário
# ---------------------------------------------------------------------------

def hub_financing(hub: dict) -> pd.DataFrame:
    """
    Plano de amortização do empréstimo bancário do Hub.

    Desembolso no ano indicado no YAML. Amortizações a partir de
    `inicio_amortizacao` (após o período de carência de obra + ramp-up).

    Colunas adicionais vs. versão anterior:
      juros_capitalizados — parte dos juros incorporada no custo do AFT
                            (NCRF 10 §8); não reconhecida na DR como gasto.
      juros_expensed      — parte dos juros reconhecida na DR (= juros − cap.).
                            É esta coluna que alimenta financiamento_anual()
                            e, por cascata, o DR e o VAL desalavancado.

    Nota de tesouraria: ambas as componentes representam saídas de caixa reais
    (NCRF 2 §33b). A distinção é puramente contabilística (DR vs. AFT),
    não afeta os fluxos financeiros reais capturados na DFC.
    """
    proj = hub["projeto_hub"]
    banco = proj["financiamento"]["Banco_Hub"]

    capital = float(banco["montante"])
    taxa = float(banco["taxa_juro"])
    amort_anual = float(banco["amortizacao_anual"])
    inicio_amort = int(banco["inicio_amortizacao"])
    desembolso_ano = int(banco["desembolso"])

    jc_map = _juros_capitalizados_map(hub)

    saldo = 0.0
    rows = []

    for y in YEARS:
        if y == desembolso_ano:
            saldo = capital

        juros = saldo * taxa

        amort = amort_anual if y >= inicio_amort and saldo > 0 else 0.0
        amort = min(amort, saldo)

        saldo = max(saldo - amort, 0.0)

        prox_amort = amort_anual if saldo > 0 else 0.0
        emp_c = min(prox_amort, saldo)
        emp_nc = max(saldo - emp_c, 0.0)

        # Decomposição do juro: capitalizado (AFT) vs. expensed (DR)
        jc = jc_map.get(y, 0.0)
        juros_exp = juros - jc  # o que vai para a DR (gasto financeiro)

        rows.append(
            {
                "ano": y,
                "saldo_fim": saldo,
                "emprestimos_nc": emp_nc,
                "emprestimos_c": emp_c,
                "juros": juros,             # total pago em caixa
                "juros_capitalizados": jc,  # vai para AFT (NCRF 10)
                "juros_expensed": juros_exp,# vai para DR (gasto financeiro)
                "amortizacao": amort,
                "desembolso": capital if y == desembolso_ano else 0.0,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# PT2030 — Subsídio ao Investimento
# ---------------------------------------------------------------------------

def pt2030_reconhecimento(hub: dict) -> dict[int, float]:
    """Subsídio PT2030 reconhecido no DR como outros rendimentos.

    SNC NCRF 22: reconhecido proporcionalmente à depreciação anual de cada pool
    vs. o total do CAPEX — equivale a amortizar o subsídio pelo mesmo ritmo
    que os ativos financiados.
    """
    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]

    montante = float(pt["montante"])
    capex_base = float(proj["capex"]["base"])

    if capex_base <= 0:
        return {y: 0.0 for y in YEARS}

    # Usa _dep_por_ano (pools base) e não hub_capex["depreciacao"] para isolar
    # o reconhecimento do subsídio dos juros capitalizados (NCRF 10):
    # o PT2030 subsidia o CAPEX elegível do projeto, não os custos financeiros.
    # Ratio = dep_pools_ano / capex_base_elegível → reconhecimento proporcional
    # às depreciações dos ativos financiados pelo subsídio (NCRF 22 §26).
    return {
        y: montante * _dep_por_ano(proj, y) / capex_base
        for y in YEARS
    }


# ---------------------------------------------------------------------------
# Necessidades de Fundo de Maneio (NFM) — Ciclo de Exploração do Hub
# ---------------------------------------------------------------------------

def hub_nfm(hub: dict) -> dict[int, float]:
    """
    Variação anual das Necessidades de Fundo de Maneio do Hub (ΔNFM).

    Definição e lógica académica:
    ┌──────────────────────────────────────────────────────────────────┐
    │  NFM = Stock Operacional + Crédito a Clientes                   │
    │        − Crédito de Fornecedores                                │
    │                                                                  │
    │  ΔNFM > 0 → aumento da NFM → saída de caixa (investimento WC)  │
    │  ΔNFM < 0 → redução da NFM → entrada de caixa (desinvestimento) │
    └──────────────────────────────────────────────────────────────────┘

    A ΔNFM reduz o FCF livre do projeto porque representa capital «preso»
    no ciclo operacional que não está disponível para distribuição ou
    reinvestimento — Brealey, Myers & Allen, 13.ª ed., §11.2:
    «A project that requires an investment in working capital generates
    a cash outflow in its early years.»

    Componentes modelados por fase:

    FASE 1 — Arranque operacional (ano_inicio, tipicamente 2026):
      1. Stock de manutenção (peças de substituição VLMs + AMRs + WMS)
         Valorizado ao custo de aquisição ou VRL, o mais baixo (NCRF 18 §9).
         Estimado em ~3 % do CAPEX de equipamento (benchmark VDMA 2022).
         Saída única no ano de arranque → não volta a crescer organicamente.
      2. Consumíveis de arranque (embalagens, etiquetas, materiais packing)
         Necessários para comissionamento e testes de carga do sistema.
      3. Crédito de fornecedores (contratos manutenção contratada)
         Mensurado ao custo amortizado (NCRF 27 §11).
         Crédito recebido no arranque → reduz a NFM inicial (ΔNFM_forn < 0).
         PSP × compras anuais de manutenção.
         Nos anos seguintes: estável → ΔNFM de fornecedores ≈ 0.

    FASE 2 — Serviços logísticos a terceiros (a partir de 2028):
      4. Crédito a clientes externos (produtores cerâmicos Aveiro/Coimbra)
         Reconhecimento do rédito à medida que o serviço é prestado (NCRF 20 §20).
         Mensurado ao custo amortizado (NCRF 27 §11).
         ΔNFM_clientes = PMR/360 × Δ(receita de serviços) por ano.
         PMR B2B logística nacional: 45 dias (mediana APLOG 2023).

    Retorna: {ano: ΔNFM} com valor positivo = saída de caixa.
    """
    proj = hub["projeto_hub"]
    nfm_cfg = proj.get("necessidades_fundo_maneio", {})

    if not nfm_cfg:
        return {y: 0.0 for y in YEARS}

    ano_inicio = int(nfm_cfg.get("ano_inicio", 2026))

    # Fase 1: stock de manutenção + consumíveis de arranque
    stock_manut = float(nfm_cfg.get("stock_manutencao_inicial", 0.0))
    consumiveis = float(nfm_cfg.get("consumiveis_arranque", 0.0))
    nfm_stock_arranque = stock_manut + consumiveis

    # Crédito de fornecedores — reduz NFM inicial (sinal negativo na ΔNFM)
    psp = float(nfm_cfg.get("psp_fornecedores_dias", 30))
    compras_anuais = float(nfm_cfg.get("compras_manutencao_anuais", 0.0))
    credito_forn_inicial = (psp / 360) * compras_anuais

    # Fase 2: clientes externos (crédito a receber por serviços logísticos)
    pmr = float(nfm_cfg.get("pmr_clientes_externos_dias", 45))
    receita_base = float(nfm_cfg.get("receita_servicos_externos_2028", 0.0))
    cresc_serv = float(nfm_cfg.get("crescimento_servicos_anuais", 0.0))
    ano_fase2 = 2028

    result: dict[int, float] = {}
    receita_prev = 0.0

    for y in YEARS:
        if y < ano_inicio:
            result[y] = 0.0
            continue

        delta_nfm = 0.0

        if y == ano_inicio:
            # Investimento inicial: stock + consumíveis − crédito inicial de fornecedores
            # O crédito de fornecedores no arranque reduz a saída de caixa líquida
            delta_nfm = nfm_stock_arranque - credito_forn_inicial

        # Fase 2: variação anual do crédito a clientes externos
        # Só o INCREMENTO de receita gera ΔNFM (não o nível absoluto)
        if y >= ano_fase2:
            n = y - ano_fase2
            receita_y = receita_base * (1 + cresc_serv) ** n
            delta_cli = (pmr / 360) * (receita_y - receita_prev)
            delta_nfm += delta_cli
            receita_prev = receita_y

        result[y] = delta_nfm

    return result


# ---------------------------------------------------------------------------
# Crédito Fiscal RFAI — CFI art. 22.º-23.º
# ---------------------------------------------------------------------------

def hub_rfai(hub: dict, irc_taxa: float | None = None) -> dict[int, float]:
    """
    Crédito fiscal RFAI anual aplicado ao IRC do hub — CFI art. 22.º-23.º.

    ┌──────────────────────────────────────────────────────────────────────────┐
    │  NATUREZA DO BENEFÍCIO: CRÉDITO FISCAL vs. DEDUÇÃO FISCAL               │
    │                                                                          │
    │  A distinção é fundamental para a correcta modelação do FCFF:           │
    │                                                                          │
    │  Dedução fiscal (e.g. SIFIDE): reduz a matéria colectável               │
    │    → poupança = dedução × t     (apenas a fracção da taxa)              │
    │                                                                          │
    │  Crédito fiscal (RFAI): deduzido directamente à colecta de IRC          │
    │    → poupança = crédito × 1     (valor integral, não multiplicado por t)│
    │                                                                          │
    │  O RFAI é por isso categorialmente mais valioso do que uma dedução      │
    │  de montante equivalente — erro frequente em modelos financeiros.       │
    └──────────────────────────────────────────────────────────────────────────┘

    Fórmula:
      crédito_total = taxa_rfai × CAPEX_elegível
      aplicado_ano  = min(crédito_restante, limite_irc_pct × IRC_bruto_ano)

    ┌──────────────────────────────────────────────────────────────────────────┐
    │  TRATAMENTO NO FCFF (abordagem WACC)                                    │
    │                                                                          │
    │  O crédito RFAI reduz o IRC efectivamente pago. No FCFF:                │
    │    IRC_pago = EBIT × t − rfai_credito_ano                               │
    │    NOPAT_efectivo = EBIT − IRC_pago = EBIT(1 − t) + rfai_credito_ano   │
    │                                                                          │
    │  Equivalência com a abordagem APV (Adjusted Present Value):             │
    │  No APV (Myers, 1974), benefícios fiscais específicos seriam            │
    │  descontados separadamente à taxa de risco do crédito (≈ rf). A        │
    │  abordagem WACC usada aqui desconta o rfai_credito ao WACC, o que      │
    │  é conservador (WACC > rf) — subestima ligeiramente o VAL do RFAI.     │
    │  Aceitável porque o RFAI é determinístico (crédito gerado = constante) │
    │  e o diferencial WACC − rf é pequeno no horizonte considerado.          │
    │                                                                          │
    │  Ref: Myers, S.C. (1974). "Interactions of Corporate Financing and      │
    │  Investment Decisions — Implications for Capital Budgeting". Journal    │
    │  of Finance, 29(1). §III — Side Effects of Financing.                   │
    │  Damodaran, "Investment Valuation", 3.ª ed., §10.5 — Tax Benefits.     │
    └──────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────────┐
    │  MECÂNICA DO CARRY-FORWARD — TIMING E VALOR TEMPORAL                   │
    │                                                                          │
    │  O crédito é gerado no momento do CAPEX (2025-2026) mas só pode ser    │
    │  utilizado quando existe IRC liquidado a deduzir — gerando um desfasam │
    │  temporal (timing mismatch). O carry-forward legal (10 anos — art.     │
    │  23.º §6 CFI) permite absorver o crédito remanescente em exercícios    │
    │  futuros, mas a cada ano de diferimento perde valor temporal (PV        │
    │  decresce ao factor 1/(1+WACC)^n).                                      │
    │                                                                          │
    │  Implicação: uma absorção mais rápida (e.g. via IRC total da Grestel   │
    │  em vez do IRC incremental do hub) tem valor presente superior.         │
    │  Este modelo apresenta o cenário conservador — limite sobre IRC hub.    │
    └──────────────────────────────────────────────────────────────────────────┘

    Nota sobre cumulação de benefícios (CFI art. 23.º §9):
      O RFAI não é cumulável com o SIFIDE sobre o mesmo investimento.
      A elegibilidade ao PT2030 (subsídio não reembolsável) não impede
      o RFAI — são regimes distintos com bases de incidência independentes,
      salvo sobreposição sobre o mesmo CAPEX (a verificar na instrução do
      processo junto do IAPMEI — art. 22.º §5 CFI).

    Retorna: {ano: crédito_rfai_aplicado} para YEARS = [2025..2029].
    """
    proj = hub["projeto_hub"]
    rfai_cfg = proj.get("rfai", {})

    if not rfai_cfg.get("aplicar", False):
        return {y: 0.0 for y in YEARS}

    taxa = float(rfai_cfg.get("taxa", 0.10))
    capex_elegivel = float(rfai_cfg.get("capex_elegivel", 0.0))
    limite_pct = float(rfai_cfg.get("limite_irc_pct", 0.50))

    if irc_taxa is None:
        irc_taxa = float(proj["viabilidade"]["irc_taxa"])

    dr_imp = hub_dr_impact(hub)

    # Crédito total gerado: determinístico, calculado uma única vez no momento
    # do reconhecimento do investimento elegível (independente do IRC futuro).
    credito_restante = taxa * capex_elegivel
    result: dict[int, float] = {}

    for y in YEARS:
        if credito_restante <= 0:
            result[y] = 0.0
            continue

        ebit_y = float(dr_imp[y].get("ebit_impact", 0.0))

        # Sem IRC liquidado (EBIT ≤ 0) não há colecta à qual deduzir o crédito.
        # O crédito não se perde — transita para o exercício seguinte dentro
        # do prazo de carry-forward (art. 23.º §6 CFI).
        if ebit_y <= 0:
            result[y] = 0.0
            continue

        irc_bruto = ebit_y * irc_taxa

        # Tecto anual: 50 % do IRC liquidado (art. 23.º §6 CFI).
        # Aplicado aqui sobre IRC incremental do hub (conservador).
        # O limite legal incide sobre o IRC total da empresa — dado que
        # a Grestel core gera IRC substancialmente superior ao do hub,
        # a absorção real pode ser até 10× mais rápida do que este modelo
        # indica. O cenário conservador é preferível para efeitos de M6.
        aplicado = min(credito_restante, limite_pct * irc_bruto)
        aplicado = max(aplicado, 0.0)

        credito_restante -= aplicado
        result[y] = aplicado

    return result


# ---------------------------------------------------------------------------
# Impacto no DR da Grestel
# ---------------------------------------------------------------------------

def hub_dr_impact(
    hub: dict,
    crescimento_anual: float | None = None,
) -> dict[int, dict]:
    """Impacto anual do Hub no DR standalone da Grestel."""
    proj = hub["projeto_hub"]

    if crescimento_anual is None:
        crescimento_anual = float(proj["beneficios_anuais"]["crescimento_anual"])

    ben = proj["beneficios_anuais"]
    ben_pontual = proj["beneficios_pontuais"]
    inicio = int(proj["ano_inicio_beneficios"])

    poupanca_op = float(ben["poupanca_operacional"])
    reducao_quebras = float(ben["reducao_quebras"])

    # Mantido por compatibilidade com o modelo atual.
    _ = abs(float(ben["opex_incremental"]))

    # Fator de ramp-up por ano (cenários adversos): reduz poupanças operacionais
    # nos primeiros anos de operação. Ausente no Base → 1.0 (100% dos benefícios).
    ramp_up = ben.get("ramp_up_por_ano", {})

    pessoal_pct = 0.68
    fse_pct = 0.32

    poupanca_pessoal_base = poupanca_op * pessoal_pct
    poupanca_fse_base = poupanca_op * fse_pct

    fse_opex_base = float(
        ben.get("opex_incremental")
        or proj.get("opex_detalhe", {}).get("total", 0)
    )

    subsidio = pt2030_reconhecimento(hub)

    inventario_one_time = float(ben_pontual["libertacao_inventario"])
    ano_inventario = int(ben_pontual["ano"])

    # Benefícios comerciais: acréscimo de VN por canal B2C direto
    ben_com = proj.get("beneficios_comerciais", {})
    ano_com = int(ben_com.get("ano_inicio", 9999))
    vn_inc_map: dict = ben_com.get("vn_incremental", {})
    cmvmc_pct_com = float(ben_com.get("cmvmc_pct_incremental", 0.55))

    df_cap = hub_capex(hub)
    capex_map = df_cap.set_index("ano")

    result: dict[int, dict] = {}

    for y in YEARS:
        # Benefícios comerciais aplicáveis independentemente de ano_inicio_beneficios
        vn_inc = float(vn_inc_map.get(y, 0.0)) if y >= ano_com else 0.0
        cmvmc_inc = vn_inc * cmvmc_pct_com
        contrib_com = vn_inc - cmvmc_inc  # margem bruta incremental B2C

        if y < inicio:
            result[y] = {
                "pessoal_reducao": 0.0,
                "fse_reducao": 0.0,
                "cmvmc_reducao": 0.0,
                "fse_opex_hub": 0.0,
                "outros_rend_subsidio": 0.0,
                "depreciacao_hub": 0.0,
                "inventario_libertado": 0.0,
                "vn_incremental": vn_inc,
                "cmvmc_incremental": cmvmc_inc,
                "beneficio_liquido": contrib_com,
                "ebitda_impact": contrib_com,
                "ebit_impact": contrib_com,
            }
            continue

        n = y - inicio
        fator = (1 + crescimento_anual) ** n
        ramp = float(ramp_up.get(y, 1.0))

        pessoal_red = poupanca_pessoal_base * fator * ramp
        fse_red = poupanca_fse_base * fator * ramp
        cmvmc_red = reducao_quebras * fator * ramp
        fse_opex = fse_opex_base * fator  # OPEX existe desde o arranque, sem ramp-up
        subsidio_y = subsidio.get(y, 0.0)

        dep_hub = (
            float(capex_map.loc[y, "depreciacao"])
            if y in capex_map.index
            else 0.0
        )

        inventario = inventario_one_time if y == ano_inventario else 0.0

        beneficio_liq = pessoal_red + fse_red + cmvmc_red - fse_opex
        ebitda_impact = beneficio_liq + subsidio_y + contrib_com
        ebit_impact = ebitda_impact - dep_hub

        result[y] = {
            "pessoal_reducao": pessoal_red,
            "fse_reducao": fse_red,
            "cmvmc_reducao": cmvmc_red,
            "fse_opex_hub": fse_opex,
            "outros_rend_subsidio": subsidio_y,
            "depreciacao_hub": dep_hub,
            "inventario_libertado": inventario,
            "vn_incremental": vn_inc,
            "cmvmc_incremental": cmvmc_inc,
            "beneficio_liquido": beneficio_liq,
            "ebitda_impact": ebitda_impact,
            "ebit_impact": ebit_impact,
        }

    return result


# ---------------------------------------------------------------------------
# Impacto no DFC da Grestel
# ---------------------------------------------------------------------------

def hub_dfc_impact(hub: dict) -> dict[int, dict]:
    """
    Impacto do Hub nos fluxos de caixa consolidados da Grestel (DFC).

    Estrutura dos fluxos por categoria (NCRF 2):

    FLUXO DE INVESTIMENTO:
      • capex_hub          — pagamento de CAPEX (construção + equipamento)
      • pt2030_recebimento — subsídio PT2030 recebido em caixa (entrada)
      → O CAPEX de caixa NÃO inclui juros capitalizados (esses são fluxo
        de financiamento, não de investimento — pagados ao banco, não ao
        fornecedor de construção)

    FLUXO DE FINANCIAMENTO:
      • desembolso_banco   — entrada do empréstimo CGD/BPI
      • amortizacao_banco  — reembolso anual do capital
      • juros_banco        — total de juros pagos em caixa (SEMPRE saída,
                             independentemente de serem capitalizados ou não)
      • juros_capitalizados— subset dos juros pagos que são capitalizados
                             no AFT (NCRF 10); separados para reconciliação
                             DFC ↔ DR (a DFC usa o total; a DR usa só expensed)

    FLUXO OPERACIONAL (via var_nfm em dfc.py):
      • nfm_delta          — ΔNFM do hub (saída de caixa para capital circulante)
                             lido por build_dfc() e adicionado a var_nfm
    """
    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]

    pt_montante = float(pt["montante"])
    pt_ano = int(pt["ano_recebimento"])

    df_cap = hub_capex(hub)
    df_fin = hub_financing(hub)

    capex_map = df_cap.set_index("ano")
    fin_map = df_fin.set_index("ano")

    nfm_map = hub_nfm(hub)

    result: dict[int, dict] = {}

    for y in YEARS:
        # CAPEX de caixa (não inclui juros capitalizados — esses pagam-se ao banco)
        capex_y = float(capex_map.loc[y, "capex"]) if y in capex_map.index else 0.0

        juros_y = float(fin_map.loc[y, "juros"]) if y in fin_map.index else 0.0
        jc_y = float(fin_map.loc[y, "juros_capitalizados"]) if y in fin_map.index else 0.0
        amort_y = float(fin_map.loc[y, "amortizacao"]) if y in fin_map.index else 0.0
        desembolso_y = float(fin_map.loc[y, "desembolso"]) if y in fin_map.index else 0.0

        pt2030_y = pt_montante if y == pt_ano else 0.0

        # ΔNFM: saída de caixa para capital circulante (fluxo operacional)
        nfm_y = nfm_map.get(y, 0.0)

        result[y] = {
            "capex_hub": -capex_y,
            "pt2030_recebimento": pt2030_y,
            "desembolso_banco": desembolso_y,
            "amortizacao_banco": -amort_y,
            "juros_banco": -juros_y,             # total pago em caixa
            "juros_capitalizados": jc_y,          # subset → reconciliação DFC/DR
            "nfm_delta": nfm_y,                   # ΔNFM → var_nfm em dfc.py
            "fluxo_investimento_hub": -capex_y + pt2030_y,
            "fluxo_financiamento_hub": desembolso_y - amort_y - juros_y,
        }

    return result


# ---------------------------------------------------------------------------
# FCF Livre — Análise de Viabilidade
# ---------------------------------------------------------------------------

def hub_fcf(
    hub: dict,
    irc_taxa: float = 0.245,
    incluir_inventario: bool = True,
) -> pd.DataFrame:
    """
    FCF Livre Unlevered (FCFF) do Hub para análise de viabilidade (VAL/TIR).

    Fórmula académica:
    ┌──────────────────────────────────────────────────────────────────────┐
    │  FCF = NOPAT + D&A − CAPEX − ΔNFM ± Variações pontuais de capital  │
    │                                                                      │
    │  NOPAT = EBIT × (1 − t)   [Net Operating Profit After Tax]          │
    │  D&A   = Depreciações e Amortizações (não-caixa, somadas de volta)  │
    │  CAPEX = Investimento em Capital Fixo (saída de caixa)              │
    │  ΔNFM  = Variação das Necessidades de Fundo de Maneio               │
    └──────────────────────────────────────────────────────────────────────┘

    Esta é a medida de fluxo de caixa relevante para desconto ao WACC
    (abordagem entity value / firm value). Referências:
      • Brealey, Myers & Allen, 13.ª ed., §19.1
      • Damodaran, "Investment Valuation", 3.ª ed., §11

    Exclusões deliberadas (e justificação académica):
      1. Juros (carência 2025-2027 e período normal 2028+)
         Excluídos porque o FCF é UNLEVERED (desalavancado). O custo da
         dívida — incluindo o tax shield dos juros — está implicitamente
         incorporado no WACC. Incluir juros e usar WACC em simultâneo
         seria dupla contagem (Damodaran, §11.3).
         Os juros de carência (2025: ~118 k€; 2026: ~118 k€; 2027: ~118 k€)
         são REAIS e impactam a tesouraria — ver mapa_servico_divida() e
         mapa_tesouraria_mensal() para a análise de liquidez consolidada.
      2. Amortizações de capital (reembolso do principal)
         Fluxo de financiamento, não operacional. Capturado no DSCR e
         mapa de serviço da dívida, não no FCF para VAL.
      3. Desembolso do banco (entrada do empréstimo)
         Fluxo de financiamento — não integra o FCFF.

    Inclusões:
      • ΔNFM anual (hub_nfm): saída de caixa para capital circulante,
        real e materialmente relevante mesmo não transitando pela DR.
      • Libertação pontual de inventário (beneficio_pontual 2026): redução
        do inventário histórico da Grestel via WMS — entrada de caixa real.
      • Depreciação extra dos juros capitalizados (NCRF 10): incluída na
        depreciação total proveniente de hub_capex(). Efeito positivo líquido
        = D&A × t (tax shield adicional da maior depreciação).
      • Crédito fiscal RFAI (hub_rfai): redução directa do IRC pago, com
        valor integral (crédito × 1, não crédito × t). Tratado como componente
        separada do NOPAT para legibilidade e auditabilidade — permite isolar
        o efeito do benefício fiscal do benefício operacional. Ver hub_rfai()
        para a justificação académica da abordagem WACC vs. APV.
    """
    dr_imp = hub_dr_impact(hub)
    df_cap = hub_capex(hub)
    nfm_map = hub_nfm(hub)
    rfai_map = hub_rfai(hub, irc_taxa=irc_taxa)

    capex_map = df_cap.set_index("ano")

    rows = []

    for y in YEARS:
        # CAPEX de caixa (excluí juros capitalizados — são fluxo de financiamento)
        capex_y = float(capex_map.loc[y, "capex"]) if y in capex_map.index else 0.0

        # Depreciação total inclui pools base + depreciação dos juros capitalizados
        dep_y = float(capex_map.loc[y, "depreciacao"]) if y in capex_map.index else 0.0

        imp = dr_imp[y]
        ebit_y = float(imp["ebit_impact"])

        inventario_y = float(imp["inventario_libertado"]) if incluir_inventario else 0.0

        # ΔNFM: saída de caixa real que reduz o FCF (não está na DR)
        delta_nfm_y = nfm_map.get(y, 0.0)

        # NOPAT = EBIT × (1 − t); convenção: EBIT negativo → sem poupança fiscal
        # (empresa não recebe cheque do Estado por prejuízo incremental do hub)
        nopat = ebit_y * (1 - irc_taxa) if ebit_y > 0 else ebit_y

        # Crédito RFAI: deduzido directamente à colecta (não à matéria colectável).
        # Apresentado como linha separada de NOPAT para distinguir o benefício
        # operacional (EBIT × (1−t)) do benefício fiscal específico do investimento.
        # Decomposição: IRC_pago = EBIT×t − rfai_y → NOPAT_ef. = EBIT(1−t) + rfai_y
        rfai_y = rfai_map.get(y, 0.0)

        # FCF = NOPAT + rfai_credito + D&A − CAPEX − ΔNFM + libertação inventário
        fcf = nopat + rfai_y + dep_y - capex_y - delta_nfm_y + inventario_y

        rows.append(
            {
                "ano": y,
                "ebitda_impact": imp["ebitda_impact"],
                "ebit_impact": ebit_y,
                "nopat": nopat,
                "rfai_credito": rfai_y,
                "depreciacao": dep_y,
                "capex": -capex_y,
                "delta_nfm": -delta_nfm_y,     # negativo = saída de caixa
                "inventario_libertado": inventario_y,
                "fcf_livre": fcf,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Mapa de Serviço da Dívida (Debt Service Schedule) — Análise de Liquidez
# ---------------------------------------------------------------------------

def mapa_servico_divida(hub: dict | None = None) -> pd.DataFrame:
    """
    Mapa anual de serviço da dívida do Hub com DSCR — análise de risco de liquidez.

    O Mapa de Serviço da Dívida é o instrumento central para avaliar o risco
    de liquidez associado ao financiamento do projeto, distinto do VAL:

    ┌─────────────────────────────────────────────────────────────────────┐
    │  SERVIÇO DA DÍVIDA = Juros Pagos (total) + Amortizações de Capital  │
    │                                                                      │
    │  DSCR = EBITDA incremental Hub / Serviço da Dívida                  │
    │  (Debt Service Coverage Ratio — rácio de cobertura do serviço)      │
    │                                                                      │
    │  DSCR > 1,0 → hub gera EBITDA suficiente para cobrir a dívida      │
    │  DSCR > 1,2 → confortável (critério mínimo bancário típico)         │
    │  DSCR > 1,5 → cobertura robusta (preferido por bancos de projeto)   │
    │  DSCR < 1,0 → tesouraria central Grestel subsidia o serviço         │
    │                                                                      │
    │  Ref: S&P Global, "Project Finance Methodology" (2014), §5.3;       │
    │       Finnerty, "Project Financing", 3.ª ed., cap. 6                │
    └─────────────────────────────────────────────────────────────────────┘

    Período de Carência (2025-2027):
      Durante a construção e ramp-up operacional, o hub apenas paga juros
      (sem amortização de capital). O DSCR neste período é calculado sobre
      o EBITDA incremental do hub, que é negativo ou nulo (o hub ainda não
      opera plenamente). A tesouraria da Grestel core (ceramics) deve
      absorver este serviço — risco de liquidez a monitorizar centralmente.

    Juros Capitalizados vs. Expensed:
      A tabela mostra ambos para clareza contabilística (NCRF 10):
      • juros_pagos_total = cash flow real saído (sempre saída, cap. ou exp.)
      • juros_capitalizados = porção adicionada ao AFT (não na DR)
      • juros_expensed_dr = porção na DR como gasto financeiro do período
    """
    if hub is None:
        hub = load()

    df_fin = hub_financing(hub)
    dr_imp = hub_dr_impact(hub)
    jc_map = _juros_capitalizados_map(hub)

    rows = []

    for _, row in df_fin.iterrows():
        y = int(row["ano"])
        juros_total = float(row["juros"])
        amort = float(row["amortizacao"])
        saldo = float(row["saldo_fim"])
        jc = jc_map.get(y, 0.0)
        juros_exp = juros_total - jc

        servico_divida = juros_total + amort

        ebitda_hub = float(dr_imp[y].get("ebitda_impact", 0.0)) if y in dr_imp else 0.0

        dscr = ebitda_hub / servico_divida if servico_divida > 0 else None

        rows.append(
            {
                "ano": y,
                "saldo_em_divida": saldo + amort,   # saldo início do ano
                "saldo_fim": saldo,
                "juros_pagos_total": juros_total,
                "juros_capitalizados": jc,
                "juros_expensed_dr": juros_exp,
                "amortizacao_capital": amort,
                "servico_total_divida": servico_divida,
                "ebitda_hub_incremental": ebitda_hub,
                "dscr_hub": dscr,
                "periodo_carencia": amort == 0.0,
            }
        )

    return pd.DataFrame(rows)


def mapa_tesouraria_mensal(hub: dict | None = None) -> pd.DataFrame:
    """
    Desdobramento mensal dos fluxos de caixa do Hub para 2025 e 2026.

    Base mensal obrigatória em M6 (alinhada com Fase 1 do M3):
    O M3 exige «previsão de base mensal» para o primeiro exercício económico.
    O M6, ao analisar o impacto do projeto sobre as projeções do M3, deve
    detalhar mensalmente o período de construção e arranque para:
      (a) Evidenciar o risco de liquidez dos juros da carência mês a mês
      (b) Identificar o momento exato da saída de caixa para NFM inicial
      (c) Modelar a recuperação de IVA sobre o CAPEX (pago antes do reembolso)
      (d) Servir como base para o «Orçamento de Tesouraria» e mapas de
          serviço da dívida — instrumentos exigidos no plano de negócios M6

    Estrutura dos fluxos mensais:
      INVESTIMENTO: CAPEX mensal (perfil de obra civil) + CAPEX equipamento
      FINANCIAMENTO: desembolso banco (mês 1/2025) + juros mensais
      OPERACIONAL: ΔNFM (arranque operacional, H2 2026)
      SUBSÍDIO PT2030: recebimento esperado (Q1 2027, fora desta janela)

    IVA sobre CAPEX:
      O CAPEX está sujeito a IVA (23 %). A empresa paga o IVA ao fornecedor
      e recupera-o via declaração periódica (tipicamente 1-3 meses depois).
      Este diferencial temporário é uma necessidade de financiamento adicional
      não capturada no modelo anual. A função mostra a exposição bruta.

    Nota: os totais anuais devem coincidir com os valores do modelo anual
    (consistência M3 ↔ M6). O primeiro mês de 2027 está fora da janela mas
    o PT2030 (recebimento 2027) aparece na DFC anual de 2027.
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    banco = proj["financiamento"]["Banco_Hub"]
    pt = proj["financiamento"]["PT2030"]
    nfm_cfg = proj.get("necessidades_fundo_maneio", {})
    cron_mensal = proj.get("cronograma_mensal", {})

    capital = float(banco["montante"])
    taxa_mensal = float(banco["taxa_juro"]) / 12
    desembolso_ano = int(banco["desembolso"])

    iva_taxa = 0.23  # IVA à taxa normal (CIVA art. 18.º §1 al. c))

    # Pré-calcular recuperação de IVA sobre CAPEX em M+2 (regime mensal CIVA art. 27.º)
    anos_janela = [2025, 2026]
    meses_lista = ["jan", "fev", "mar", "abr", "mai", "jun",
                   "jul", "ago", "set", "out", "nov", "dez"]
    iva_recuperacao: dict[tuple[int, int], float] = {}
    for _ano in anos_janela:
        _cron = cron_mensal.get(str(_ano), {})
        for _i, _mes in enumerate(meses_lista, start=1):
            _capex = float(_cron.get(_mes, 0.0))
            if _capex == 0.0:
                continue
            _rec_i = _i + 2
            _rec_ano = _ano
            if _rec_i > 12:
                _rec_i -= 12
                _rec_ano += 1
            if _rec_ano in anos_janela:
                key = (_rec_ano, _rec_i)
                iva_recuperacao[key] = iva_recuperacao.get(key, 0.0) + _capex * iva_taxa

    rows = []
    saldo = 0.0
    nfm_lancado = False

    for ano in anos_janela:
        cron_ano = cron_mensal.get(str(ano), {})

        for i, mes in enumerate(meses_lista, start=1):
            capex_mes = float(cron_ano.get(mes, 0.0))

            # Desembolso do banco: Janeiro do ano de desembolso (mês 1)
            desembolso_mes = capital if (ano == desembolso_ano and i == 1) else 0.0
            if desembolso_mes > 0:
                saldo = capital

            juros_mes = saldo * taxa_mensal

            iva_capex = capex_mes * iva_taxa
            iva_recuperado = iva_recuperacao.get((ano, i), 0.0)

            # ΔNFM: lançado no 1.º mês de operação (Julho 2026 — arranque faseado)
            delta_nfm_mes = 0.0
            if ano == 2026 and i == 7 and not nfm_lancado:
                stock_manut = float(nfm_cfg.get("stock_manutencao_inicial", 0.0))
                consumiveis = float(nfm_cfg.get("consumiveis_arranque", 0.0))
                psp = float(nfm_cfg.get("psp_fornecedores_dias", 30))
                compras = float(nfm_cfg.get("compras_manutencao_anuais", 0.0))
                cred_forn = (psp / 360) * compras
                delta_nfm_mes = stock_manut + consumiveis - cred_forn
                nfm_lancado = True

            fluxo_inv = -capex_mes
            fluxo_fin = desembolso_mes - juros_mes
            fluxo_op = -delta_nfm_mes
            # IVA: saída no mês do CAPEX, recuperação em M+2
            fluxo_iva = -iva_capex + iva_recuperado

            rows.append(
                {
                    "ano": ano,
                    "mes": i,
                    "mes_nome": mes,
                    "capex_mensal": -capex_mes,
                    "iva_capex_pago": -iva_capex,
                    "iva_capex_recuperado": iva_recuperado,
                    "desembolso_banco": desembolso_mes,
                    "juros_mensais": -juros_mes,
                    "delta_nfm": -delta_nfm_mes,
                    "fluxo_investimento": fluxo_inv,
                    "fluxo_financiamento": fluxo_fin,
                    "fluxo_operacional": fluxo_op,
                    "variacao_caixa_mensal": fluxo_inv + fluxo_fin + fluxo_op + fluxo_iva,
                    "saldo_divida_fim": saldo,
                }
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Funções financeiras: VAL, TIR, Payback
# ---------------------------------------------------------------------------

def _npv(cashflows: Sequence[float], rate: float) -> float:
    """Valor Presente Líquido."""
    return sum(
        cf / (1 + rate) ** t
        for t, cf in enumerate(cashflows)
    )


def _irr(
    cashflows: Sequence[float],
    low: float = -0.99,
    high: float = 10.0,
    tol: float = 1e-7,
    max_iter: int = 300,
) -> float | None:
    """Taxa Interna de Rentabilidade por bissecção."""
    try:
        v_low = _npv(cashflows, low)
        v_high = _npv(cashflows, high)

        if v_low * v_high > 0:
            return None

        for _ in range(max_iter):
            mid = (low + high) / 2.0
            v_mid = _npv(cashflows, mid)

            if abs(v_mid) < tol:
                return mid

            if _npv(cashflows, low) * v_mid < 0:
                high = mid
            else:
                low = mid

        return (low + high) / 2.0

    except Exception:
        return None


def _payback(cashflows: Sequence[float]) -> float | None:
    """Payback simples."""
    acum = 0.0

    for t, cf in enumerate(cashflows):
        prev_acum = acum
        acum += cf

        if prev_acum < 0 and acum >= 0 and t > 0:
            frac = (-prev_acum) / cf if cf else 0.0
            return (t - 1) + frac

    return None


def _discounted_payback(
    cashflows: Sequence[float],
    rate: float,
) -> float | None:
    """Payback atualizado."""
    disc = [
        cf / (1 + rate) ** t
        for t, cf in enumerate(cashflows)
    ]

    return _payback(disc)


def _vlq_ativos(hub: dict, ano_fim: int) -> float:
    """
    Valor Líquido Contabilístico (VLQ) de todos os pools + juros capitalizados
    no final do horizonte de análise — componente base do Valor Residual (NCRF 7).

    VLQ_pool = montante × max(ano_dep_fim − ano_fim, 0) / vida_util
    onde ano_dep_fim = max(ano_pool, ano_inicio_op) + vida_util − 1.
    """
    proj = hub["projeto_hub"]
    pools = proj["capex"]["pools"]
    ano_inicio_op = int(proj["ano_inicio_beneficios"])

    vlq = 0.0
    for pool in pools.values():
        montante = float(pool["montante"])
        vida_util = int(pool["vida_util_anos"])
        ano_pool = int(pool["ano_inicio"])
        ano_dep_inicio = max(ano_pool, ano_inicio_op)
        ano_dep_fim = ano_dep_inicio + vida_util - 1
        anos_restantes = max(ano_dep_fim - ano_fim, 0)
        vlq += montante * anos_restantes / vida_util

    # Pool virtual dos juros capitalizados (NCRF 10) — mesma vida útil da construção civil
    jc_map = _juros_capitalizados_map(hub)
    jc_total = sum(jc_map.values())
    if jc_total > 0:
        vida_jc = int(pools["construcao_civil"]["vida_util_anos"])
        ano_dep_jc_fim = ano_inicio_op + vida_jc - 1
        anos_restantes_jc = max(ano_dep_jc_fim - ano_fim, 0)
        vlq += jc_total * anos_restantes_jc / vida_jc

    return vlq


def _capital_vivo(hub: dict, ano_fim: int) -> float:
    """Saldo da dívida bancária no final do horizonte (capital por amortizar)."""
    proj = hub["projeto_hub"]
    banco = proj["financiamento"]["Banco_Hub"]
    capital = float(banco["montante"])
    amort_anual = float(banco["amortizacao_anual"])
    inicio_amort = int(banco["inicio_amortizacao"])
    desembolso_ano = int(banco["desembolso"])

    if ano_fim < desembolso_ano:
        return 0.0

    anos_amort = max(0, ano_fim - inicio_amort + 1)
    amortizado = min(amort_anual * anos_amort, capital)
    return max(capital - amortizado, 0.0)


def ponto_critico_hub(
    driver: str,
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
    tol: float = 1.0,
    max_iter: int = 100,
) -> dict:
    """
    Ponto crítico do VAL: valor do driver que faz VPL = 0.

    Usa bissecção sobre sensibilidade_hub(). A margem de segurança indica
    o desvio percentual máximo admissível face ao valor base do driver antes
    de o projeto se tornar não viável (VPL < 0).

    Retorna: {driver, valor_base, ponto_critico, vpl_base, margem_seguranca_pct, status}
    """
    if hub_base is None:
        hub_base = load()

    proj = hub_base["projeto_hub"]

    _cfg: dict[str, dict] = {
        "pessoal":     {"base": float(proj["beneficios_anuais"]["poupanca_operacional"]),
                        "low": 0.0, "high": float(proj["beneficios_anuais"]["poupanca_operacional"]) * 4},
        "inventario":  {"base": float(proj["beneficios_pontuais"]["libertacao_inventario"]),
                        "low": 0.0, "high": float(proj["beneficios_pontuais"]["libertacao_inventario"]) * 4},
        "capex":       {"base": float(proj["capex"]["base"]),
                        "low": float(proj["capex"]["base"]) * 0.3,
                        "high": float(proj["capex"]["base"]) * 3.0},
        "wacc":        {"base": float(proj["viabilidade"]["wacc"]),
                        "low": 0.001, "high": 0.80},
        "b2c":         {"base": 1.0, "low": 0.0, "high": 3.0},
        "crescimento": {"base": float(proj["beneficios_anuais"]["crescimento_anual"]),
                        "low": 0.0, "high": 0.50},
        "pt2030_taxa": {"base": float(proj["financiamento"]["PT2030"]["montante"])
                               / float(proj["capex"]["base"]),
                        "low": 0.0, "high": 0.75},
        "quebras":     {"base": float(proj["beneficios_anuais"]["reducao_quebras"]),
                        "low": 0.0, "high": float(proj["beneficios_anuais"]["reducao_quebras"]) * 10},
    }

    if driver not in _cfg:
        raise ValueError(f"Driver não suportado para ponto crítico: {driver!r}")

    cfg = _cfg[driver]
    base = cfg["base"]
    low, high = cfg["low"], cfg["high"]

    def _vpl(v: float) -> float:
        df = sensibilidade_hub(driver, [v], hub_base, irc_taxa)
        return float(df["vpl"].iloc[0])

    vpl_base = _vpl(base)
    vpl_low = _vpl(low)
    vpl_high = _vpl(high)

    if vpl_low * vpl_high > 0:
        return {
            "driver": driver,
            "valor_base": base,
            "ponto_critico": None,
            "vpl_base": vpl_base,
            "margem_seguranca_pct": None,
            "status": "sem_cruzamento_no_intervalo",
        }

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        vpl_mid = _vpl(mid)
        if abs(vpl_mid) < tol:
            break
        if vpl_low * vpl_mid < 0:
            high = mid
            vpl_high = vpl_mid
        else:
            low = mid
            vpl_low = vpl_mid

    pc = (low + high) / 2.0
    margem = abs(base - pc) / abs(base) if base != 0 else None

    return {
        "driver": driver,
        "valor_base": base,
        "ponto_critico": pc,
        "vpl_base": vpl_base,
        "margem_seguranca_pct": margem,
        "status": "ok",
    }


def viabilidade_hub(
    hub: dict | None = None,
    irc_taxa: float | None = None,
    wacc: float | None = None,
    incluir_inventario: bool = True,
    incluir_liquidacao_divida: bool = False,
    taxa_realizacao_ativos: float = 1.0,
) -> dict:
    """Análise de viabilidade completa do Hub Logístico 4.0.

    Parâmetros adicionais:
      incluir_liquidacao_divida — se True, subtrai o capital bancário vivo
        no ano horizonte do FCF terminal (perspetiva acionista / FCFE).
        Por defeito False: abordagem FCFF pura (dívida no WACC).
      taxa_realizacao_ativos — rácio valor de mercado / VLQ no final do
        horizonte. 1,0 = VLQ = valor de saída (mais-valia zero, sem imposto).
        >1,0 gera mais-valia: imposto = (realizacao − VLQ) × irc_taxa.
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.225))

    if wacc is None:
        wacc = float(via["wacc"])

    horizonte = int(via["horizonte_anos"])

    df_fcf = hub_fcf(
        hub,
        irc_taxa=irc_taxa,
        incluir_inventario=incluir_inventario,
    )

    anos_modelo = list(df_fcf["ano"])
    ultimo_ano = anos_modelo[-1]

    fcf_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["fcf_livre"].iloc[0])
    ebitda_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["ebitda_impact"].iloc[0])
    dep_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["depreciacao"].iloc[0])

    # ---------------------------------------------------------------------------
    # Carry-forward RFAI para os anos de extensão (2030–2034)
    #
    # Fundamento: o crédito gerado em 2025-2026 sobre o CAPEX elegível tem
    # carry-forward legal de 10 exercícios (CFI art. 23.º §6). O horizonte
    # do modelo estende-se até 2034, pelo que saldos não absorvidos em YEARS
    # (2025-2029) devem continuar a ser aplicados nos anos de extensão.
    #
    # Relevância para o VAL: quanto mais tarde for absorvido o crédito, menor
    # o seu valor presente. O crédito gerado em 2026 e absorvido apenas em
    # 2032 perde, ao WACC de 8 %, cerca de 37 % do seu valor inicial
    # (1 − 1/1.08⁶ ≈ 0.37). Este efeito de timing penaliza o VAL no cenário
    # conservador (limite sobre IRC hub) vs. o cenário real (IRC Grestel total).
    # ---------------------------------------------------------------------------
    rfai_cfg = proj.get("rfai", {})
    rfai_restante_ext = 0.0
    rfai_limite_pct_ext = float(rfai_cfg.get("limite_irc_pct", 0.50))
    if rfai_cfg.get("aplicar", False):
        rfai_total = float(rfai_cfg.get("taxa", 0.10)) * float(rfai_cfg.get("capex_elegivel", 0.0))
        rfai_aplicado = float(df_fcf["rfai_credito"].sum()) if "rfai_credito" in df_fcf.columns else 0.0
        rfai_restante_ext = max(rfai_total - rfai_aplicado, 0.0)

    ext_rows = []
    g = float(proj["beneficios_anuais"]["crescimento_anual"])

    ebitda_prev = ebitda_ultimo

    for k in range(1, horizonte - len(anos_modelo) + 1):
        y_ext = ultimo_ano + k

        ebitda_ext = ebitda_prev * (1 + g)
        dep_ext = _dep_por_ano(proj, y_ext)
        ebit_ext = ebitda_ext - dep_ext

        # RFAI carry-forward: aplica o saldo remanescente de exercícios anteriores.
        # O tecto de 50 % é recalculado sobre o IRC incremental do ano de extensão
        # (mesma lógica conservadora de hub_rfai). O saldo decresce a cada ano
        # de absorção até esgotar ou expirar o prazo legal de carry-forward.
        rfai_ext = 0.0
        irc_bruto_ext = max(ebit_ext, 0.0) * irc_taxa
        if rfai_restante_ext > 0 and irc_bruto_ext > 0:
            rfai_ext = min(rfai_restante_ext, rfai_limite_pct_ext * irc_bruto_ext)
            rfai_restante_ext -= rfai_ext

        # NOPAT com RFAI: crédito absorvido neste exercício aumenta o caixa fiscal
        nopat_ext = max(ebit_ext, 0.0) * (1 - irc_taxa) + rfai_ext
        fcf_ext = nopat_ext + dep_ext

        ext_rows.append(
            {
                "ano": y_ext,
                "ebitda_impact": ebitda_ext,
                "ebit_impact": ebit_ext,
                "nopat": nopat_ext,
                "rfai_credito": rfai_ext,
                "depreciacao": dep_ext,
                "capex": 0.0,
                "delta_nfm": 0.0,
                "inventario_libertado": 0.0,
                "fcf_livre": fcf_ext,
            }
        )

        ebitda_prev = ebitda_ext

    if ext_rows:
        df_fcf = pd.concat(
            [df_fcf, pd.DataFrame(ext_rows)],
            ignore_index=True,
        )

    # ── Valor Residual ──────────────────────────────────────────────────────
    # O projeto cessa financeiramente no ano horizonte; não se usa perpetuidade.
    ano_horizonte = int(df_fcf["ano"].iloc[-1])
    vr_ativos = _vlq_ativos(hub, ano_horizonte)

    # Mais-valias: se valor de realização > VLQ (taxa_realizacao_ativos > 1)
    valor_realizacao = vr_ativos * taxa_realizacao_ativos
    mais_valia = max(valor_realizacao - vr_ativos, 0.0)
    imposto_mais_valia = mais_valia * irc_taxa

    # NFM acumulada — capital circulante que reverte quando o projeto termina
    nfm_map = hub_nfm(hub)
    nfm_recovery_terminal = sum(nfm_map.values())

    # Dívida viva no final do horizonte (sempre calculada para informação)
    capital_vivo_t10 = _capital_vivo(hub, ano_horizonte)
    deducao_divida = capital_vivo_t10 if incluir_liquidacao_divida else 0.0

    vt = (valor_realizacao - imposto_mais_valia) + nfm_recovery_terminal - deducao_divida

    cfs = list(df_fcf["fcf_livre"])
    cfs[-1] += vt

    vpl = _npv(cfs, wacc)
    tir = _irr(cfs)
    pb = _payback(cfs)
    pb_disc = _discounted_payback(cfs, wacc)

    capex_base = float(proj["capex"]["base"])
    indice_rendibilidade = (1 + vpl / capex_base) if capex_base else None

    # NFM total acumulado ao longo do horizonte (soma das ΔNFM > 0)
    nfm_total_saida = sum(v for v in nfm_map.values() if v > 0)

    # Juros capitalizados totais (informação para reconciliação)
    jc_map = _juros_capitalizados_map(hub)
    juros_cap_total = sum(jc_map.values())

    nfm_cfg = proj.get("necessidades_fundo_maneio", {})
    jc_cfg = proj.get("juros_capitalizaveis", {})

    rfai_total_gerado = (
        float(rfai_cfg.get("taxa", 0.0)) * float(rfai_cfg.get("capex_elegivel", 0.0))
        if rfai_cfg.get("aplicar", False) else 0.0
    )
    rfai_aplicado_total = float(df_fcf["rfai_credito"].sum()) if "rfai_credito" in df_fcf.columns else 0.0

    return {
        "fcf_df": df_fcf,
        "valor_terminal": vt,
        "valor_residual_ativos": vr_ativos,
        "mais_valia": mais_valia,
        "imposto_mais_valia": imposto_mais_valia,
        "nfm_recovery_terminal": nfm_recovery_terminal,
        "capital_vivo_t10": capital_vivo_t10,
        "deducao_divida_terminal": deducao_divida,
        "cashflows_vpl": cfs,
        "vpl": vpl,
        "tir": tir,
        "payback_simples": pb,
        "payback_atualizado": pb_disc,
        "indice_rendibilidade": indice_rendibilidade,
        "parametros": {
            "wacc": wacc,
            "irc_taxa": irc_taxa,
            "metodologia_vt": "valor_residual_ativos_nfm",
            "valor_residual_ativos": vr_ativos,
            "nfm_recovery_terminal": nfm_recovery_terminal,
            "capital_vivo_t10": capital_vivo_t10,
            "incluir_liquidacao_divida": incluir_liquidacao_divida,
            "taxa_realizacao_ativos": taxa_realizacao_ativos,
            "mais_valia": mais_valia,
            "imposto_mais_valia": imposto_mais_valia,
            "horizonte_anos": horizonte,
            "incluir_inventario": incluir_inventario,
            "capex_base": capex_base,
            "capex_2025": float(proj["capex"]["cronograma"].get(2025, 0)),
            "capex_2026": float(proj["capex"]["cronograma"].get(2026, 0)),
            "depreciacao_descricao": (
                "4 %–25 % por pool · construção 25 a · VLM 8 a · AMR 5 a"
                " · WMS 4 a · integração 3 a · juros cap. 25 a (NCRF 10)"
            ),
            "poupanca_operacional": float(proj["beneficios_anuais"]["poupanca_operacional"]),
            "reducao_quebras": float(proj["beneficios_anuais"]["reducao_quebras"]),
            "opex_incremental": float(
                proj["beneficios_anuais"].get("opex_incremental")
                or proj.get("opex_detalhe", {}).get("total", 0)
            ),
            "beneficio_liquido_anual": float(proj["beneficios_anuais"]["beneficio_liquido_anual"]),
            "crescimento_anual": float(proj["beneficios_anuais"]["crescimento_anual"]),
            "libertacao_inventario": float(proj["beneficios_pontuais"]["libertacao_inventario"]),
            "ano_inventario": int(proj["beneficios_pontuais"]["ano"]),
            "banco_montante": float(proj["financiamento"]["Banco_Hub"]["montante"]),
            "banco_taxa_juro": float(proj["financiamento"]["Banco_Hub"]["taxa_juro"]),
            "pt2030_montante": float(proj["financiamento"]["PT2030"]["montante"]),
            "pt2030_ano": int(proj["financiamento"]["PT2030"]["ano_recebimento"]),
            "ano_inicio_beneficios": int(proj["ano_inicio_beneficios"]),
            # NFM
            "nfm_stock_manutencao": float(nfm_cfg.get("stock_manutencao_inicial", 0)),
            "nfm_consumiveis_arranque": float(nfm_cfg.get("consumiveis_arranque", 0)),
            "nfm_psp_fornecedores_dias": float(nfm_cfg.get("psp_fornecedores_dias", 30)),
            "nfm_pmr_clientes_externos_dias": float(nfm_cfg.get("pmr_clientes_externos_dias", 45)),
            "nfm_total_saida_caixa": nfm_total_saida,
            # Juros capitalizados (NCRF 10)
            "juros_capitalizados_total": juros_cap_total,
            "juros_capitalizaveis_ativo": jc_cfg.get("capitalizar", False),
            "juros_cap_ano_inicio": jc_cfg.get("ano_inicio_capitalizacao", None),
            "juros_cap_ano_fim": jc_cfg.get("ano_fim_capitalizacao", None),
            # RFAI
            "rfai_aplicar": rfai_cfg.get("aplicar", False),
            "rfai_taxa": float(rfai_cfg.get("taxa", 0.0)) if rfai_cfg.get("aplicar", False) else 0.0,
            "rfai_capex_elegivel": float(rfai_cfg.get("capex_elegivel", 0.0)) if rfai_cfg.get("aplicar", False) else 0.0,
            "rfai_credito_total_gerado": rfai_total_gerado,
            "rfai_credito_aplicado_horizonte": rfai_aplicado_total,
            "rfai_credito_restante_pos_horizonte": max(rfai_total_gerado - rfai_aplicado_total, 0.0),
        },
    }


# ---------------------------------------------------------------------------
# Análise de Sensibilidade / Tornado
# ---------------------------------------------------------------------------

def sensibilidade_hub(
    driver: str,
    valores: Sequence[float],
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
) -> pd.DataFrame:
    """One-at-a-time sensibilidade do VPL do Hub."""
    if hub_base is None:
        hub_base = load()

    rows = []

    for v in valores:
        h = copy.deepcopy(hub_base)
        proj = h["projeto_hub"]

        if driver == "beneficio":
            ben = proj["beneficios_anuais"]
            factor = v / float(ben["beneficio_liquido_anual"])

            ben["poupanca_operacional"] = (
                float(ben["poupanca_operacional"]) * factor
            )
            ben["reducao_quebras"] = (
                float(ben["reducao_quebras"]) * factor
            )

        elif driver == "capex":
            old = float(proj["capex"]["base"])
            factor = v / old if old else 1.0

            proj["capex"]["base"] = v

            for y in proj["capex"]["cronograma"]:
                proj["capex"]["cronograma"][y] = (
                    float(proj["capex"]["cronograma"][y]) * factor
                )

        elif driver == "wacc":
            res = viabilidade_hub(h, irc_taxa=irc_taxa, wacc=v)

            rows.append(
                {
                    "driver": driver,
                    "valor": v,
                    "vpl": res["vpl"],
                    "tir": res["tir"],
                }
            )

            continue

        elif driver == "inventario":
            proj["beneficios_pontuais"]["libertacao_inventario"] = v

        elif driver == "quebras":
            proj["beneficios_anuais"]["reducao_quebras"] = v

        elif driver == "crescimento":
            proj["beneficios_anuais"]["crescimento_anual"] = v

        elif driver == "pt2030_taxa":
            # v = fracção do CAPEX (ex: 0.20 = 20 %, 0.45 = 45 %)
            capex_val = float(proj["capex"]["base"])
            proj["financiamento"]["PT2030"]["montante"] = v * capex_val

        elif driver == "pessoal":
            # v = poupança operacional total (€/ano); base = 380 000 €
            ben = proj["beneficios_anuais"]
            ben["poupanca_operacional"] = v
            quebras = float(ben.get("reducao_quebras", 0))
            opex = abs(float(
                ben.get("opex_incremental")
                or proj.get("opex_detalhe", {}).get("total", 0)
                or 0
            ))
            ben["beneficio_liquido_anual"] = v + quebras - opex

        elif driver == "b2c":
            # v = factor de escala sobre vn_incremental (1.0 = base; 0.5 = pessimista; 1.5 = otimista)
            ben_com = proj.get("beneficios_comerciais", {})
            vn_map = ben_com.get("vn_incremental", {})
            for yr in list(vn_map.keys()):
                vn_map[yr] = float(vn_map[yr]) * v

        else:
            raise ValueError(f"Driver desconhecido: {driver}")

        res = viabilidade_hub(h, irc_taxa=irc_taxa)

        rows.append(
            {
                "driver": driver,
                "valor": v,
                "vpl": res["vpl"],
                "tir": res["tir"],
            }
        )

    return pd.DataFrame(rows)


def tornado_hub(
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
) -> pd.DataFrame:
    """Tornado do VAL Hub — análise de sensibilidade one-at-a-time.

    6 variáveis críticas identificadas no diagnóstico financeiro da Grestel:
      1. Libertação de inventário  — maior motor de liquidez a curto prazo
      2. Co-financiamento PT2030   — subsidio a fundo perdido que determina viabilidade
      3. Crescimento B2C           — canal de margem superior (+18 pp vs retalho)
      4. Poupança operacional      — eficácia da automação (AMR + VLM) no custo de pessoal
      5. WACC                      — reflecte risco percebido pelo mercado/bancos
      6. Desvio no CAPEX           — risco de derrapagem orçamental em projetos 4.0
    """
    if hub_base is None:
        hub_base = load()

    proj = hub_base["projeto_hub"]
    capex_base = float(proj["capex"]["base"])

    vpl_base = viabilidade_hub(hub_base, irc_taxa=irc_taxa)["vpl"]

    # --- 6 variáveis críticas com ranges calibrados ao diagnóstico Grestel ----
    # Convenção: vals = [pessimista, otimista]
    # low e high no output referem-se ao impacto no VAL (não ao valor da variável):
    #   vpl_low = VAL quando a variável assume o valor vals[0] (pessimista)
    #   vpl_high = VAL quando a variável assume o valor vals[1] (otimista)
    cfg = {
        # 1. Inventário — €2,0 M base; 13 M€ imobilizados → meta conservadora de 15 %
        "inventario": {
            "vals": [1_000_000.0, 2_500_000.0],
            "label": "Libertação de inventário (€)",
            "desc_low": "€1,0 M (pess.)",
            "desc_high": "€2,5 M (otim.)",
        },
        # 2. PT2030 — 20 % (aprovação parcial) vs 45 % (aprovação majorada)
        "pt2030_taxa": {
            "vals": [0.20, 0.45],
            "label": "Co-financiamento PT2030 (% CAPEX)",
            "desc_low": "20 % (€760 k)",
            "desc_high": "45 % (€1 710 k)",
        },
        # 3. B2C — escala do VN incremental: +40 % 2024 → abrandamento vs aceleração
        "b2c": {
            "vals": [0.50, 1.50],
            "label": "Crescimento B2C/e-commerce (×base)",
            "desc_low": "×0,5 (abrand.)",
            "desc_high": "×1,5 (aceleração)",
        },
        # 4. Poupança operacional — automação sem vs com impacto pleno
        "pessoal": {
            "vals": [200_000.0, 500_000.0],
            "label": "Poupança operacional (€/ano)",
            "desc_low": "€200 k (pess.)",
            "desc_high": "€500 k (otim.)",
        },
        # 5. WACC — perfil de risco elevado 2024 (rating deteriorou); intervalo 6%–10%
        "wacc": {
            "vals": [0.10, 0.06],
            "label": "WACC (%)",
            "desc_low": "10 % (risco alto)",
            "desc_high": "6 % (risco baixo)",
        },
        # 6. CAPEX — derrapagem orçamental ±15 % (benchmark projetos 4.0)
        "capex": {
            "vals": [capex_base * 1.15, capex_base * 0.85],
            "label": "CAPEX ±15% (€)",
            "desc_low": "+15 % (derrap.)",
            "desc_high": "−15 % (poupança)",
        },
    }

    rows = []

    for key, info in cfg.items():
        low_v, high_v = info["vals"]

        df_low = sensibilidade_hub(key, [low_v], hub_base, irc_taxa)
        df_high = sensibilidade_hub(key, [high_v], hub_base, irc_taxa)

        vpl_low = float(df_low["vpl"].iloc[0])
        vpl_high = float(df_high["vpl"].iloc[0])

        rows.append(
            {
                "driver": key,
                "label": info["label"],
                "desc_low": info.get("desc_low", str(round(low_v, 4))),
                "desc_high": info.get("desc_high", str(round(high_v, 4))),
                "valor_low": low_v,
                "valor_high": high_v,
                "vpl_low": vpl_low,
                "vpl_base": vpl_base,
                "vpl_high": vpl_high,
                "impacto_total": abs(vpl_high - vpl_low),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("impacto_total", ascending=False)
        .reset_index(drop=True)
    )
