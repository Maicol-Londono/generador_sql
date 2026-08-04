"""
engine/pipeline.py

Orquesta el proceso completo de importación.

Flujo:

Profile
    ↓
Reader
    ↓
Mapper (con ErrorManager)
    ↓
SQLBuilder & ReportGenerator
    ↓
Archivos SQL y Reportes
"""

from pathlib import Path
import datetime

from engine.reader import ExcelReader
from engine.profile_loader import ProfileLoader
from engine.mapper import Mapper
from engine.sql_builder import SQLBuilder
from engine.error_manager import ErrorManager
from engine.report import ReportGenerator


class Pipeline:

    def __init__(
        self,
        profile_path: str,
        input_file: str,
        output_directory: str = "output/sql"
    ):
        self.profile_path = profile_path
        self.input_file = input_file
        self.output_directory = Path(output_directory)

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    def run(self):
        start_time = datetime.datetime.now()
        
        print("===================================")
        print("GENERADOR SQL")
        print("===================================")

        print("Cargando Profile...")
        profile = ProfileLoader(self.profile_path)
        print(f"Tabla destino : {profile.table_name}")
        print(f"Hoja Excel    : {profile.sheet_name}")
        print()
        
        error_manager = ErrorManager(profile.error_policy)

        print("Leyendo Excel...")
        reader = ExcelReader(self.input_file)
        rows = reader.read_sheet(
            profile.sheet_name,
            header_row=0,
            data_start_row=profile.data_start_row,
            ignore_empty_rows=profile.ignore_empty_rows
        )
        rows_read = len(rows)
        print(f"Registros encontrados: {rows_read}\n")

        print("Mapeando registros...")
        mapper = Mapper(profile, error_manager)
        registros = mapper.map_rows(rows)
        print(f"Registros procesados: {len(registros)}\n")
        
        if registros:
            print("Generando SQL...")
            
            db_columns = profile.db_columns()
            if profile.profile.get("timestamps", False):
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for registro in registros:
                    registro["created_at"] = current_time
                    registro["updated_at"] = current_time
                db_columns.extend(["created_at", "updated_at"])

            sql = SQLBuilder.insert(
                table=profile.table_name,
                columns=db_columns,
                rows=registros
            )

            output_file = self.output_directory / f"insert_{profile.table_name}.sql"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(sql)
            
        print("Generando Reportes...")
        end_time = datetime.datetime.now()
        report_gen = ReportGenerator(error_manager)
        report_gen.generate_all(profile, start_time, end_time, rows_read, len(registros))
        
        # Validacion estricta obligatoria
        filas_generadas = len(registros)
        filas_rechazadas = len(error_manager.skipped_rows)
        if rows_read != filas_generadas + filas_rechazadas:
            raise RuntimeError(f"Inconsistencia en el pipeline: {rows_read} filas leídas != {filas_generadas} generadas + {filas_rechazadas} rechazadas.")

        print()
        print("===================================")
        print("Proceso finalizado")
        print("===================================")
        print(f"Archivo generado: {output_file}")
        print(f"Total registros insertados: {filas_generadas}")
        print(f"Total omitidos: {filas_rechazadas}")

        return output_file