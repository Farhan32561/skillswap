# Farhan's part
from bson import ObjectId


class ObjectIdConverter:
    regex = '[0-9a-fA-F]{24}'

    def to_python(self, value):
        return ObjectId(value)

    def to_url(self, value):
        return str(value)
