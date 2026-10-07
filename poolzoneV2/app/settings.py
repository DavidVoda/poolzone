import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://poolzone:poolzone@localhost:5433/poolzone",
)

# "production" locks the app down: every /api route requires a logged-in user.
# Anything else (dev default) leaves localhost open so curl / the feature-runner
# keep working without auth.
ENV = os.environ.get("POOLZONE_ENV", "development")
IS_PRODUCTION = ENV == "production"

# Session cookie signing key. A fixed dev default keeps logins working across
# reloads; production MUST set its own (enforced below).
SECRET_KEY = os.environ.get("POOLZONE_SECRET_KEY", "dev-insecure-secret-change-me")

if IS_PRODUCTION and SECRET_KEY == "dev-insecure-secret-change-me":
    raise RuntimeError("POOLZONE_SECRET_KEY must be set in production")
