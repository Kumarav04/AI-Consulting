# app/standardize.py
import pandas as pd
from pathlib import Path
import uuid

CLEAN_COLUMNS = {
    "Order ID": "Order_ID",
    "Order Date": "Order_Date",
    "Item Type": "Product_Name",      # NEW
    "Product": "Product_Name",
    "Units Sold": "Units_Sold",       # NEW
    "Quantity Ordered": "Units_Sold",
    "Unit Price": "Unit_Price",
    "Price Each": "Unit_Price",
}

ORDER = ["Order_ID", "Order_Date", "Product_Name", "Units_Sold", "Unit_Price"]

def standardize_csv(csv_path: Path) -> Path:
    """Return path to a standardized CSV derived from *csv_path*."""
    df = (
        pd.read_csv(csv_path)
        .dropna(how="all")                             # drop blank rows
        .rename(columns=CLEAN_COLUMNS)
    )
    df = df[ORDER]                                    # reorder / subset
    df["Units_Sold"] = pd.to_numeric(df["Units_Sold"], errors="coerce")
    df["Unit_Price"] = pd.to_numeric(df["Unit_Price"], errors="coerce")
    df["Revenue"] = df["Units_Sold"] * df["Unit_Price"]

    out = csv_path.with_stem(f"standardized_{uuid.uuid4().hex[:6]}")
    df.to_csv(out, index=False)
    return out
