import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://poolzone:poolzone@localhost:5433/poolzone",
    )


settings = Settings()
