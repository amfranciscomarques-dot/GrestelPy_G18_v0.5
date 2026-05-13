import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.engine.operacional import fse
from src.engine.operacional import vendas
from src.engine.inputs import load


def test_fse_mensal_has_values():
    a, b, s = load("Base")
    df_prod = vendas.vendas_anuais(a, b, s)
    df_merc = vendas.vendas_mercadorias_anuais(a, b)
    df_total = vendas.resumo_anual(df_prod, df_merc)

    vn_2024 = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])
    factor = vn_2025 / vn_2024

    result = fse.fse_detalhe_mensal_2025(a, b, factor)
    total = sum(sum(v.values()) for v in result.values())

    assert result
    assert total > 0

