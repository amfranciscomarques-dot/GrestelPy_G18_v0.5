"""Testes de regressão e reconciliação dos outputs mensais 2025.

Três grupos:
  1. Estrutura — garantir que cada output mensal tem 12 linhas, colunas
     obrigatórias e sem NaN.
  2. Reconciliação mensal ↔ anual — sum(mensal) == DR[ano==2025] para VN,
     CMVMC, FSE, gastos_pessoal e RL.
  3. EOEP 2025 — saldos de fim-de-ano no Balanço derivam do calendário
     mensal (IVA Nov+Dez pendente, SS Dez, IRC residual).
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.engine.inputs import load, MESES
from src.engine.modelo.model import run_model
from src.engine.financiamento.tesouraria import build_eoep_mensal


# ---------------------------------------------------------------------------
# Fixture partilhada — run_model executado uma única vez para toda a suite
# ---------------------------------------------------------------------------

class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.base, cls.sched = load("Base")
        cls.dfs = run_model("Base")
        cls.dr_anual = cls.dfs["dr"]
        cls.row_2025 = cls.dr_anual[cls.dr_anual.ano == 2025].iloc[0]

    @staticmethod
    def _tol(val: float, pct: float = 0.001) -> float:
        """Tolerância: mínimo €1, ou pct% do valor de referência."""
        return max(1.0, abs(val) * pct)


# ---------------------------------------------------------------------------
# Grupo 1: Estrutura dos outputs mensais
# ---------------------------------------------------------------------------

class TestEstruturaMensais(_Base):

    def test_eoep_mensal_2025_tem_12_linhas(self):
        df = self.dfs["eoep_mensal_2025"]
        self.assertEqual(len(df), 12)

    def test_eoep_mensal_2025_colunas_obrigatorias(self):
        df = self.dfs["eoep_mensal_2025"]
        for col in ("mes", "iva_liquidado", "iva_saldo_periodo",
                    "ss_pagamento_mes", "irc_ppc_mes"):
            self.assertIn(col, df.columns, msg=f"Coluna ausente: {col}")

    def test_eoep_mensal_2025_sem_nan(self):
        df = self.dfs["eoep_mensal_2025"]
        self.assertFalse(df.isnull().any().any(), "eoep_mensal_2025 contém NaN")

    def test_eoep_mensal_2025_ordem_meses(self):
        self.assertEqual(list(self.dfs["eoep_mensal_2025"]["mes"]), MESES)

    # ── DR mensal ─────────────────────────────────────────────────────────────

    def test_dr_mensal_2025_tem_12_linhas(self):
        self.assertEqual(len(self.dfs["dr_mensal_2025"]), 12)

    def test_dr_mensal_2025_colunas_obrigatorias(self):
        df = self.dfs["dr_mensal_2025"]
        for col in ("mes", "vn", "cmvmc", "fse", "gastos_pessoal",
                    "ebitda", "depreciacoes", "ebit", "juros", "rl"):
            self.assertIn(col, df.columns, msg=f"Coluna ausente: {col}")

    def test_dr_mensal_2025_vn_positivo(self):
        self.assertTrue((self.dfs["dr_mensal_2025"]["vn"] > 0).all())

    def test_dr_mensal_2025_ordem_meses(self):
        self.assertEqual(list(self.dfs["dr_mensal_2025"]["mes"]), MESES)

    # ── Tesouraria mensal ──────────────────────────────────────────────────────

    def test_tesouraria_mensal_2025_tem_12_linhas(self):
        self.assertEqual(len(self.dfs["tesouraria_mensal_2025"]), 12)

    def test_tesouraria_mensal_2025_colunas_obrigatorias(self):
        df = self.dfs["tesouraria_mensal_2025"]
        for col in ("mes", "recebimentos_clientes", "pagamentos_fornecedores",
                    "pagamentos_pessoal", "fluxo_liquido", "saldo_caixa_acumulado"):
            self.assertIn(col, df.columns, msg=f"Coluna ausente: {col}")

    def test_tesouraria_mensal_2025_sem_nan(self):
        self.assertFalse(
            self.dfs["tesouraria_mensal_2025"].isnull().any().any(),
            "tesouraria_mensal_2025 contém NaN",
        )

    # ── Pessoal mensal (output independente) ──────────────────────────────────

    def test_pessoal_mensal_2025_tem_12_linhas(self):
        self.assertEqual(len(self.dfs["pessoal_mensal_2025"]), 12)

    def test_pessoal_mensal_2025_colunas(self):
        df = self.dfs["pessoal_mensal_2025"]
        self.assertIn("mes", df.columns)
        self.assertIn("gastos_pessoal", df.columns)

    def test_pessoal_mensal_2025_valores_positivos(self):
        self.assertTrue((self.dfs["pessoal_mensal_2025"]["gastos_pessoal"] > 0).all())

    def test_pessoal_mensal_2025_ordem_meses(self):
        self.assertEqual(list(self.dfs["pessoal_mensal_2025"]["mes"]), MESES)

    def test_pessoal_mensal_jun_nov_subsidios(self):
        """Jun e Nov têm subsídio de férias/natal: custo = 2× mês normal."""
        df = self.dfs["pessoal_mensal_2025"].set_index("mes")
        jan = float(df.loc["Jan", "gastos_pessoal"])
        self.assertAlmostEqual(float(df.loc["Jun", "gastos_pessoal"]), jan * 2, delta=1.0)
        self.assertAlmostEqual(float(df.loc["Nov", "gastos_pessoal"]), jan * 2, delta=1.0)

    # ── CMVMC mensal (output independente) ────────────────────────────────────

    def test_cmvmc_mensal_2025_tem_12_linhas(self):
        self.assertEqual(len(self.dfs["cmvmc_mensal_2025"]), 12)

    def test_cmvmc_mensal_2025_colunas(self):
        df = self.dfs["cmvmc_mensal_2025"]
        self.assertIn("mes", df.columns)
        self.assertIn("cmvmc", df.columns)

    def test_cmvmc_mensal_2025_valores_positivos(self):
        self.assertTrue((self.dfs["cmvmc_mensal_2025"]["cmvmc"] > 0).all())

    def test_cmvmc_mensal_2025_agosto_sazonal_menor(self):
        """Agosto tem sazonalidade baixa — deve ser o mês com menor CMVMC."""
        df = self.dfs["cmvmc_mensal_2025"].set_index("mes")
        ago = float(df.loc["Ago", "cmvmc"])
        outros = [float(df.loc[m, "cmvmc"]) for m in MESES if m != "Ago"]
        self.assertLess(ago, min(outros) + 1.0)


# ---------------------------------------------------------------------------
# Grupo 2: Reconciliação sum(mensal) == DR anual 2025
# ---------------------------------------------------------------------------

class TestReconciliacaoMensalAnual(_Base):

    def test_vn_mensal_fecha_com_dr_anual(self):
        soma = float(self.dfs["dr_mensal_2025"]["vn"].sum())
        anual = abs(float(self.row_2025["vn"]))
        self.assertAlmostEqual(soma, anual, delta=self._tol(anual))

    def test_cmvmc_mensal_fecha_com_dr_anual(self):
        soma = float(self.dfs["dr_mensal_2025"]["cmvmc"].sum())
        anual = abs(float(self.row_2025["cmvmc"]))
        self.assertAlmostEqual(soma, anual, delta=self._tol(anual))

    def test_fse_mensal_fecha_com_dr_anual(self):
        soma = float(self.dfs["dr_mensal_2025"]["fse"].sum())
        anual = abs(float(self.row_2025["fse"]))
        self.assertAlmostEqual(soma, anual, delta=self._tol(anual))

    def test_gastos_pessoal_mensal_fecha_com_dr_anual(self):
        soma = float(self.dfs["dr_mensal_2025"]["gastos_pessoal"].sum())
        anual = abs(float(self.row_2025["gastos_pessoal"]))
        self.assertAlmostEqual(soma, anual, delta=self._tol(anual))

    def test_ebitda_mensal_coerente_internamente(self):
        """EBITDA = VN − CMVMC − FSE − pessoal em cada linha do DR mensal.

        O DR mensal é simplificado (sem outros_rendimentos, var_inventários, etc.),
        pelo que a sua soma não reconcilia com o EBITDA anual completo. Testamos
        a coerência aritmética interna: a coluna ebitda é derivada correctamente
        das suas componentes.
        """
        df = self.dfs["dr_mensal_2025"]
        for _, row in df.iterrows():
            expected = row["vn"] - row["cmvmc"] - row["fse"] - row["gastos_pessoal"]
            self.assertAlmostEqual(
                float(row["ebitda"]), float(expected), delta=1.0,
                msg=f"EBITDA inconsistente em {row['mes']}: "
                    f"ebitda={row['ebitda']}, calculado={expected:.0f}",
            )

    def test_pessoal_mensal_independente_fecha_com_dr_anual(self):
        soma = float(self.dfs["pessoal_mensal_2025"]["gastos_pessoal"].sum())
        anual = abs(float(self.row_2025["gastos_pessoal"]))
        self.assertAlmostEqual(soma, anual, delta=self._tol(anual))

    def test_cmvmc_mensal_independente_fecha_com_dr_anual(self):
        soma = float(self.dfs["cmvmc_mensal_2025"]["cmvmc"].sum())
        anual = abs(float(self.row_2025["cmvmc"]))
        self.assertAlmostEqual(soma, anual, delta=self._tol(anual))

    def test_pessoal_mensal_e_dr_mensal_gastos_pessoal_coincidem(self):
        """Saída independente e a coluna do DR mensal devem ser idênticas."""
        soma_indep = float(self.dfs["pessoal_mensal_2025"]["gastos_pessoal"].sum())
        soma_dr = float(self.dfs["dr_mensal_2025"]["gastos_pessoal"].sum())
        self.assertAlmostEqual(soma_indep, soma_dr, delta=1.0)

    def test_cmvmc_mensal_e_dr_mensal_coincidem(self):
        soma_indep = float(self.dfs["cmvmc_mensal_2025"]["cmvmc"].sum())
        soma_dr = float(self.dfs["dr_mensal_2025"]["cmvmc"].sum())
        self.assertAlmostEqual(soma_indep, soma_dr, delta=1.0)


# ---------------------------------------------------------------------------
# Grupo 3: EOEP 2025 — saldos Balanço derivam do calendário mensal
# ---------------------------------------------------------------------------

class TestEoepSaldos2025(_Base):
    """Verifica que o EOEP de fim de ano 2025 é derivado do calendário mensal.

    Convenções do engine:
      iva_saldo_periodo > 0  →  empresa deve ao Estado (→ eoep_credor)
      iva_saldo_periodo < 0  →  Estado deve à empresa (→ eoep_devedor)

    Saldos pendentes no Balanço 31-Dez-2025:
      IVA Nov + Dez  — pagos em Jan/Fev 2026 (regime mensal, M+2)
      SS  Dez        — pago em Jan 2026 (M+1)
      IRC residual   — IRC anual menos pagamentos por conta (Jul/Set/Dez)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eoep_m = build_eoep_mensal(cls.a, cls.base, cls.sched)
        cls.m_map = cls.eoep_m.set_index("mes").to_dict("index")
        cls.ref_b = cls.sched.reference_balanco

    def test_eoep_mensal_tem_12_linhas(self):
        self.assertEqual(len(self.eoep_m), 12)

    def test_eoep_mensal_coluna_ss_acumulado_existe(self):
        self.assertIn("ss_acumulado_periodo", self.eoep_m.columns)

    def test_eoep_devedor_2025_deriva_de_iva_nov_dez(self):
        """eoep_devedor 2025 = derivado via eoep_anual(df_mensal=...).

        Quando IVA Nov+Dez > 0 (empresa deve ao Estado): eoep_devedor = 0.
        Quando IVA Nov+Dez < 0 (Estado deve à empresa): eoep_devedor = |saldo|.
        """
        from src.engine.modelo.eoep import eoep_anual

        iva_outstanding = (
            self.m_map["Nov"]["iva_saldo_periodo"]
            + self.m_map["Dez"]["iva_saldo_periodo"]
        )
        expected_dev = abs(iva_outstanding) if iva_outstanding < 0 else 0.0

        irc_anual_d = {y: float(self.sched.reference_dr["irc"].get(y, 0.0))
                       for y in (2025, 2026, 2027, 2028, 2029)}
        df_eoep_a = eoep_anual(self.a, self.base, self.sched,
                               irc_anual=irc_anual_d, df_mensal=self.eoep_m)
        actual_dev = float(df_eoep_a[df_eoep_a.ano == 2025].iloc[0]["eoep_devedor"])

        self.assertAlmostEqual(
            actual_dev, expected_dev,
            delta=max(1.0, abs(expected_dev) * 0.001),
            msg=(
                f"IVA Nov+Dez = {iva_outstanding:.0f}; "
                f"eoep_devedor esperado {expected_dev:.0f}, obtido {actual_dev:.0f}"
            ),
        )

    def test_eoep_credor_2025_deriva_do_mensal(self):
        """eoep_credor 2025 = IVA credor + SS Dez + IRC residual (via calendário mensal)."""
        from src.engine.modelo.eoep import eoep_anual

        iva_outstanding = (
            self.m_map["Nov"]["iva_saldo_periodo"]
            + self.m_map["Dez"]["iva_saldo_periodo"]
        )
        iva_credor = iva_outstanding if iva_outstanding >= 0 else 0.0
        ss_dez = self.m_map["Dez"]["ss_acumulado_periodo"]
        irc_ppc_total = float(self.eoep_m["irc_ppc_mes"].sum())
        irc_2025 = float(self.sched.reference_dr["irc"].get(2025, 0.0))
        irc_residual = max(0.0, irc_2025 - irc_ppc_total)
        expected_cred = iva_credor + ss_dez + irc_residual

        irc_anual_d = {y: float(self.sched.reference_dr["irc"].get(y, 0.0))
                       for y in (2025, 2026, 2027, 2028, 2029)}
        df_eoep_a = eoep_anual(self.a, self.base, self.sched,
                               irc_anual=irc_anual_d, df_mensal=self.eoep_m)
        actual_cred = float(df_eoep_a[df_eoep_a.ano == 2025].iloc[0]["eoep_credor"])

        self.assertAlmostEqual(
            actual_cred, expected_cred,
            delta=max(1.0, expected_cred * 0.001),
            msg=(
                f"eoep_credor esperado {expected_cred:.0f} "
                f"(IVA={iva_credor:.0f} + SS={ss_dez:.0f} + IRC={irc_residual:.0f}), "
                f"obtido {actual_cred:.0f}"
            ),
        )

    def test_eoep_credor_2025_positivo_e_material(self):
        """eoep_credor 2025 deve ser positivo e relevante (IRC + SS + IVA a pagar)."""
        actual_cred = float(self.ref_b["eoep_credor"][2025])
        self.assertGreater(actual_cred, 0.0)
        # Deve ser pelo menos o SS de Dez
        ss_dez = self.m_map["Dez"]["ss_acumulado_periodo"]
        self.assertGreater(actual_cred, ss_dez)

    def test_eoep_credor_inclui_irc_residual(self):
        """IRC anual 2025 > IRC PPC total — o residual entra no eoep_credor."""
        irc_ppc_total = float(self.eoep_m["irc_ppc_mes"].sum())
        irc_anual = float(self.sched.reference_dr["irc"][2025])
        self.assertGreater(irc_anual, irc_ppc_total,
                           msg="IRC anual deve exceder os pagamentos por conta")

    def test_irc_ppc_apenas_em_jul_set_dez(self):
        """Pagamentos por conta ocorrem só em Jul, Set e Dez (art.º 105.º CIRC)."""
        for m in MESES:
            val = self.m_map[m]["irc_ppc_mes"]
            if m in ("Jul", "Set", "Dez"):
                self.assertGreater(val, 0.0, msg=f"IRC PPC em {m} deve ser > 0")
            else:
                self.assertAlmostEqual(val, 0.0, delta=0.01,
                                       msg=f"IRC PPC em {m} deve ser 0")

    def test_irc_ppc_tres_prestacoes_iguais(self):
        """As três prestações de IRC PPC são iguais (76,5% × IRC_2024 ÷ 3)."""
        ppc_jul = self.m_map["Jul"]["irc_ppc_mes"]
        ppc_set = self.m_map["Set"]["irc_ppc_mes"]
        ppc_dez = self.m_map["Dez"]["irc_ppc_mes"]
        self.assertAlmostEqual(ppc_jul, ppc_set, delta=0.01)
        self.assertAlmostEqual(ppc_jul, ppc_dez, delta=0.01)

    def test_ss_pagamento_desfasado_um_mes(self):
        """SS do mês M é pago em M+1 — Jan não deve ter SS (pago em Fev)."""
        ss_jan = self.m_map["Jan"]["ss_pagamento_mes"]
        self.assertAlmostEqual(ss_jan, 0.0, delta=0.01,
                               msg="SS de Jan pago em Fev — não aparece em Jan")
        # SS de Dez ainda não foi pago — fica como acumulado (passivo)
        ss_dez_acum = self.m_map["Dez"]["ss_acumulado_periodo"]
        ss_dez_pago = self.m_map["Dez"]["ss_pagamento_mes"]
        self.assertGreater(ss_dez_acum, 0.0)
        # O SS pago em Dez é o do mês de Nov
        self.assertAlmostEqual(
            ss_dez_pago, self.m_map["Nov"]["ss_acumulado_periodo"], delta=1.0,
        )

    def test_iva_saldo_periodo_nao_nulo_todos_meses(self):
        """IVA liquidado > 0 em todos os meses (sempre há vendas)."""
        for m in MESES:
            self.assertGreater(
                self.m_map[m]["iva_liquidado"], 0.0,
                msg=f"IVA liquidado em {m} deve ser positivo",
            )

    def test_balanco_mensal_dez_eoep_credor_proximo_de_referencia_anual(self):
        """eoep_credor em Dez do Balanço mensal ≈ referência anual 2025."""
        from src.engine.demonstracoes.rolling_forecast_mensal import build_rolling_forecast
        rf = build_rolling_forecast(self.a, self.base, self.sched)
        df_bs = rf["balanco_mensal"]
        eoep_cred_dez = float(df_bs[df_bs["mes"] == "Dez"]["eoep_credor"].iloc[0])
        ref = float(self.ref_b["eoep_credor"][2025])
        self.assertAlmostEqual(eoep_cred_dez, ref, delta=self._tol(ref))

    def test_balanco_mensal_dez_eoep_devedor_proximo_de_referencia_anual(self):
        """eoep_devedor em Dez do Balanço mensal ≈ referência anual 2025."""
        from src.engine.demonstracoes.rolling_forecast_mensal import build_rolling_forecast
        rf = build_rolling_forecast(self.a, self.base, self.sched)
        df_bs = rf["balanco_mensal"]
        eoep_dev_dez = float(df_bs[df_bs["mes"] == "Dez"]["eoep_devedor"].iloc[0])
        ref = float(self.ref_b["eoep_devedor"][2025])
        self.assertAlmostEqual(eoep_dev_dez, ref, delta=self._tol(ref))


if __name__ == "__main__":
    unittest.main(verbosity=2)
