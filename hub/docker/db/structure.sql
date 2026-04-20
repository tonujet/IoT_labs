CREATE TABLE processed_agent_data (
    id SERIAL PRIMARY KEY,
    road_state VARCHAR(255) NOT NULL,
    rain_state VARCHAR(255) NOT NULL,
    traffic_light_state VARCHAR(255),
    air_quality_state VARCHAR(255),
    user_id INTEGER NOT NULL,
    x FLOAT,
    y FLOAT,
    z FLOAT,
    latitude FLOAT,
    longitude FLOAT,
    rain_intensity FLOAT,
    temperature FLOAT,
    traffic_light_color VARCHAR(10),
    traffic_light_duration INTEGER,
    traffic_light_latitude FLOAT,
    traffic_light_longitude FLOAT,
    pm25 FLOAT,
    pm10 FLOAT,
    co2 FLOAT,
    timestamp TIMESTAMP
);

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    field_name VARCHAR(50) NOT NULL,
    predicted_value FLOAT NOT NULL,
    prediction_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    model_name VARCHAR(100),
    mae FLOAT,
    rmse FLOAT
);