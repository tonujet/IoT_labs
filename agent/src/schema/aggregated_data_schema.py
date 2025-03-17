from marshmallow import Schema, fields
from schema.accelerometer_schema import AccelerometerSchema
from schema.gps_schema import GpsSchema
from schema.parking_schema import ParkingSchema
from schema.rain_schema import RainSchema

class AggregatedDataSchema(Schema):
    accelerometer = fields.Nested(AccelerometerSchema)
    gps = fields.Nested(GpsSchema)
    parking = fields.Nested(ParkingSchema)
    rain = fields.Nested(RainSchema)
    temperature = fields.Number()
    timestamp = fields.DateTime("iso")
    user_id = fields.Int()
