from engine.pipeline import Pipeline

Pipeline(
    profile_path="profiles/wellezy/seguimientos_observaciones.json",
    input_file="input/excel/BD Cartera.xlsx"
).run()