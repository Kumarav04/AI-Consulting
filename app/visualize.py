from pathlib import Path
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["figure.autolayout"] = True

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def prepare_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce", infer_datetime_format=True)
    df = df.dropna(subset=["Order_Date"])
    df["Month"] = df["Order_Date"].dt.month_name()
    df["Month"] = pd.Categorical(df["Month"], categories=MONTH_ORDER, ordered=True)
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")
    return df


def create_monthly_revenue(df, out_dir):
    monthly_rev = df.groupby("Month", as_index=False)["Revenue"].sum().sort_values("Month")
    path = out_dir / "monthly_revenue.png"
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=monthly_rev, x="Month", y="Revenue", marker="o")
    plt.title("Monthly Revenue")
    plt.xticks(rotation=45)
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def create_product_revenue(df, out_dir):
    product_rev = df.groupby("Product_Name")["Revenue"].sum().sort_values(ascending=False).reset_index()
    path = out_dir / "product_revenue.png"
    plt.figure(figsize=(10, 6))
    sns.barplot(data=product_rev, x="Product_Name", y="Revenue", color="g")
    plt.title("Product Revenue")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def create_top5_per_month(df, out_dir):
    monthly_prod = df.groupby(["Month", "Product_Name"], as_index=False)["Revenue"].sum()
    top5_each = monthly_prod.sort_values(["Month", "Revenue"], ascending=[True, False]).groupby("Month").head(5)
    path = out_dir / "top_products_month.png"
    plt.figure(figsize=(14, 8))
    sns.barplot(data=top5_each, x="Month", y="Revenue", hue="Product_Name")
    plt.title("Top 5 Products by Revenue per Month")
    plt.xticks(rotation=45)
    plt.legend(title="Item", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def create_footfall(df, out_dir):
    month_counts = df.groupby("Month").size().reset_index(name="Count")
    path = out_dir / "monthly_footfall.png"
    plt.figure(figsize=(10, 6))
    sns.barplot(data=month_counts, x="Month", y="Count", color="skyblue")
    plt.title("Monthly Footfall")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def create_pie_chart(df, out_dir):
    product_rev = df.groupby("Product_Name")["Revenue"].sum().sort_values(ascending=False).reset_index()
    top_products = product_rev.head(5)
    explode = [0, 0.1, 0, 0, 0]
    colors = sns.color_palette("dark")
    path = out_dir / "products_by_revenue_pie.png"
    plt.pie(
        top_products["Revenue"],
        labels=top_products["Product_Name"],
        colors=colors,
        explode=explode,
        autopct="%.0f%%",
    )
    plt.title("Top Products by Revenue")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def create_boxplot(df, out_dir):
    product_rev = df.groupby("Product_Name")["Revenue"].sum().sort_values(ascending=False).reset_index()
    top5_names = product_rev.head(5)["Product_Name"]
    df_top = df[df["Product_Name"].isin(top5_names)]
    path = out_dir / "revenue_distribution_boxplot.png"
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df_top, x="Product_Name", y="Revenue")
    plt.title("Revenue Distribution – Top 5 Products")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return path


VISUALIZATION_REGISTRY = {
    "monthly_revenue": {
        "keywords": ["monthly revenue", "trend", "sales over time", "line chart"],
        "function": create_monthly_revenue,
    },
    "product_revenue": {
        "keywords": ["product revenue", "top products", "bar chart"],
        "function": create_product_revenue,
    },
    "top_products_month": {
        "keywords": ["top 5 products", "monthly product performance"],
        "function": create_top5_per_month,
    },
    "monthly_footfall": {
        "keywords": ["footfall", "order count", "traffic"],
        "function": create_footfall,
    },
    "products_by_revenue_pie": {
        "keywords": ["pie chart", "revenue share", "product distribution"],
        "function": create_pie_chart,
    },
    "revenue_distribution_boxplot": {
        "keywords": ["distribution", "boxplot", "revenue variance"],
        "function": create_boxplot,
    },
}


def select_visualizations_for_prompt(prompt: str) -> list[str]:
    prompt = prompt.lower()
    selected = [
        key for key, meta in VISUALIZATION_REGISTRY.items()
        if any(keyword in prompt for keyword in meta["keywords"])
    ]
    return selected or ["monthly_revenue", "product_revenue"]


def create_relevant_charts(csv_path: Path, out_dir: Path, prompt: str) -> list[Path]:
    df = prepare_dataframe(csv_path)
    selected_keys = select_visualizations_for_prompt(prompt)
    paths = []
    for key in selected_keys:
        try:
            chart_func = VISUALIZATION_REGISTRY[key]["function"]
            path = chart_func(df, out_dir)
            paths.append(path)
        except Exception as e:
            print(f"Error generating chart '{key}': {e}")
    return paths
