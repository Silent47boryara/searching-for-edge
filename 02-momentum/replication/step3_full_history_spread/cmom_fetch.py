import pandas as pd
liu = pd.read_parquet("https://huggingface.co/datasets/sstoeckl/opencryptoassetpricing/resolve/main/data/factors_liu.parquet")
liu[liu["week_start"] >= "2020-01-01"][["week_start","CMOM"]].to_csv("cmom_2020_2026.csv", index=False)
print("готово:", len(liu), "строк всего")
