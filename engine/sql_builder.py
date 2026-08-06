"""
engine/sql_builder.py

Generador universal de sentencias SQL (INSERT, UPDATE).
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
    def build(cls, mode, table, columns, rows, search_keys=None, update_columns=None):
        if mode == "update":
            return cls._update(table, update_columns or [], search_keys or [], rows)
        else:
            return cls._insert(table, columns, rows)

    @classmethod
    def _insert(cls, table, columns, rows):
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

    @classmethod
    def _update(cls, table, update_columns, search_keys, rows):
        sql = []
        for row in rows:
            set_statements = []
            for col in update_columns:
                set_statements.append(f"{col} = {cls._value(row.get(col))}")
            
            where_statements = []
            for key in search_keys:
                where_statements.append(f"{key} = {cls._value(row.get(key))}")
                
            sql.append(f"UPDATE {table} SET {', '.join(set_statements)} WHERE {' AND '.join(where_statements)};")
        
        return "\n".join(sql)