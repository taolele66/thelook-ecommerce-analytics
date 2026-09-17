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
| `rfm_user_detail.csv` | RFM quadrant scatter | X = `frequency`, Y = `monetary`, color = `user_segment` (keep the segment colors below), size = `recency_days` (inverted, so recent = larger). Add two reference lines at the median of each axis to split the four quadrants. One row per user (72K) — expect Tableau to sample/aggregate at low zoom; that's expected. |
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

Put all four sheets on one dashboard and add a **filter action**: source =
the RFM quadrant scatter (or the segment field on any sheet), target = the
other three sheets, run on select. Clicking a segment (or a country on the
map) then filters the whole dashboard to it — this is the specific Tableau
capability that's worth calling out on a resume over a static screenshot.

## Publishing

Publish the finished workbook to Tableau Public (not Tableau Cloud — the
Cloud trial expires; Public is free indefinitely and gives a stable
shareable link). Add that link and a screenshot to the main
[README](../README.md#screenshots) once published.
