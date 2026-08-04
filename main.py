from engine.pipeline import Pipeline

Pipeline(
    profile_path="profiles/wellezy/finance_accounts.json",
    input_file="input/excel/BD Cartera.xlsx"
).run()