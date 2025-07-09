# app/standardize.py
from __future__ import annotations
import pandas as pd, uuid, re
from pathlib import Path
from typing import Sequence

class ColumnMappingNeeded(Exception):
    """Raised when required columns are missing.
    .missing holds a list of canonical names that still need mapping."""
    def __init__(self, missing: Sequence[str]):
        self.missing = list(missing)
        super().__init__(f"Missing columns: {', '.join(self.missing)}")

CLEAN_COLUMNS = {
    r"order[ _]?id"        : "Order_ID",
    r"order[ _]?date"      : "Order_Date",
    r"(item[ _]?type|product|product name)" : "Product_Name",
    r"(units[ _]?sold|quantity ordered)"    : "Units_Sold",
    r"(unit[ _]?price|price each)"          : "Unit_Price",
}
REQUIRED = {"Order_ID", "Order_Date", "Product_Name",
            "Units_Sold", "Unit_Price"}

def _auto_rename(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for regex, canon in CLEAN_COLUMNS.items():
        for col in df.columns:
            if re.fullmatch(regex, col, re.I):
                rename_map[col] = canon; break
    return df.rename(columns=rename_map)

def standardize_csv(path: Path, user_map: dict[str, str] | None = None) -> Path:
    df = pd.read_csv(path, dtype=str)

    # 1) auto-rename using regexes
    df = _auto_rename(df)

    # 2) apply any user-supplied mapping
    if user_map:
        df = df.rename(columns=user_map)

    # 3) check what’s still missing
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ColumnMappingNeeded(missing)

    # --- coerce & derive revenue ---
    df["Units_Sold"]  = pd.to_numeric(df["Units_Sold"],  errors="coerce")
    df["Unit_Price"]  = pd.to_numeric(df["Unit_Price"],  errors="coerce")
    df["Order_Date"]  = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Revenue"]     = df["Units_Sold"] * df["Unit_Price"]

    df = df.dropna(subset=["Order_ID", "Order_Date", "Revenue"])
    out = path.with_stem(f"standardized_{uuid.uuid4().hex[:6]}")
    df.to_csv(out, index=False)
    return out
