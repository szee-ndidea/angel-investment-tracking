import io
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Angel Portfolio Tracker", layout="wide")

DATA_FILE = Path("portfolio_data.csv")

EXPECTED_COLUMNS = [
    "Date",
    "Company",
    "Security Type",
    "Round",
    "Investment Amount",
    "Shares",
    "Price Per Share",
    "Post Money Valuation",
    "Current Value",
    "Status",
    "Notes",
]


def load_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=EXPECTED_COLUMNS)

    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[EXPECTED_COLUMNS].copy()

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        numeric_cols = [
            "Investment Amount",
            "Shares",
            "Price Per Share",
            "Post Money Valuation",
            "Current Value",
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def save_data(df: pd.DataFrame) -> None:
    out = df.copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out.to_csv(DATA_FILE, index=False)


def clean_imported_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=renamed).copy()

    column_map = {
        "date": "Date",
        "company": "Company",
        "security type": "Security Type",
        "security": "Security Type",
        "round": "Round",
        "investment amount": "Investment Amount",
        "amount": "Investment Amount",
        "shares": "Shares",
        "price per share": "Price Per Share",
        "pps": "Price Per Share",
        "post money valuation": "Post Money Valuation",
        "valuation": "Post Money Valuation",
        "current value": "Current Value",
        "status": "Status",
        "notes": "Notes",
    }

    normalized = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in column_map:
            normalized[col] = column_map[key]

    df = df.rename(columns=normalized)

    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[EXPECTED_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    numeric_cols = [
        "Investment Amount",
        "Shares",
        "Price Per Share",
        "Post Money Valuation",
        "Current Value",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(how="all")
    return df


def import_from_excel(uploaded_file) -> pd.DataFrame:
    xls = pd.ExcelFile(uploaded_file)
    combined = []

    for sheet in xls.sheet_names:
        try:
            temp = pd.read_excel(uploaded_file, sheet_name=sheet)
            cleaned = clean_imported_dataframe(temp)
            if not cleaned.empty and cleaned["Company"].notna().any():
                combined.append(cleaned)
        except Exception:
            continue

    if not combined:
        raise ValueError("Could not find a usable transaction table in the uploaded workbook.")

    result = pd.concat(combined, ignore_index=True)
    result = result.dropna(subset=["Company"], how="all")
    return result


def format_currency(value) -> str:
    if pd.isna(value):
        return ""
    return f"${value:,.0f}"


def company_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    summary = (
        df.groupby("Company", dropna=False)
        .agg(
            total_invested=("Investment Amount", "sum"),
            total_shares=("Shares", "sum"),
            latest_value=("Current Value", "last"),
            deals=("Company", "count"),
            latest_status=("Status", "last"),
        )
        .reset_index()
        .sort_values(["total_invested", "Company"], ascending=[False, True])
    )

    summary["multiple"] = summary["latest_value"] / summary["total_invested"]
    summary.replace([float("inf"), -float("inf")], pd.NA, inplace=True)
    return summary


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["Year"] = pd.to_datetime(temp["Date"], errors="coerce").dt.year

    yearly = (
        temp.groupby("Year", dropna=False)
        .agg(
            total_invested=("Investment Amount", "sum"),
            current_value=("Current Value", "sum"),
            deal_count=("Company", "count"),
        )
        .reset_index()
        .sort_values("Year")
    )
    yearly["gain_loss"] = yearly["current_value"] - yearly["total_invested"]
    return yearly


def portfolio_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_invested": 0.0,
            "current_value": 0.0,
            "unrealized_gain": 0.0,
            "positions": 0,
        }

    total_invested = df["Investment Amount"].fillna(0).sum()
    current_value = df["Current Value"].fillna(0).sum()
    unrealized_gain = current_value - total_invested
    positions = df["Company"].nunique()

    return {
        "total_invested": total_invested,
        "current_value": current_value,
        "unrealized_gain": unrealized_gain,
        "positions": positions,
    }


def transaction_form(existing_row=None, form_key="transaction_form"):
    if existing_row is None:
        existing_row = {}

    with st.form(form_key, clear_on_submit=False):
        c1, c2, c3 = st.columns(3)

        with c1:
            date_val = existing_row.get("Date")
            if pd.isna(date_val):
                date_val = pd.Timestamp.today().date()
            elif hasattr(date_val, "date"):
                date_val = date_val.date()

            date = st.date_input("Date", value=date_val)
            company = st.text_input("Company", value=existing_row.get("Company", "") or "")
            security_type = st.text_input("Security Type", value=existing_row.get("Security Type", "") or "")
            round_name = st.text_input("Round", value=existing_row.get("Round", "") or "")

        with c2:
            investment_amount = st.number_input(
                "Investment Amount",
                min_value=0.0,
                value=float(existing_row.get("Investment Amount") or 0.0),
                step=1000.0,
            )
            shares = st.number_input(
                "Shares",
                min_value=0.0,
                value=float(existing_row.get("Shares") or 0.0),
                step=1.0,
            )
            price_per_share = st.number_input(
                "Price Per Share",
                min_value=0.0,
                value=float(existing_row.get("Price Per Share") or 0.0),
                step=0.01,
            )

        with c3:
            post_money_valuation = st.number_input(
                "Post Money Valuation",
                min_value=0.0,
                value=float(existing_row.get("Post Money Valuation") or 0.0),
                step=10000.0,
            )
            current_value = st.number_input(
                "Current Value",
                min_value=0.0,
                value=float(existing_row.get("Current Value") or 0.0),
                step=1000.0,
            )
            status = st.selectbox(
                "Status",
                options=["Active", "Exited", "Written Off", "Paused", "Other"],
                index=["Active", "Exited", "Written Off", "Paused", "Other"].index(
                    existing_row.get("Status", "Active") if existing_row.get("Status", "Active") in ["Active", "Exited", "Written Off", "Paused", "Other"] else "Other"
                ),
            )

        notes = st.text_area("Notes", value=existing_row.get("Notes", "") or "")
        submitted = st.form_submit_button("Save Transaction")

    if not submitted:
        return None

    return {
        "Date": pd.to_datetime(date),
        "Company": company.strip(),
        "Security Type": security_type.strip(),
        "Round": round_name.strip(),
        "Investment Amount": investment_amount,
        "Shares": shares,
        "Price Per Share": price_per_share,
        "Post Money Valuation": post_money_valuation,
        "Current Value": current_value,
        "Status": status,
        "Notes": notes.strip(),
    }


st.title("Angel Investment Portfolio Tracker")

if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df.copy()

with st.sidebar:
    st.header("Data")
    st.caption("Your data is saved locally to portfolio_data.csv")

    uploaded_csv = st.file_uploader("Import CSV", type=["csv"])
    uploaded_excel = st.file_uploader("Import Excel", type=["xlsx", "xls"])

    if uploaded_csv is not None:
        try:
            imported = pd.read_csv(uploaded_csv)
            imported = clean_imported_dataframe(imported)
            st.session_state.df = imported
            save_data(imported)
            st.success("CSV imported successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"CSV import failed: {e}")

    if uploaded_excel is not None:
        try:
            imported = import_from_excel(uploaded_excel)
            st.session_state.df = imported
            save_data(imported)
            st.success("Excel file imported successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Excel import failed: {e}")

    if st.button("Save Current Data"):
        save_data(st.session_state.df)
        st.success("Data saved.")

    export_df = st.session_state.df.copy()
    if not export_df.empty:
        export_df["Date"] = pd.to_datetime(export_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="portfolio_data.csv", mime="text/csv")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Add Investment", "Edit Investments", "Raw Data"])

with tab1:
    metrics = portfolio_metrics(df)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Invested", format_currency(metrics["total_invested"]))
    m2.metric("Current Value", format_currency(metrics["current_value"]))
    m3.metric("Unrealized Gain", format_currency(metrics["unrealized_gain"]))
    m4.metric("Portfolio Companies", f'{metrics["positions"]:,}')

    st.subheader("Company Summary")
    comp = company_summary(df)
    if comp.empty:
        st.info("No investments yet.")
    else:
        display_comp = comp.copy()
        display_comp["total_invested"] = display_comp["total_invested"].map(format_currency)
        display_comp["latest_value"] = display_comp["latest_value"].map(format_currency)
        display_comp["multiple"] = display_comp["multiple"].map(
            lambda x: "" if pd.isna(x) else f"{x:.2f}x"
        )
        st.dataframe(display_comp, use_container_width=True, hide_index=True)

    st.subheader("Yearly Summary")
    yearly = yearly_summary(df)
    if not yearly.empty:
        chart_df = yearly.dropna(subset=["Year"]).copy()
        if not chart_df.empty:
            chart_df["Year"] = chart_df["Year"].astype(int).astype(str)
            st.bar_chart(chart_df.set_index("Year")[["total_invested", "current_value"]])

        display_yearly = yearly.copy()
        for col in ["total_invested", "current_value", "gain_loss"]:
            display_yearly[col] = display_yearly[col].map(format_currency)
        st.dataframe(display_yearly, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Add New Investment")
    new_row = transaction_form(form_key="new_transaction_form")
    if new_row is not None:
        if not new_row["Company"]:
            st.error("Company is required.")
        else:
            updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
            st.session_state.df = updated
            save_data(updated)
            st.success("Investment added.")
            st.rerun()

with tab3:
    st.subheader("Edit Existing Investments")

    if df.empty:
        st.info("No transactions available to edit.")
    else:
        edit_df = df.copy()
        edit_df["label"] = (
            edit_df["Company"].fillna("Unknown")
            + " | "
            + pd.to_datetime(edit_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("No Date")
            + " | "
            + edit_df["Investment Amount"].fillna(0).map(lambda x: f"${x:,.0f}")
        )

        selected_label = st.selectbox("Select a transaction", options=edit_df["label"].tolist())
        selected_idx = edit_df.index[edit_df["label"] == selected_label][0]
        selected_row = df.loc[selected_idx].to_dict()

        edited_row = transaction_form(existing_row=selected_row, form_key="edit_transaction_form")

        c1, c2 = st.columns(2)

        with c1:
            if edited_row is not None:
                if not edited_row["Company"]:
                    st.error("Company is required.")
                else:
                    updated = df.copy()
                    for key, value in edited_row.items():
                        updated.at[selected_idx, key] = value
                    updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                    st.session_state.df = updated
                    save_data(updated)
                    st.success("Transaction updated.")
                    st.rerun()

        with c2:
            if st.button("Delete Transaction", type="secondary"):
                updated = df.drop(index=selected_idx).reset_index(drop=True)
                st.session_state.df = updated
                save_data(updated)
                st.success("Transaction deleted.")
                st.rerun()

with tab4:
    st.subheader("Raw Data")
    st.dataframe(df, use_container_width=True, hide_index=True)
