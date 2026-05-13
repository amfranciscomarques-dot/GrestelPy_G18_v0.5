import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

import unittest


class TestFseReconciliations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.engine.inputs import load, YEARS
        from src.engine.demonstracoes.dr import build_dr
        from src.engine.financiamento.tesouraria import build_dr_mensal
        from src.engine.operacional.fse import FSE_DETALHE_KEYS

        cls.YEARS = YEARS
        cls.a, cls.base, cls.sched = load(cenario="Base")

        # DR anual: coluna 'fse' e detalhe por rubrica em sinal financeiro (custos negativos na DR).
        cls.dr_anual = build_dr(cls.a, cls.base, cls.sched)
        # DR mensal 2025: detalhe de FSE por rubrica em sinal positivo (custos positivos na tabela mensal).
        cls.dr_mensal = build_dr_mensal(cls.a, cls.base, cls.sched)

        cls.dr_anual_by_year = {int(r["ano"]): r for _, r in cls.dr_anual.iterrows()}
        cls.monthly_sum_2025_by_col = {
            col: float(cls.dr_mensal[col].sum()) for col in FSE_DETALHE_KEYS.values()
        }
        cls.fse_cols_by_rub = FSE_DETALHE_KEYS

    def test_2025_mensal_rubricas_fecha_com_dr_anual(self):
        # DR anual (custos) é negativo; DR mensal detalhado é positivo.
        year = 2025
        dr_row = self.dr_anual_by_year.get(year)
        self.assertIsNotNone(dr_row)

        # Teste de reconciliação TOTAL (não rubrica a rubrica, que pode ter diferenças por reconciliação)
        total_anual = 0.0
        total_mensal = 0.0
        for rub, col in self.fse_cols_by_rub.items():
            total_anual += -float(dr_row.get(col, 0.0) or 0.0)
            total_mensal += self.monthly_sum_2025_by_col.get(col, 0.0)

        # Tolerância para arredondamentos (< 0.1% do total)
        tol = max(1.0, total_anual * 0.001)
        self.assertAlmostEqual(total_mensal, total_anual, delta=tol)

    def test_rubricas_fecha_com_fse_total_no_dr_anual(self):
        # Na DR anual, fse é agregado (negativo); detalhe deve somar para fechar no mesmo sinal.
        for year in self.YEARS:
            dr_row = self.dr_anual_by_year.get(year)
            self.assertIsNotNone(dr_row)

            fse_total = float(dr_row.get("fse", 0.0) or 0.0)
            rub_sum = 0.0
            for _, col in self.fse_cols_by_rub.items():
                rub_sum += float(dr_row.get(col, 0.0) or 0.0)

            tol = max(1.0, abs(fse_total) * 1e-6)
            self.assertAlmostEqual(rub_sum, fse_total, delta=tol)


if __name__ == "__main__":
    unittest.main()

