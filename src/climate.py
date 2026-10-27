"""Large-hail hazard trend from NOAA Storm Events (1996-2025), projected to 2030, and why the damage column misleads.

Data: NOAA NCEI Storm Events Database "details" files (US public domain); US CPI-U (FRED CPIAUCSL)
to restate damage in 2025 dollars.

Pipeline
1. Hazard: yearly count of hail reports >= 2 inches (unaffected by the 2010 change of the
   severe-hail criterion to 1 inch), quasi-Poisson GLM with a year trend vs a flat mean.
2. Robustness: share of hail reports that are >= 2 inches, 2010-2025 (consistent criterion).
3. Damage column: yearly count of NWS episodes with >= 10M USD (2025) recorded property damage,
   same trend model, and the yearly share of events that carry any damage estimate.
4. 2030: predictive distribution of the large-hail count (parameter + negative-binomial noise).
5. Check: fit 1996-2015, predict 2016-2025 with the trend model and with the flat mean.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

SEED = 42
BASE_YEAR = 2025
YEARS = np.arange(1996, BASE_YEAR + 1)
LARGE_DAMAGE = 10e6             # 2025 USD per episode
LARGE_HAIL = 2.0                # inches
UNITS = {"K": 1e3, "M": 1e6, "B": 1e9}


def parse_damage(s: pd.Series) -> pd.Series:
    s = s.fillna("0").astype(str).str.strip().str.upper()
    unit = s.str[-1].map(UNITS).fillna(1.0)
    num = pd.to_numeric(s.str.rstrip("KMB").replace("", "0"), errors="coerce").fillna(0.0)
    return num * unit


def load_events(noaa_dir: Path, cpi_csv: Path, cache: Path | None = None) -> pd.DataFrame:
    if cache and cache.exists():
        return pd.read_parquet(cache)
    cols = ["EPISODE_ID", "EVENT_ID", "YEAR", "EVENT_TYPE", "STATE", "MAGNITUDE", "DAMAGE_PROPERTY"]
    df = pd.concat([pd.read_csv(f, usecols=cols, low_memory=False) for f in sorted(glob.glob(str(noaa_dir / "*.csv.gz")))])
    df = df[df["YEAR"].between(YEARS[0], BASE_YEAR)]
    cpi = pd.read_csv(cpi_csv, parse_dates=["observation_date"])
    cpi = cpi.groupby(cpi["observation_date"].dt.year)["CPIAUCSL"].mean()
    df["damage_reported"] = df["DAMAGE_PROPERTY"].notna()
    df["damage"] = parse_damage(df["DAMAGE_PROPERTY"]) * (cpi[BASE_YEAR] / df["YEAR"].map(cpi))
    df = df.drop(columns="DAMAGE_PROPERTY")
    if cache:
        df.to_parquet(cache)
    return df


def fit_trend(counts: pd.Series) -> dict:
    """Quasi-Poisson GLM log(lambda) = a + b * (year - 2010)."""
    t = counts.index.to_numpy().astype(float) - 2010
    m = sm.GLM(counts.to_numpy(), sm.add_constant(t), family=sm.families.Poisson()).fit()
    disp = float(m.pearson_chi2 / m.df_resid)
    se = float(m.bse[1] * np.sqrt(max(disp, 1.0)))
    return {"a": float(m.params[0]), "b": float(m.params[1]), "b_se": se, "dispersion": disp,
            "annual_change": float(np.exp(m.params[1]) - 1),
            "annual_change_ci95": [float(np.exp(m.params[1] - 1.96 * se) - 1), float(np.exp(m.params[1] + 1.96 * se) - 1)]}


def rate(trend: dict, year: int | np.ndarray) -> np.ndarray | float:
    return np.exp(trend["a"] + trend["b"] * (np.asarray(year) - 2010))


def predictive(trend: dict, year: int, sims: int, rng) -> np.ndarray:
    """Counts in `year`: slope drawn from its sampling distribution, negative-binomial noise with the fitted dispersion."""
    b = rng.normal(trend["b"], trend["b_se"], sims)
    lam = np.exp(trend["a"] + b * (year - 2010))
    d = max(trend["dispersion"], 1.0 + 1e-9)
    return rng.negative_binomial(lam / (d - 1), 1 / d)


def poisson_deviance(y: np.ndarray, mu: np.ndarray) -> float:
    return float(2 * np.sum(np.where(y > 0, y * np.log(np.maximum(y, 1e-12) / mu), 0) - (y - mu)))


def run(data_dir: Path, out_dir: Path, sims: int = 200_000) -> tuple[dict, dict]:
    rng = np.random.default_rng(SEED)
    ev = load_events(data_dir / "noaa", data_dir / "cpi_cpiaucsl.csv", data_dir / "events_v2.parquet")
    hail = ev[ev["EVENT_TYPE"] == "Hail"]
    big_hail = hail[hail["MAGNITUDE"] >= LARGE_HAIL].groupby("YEAR").size().reindex(YEARS, fill_value=0)
    all_hail = hail.groupby("YEAR").size().reindex(YEARS, fill_value=0)
    ep = ev[ev["damage"] > 0].groupby("EPISODE_ID").agg(year=("YEAR", "min"), damage=("damage", "sum"))
    big_dmg = ep[ep["damage"] >= LARGE_DAMAGE].groupby("year").size().reindex(YEARS, fill_value=0)
    reported = ev.groupby("YEAR")["damage_reported"].mean().reindex(YEARS)
    nonzero = ev.assign(nz=ev["damage"] > 0).groupby("YEAR")["nz"].mean().reindex(YEARS)

    res: dict = {"events": int(len(ev)), "hail_reports": int(len(hail)), "large_hail_reports": int(big_hail.sum()),
                 "events_per_year_1996_2005": float(ev[ev["YEAR"] <= 2005].groupby("YEAR").size().mean()),
                 "events_per_year_2016_2025": float(ev[ev["YEAR"] >= 2016].groupby("YEAR").size().mean())}

    # 1. hazard trend
    res["large_hail"] = {"trend": fit_trend(big_hail), "mean_1996_2005": float(big_hail.loc[:2005].mean()),
                         "mean_2016_2025": float(big_hail.loc[2016:].mean()), "mean_1996_2025": float(big_hail.mean()),
                         "last3": big_hail.loc[2023:].astype(int).to_dict()}
    # 2. share of hail reports >= 2 in, consistent 1-inch criterion era
    s_years = np.arange(2010, BASE_YEAR + 1)
    t = s_years.astype(float) - 2010
    m = sm.GLM(np.c_[big_hail.loc[s_years], all_hail.loc[s_years] - big_hail.loc[s_years]], sm.add_constant(t),
               family=sm.families.Binomial()).fit(scale="X2")
    share = big_hail / all_hail
    res["large_hail_share"] = {"2010_2014": float(big_hail.loc[2010:2014].sum() / all_hail.loc[2010:2014].sum()),
                               "2021_2025": float(big_hail.loc[2021:].sum() / all_hail.loc[2021:].sum()),
                               "odds_change_per_year": float(np.exp(m.params[1]) - 1), "p_value": float(m.pvalues[1])}
    # 3. damage column
    res["large_damage_episodes"] = {"trend": fit_trend(big_dmg), "mean_1996_2005": float(big_dmg.loc[:2005].mean()),
                                    "mean_2016_2025": float(big_dmg.loc[2016:].mean())}
    res["damage_nonzero_share"] = {"2008_2011": float(nonzero.loc[2008:2011].mean()), "2022_2025": float(nonzero.loc[2022:].mean())}
    res["damage_field_filled"] = {"1996_2006": float(reported.loc[:2006].mean()), "2007_2025": float(reported.loc[2007:].mean())}
    ian = ep[(ep["year"] == 2022)].nlargest(1, "damage")
    res["largest_2022_episode_bn"] = float(ian["damage"].iloc[0] / 1e9)

    # 4. 2030 projection
    tr = res["large_hail"]["trend"]
    p2030 = predictive(tr, 2030, sims, rng)
    res["projection_2030"] = {"mean": float(p2030.mean()), "median": float(np.median(p2030)),
                              "pi80": np.quantile(p2030, [0.1, 0.9]).tolist(), "pi95": np.quantile(p2030, [0.025, 0.975]).tolist(),
                              "vs_30yr_mean": float(p2030.mean() / big_hail.mean() - 1),
                              "prob_above_30yr_mean": float((p2030 > big_hail.mean()).mean())}

    # 5. hold-out
    tr_old = fit_trend(big_hail.loc[:2015])
    test = np.arange(2016, BASE_YEAR + 1)
    obs = big_hail.loc[2016:].to_numpy()
    mu_trend, mu_flat = rate(tr_old, test), np.full(len(test), big_hail.loc[:2015].mean())
    res["holdout"] = {"train_trend": tr_old, "observed_total": int(obs.sum()),
                      "predicted_total_trend": float(mu_trend.sum()), "predicted_total_flat": float(mu_flat.sum()),
                      "deviance_trend": poisson_deviance(obs, mu_trend), "deviance_flat": poisson_deviance(obs, mu_flat)}

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame({"year": YEARS, "hail_reports": all_hail.values, "hail_reports_2in_plus": big_hail.values,
                  "share_2in_plus": share.values, "episodes_damage_10m_plus_usd2025": big_dmg.values,
                  "events": ev.groupby("YEAR").size().reindex(YEARS).values, "share_events_with_damage": nonzero.values,
                  "trend_fit_2in_plus": rate(tr, YEARS)}).to_csv(out_dir / "annual_series.csv", index=False)
    model = {"model": "quasi-Poisson GLM, log(lambda) = a + b * (year - 2010)", "target": "yearly NOAA hail reports >= 2 inches",
             "fit_years": [int(YEARS[0]), BASE_YEAR], **{k: tr[k] for k in ("a", "b", "b_se", "dispersion")},
             "projection_2030": res["projection_2030"]}
    (out_dir / "trend_model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    return res, {"big_hail": big_hail, "all_hail": all_hail, "share": share, "big_dmg": big_dmg, "nonzero": nonzero, "p2030": p2030}
