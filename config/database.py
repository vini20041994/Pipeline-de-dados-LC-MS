import os
from sqlalchemy import create_engine


def get_database_url() -> str:
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "quimioanalytics")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_engine(echo: bool = False):
    schema = os.getenv("DB_SCHEMA", "quimioanalytics")
    return create_engine(
        get_database_url(),
        echo=echo,
        future=True,
        connect_args={"options": f"-csearch_path={schema},public"},
    )
