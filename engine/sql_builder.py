"""
engine/sql_builder.py

Generador universal de sentencias INSERT.
"""


class SQLBuilder:

    @staticmethod
    def _value(value):

        if value is None:
            return "NULL"

        if isinstance(value, bool):
            return "1" if value else "0"

        if isinstance(value, (int, float)):
            return str(value)

        value = str(value)

        value = value.replace("\\", "\\\\")
        value = value.replace("'", "''")

        return f"'{value}'"

    @classmethod
    def insert(cls, table, columns, rows):

        sql = []

        sql.append(f"INSERT INTO {table}")

        sql.append("(")
        sql.append(", ".join(columns))
        sql.append(")")

        sql.append("VALUES")

        registros = []

        for row in rows:

            valores = []

            for column in columns:
                valores.append(cls._value(row.get(column)))

            registros.append("(" + ", ".join(valores) + ")")

        sql.append(",\n".join(registros))

        sql.append(";")

        return "\n".join(sql)