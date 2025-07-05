# app/visualize.py
from __future__ import annotations

from pathlib import Path
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["figure.autolayout"] = True

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def create_visualizations(csv_path: Path, out_dir: Path) -> list[Path]:
    df = pd.read_csv(csv_path)
    print(df.columns.tolist())


    # ── Date & month handling ───────────────────────────────────────────
    df["Order_Date"] = pd.to_datetime(
        df["Order_Date"], errors="coerce", infer_datetime_format=True
    )
    df = df.dropna(subset=["Order_Date"])
    df["Month"] = df["Order_Date"].dt.month_name()
    df["Month"] = pd.Categorical(df["Month"], categories=MONTH_ORDER, ordered=True)

    # ── 1) Monthly Revenue line plot ────────────────────────────────────
    monthly_rev = (
        df.groupby("Month", as_index=False)["Revenue"]
        .sum()
        .sort_values("Month")
    )
    p1 = out_dir / "monthly_revenue.png"
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=monthly_rev, x="Month", y="Revenue", marker="o")
    plt.title("Monthly Revenue")
    plt.xticks(rotation=45)
    plt.savefig(p1, dpi=150)
    plt.close()

    # ── 2) Revenue by product bar chart ────────────────────────────────
    product_rev = (
        df.groupby("Product_Name")["Revenue"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    p2 = out_dir / "product_revenue.png"
    plt.figure(figsize=(10, 6))
    sns.barplot(data=product_rev, x="Product_Name", y="Revenue", color="g")
    plt.title("Product Revenue")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(p2, dpi=150)
    plt.close()

    # ── 3) Top-5 products per month ────────────────────────────────────
    monthly_prod = (
        df.groupby(["Month", "Product_Name"], as_index=False)["Revenue"]
        .sum()
    )
    top5_each = (
        monthly_prod.sort_values(["Month", "Revenue"], ascending=[True, False])
        .groupby("Month")
        .head(5)
    )
    p3 = out_dir / "top_products_month.png"
    plt.figure(figsize=(14, 8))
    sns.barplot(data=top5_each, x="Month", y="Revenue", hue="Product_Name")
    plt.title("Top 5 Products by Revenue per Month")
    plt.xticks(rotation=45)
    plt.legend(title="Item", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(p3, dpi=150)
    plt.close()

    # ── 4) Monthly footfall bar chart ──────────────────────────────────
    month_counts = df.groupby("Month").size().reset_index(name="Count")
    p4 = out_dir / "monthly_footfall.png"
    plt.figure(figsize=(10, 6))
    sns.barplot(data=month_counts, x="Month", y="Count", color="skyblue")
    plt.title("Monthly Footfall")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(p4, dpi=150)
    plt.close()

    # ── 5) Pie chart: top 5 products by revenue ────────────────────────
    top_products = product_rev.head(5)
    explode = [0, 0.1, 0, 0, 0]
    colors = sns.color_palette("dark")
    p5 = out_dir / "products_by_revenue_pie.png"
    plt.pie(
        top_products["Revenue"],
        labels=top_products["Product_Name"],
        colors=colors,
        explode=explode,
        autopct="%.0f%%",
    )
    plt.title("Top Products by Revenue")
    plt.savefig(p5, dpi=150)
    plt.close()

    # ── 6) Boxplot: revenue distribution (top 5 products) ──────────────
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")
    top5_names = top_products["Product_Name"]
    df_top = df[df["Product_Name"].isin(top5_names)]
    p6 = out_dir / "revenue_distribution_boxplot.png"
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df_top, x="Product_Name", y="Revenue")
    plt.title("Revenue Distribution – Top 5 Products")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(p6, dpi=150)
    plt.close()

    return [p1, p2, p3, p4, p5, p6]
