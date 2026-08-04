"""
engine/mapper.py

Convierte un registro del Excel en un registro listo
para generar SQL usando un Profile Schema v1.
Reporta eventos al ErrorManager.
"""

from engine.normalizer import Normalizer
from engine.validator import Validator


class Mapper:

    def __init__(self, profile, error_manager, lookup_cache=None):
        self.profile = profile
        self.error_manager = error_manager
        self.lookup_cache = lookup_cache
        self.seen_slugs = set()
        self.seen_emails = set()

    def apply_transformations(self, value, transformations, row_index, column_name):
        if value is None or not transformations:
            return value
            
        for t in transformations:
            original_step_value = value
            if t == "trim":
                value = Normalizer.text(value)
            elif t == "uppercase":
                value = str(value).upper() if value else value
            elif t == "lowercase":
                value = str(value).lower() if value else value
            elif t == "titlecase":
                value = str(value).title() if value else value
            elif t == "remove_symbols":
                if value:
                    value = "".join(e for e in str(value) if e.isalnum())
            elif t.startswith("truncate("):
                try:
                    length = int(t.split("(")[1].split(")")[0])
                    value = str(value)[:length] if value else value
                except:
                    pass
            elif t == "abs":
                try:
                    value = abs(float(value))
                except:
                    pass
                    
            if original_step_value != value:
                self.error_manager.report_normalization(row_index, column_name, original_step_value, value, reason=t)
                
        return value

    def map_row(self, excel_row, row_index):
        registro = {}

        for config in self.profile.columns:
            if config.get("skip", False):
                continue
                
            db_column = config.get("db_column")
            
            # Static Value Handling
            column_type = config.get("type")
            if column_type == "static_value":
                registro[db_column] = config.get("value")
                continue

            source_column = config.get("source_column")
            default_value = config.get("default_value")
            nullable = config.get("nullable", True)
            
            # 1. Leer valor
            original_value = excel_row.get(source_column)
            value = original_value

            # 2. Normalizar por tipo
            parsing_failed = False
            parsing_error = ""
            if value is not None and str(value).strip() != "":
                if column_type == "date":
                    parsed = Normalizer.date(value)
                    if parsed is None:
                        parsing_failed = True
                        parsing_error = "Fecha inválida"
                    value = parsed
                elif column_type == "integer":
                    parsed = Normalizer.integer(value)
                    if parsed is None:
                        parsing_failed = True
                        parsing_error = "Entero inválido"
                    value = parsed
                elif column_type in ("decimal", "float"):
                    parsed = Normalizer.decimal(value)
                    if parsed is None:
                        parsing_failed = True
                        parsing_error = "Decimal inválido"
                    value = parsed
                elif column_type == "boolean":
                    value = Normalizer.boolean(value)
                else:
                    value = Normalizer.text(value, config.get("length"))
            else:
                if column_type in ("integer", "decimal", "float", "date"):
                    value = None
                else:
                    value = Normalizer.text(value, config.get("length"))
                
            if original_value != value and original_value is not None:
                self.error_manager.report_normalization(row_index, source_column, original_value, value, reason=f"type_cast:{column_type}")
                
            # 3. Aplicar transformations
            transformations = config.get("transformations", [])
            value = self.apply_transformations(value, transformations, row_index, source_column)
            
            # 4. Aplicar value_map
            value_map = config.get("value_map")
            if value_map and value is not None:
                search_key = str(value).strip().lower()
                lower_value_map = {str(k).strip().lower(): v for k, v in value_map.items()}
                
                if search_key in lower_value_map:
                    mapped_value = lower_value_map[search_key]
                    self.error_manager.report_normalization(row_index, source_column, value, mapped_value, reason="value_map")
                    value = mapped_value
            
            # 5. Ejecutar validators
            validator_failed = False
            validator_error = ""
            validators = config.get("validators", [])
            if validators and value is not None:
                try:
                    value = Validator.validate(value, validators, nullable)
                except ValueError as e:
                    validator_failed = True
                    validator_error = str(e)
                    value = None
            
            # 6. Validar valid_values
            valid_values = config.get("valid_values")
            valid_values_failed = False
            if valid_values is not None and value is not None:
                if value not in valid_values:
                    valid_values_failed = True
                    value = None
            
            # 6.5 Validar Lookups
            lookup_name = config.get("lookup")
            lookup_failed = False
            lookup_target_table = None
            lookup_on_not_found = None
            if lookup_name and value is not None and self.lookup_cache:
                lookup_config = self.profile.profile.get("lookups", {}).get(lookup_name)
                if lookup_config:
                    lookup_target_table = lookup_config.get("target_table")
                    lookup_on_not_found = lookup_config.get("on_not_found", "error")
                    if not self.lookup_cache.exists(lookup_target_table, value):
                        if lookup_on_not_found == "error":
                            lookup_failed = True
                        elif lookup_on_not_found == "null":
                            self.error_manager.report_warning(row_index, source_column, f"ID {value} no existe en {lookup_target_table}. Convertido a NULL.")
                            value = None
                        elif lookup_on_not_found == "default":
                            pass # Será manejado por default_value fallback

            # 7. Aplicar default_value & 8. Aplicar nullable & 9. Reportar eventos al ErrorManager
            if value is None:
                if default_value is not None:
                    # Normalization
                    self.error_manager.report_normalization(row_index, source_column, original_value, default_value, reason="default_value")
                    value = default_value
                    
                elif nullable:
                    # Warning (porque se pierde informacion y se fuerza a NULL)
                    self.error_manager.report_normalization(row_index, source_column, original_value, "NULL", reason="nullable_fallback")
                    value = None
                    
                    if parsing_failed:
                        self.error_manager.report_warning(row_index, source_column, f"{parsing_error}. Convertido a NULL (nullable).")
                    if validator_failed:
                        self.error_manager.report_warning(row_index, source_column, f"Validator falló: {validator_error}. Convertido a NULL (nullable).")
                    if valid_values_failed:
                        self.error_manager.report_warning(row_index, source_column, "Valor no permitido en valid_values. Convertido a NULL (nullable).")
                        
                else:
                    # Error
                    if parsing_failed:
                        self.error_manager.report_error(row_index, source_column, original_value, "NULL", f"{parsing_error} (columna obligatoria)", "Fila omitida")
                    elif validator_failed:
                        self.error_manager.report_error(row_index, source_column, original_value, "NULL", f"Validator falló: {validator_error} (columna obligatoria)", "Fila omitida")
                    elif valid_values_failed:
                        self.error_manager.report_error(row_index, source_column, original_value, "NULL", "valid_values sin posibilidad de corrección", "Fila omitida")
                    else:
                        self.error_manager.report_error(row_index, source_column, original_value, "NULL", "columna obligatoria sin valor", "Fila omitida")
            
            if lookup_failed:
                self.error_manager.report_lookup_error(row_index, source_column, lookup_target_table, original_value)
                value = None

            registro[db_column] = value
            
        # Duplicated Slug Resolution
        if "slug" in registro and registro["slug"] is not None:
            slug = registro["slug"]
            if slug in self.seen_slugs:
                doc_num = registro.get("document_number")
                if doc_num:
                    new_slug = f"{slug}-{doc_num}"
                    # Para saber la columna origen iteramos el profile o asumimos "slug" (o la fuente del slug)
                    # En Wellezy suele haber transformaciones multi-columna, pero por convención:
                    source_col = next((c.get("source_column") for c in self.profile.columns if c.get("db_column") == "slug"), "slug")
                    self.error_manager.report_normalization(row_index, source_col, slug, new_slug, reason="slug_duplicate_resolution")
                    registro["slug"] = new_slug
                    self.seen_slugs.add(new_slug)
            else:
                self.seen_slugs.add(slug)
                
        # Duplicated Email Resolution
        if "email" in registro and registro["email"] is not None:
            email = registro["email"]
            if email in self.seen_emails:
                source_col = next((c.get("source_column") for c in self.profile.columns if c.get("db_column") == "email"), "email")
                self.error_manager.report_normalization(row_index, source_col, email, "NULL", reason="email_duplicate_resolution")
                registro["email"] = None
            else:
                self.seen_emails.add(email)

        return registro

    def map_rows(self, rows, start_index=2):
        resultados = []
        for i, row in enumerate(rows):
            row_index = start_index + i
            
            try:
                registro = self.map_row(row, row_index)
                if self.error_manager.is_row_valid(row_index):
                    resultados.append(registro)
            except RuntimeError as e:
                # Si ErrorManager dice fail_fast o abort, propagamos.
                raise e
                
        return resultados