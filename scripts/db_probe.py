import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def main() -> None:
    load_dotenv()

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")
    db = os.getenv("DB_NAME")

    if not all([host, port, user, pwd, db]):
        raise RuntimeError("DB env vars are missing in .env")

    root_url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/"
    db_url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"

    root_engine = create_engine(root_url, pool_pre_ping=True)
    db_engine = create_engine(db_url, pool_pre_ping=True)

    print("CONNECTED_ROOT_OK")
    with root_engine.connect() as conn:
        databases = [row[0] for row in conn.execute(text("SHOW DATABASES"))]
        print("DATABASES:", ", ".join(databases))

    print("CONNECTED_DB_OK:", db)
    with db_engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text("SHOW TABLES"))]
        print("TABLE_COUNT:", len(tables))
        print("TABLES:", ", ".join(tables) if tables else "(none)")
        for table in tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()
            print(f"ROWS {table}: {count}")


if __name__ == "__main__":
    main()
