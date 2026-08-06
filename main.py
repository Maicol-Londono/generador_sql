from engine.pipeline import Pipeline

Pipeline(
    profile_path="profiles/wellezy/finance_accounts_status_update.json",
    input_file="input/excel/BD Cartera.xlsx"
).run()