from pydantic import BaseModel
from app.entities.agent_data import AgentData

class ProcessedAgentData(BaseModel):
    road_state: str
    rain_state: str
    traffic_light_state: str
    air_quality_state: str
    agent_data: AgentData
