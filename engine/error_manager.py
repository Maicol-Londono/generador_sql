import csv
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from typing import Any, List


class EventType(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    NORMALIZATION = "NORMALIZATION"
    INFO = "INFO"


@dataclass
class NormalizationEvent:
    row_index: int
    column: str
    original_value: Any
    final_value: Any
    reason: str


@dataclass
class WarningEvent:
    row_index: int
    column: str
    description: str


@dataclass
class ErrorEvent:
    row_index: int
    column: str
    original_value: Any
    final_value: Any
    description: str
    action: str


@dataclass
class Report:
    normalizations: List[NormalizationEvent]
    warnings: List[WarningEvent]
    errors: List[ErrorEvent]
    skipped_rows: set
    lookup_failures: dict


class ErrorManager:

    def __init__(self, error_policy: dict):
        self.mode = error_policy.get("mode", "continue")
        self.max_errors = error_policy.get("max_errors", 100)
        
        self.errors = []
        self.warnings = []
        self.normalizations = []
        self.info = []
        
        self.error_count = 0
        self.warning_count = 0
        self.normalization_count = 0
        self.skipped_rows = set()
        
        # Auditoría de relaciones
        self.lookup_failures = {} # target_table -> {"errors": int, "missing_ids": set(), "affected_rows": set()}

    def report_lookup_error(self, row_index, column, target_table, missing_id):
        if target_table not in self.lookup_failures:
            self.lookup_failures[target_table] = {"errors": 0, "missing_ids": set(), "affected_rows": set()}
            
        self.lookup_failures[target_table]["errors"] += 1
        self.lookup_failures[target_table]["missing_ids"].add(missing_id)
        self.lookup_failures[target_table]["affected_rows"].add(row_index)
        
        self.report_error(row_index, column, missing_id, "NULL", f"ID no existe en tabla {target_table} (lookup)", "Fila omitida")

    def report_error(self, row_index, column, original_value, final_value, description, action):
        self.error_count += 1
        self.errors.append(ErrorEvent(
            row_index=row_index,
            column=column,
            original_value=original_value,
            final_value=final_value,
            description=description,
            action=action
        ))
        self.skipped_rows.add(row_index)
        
        if self.mode == "fail_fast":
            raise RuntimeError(f"Error crítico en fila {row_index}, columna {column}: {description}")
            
        if self.mode == "abort_after_limit" and self.error_count >= self.max_errors:
            raise RuntimeError(f"Límite de errores excedido ({self.max_errors}). Abortando importación.")

    def report_warning(self, row_index, column, description):
        self.warning_count += 1
        self.warnings.append(WarningEvent(
            row_index=row_index,
            column=column,
            description=description
        ))

    def report_normalization(self, row_index, column, original_value, final_value, reason: str = "auto_fix"):
        if original_value != final_value:
            self.normalization_count += 1
            self.normalizations.append(NormalizationEvent(
                row_index=row_index,
                column=column,
                original_value=original_value,
                final_value=final_value,
                reason=reason
            ))

    def report_info(self, description):
        self.info.append(description)

    def is_row_valid(self, row_index):
        return row_index not in self.skipped_rows

    def get_report(self) -> Report:
        return Report(
            normalizations=self.normalizations,
            warnings=self.warnings,
            errors=self.errors,
            skipped_rows=self.skipped_rows,
            lookup_failures=self.lookup_failures
        )
