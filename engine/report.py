"""
engine/report.py

Genera reportes de importacion.
"""
import csv
import datetime
from pathlib import Path
from collections import Counter
from engine.error_manager import Report

class ReportGenerator:

    def generate(self):
        pass

    def __init__(self, error_manager, output_directory="output/reports"):
        self.em = error_manager
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def write_csv(self, filename, headers, data_dicts):
        filepath = self.output_directory / filename
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in data_dicts:
                writer.writerow(row)
        return filepath

    def generate_errors(self, report: Report):
        data = [{
            "fila_excel": e.row_index,
            "columna": e.column,
            "valor_original": e.original_value,
            "valor_final": e.final_value,
            "error": e.description,
            "accion": e.action
        } for e in report.errors]
        return self.write_csv("errors.csv", ["fila_excel", "columna", "valor_original", "valor_final", "error", "accion"], data)

    def generate_warnings(self, report: Report):
        data = [{
            "fila_excel": w.row_index,
            "columna": w.column,
            "descripcion": w.description
        } for w in report.warnings]
        return self.write_csv("warnings.csv", ["fila_excel", "columna", "descripcion"], data)

    def generate_normalizations(self, report: Report):
        data = [{
            "fila_excel": n.row_index,
            "columna": n.column,
            "valor_original": n.original_value,
            "valor_final": n.final_value,
            "motivo": n.reason
        } for n in report.normalizations]
        return self.write_csv("normalizations.csv", ["fila_excel", "columna", "valor_original", "valor_final", "motivo"], data)

    def generate_summary(self, profile, start_time, end_time, rows_read, rows_inserted, report: Report):
        filepath = self.output_directory / "import_summary.txt"
        
        duration = end_time - start_time
        rows_skipped = len(report.skipped_rows)
        
        reasons_counter = Counter(n.reason for n in report.normalizations if not n.reason.startswith("type_cast:"))
        
        normalizations_lines = []
        for reason, count in reasons_counter.items():
            normalizations_lines.append(f"{reason.ljust(30)}{count}")
            if reason == "nullable_fallback":
                col_counter = Counter(n.column for n in report.normalizations if n.reason == "nullable_fallback")
                for col, col_count in col_counter.items():
                    normalizations_lines.append(f"    {col.ljust(26)}{col_count}")
                    
        normalizations_breakdown = "\n".join(normalizations_lines)
        if not normalizations_breakdown:
            normalizations_breakdown = "Ninguna"
            
        summary_template = f"""========================================
IMPORT SUMMARY
========================================
Archivo origen      : {profile.sheet_name}
Profile utilizado   : {profile.profile.get('metadata', dict()).get('profile_name', 'Desconocido')}
Tabla destino       : {profile.table_name}
Hora inicio         : {start_time.strftime("%Y-%m-%d %H:%M:%S")}
Hora fin            : {end_time.strftime("%Y-%m-%d %H:%M:%S")}
Tiempo total        : {duration}

Filas leídas        : {rows_read}
Filas procesadas    : {rows_inserted + rows_skipped}
Filas insertadas    : {rows_inserted}
Filas omitidas      : {rows_skipped}

Errores             : {len(report.errors)}
Warnings            : {len(report.warnings)}
Normalizaciones     : {len(report.normalizations)}

Desglose de Normalizaciones:
{normalizations_breakdown}

SQL generado        : insert_{profile.table_name}.sql
Reportes generados  : errors.csv, warnings.csv, normalizations.csv
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(summary_template)
            
        return filepath

    def generate_all(self, profile, start_time, end_time, rows_read, rows_inserted):
        if not self.em: return
        report = self.em.get_report()
        self.generate_errors(report)
        self.generate_warnings(report)
        self.generate_normalizations(report)
        self.generate_summary(profile, start_time, end_time, rows_read, rows_inserted, report)
