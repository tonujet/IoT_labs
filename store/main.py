import asyncio
import json
from typing import Set, Dict, List, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    text,
)
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pydantic import BaseModel, field_validator
from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

# FastAPI app setup
app = FastAPI()

# SQLAlchemy setup
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define the ProcessedAgentData table
processed_agent_data = Table(
    "processed_agent_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("road_state", String),
    Column("rain_state", String),
    Column("traffic_light_state", String),
    Column("air_quality_state", String),
    Column("user_id", Integer),
    Column("x", Float),
    Column("y", Float),
    Column("z", Float),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("rain_intensity", Float),
    Column("temperature", Float),
    Column("traffic_light_color", String),
    Column("traffic_light_duration", Integer),
    Column("traffic_light_latitude", Float),
    Column("traffic_light_longitude", Float),
    Column("pm25", Float),
    Column("pm10", Float),
    Column("co2", Float),
    Column("timestamp", DateTime),
)
SessionLocal = sessionmaker(bind=engine)

# FastAPI models
class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float

class RainData(BaseModel):
    intensity: float


class GpsData(BaseModel):
    latitude: float
    longitude: float


class TrafficLightData(BaseModel):
    state: str         # "red", "yellow", "green"
    duration: int
    gps: GpsData


class AirQualityData(BaseModel):
    pm25: float
    pm10: float
    co2: float


class AgentData(BaseModel):
    user_id: int
    accelerometer: AccelerometerData
    gps: GpsData
    rain: RainData
    traffic_light: TrafficLightData
    air_quality: AirQualityData
    temperature: float
    timestamp: datetime

    @classmethod
    @field_validator("timestamp", mode="before")
    def check_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid timestamp format. Expected ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)."
            )

class ProcessedAgentData(BaseModel):
    road_state: str
    rain_state: str
    traffic_light_state: str
    air_quality_state: str
    agent_data: AgentData

# WebSocket subscriptions
subscriptions: Dict[int, Set[WebSocket]] = {}

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    if user_id not in subscriptions:
        subscriptions[user_id] = set()
    subscriptions[user_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        subscriptions[user_id].remove(websocket)

# Function to send data to subscribers
async def send_data_to_subscribers(user_id: int, data):
    if user_id in subscriptions:
        for websocket in subscriptions[user_id]:
            await websocket.send_json(json.dumps(data, default=str))


# CRUD Operations
@app.post("/processed_agent_data/")
async def create_processed_agent_data(data: List[ProcessedAgentData]):
    db = SessionLocal()
    try:
        for record in data:
            agent_data = record.agent_data
            db.execute(processed_agent_data.insert().values(
                road_state=record.road_state,
                rain_state=record.rain_state,
                traffic_light_state=record.traffic_light_state,
                air_quality_state=record.air_quality_state,
                user_id=agent_data.user_id,
                x=agent_data.accelerometer.x,
                y=agent_data.accelerometer.y,
                z=agent_data.accelerometer.z,
                latitude=agent_data.gps.latitude,
                longitude=agent_data.gps.longitude,
                rain_intensity=agent_data.rain.intensity,
                temperature=agent_data.temperature,
                traffic_light_color=agent_data.traffic_light.state,
                traffic_light_duration=agent_data.traffic_light.duration,
                traffic_light_latitude=agent_data.traffic_light.gps.latitude,
                traffic_light_longitude=agent_data.traffic_light.gps.longitude,
                pm25=agent_data.air_quality.pm25,
                pm10=agent_data.air_quality.pm10,
                co2=agent_data.air_quality.co2,
                timestamp=agent_data.timestamp
            ))
            await send_data_to_subscribers(agent_data.user_id, record.dict())
        db.commit()
        return {"status": "Data saved and sent to WebSocket subscribers"}
    finally:
        db.close()

@app.get("/processed_agent_data/{processed_agent_data_id}")
def read_processed_agent_data(processed_agent_data_id: int):
    db = SessionLocal()
    try:
        result = db.execute(
            processed_agent_data.select().where(processed_agent_data.c.id == processed_agent_data_id)
        ).fetchone()
        if result:
            return dict(result._mapping)
        raise HTTPException(status_code=404, detail="Data not found")
    finally:
        db.close()

@app.get("/processed_agent_data/")
def list_processed_agent_data():
    db = SessionLocal()
    try:
        results = db.execute(processed_agent_data.select()).fetchall()
        return [dict(row._mapping) for row in results]
    finally:
        db.close()

@app.put("/processed_agent_data/{processed_agent_data_id}")
def update_processed_agent_data(processed_agent_data_id: int, data: ProcessedAgentData):
    db = SessionLocal()
    try:
        agent_data = data.agent_data
        db.execute(
            processed_agent_data.update()
            .where(processed_agent_data.c.id == processed_agent_data_id)
            .values(
                road_state=data.road_state,
                rain_state=data.rain_state,
                traffic_light_state=data.traffic_light_state,
                air_quality_state=data.air_quality_state,
                user_id=agent_data.user_id,
                x=agent_data.accelerometer.x,
                y=agent_data.accelerometer.y,
                z=agent_data.accelerometer.z,
                latitude=agent_data.gps.latitude,
                longitude=agent_data.gps.longitude,
                rain_intensity=agent_data.rain.intensity,
                temperature=agent_data.temperature,
                traffic_light_color=agent_data.traffic_light.state,
                traffic_light_duration=agent_data.traffic_light.duration,
                traffic_light_latitude=agent_data.traffic_light.gps.latitude,
                traffic_light_longitude=agent_data.traffic_light.gps.longitude,
                pm25=agent_data.air_quality.pm25,
                pm10=agent_data.air_quality.pm10,
                co2=agent_data.air_quality.co2,
                timestamp=agent_data.timestamp,
            )
        )
        db.commit()
        return {"status": "Updated"}
    finally:
        db.close()

@app.delete("/processed_agent_data/{processed_agent_data_id}")
def delete_processed_agent_data(processed_agent_data_id: int):
    db = SessionLocal()
    try:
        db.execute(
            processed_agent_data.delete().where(processed_agent_data.c.id == processed_agent_data_id)
        )
        db.commit()
        return {"status": "Deleted"}
    finally:
        db.close()

@app.get("/metrics/summary")
def get_metrics_summary():
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT
                COUNT(*) as total_records,
                ROUND(AVG(temperature)::numeric, 2) as avg_temp,
                ROUND(AVG(rain_intensity)::numeric, 2) as avg_rain,
                ROUND(AVG(pm25)::numeric, 2) as avg_pm25,
                COUNT(CASE WHEN road_state = 'Pit' THEN 1 END) as potholes,
                COUNT(CASE WHEN road_state = 'Speeding bump' THEN 1 END) as bumps,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record
            FROM processed_agent_data
        """)).fetchone()
        return dict(result._mapping)
    finally:
        db.close()


@app.get("/metrics/timeseries")
def get_timeseries(field: str = "temperature", limit: int = 100):
    allowed_fields = ["temperature", "rain_intensity", "x", "y", "z", "pm25", "pm10", "co2"]
    if field not in allowed_fields:
        raise HTTPException(400, f"Field must be one of: {allowed_fields}")
    db = SessionLocal()
    try:
        # field is validated against allowed_fields above — safe to interpolate.
        results = db.execute(text(
            f"SELECT timestamp, {field} FROM processed_agent_data ORDER BY timestamp DESC LIMIT :limit"
        ), {"limit": limit}).fetchall()
        return [dict(row._mapping) for row in results]
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
