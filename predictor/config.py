import os

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "pass")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "test_db")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

PREDICTION_INTERVAL = int(os.environ.get("PREDICTION_INTERVAL", 30))  # seconds
PREDICTION_STEPS = int(os.environ.get("PREDICTION_STEPS", 20))        # steps ahead
HISTORY_SIZE = int(os.environ.get("HISTORY_SIZE", 100))                # records for training
