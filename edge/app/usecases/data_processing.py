import logging

from app.entities.agent_data import AgentData
from app.entities.processed_agent_data import ProcessedAgentData

data_points = []
MAX_DATA_POINTS = 5
ANOMALY_THRESHOLD = 0.01


def process_agent_data(
        agent_data: AgentData,
) -> ProcessedAgentData:
    road_state = process_road_state(agent_data)
    rain_state = process_rain_state(agent_data)
    traffic_light_state = process_traffic_light_state(agent_data)
    air_quality_state = process_air_quality_state(agent_data)
    prep = ProcessedAgentData(
        road_state=road_state,
        rain_state=rain_state,
        traffic_light_state=traffic_light_state,
        air_quality_state=air_quality_state,
        agent_data=agent_data,
    )
    logging.info(prep)
    return prep


def process_road_state(agent_data: AgentData):
    data_points.append(agent_data.accelerometer)

    if len(data_points) > MAX_DATA_POINTS:
        data_points.pop(0)

    if len(data_points) < 2:
        return "Not enough data"

    last_point = data_points[-1]
    prev_points = data_points[:-1]

    is_upper_anomaly = all(
        last_point.z > prev_point.z * (1 + ANOMALY_THRESHOLD) for prev_point in prev_points)
    is_lower_anomaly = all(
        last_point.z < prev_point.z * (1 - ANOMALY_THRESHOLD) for prev_point in prev_points)

    if is_upper_anomaly:
        road_state = "Speeding bump"
    elif is_lower_anomaly:
        road_state = "Pit"
    else:
        road_state = "Even"

    return road_state

def process_rain_state(agent_data: AgentData):
    intensity = agent_data.rain.intensity
    if intensity == 0:
        return "Clear"
    elif 0 < intensity <= 0.2:
        return "Drizzle"
    elif 0.2 < intensity <= 0.4:
        return "Sprinkle"
    elif 0.4 < intensity <= 0.6:
        return "Shower"
    elif 0.6 < intensity <= 0.8:
        return "Rain"
    elif 0.8 < intensity <= 1:
        return "Downpour"
    else:
        return "Invalid intensity"


def process_traffic_light_state(agent_data: AgentData) -> str:
    """Classify safety based on traffic light state and time until change"""
    state = agent_data.traffic_light.state
    duration = agent_data.traffic_light.duration
    if state == "green" and duration > 10:
        return "Safe to go"
    elif state == "green" and duration <= 10:
        return "Caution"
    elif state == "yellow":
        return "Caution"
    else:  # red
        return "Stop"


def process_air_quality_state(agent_data: AgentData) -> str:
    """Classify air quality by PM2.5 (AQI standard)"""
    pm25 = agent_data.air_quality.pm25
    if pm25 <= 12:
        return "Good"
    elif pm25 <= 35.4:
        return "Moderate"
    elif pm25 <= 55.4:
        return "Unhealthy for Sensitive"
    elif pm25 <= 150.4:
        return "Unhealthy"
    elif pm25 <= 250.4:
        return "Very Unhealthy"
    else:
        return "Hazardous"
