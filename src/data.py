"""Pull a marts table from BigQuery into a pandas DataFrame, with a local
parquet cache under data/ (gitignored) so repeat runs don't re-bill BigQuery."""
import pandas as pd

from src.bq_client import MARTS_DATASET, PROJECT_ID, REPO_ROOT, get_client

CACHE_DIR = REPO_ROOT / "data"


def load_table(table_name: str, use_cache: bool = True) -> pd.DataFrame:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{table_name}.parquet"

    if use_cache and cache_path.exists():
        return pd.read_parquet(cache_path)

    client = get_client()
    df = client.query(f"SELECT * FROM `{PROJECT_ID}.{MARTS_DATASET}.{table_name}`").to_dataframe()
    df.to_parquet(cache_path, index=False)
    return df
