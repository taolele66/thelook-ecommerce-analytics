"""Run every .sql file under sql/ in directory order, substituting {project}.

Usage:
    python -m src.run_sql              # run everything
    python -m src.run_sql 02_rfm       # run only one stage (folder prefix match)
"""
import sys

from src.bq_client import PROJECT_ID, REPO_ROOT, ensure_marts_dataset, get_client


def main() -> None:
    stage_filter = sys.argv[1] if len(sys.argv) > 1 else None
    client = get_client()
    ensure_marts_dataset(client)

    sql_files = sorted((REPO_ROOT / "sql").glob("*/*.sql"))
    if stage_filter:
        sql_files = [f for f in sql_files if f.parent.name.startswith(stage_filter)]

    if not sql_files:
        print(f"No SQL files matched filter: {stage_filter!r}")
        return

    for path in sql_files:
        print(f"-- running {path.relative_to(REPO_ROOT)}")
        sql = path.read_text().format(project=PROJECT_ID)
        for statement in filter(None, (s.strip() for s in sql.split(";"))):
            job = client.query(statement)
            job.result()
        print(f"   done ({job.total_bytes_billed / 1e6:.1f} MB billed)")


if __name__ == "__main__":
    main()
