"""Shared BigQuery client + config, loaded from .env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("BQ_LOCATION", "US")
MARTS_DATASET = "thelook_marts"
REPO_ROOT = Path(__file__).resolve().parents[1]


def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def ensure_marts_dataset(client: bigquery.Client) -> None:
    dataset_id = f"{PROJECT_ID}.{MARTS_DATASET}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
