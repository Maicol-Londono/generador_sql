import re

class Validator:
    @staticmethod
    def is_valid_email(email):
        if not email:
            return False
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, str(email)) is not None

    @classmethod
    def validate(cls, value, validators, nullable=True):
        if value is None or not validators:
            return value

        for v in validators:
            if v == "is_valid_email":
                if not cls.is_valid_email(value):
                    if nullable:
                        return None
                    else:
                        raise ValueError(f"Validation error: '{value}' is not a valid email.")
        return value
