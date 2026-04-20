from marshmallow import Schema, fields


class AirQualitySchema(Schema):
    pm25 = fields.Float()
    pm10 = fields.Float()
    co2 = fields.Float()
