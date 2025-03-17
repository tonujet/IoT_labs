from marshmallow import Schema, fields


class RainSchema(Schema):
    intensity = fields.Number()
