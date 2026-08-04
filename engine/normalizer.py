"""
engine/normalizer.py

Funciones para normalizar valores provenientes de Excel.
No conocen nada del modelo de datos.
"""

from datetime import datetime
from dateutil.parser import parse


class Normalizer:

    @staticmethod
    def text(value, max_length=None):

        if value is None:
            return None

        value = str(value).strip()

        if value == "":
            return None

        if value.lower() in (
            "nan",
            "none",
            "null",
            "no tiene",
            "n/a",
        ):
            return None

        value = " ".join(value.split())

        if max_length:
            value = value[:max_length]

        return value

    @staticmethod
    def integer(value):

        if value in (None, ""):
            return None

        try:
            return int(float(value))
        except:
            return None

    @staticmethod
    def decimal(value):

        if value in (None, ""):
            return None

        try:
            return float(value)
        except:
            return None

    @staticmethod
    def date(value):

        if value in (None, ""):
            return None

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")

        try:
            return parse(
                str(value),
                dayfirst=False,
                fuzzy=True
            ).strftime("%Y-%m-%d")
        except:
            return None

    @staticmethod
    def boolean(value):

        if value in (
            True,
            1,
            "1",
            "true",
            "True",
            "SI",
            "Sí",
            "YES",
        ):
            return True

        return False