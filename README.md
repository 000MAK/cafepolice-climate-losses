# Café Poliçe: large hail is growing, damage records are shrinking (NOAA 1996–2025)

[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)

Code, results and the Turkish article *"Dolu Büyüyor, Veri Küçülüyor"* (Café Poliçe): a forward-looking hazard model for hail, projected to 2030, and evidence that the damage column of the same open database understates recent losses.

- Data on Hugging Face: [makactuary/noaa-storm-events-hail-1996-2025](https://huggingface.co/datasets/makactuary/noaa-storm-events-hail-1996-2025)
- Model and 2030 projection: [makactuary/noaa-hail-trend-2030](https://huggingface.co/makactuary/noaa-hail-trend-2030)

## Data

NOAA NCEI [Storm Events Database](https://www.ncei.noaa.gov/stormevents/) "details" files, 1996–2025 (US public domain): 1,780,730 events, 337,858 hail reports. Property damage is parsed ("10.00K", "1.5M") and restated in 2025 dollars with US CPI-U (FRED `CPIAUCSL`). Raw files are downloaded into `data/` (git-ignored); the processed event table is on Hugging Face.

## Results

| | |
|---|---|
| Hail reports ≥ 2 in a year | 527 (1996–2005) → 852 (2016–2025); +2.5% a year (95% CI 1.5–3.5%), quasi-Poisson GLM |
| Share of hail reports ≥ 2 in | 6.0% (2010–14) → 11.3% (2021–25), consistent 1-inch criterion era |
| Hold-out (fit 1996–2015, predict 2016–2025) | trend model 8,539 vs 8,525 observed; flat mean 6,072 (−29%) |
| 2030 projection | 1,096 a year (80% interval 808–1,405), 59% above the 30-year mean |
| Damage column | episodes with ≥ $10M recorded damage fall 3.2% a year; share of events with any damage estimate 27% (2008–11) → 19% (2022–25); Hurricane Ian recorded at $14.5bn vs $112.9bn in NOAA's Billion-Dollar Disasters list |

The hazard measure carried the signal when the loss record did not.

## Run

```bash
pip install -r requirements.txt
# download StormEvents_details-ftp_v1.0_d{1996..2025}_c*.csv.gz into data/noaa/ and
# https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL into data/cpi_cpiaucsl.csv
python -c "import sys; sys.path.insert(0,'src'); from pathlib import Path; from climate import run; from charts import figure; r,a=run(Path('data'), Path('outputs')); figure(r,a,Path('outputs/charts/01_dolu_ve_hasar_kaydi.png'))"
python article/build_article.py
python -m pytest tests -q
```

## Contents

| Path | |
|---|---|
| `src/climate.py` | Parsing, CPI restatement, trend models, 2030 predictive distribution, hold-out |
| `src/charts.py` | Article figure |
| `outputs/metrics.json`, `outputs/trend_model.json`, `outputs/annual_series.csv` | All reported numbers, model parameters, yearly series |
| `article/` | Article (.docx, .pdf, .md) and its build script |

## Limitations

US data; economic damage estimates, not insured losses. Hail report counts depend on observers and population; the share analysis reduces but does not remove this. The data cannot separate climate from reporting and building growth.

## Licence

Code: MIT. Data: NOAA NCEI, US public domain.
