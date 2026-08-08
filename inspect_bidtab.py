import pandas as pd
from pathlib import Path

path = Path(r"C:\Users\genna\OneDrive\Documents\Contracts_Training_Data\Prequal_Test_Docs\Bid Tab Prototype Rev B.xlsx")

# Read with no header so we see everything
df = pd.read_excel(path, header=None, engine="openpyxl")

print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print("=" * 80)
print("First 25 rows (all columns):")
print("=" * 80)

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 25)

print(df.head(25).to_string())