CREATE TABLE processed_agent_data (
    id SERIAL PRIMARY KEY,
    road_state VARCHAR(255) NOT NULL,
    rain_state VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    x FLOAT,
    y FLOAT,
    z FLOAT,
    latitude FLOAT,
    longitude FLOAT,
    rain_intensity FLOAT,
    temperature FLOAT,
    timestamp TIMESTAMP
);