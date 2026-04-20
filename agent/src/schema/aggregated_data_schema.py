from marshmallow import Schema, fields
from schema.accelerometer_schema import AccelerometerSchema
from schema.gps_schema import GpsSchema
from schema.parking_schema import ParkingSchema
from schema.rain_schema import RainSchema
from schema.traffic_light_schema import TrafficLightSchema
from schema.air_quality_schema import AirQualitySchema

class AggregatedDataSchema(Schema):
    accelerometer = fields.Nested(AccelerometerSchema)
    gps = fields.Nested(GpsSchema)
    parking = fields.Nested(ParkingSchema)
    rain = fields.Nested(RainSchema)
    traffic_light = fields.Nested(TrafficLightSchema)
    air_quality = fields.Nested(AirQualitySchema)
    temperature = fields.Number()
    timestamp = fields.DateTime("iso")
    user_id = fields.Int()
