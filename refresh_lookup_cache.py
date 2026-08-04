"""
refresh_lookup_cache.py
Script oficial para regenerar cache/lookups.json desde la base de datos de producción.
Obtiene parámetros de conexión directamente desde archivo .env.
"""

import argparse
import json
import pymysql
import sys
from pathlib import Path

def find_env_file():
    """Busca automáticamente el archivo .env en las rutas relativas permitidas."""
    paths_to_check = [
        Path("./.env"),
        Path("../.env"),
        Path("../../.env")
    ]
    for path in paths_to_check:
        if path.exists() and path.is_file():
            return path
    raise RuntimeError("No fue posible localizar un archivo .env automáticamente en (./, ../, ../../). Use --env.")

def parse_env_file(env_path):
    """Extrae las variables de entorno de un archivo .env ignorando comentarios y líneas vacías."""
    env_vars = {}
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip("'\"")
    except Exception as e:
        raise RuntimeError(f"Error al leer el archivo .env ({env_path}): {e}")
    return env_vars

def get_db_connection(env_vars):
    """Construye la conexión a MySQL asegurando que los campos requeridos existan."""
    required_keys = ["DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USERNAME", "DB_PASSWORD"]
    
    missing_keys = [key for key in required_keys if key not in env_vars]
    if missing_keys:
        raise RuntimeError(f"Faltan parámetros obligatorios en el archivo .env: {', '.join(missing_keys)}")
        
    try:
        port = int(env_vars["DB_PORT"])
    except ValueError:
        raise RuntimeError("DB_PORT en .env no es un número válido.")

    try:
        connection = pymysql.connect(
            host=env_vars["DB_HOST"],
            port=port,
            user=env_vars["DB_USERNAME"],
            password=env_vars["DB_PASSWORD"],
            database=env_vars["DB_DATABASE"],
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.Error as e:
        raise RuntimeError(f"Error crítico al conectar a MySQL: {e}")

def fetch_valid_ids(connection, table_name):
    """Obtiene los IDs válidos de una tabla, lanzando excepción si ocurre un error."""
    print(f"Obteniendo IDs válidos de la tabla '{table_name}'...")
    try:
        with connection.cursor() as cursor:
            sql = f"SELECT id FROM `{table_name}`"
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row["id"] for row in rows]
    except Exception as e:
        raise RuntimeError(f"Error al consultar la tabla '{table_name}': {e}")

def main():
    parser = argparse.ArgumentParser(description="Regenerar cache de Lookups desde MySQL (vía .env).")
    parser.add_argument("profile_path", help="Ruta del archivo profile (ej: profiles/wellezy/solicitudes.json)")
    parser.add_argument("--env", help="Ruta explícita al archivo .env (opcional)")
    
    args = parser.parse_args()
    
    try:
        # 1. Resolver archivo .env
        if args.env:
            env_path = Path(args.env)
            if not env_path.exists():
                raise RuntimeError(f"No se encontró el archivo .env especificado en: {env_path}")
        else:
            env_path = find_env_file()
                
        print(f"Utilizando configuración DB desde: {env_path}")
        env_vars = parse_env_file(env_path)
        
        # 2. Leer Profile
        print(f"Leyendo Profile: {args.profile_path}")
        try:
            with open(args.profile_path, "r", encoding="utf-8-sig") as f:
                profile_data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Error al leer el profile: {e}")
            
        lookups = profile_data.get("lookups", {})
        if not lookups:
            print("El profile no define ningún bloque 'lookups'. No hay dependencias para cachear.")
            sys.exit(0)
            
        tables_to_cache = set()
        for lookup_config in lookups.values():
            target = lookup_config.get("target_table")
            if target:
                tables_to_cache.add(target)
                
        if not tables_to_cache:
            print("No se encontraron tablas de destino en el profile.")
            sys.exit(0)
            
        print(f"Tablas identificadas para caché: {', '.join(tables_to_cache)}")
        
        # 3. Construir Conexión y Consultar (Todo o Nada)
        print("Iniciando regeneración de LookupCache...")
        cache_data = {}
        
        connection = get_db_connection(env_vars)
        
        with connection:
            for table in tables_to_cache:
                valid_ids = fetch_valid_ids(connection, table)
                cache_data[table] = valid_ids
                print(f"-> {table}: {len(valid_ids)} IDs recuperados.")
                
        # 4. Guardar resultados
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        
        cache_file = cache_dir / "lookups.json"
        
        # Cargar caché existente si existe para no sobreescribir tablas de otros perfiles
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8-sig") as f:
                    existing_cache = json.load(f)
                    existing_cache.update(cache_data)
                    cache_data = existing_cache
            except Exception:
                pass # Si falla lectura del cache anterior, sobreescribir
                
        with open(cache_file, "w", encoding="utf-8-sig") as f:
            json.dump(cache_data, f, indent=4)
            
        print(f"\nGeneración exitosa. Archivo guardado en: {cache_file}")

    except RuntimeError as e:
        print(f"Error: {e}")
        print("Abortando completamente. No se guardará un caché parcial.")
        sys.exit(1)

if __name__ == "__main__":
    main()
