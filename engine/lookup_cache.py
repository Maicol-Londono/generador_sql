import json
from pathlib import Path

class LookupCache:
    def __init__(self, cache_file="cache/lookups.json"):
        cache_path = Path(cache_file)
        if not cache_path.exists():
            raise FileNotFoundError(f"Error crítico: El archivo de caché {cache_file} no existe. Debe regenerarse el cache usando refresh_lookup_cache.py.")
            
        with open(cache_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
            
        self.data = {}
        for table, ids in raw_data.items():
            self.data[table] = set(ids)

    def exists(self, table_name, record_id):
        if table_name not in self.data:
            return False
        return record_id in self.data[table_name]
