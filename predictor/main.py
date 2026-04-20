"""
ML Predictor Service — time series prediction.
Reads historical data from PostgreSQL, trains models,
writes predictions back to DB for Grafana visualization.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from config import (
    DATABASE_URL, PREDICTION_INTERVAL,
    PREDICTION_STEPS, HISTORY_SIZE
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Lazy engine creation — only connects to DB when first needed."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


ALLOWED_FIELDS = {"temperature", "pm25"}


def fetch_historical_data(field: str, limit: int = 100) -> List[Tuple[datetime, float]]:
    """Fetch last N records from DB.

    Args:
        field: column name to fetch — must be in ALLOWED_FIELDS whitelist.
        limit: maximum number of records to return.

    Raises:
        ValueError: if field is not in the whitelist (prevents SQL injection).
    """
    if field not in ALLOWED_FIELDS:
        raise ValueError(
            f"Invalid field '{field}'. Allowed: {ALLOWED_FIELDS}"
        )
    # field is validated against ALLOWED_FIELDS above, safe to interpolate.
    with get_engine().connect() as conn:
        result = conn.execute(text(f"""
            SELECT timestamp, {field}
            FROM processed_agent_data
            WHERE {field} IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT :limit
        """), {"limit": limit})
        rows = result.fetchall()
    # Reverse so oldest come first
    return [(row[0], row[1]) for row in reversed(rows)]


def train_and_predict_linear(
    data: List[Tuple[datetime, float]], steps: int = 20
) -> Tuple[Optional[List[float]], Optional[float], Optional[float]]:
    """
    Linear Regression — simple baseline.
    Returns: predictions, mae, rmse
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    values = np.array([d[1] for d in data])
    n = len(values)

    if n < 10:
        return None, None, None

    # Train/test split: 80/20
    split = int(n * 0.8)
    X_train = np.arange(split).reshape(-1, 1)
    y_train = values[:split]
    X_test = np.arange(split, n).reshape(-1, 1)
    y_test = values[split:]

    model = LinearRegression()
    model.fit(X_train, y_train)

    # Metrics on test set
    y_pred_test = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

    # Predict steps ahead
    X_future = np.arange(n, n + steps).reshape(-1, 1)
    predictions = model.predict(X_future)

    return predictions.tolist(), float(mae), float(rmse)


def train_and_predict_moving_avg(
    data: List[Tuple[datetime, float]], window: int = 10, steps: int = 20
) -> Tuple[Optional[List[float]], Optional[float], Optional[float]]:
    """
    Moving Average — another baseline.
    More robust to noise than linear regression.
    """
    values = np.array([d[1] for d in data])
    n = len(values)

    if n < window:
        return None, None, None

    # Metrics: MAE on last window records
    last_window = values[-window:]
    avg = np.mean(last_window)
    mae = np.mean(np.abs(last_window - avg))
    rmse = np.sqrt(np.mean((last_window - avg) ** 2))

    # Prediction: repeat average with slight trend
    trend = (values[-1] - values[-window]) / window if window > 1 else 0
    predictions = [avg + trend * i for i in range(1, steps + 1)]

    return predictions, float(mae), float(rmse)


def save_predictions(field: str, predictions: List[float],
                     timestamps: List[datetime],
                     model_name: str, mae: float, rmse: float) -> None:
    """Save predictions to the predictions table."""
    with get_engine().connect() as conn:
        for pred_val, pred_ts in zip(predictions, timestamps):
            conn.execute(text("""
                INSERT INTO predictions
                    (field_name, predicted_value, prediction_timestamp,
                     model_name, mae, rmse)
                VALUES
                    (:field, :value, :ts, :model, :mae, :rmse)
            """), {
                "field": field,
                "value": float(pred_val),
                "ts": pred_ts,
                "model": model_name,
                "mae": mae,
                "rmse": rmse,
            })
        conn.commit()
    logging.info(f"Saved {len(predictions)} predictions for {field} ({model_name})")


def run_prediction_cycle() -> None:
    """One prediction cycle for all fields."""
    for field in ALLOWED_FIELDS:
        data = fetch_historical_data(field, limit=HISTORY_SIZE)
        if len(data) < 10:
            logging.warning(f"Not enough data for {field}: {len(data)} records")
            continue

        # Model 1: Linear Regression
        preds_lr, mae_lr, rmse_lr = train_and_predict_linear(data, PREDICTION_STEPS)
        if preds_lr:
            last_ts = data[-1][0]
            # Approximate interval between records
            if len(data) > 1:
                interval = (data[-1][0] - data[-2][0])
            else:
                interval = timedelta(seconds=1)
            future_timestamps = [last_ts + interval * (i + 1) for i in range(PREDICTION_STEPS)]
            save_predictions(field, preds_lr, future_timestamps,
                           "LinearRegression", mae_lr, rmse_lr)

        # Model 2: Moving Average
        preds_ma, mae_ma, rmse_ma = train_and_predict_moving_avg(data, window=10,
                                                                   steps=PREDICTION_STEPS)
        if preds_ma:
            last_ts = data[-1][0]
            if len(data) > 1:
                interval = (data[-1][0] - data[-2][0])
            else:
                interval = timedelta(seconds=1)
            future_timestamps = [last_ts + interval * (i + 1) for i in range(PREDICTION_STEPS)]
            save_predictions(field, preds_ma, future_timestamps,
                           "MovingAverage", mae_ma, rmse_ma)


def main() -> None:
    """Main loop: wait for data, then predict periodically."""
    logging.info("Predictor service started")
    logging.info(f"Interval: {PREDICTION_INTERVAL}s, Steps: {PREDICTION_STEPS}")

    while True:
        try:
            run_prediction_cycle()
        except Exception as e:
            logging.error(f"Prediction cycle failed: {e}")
        time.sleep(PREDICTION_INTERVAL)


if __name__ == "__main__":
    main()
