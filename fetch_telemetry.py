import pandas as pd 

PATH = r"C:\MY_Files\DE\dcs_data_pipeline\Medallion\bronze_layer\master_data.parquet"
df_check = pd.read_parquet(PATH)
bad_missions = [
    '78ea836c-7e7b-4e1c-83e2-575eb9c787ce',
    'd9350240-879c-47db-87c5-11e6c3834468',
    '150f3f47-85dd-414c-bd0c-010ca6afcc09',
    '75a76322-0a6a-4d5f-8f02-3cfa74dd83e9',
    '64cc9ef4-8b7c-4b5c-bea3-4d4bbfd07dba',
    '6e73581c-5cbc-48f4-8db2-f6e501643eeb',
    '72265eae-f52a-403e-92a7-b87cb4b27dea',
    'a7659d0d-c525-4bd0-90fb-9b6b0b91af47',
    '1597b009-1b76-43c0-84a4-112bde46de71',
    '63d90794-6a72-4a69-b1e9-0515ba9be33c',
]
found = df_check[df_check["mission_id"].isin(bad_missions)]["mission_id"].unique()
print(f"Bad missions still in master data: {len(found)}")
print(found)