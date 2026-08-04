from engine.pipeline import Pipeline

Pipeline(
    profile_path="profiles/wellezy/solicitudes.json",
    input_file="input/excel/BD Cartera.xlsx"
).run()