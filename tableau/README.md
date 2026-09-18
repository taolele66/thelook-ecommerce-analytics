# Tableau layer

A third presentation layer alongside Looker Studio and the Streamlit app,
built for the two chart types Tableau does better than either: a
geographic map and a linked, click-to-filter dashboard.

Tableau Public's free tier has no live BigQuery connector — it only reads
files (CSV/Excel/Google Sheets/spatial). `src/export_tableau.py` produces
the four CSVs in `tableau/data/`, each shaped for one specific chart rather
than being a raw table dump. Regenerate them any time with:

```bash
python -m src.export_tableau
```

## The four sheets

| File | Chart | Build notes |
|---|---|---|
| `country_gmv_map.csv` | Filled/symbol map of GMV & users by country | Country names are pre-normalized (`Brasil`→`Brazil`, `Deutschland`→`Germany` — this dataset has both spellings for the same country) so Tableau's built-in geocoding resolves every row. Drag `country` to the map, `users` or `gmv` to color/size. |
| `rfm_user_detail.csv` | RFM quadrant scatter | X = `frequency`, Y = `monetary`, color = `user_segment` (keep the segment colors below), size = `recency_days` (inverted, so recent = larger). Add two reference lines at the median of each axis to split the four quadrants. Also carries `country` (normalized the same way as the map export) so a filter action can link it to the map — see Dashboard actions below. One row per user (72K); in Tableau, turn off **Analysis → Aggregate Measures** so `frequency`/`monetary` plot per-user instead of summing overlapping points, and set the size field's aggregation to **Average** (not Sum), or a handful of overlapping points will render as one oversized mark. |
| `cohort_retention.csv` | Cohort highlight table | Rows = `cohort_month`, columns = `months_since_signup`, color + label = `retention_rate`. Use Analysis → Create Calculated Field only if you want a %-formatted label; the raw column is already 0–1. |
| `category_affinity_matrix.csv` | Category × category lift heatmap | Already mirrored into a full square matrix (both `(A,B)` and `(B,A)` rows), so `category_a` on rows and `category_b` on columns works directly — no calculated field needed. Color by `lift`; a diverging palette centered at 1.0 reads best (below 1 = bought together less than chance, above 1 = more). |

## Segment colors (match the Streamlit app)

Reuse the same fixed mapping so a reader sees one consistent segment
identity across every artifact in this repo — colors are the Wong (2011,
*Nature Methods*) colorblind-safe palette:

| Segment | Hex |
|---|---|
| 高价值活跃用户 | `#0072B2` |
| 新用户/潜力用户 | `#009E73` |
| 一般用户 | `#E69F00` |
| 沉睡/低价值用户 | `#CC79A7` |
| 高价值流失预警 | `#D55E00` |

## Dashboard actions

The four CSVs each feed one chart and otherwise share no common field —
`cohort_retention.csv` and `category_affinity_matrix.csv` are global
aggregates with no country or segment column, so they can't be filtered by
the other charts. The one pair that *can* link is the map and the RFM
scatter, since `rfm_user_detail.csv` carries `country`: add a **filter
action** (Dashboard → Actions → Add Action → Filter) with source = the map,
target = the RFM scatter, field = Country → Country, run on select.
Clicking a country on the map then filters the scatter to it.

## Publishing

Tableau Public only accepts workbooks whose data sources are **extracts**,
not live file connections — a workbook built in Tableau Cloud (which uses
live connections) will fail to publish with "must use an extract" until
each data source is converted (right-click the connection → Extract Data).
The simpler path: build directly in **Tableau Public Desktop** (free)
connected straight to the CSVs in `tableau/data/` — Public Desktop only
ever creates extracts, so this sidesteps the conversion step entirely.

Published workbook: [TheLook E-commerce Analytics](https://public.tableau.com/app/profile/winter.lee/viz/TheLookE-commerceAnalytics/E-commerceCustomerAnalytics).
