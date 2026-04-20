from marshmallow import Schema, fields
from schema.gps_schema import GpsSchema


class TrafficLightSchema(Schema):
    state = fields.Str()
    duration = fields.Int()
    gps = fields.Nested(GpsSchema)
