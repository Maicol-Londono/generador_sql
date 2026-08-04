"""
engine/profile_loader.py

Carga perfiles de importación compatibles con Profile Schema v1.
"""

import json
from pathlib import Path


class ProfileLoader:

    def __init__(self, profile_path: str):
        self.profile_path = Path(profile_path)
        if not self.profile_path.exists():
            raise FileNotFoundError(f"No existe el perfil: {self.profile_path}")

        with open(self.profile_path, "r", encoding="utf-8") as f:
            self.profile = json.load(f)

    @property
    def table_name(self):
        return self.profile.get("destination", {}).get("table_name")

    @property
    def sheet_name(self):
        return self.profile.get("source", {}).get("sheet_name")

    @property
    def columns(self):
        return self.profile.get("columns", [])

    @property
    def lookups(self):
        return self.profile.get("lookups", {})

    @property
    def batch_size(self):
        return self.profile.get("sql_generation", {}).get("batch_size", 500)

    @property
    def insert_mode(self):
        return self.profile.get("import_strategy", {}).get("mode", "insert")
        
    @property
    def error_policy(self):
        return self.profile.get("error_policy", {"mode": "continue", "max_errors": 100})

    @property
    def sql_generation(self):
        return self.profile.get("sql_generation", {})

    @property
    def ignore_empty_rows(self):
        return self.profile.get("source", {}).get("ignore_empty_rows", True)

    @property
    def data_start_row(self):
        return self.profile.get("source", {}).get("data_start_row", 1)


    def db_columns(self):
        return [
            col["db_column"]
            for col in self.columns
            if not col.get("skip", False)
        ]

    def info(self):
        return {
            "table": self.table_name,
            "sheet": self.sheet_name,
            "columns": len(self.columns)
        }