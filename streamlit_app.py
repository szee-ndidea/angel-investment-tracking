from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Angel Investment Tracker", layout="wide")

EXPECTED_COLUMNS = [
    "Date",
    "Company",
    "Instrument Type",
    "Round/Stage",
    "Gross Investment",
    "Fees",
    "Current Value",
    "Status",
]

STATUS_OPTIONS = [
    "Active",
    "Exited",
    "Written Off",
    "Partially Realized",
    "Converted",
    "Paused",
    "Other",
]

INSTRUMENT_OPTIONS = [
    "SAFE",
    "Convertible Note",
    "Equity",
    "Loan",
    "SPV",
    "Fund",
    "Other",
]


def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPECTED_COLUMNS)


def parse_money(value) -> float:
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        if pd.isna(value):
            return 0.0
        return float(value)

    text = str(value).strip()
    if text == "":
        return 0.0

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    text = (
        text.replace("$", "")
        .replace(",", "")
        .replace(" ", "")
        .replace("USD", "")
        .replace("usd", "")
    )

    if text in {"", "-", ".", "-."}:
        return 0.0

    amount = float(text)
    return -amount if negative else amount


def money_input(label: str, value=0.0, help_text: str | None = None) -> float:
    default_text = f"{float(value):,.0f}" if value not in [None, ""] and not pd.isna(value) else ""
    raw = st.text_input(label, value=default_text, help=help_text)
    try:
        return parse_money(raw)
    except Exception:
        st.error(f"{label} must be a valid dollar amount.")
        st.stop()


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    column_map = {
        "date": "Date",
        "company": "Company",
        "instrument": "Instrument Type",
        "instrument type": "Instrument Type",
        "security": "Instrument Type",
        "security type": "Instrument Type",
        "round": "Round/Stage",
        "stage": "Round/Stage",
        "round/stage": "Round/Stage",
        "gross investment": "Gross Investment",
        "investment amount": "Gross Investment",
        "amount": "Gross Investment",
        "fees": "Fees",
        "current value": "Current Value",
        "value": "Current Value",
        "status": "Status",
    }

    rename_dict = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in column_map:
            rename_dict[col] = column_map[key]

    df = df.rename(columns=rename_dict)

    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[EXPECTED_COLUMNS].copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Gross Investment", "Fees", "Current Value"]:
        df[col] = df[col].apply(parse_money)

    df["Company"] = df["Company"].fillna("").astype(str).str.strip()
    df["Instrument Type"] = df["Instrument Type"].fillna("").astype(str).str.strip()
    df["Round/Stage"] = df["Round/Stage"].fillna("").astype(str).str.strip()
    df["Status"] = df["Status"].fillna("Active").astype(str).str.strip()

    df = df.dropna(how="all")
    return df


def export_ready_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not out.empty:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def format_currency(value) -> str:
    if pd.isna(value):
        return ""
    return f"${value:,.0f}"


def format_multiple(value) -> str:
    if pd.isna(value):
        return ""
    return f"{value:.2f}x"


def add_calculated_fields(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out["Total Invested"] = out["Gross Investment"] + out["Fees"]
    out["Gain / Loss"] = out["Current Value"] - out["Total Invested"]
    out["MoM"] = out["Current Value"] / out["Total Invested"].replace(0, pd.NA)
    return out


def portfolio_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "gross_investment": 0.0,
            "fees": 0.0,
            "total_invested": 0.0,
            "current_value": 0.0,
            "gain_loss": 0.0,
            "positions": 0,
        }

    gross_investment = df["Gross Investment"].fillna(0).sum()
    fees = df["Fees"].fillna(0).sum()
    total_invested = gross_investment + fees
    current_value = df["Current Value"].fillna(0).sum()
    gain_loss = current_value - total_invested
    positions = df["Company"].replace("", pd.NA).dropna().nunique()

    return {
        "gross_investment": gross_investment,
        "fees": fees,
        "total_invested": total_invested,
        "current_value": current_value,
        "gain_loss": gain_loss,
        "positions": positions,
    }


def company_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["Date_Sort"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp = temp.sort_values(["Company", "Date_Sort"])

    summary = (
        temp.groupby("Company", dropna=False)
        .agg(
            deals=("Company", "count"),
            gross_investment=("Gross Investment", "sum"),
            fees=("Fees", "sum"),
            current_value=("Current Value", "last"),
            latest_status=("Status", "last"),
            latest_instrument=("Instrument Type", "last"),
            latest_round=("Round/Stage", "last"),
        )
        .reset_index()
    )

    summary["total_invested"] = summary["gross_investment"] + summary["fees"]
    summary["gain_loss"] = summary["current_value"] - summary["total_invested"]
    summary["mom"] = summary["current_value"] / summary["total_invested"].replace(0, pd.NA)

    summary = summary.sort_values(["total_invested", "Company"], ascending=[False, True])
    return summary


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["Year"] = pd.to_datetime(temp["Date"], errors="coerce").dt.year

    yearly = (
        temp.groupby("Year", dropna=False)
        .agg(
            gross_investment=("Gross Investment", "sum"),
            fees=("Fees", "sum"),
            current_value=("Current Value", "sum"),
            deal_count=("Company", "count"),
        )
        .reset_index()
        .sort_values("Year")
    )

    yearly["total_invested"] = yearly["gross_investment"] + yearly["fees"]
    yearly["gain_loss"] = yearly["current_value"] - yearly["total_invested"]
    yearly["mom"] = yearly["current_value"] / yearly["total_invested"].replace(0, pd.NA)
    return yearly


def transaction_form(existing_row=None, form_key="transaction_form"):
    if existing_row is None:
        existing_row = {}

    existing_date = existing_row.get("Date")
    if pd.isna(existing_date):
        existing_date = pd.Timestamp.today().date()
    elif hasattr(existing_date, "date"):
        existing_date = existing_date.date()

    existing_instrument = existing_row.get("Instrument Type", "SAFE")
    if existing_instrument not in INSTRUMENT_OPTIONS:
        existing_instrument = "Other"

    existing_status = existing_row.get("Status", "Active")
    if existing_status not in STATUS_OPTIONS:
        existing_status = "Other"

    with st.form(form_key, clear_on_submit=False):
        c1, c2, c3 = st.columns(3)

        with c1:
            date = st.date_input("Date", value=existing_date)
            company = st.text_input("Company", value=existing_row.get("Company", "") or "")
            instrument_type = st.selectbox(
                "Instrument Type",
                options=INSTRUMENT_OPTIONS,
                index=INSTRUMENT_OPTIONS.index(existing_instrument),
            )

        with c2:
            round_stage = st.text_input("Round / Stage", value=existing_row.get("Round/Stage", "") or "")
            gross_investment = money_input("Gross Investment", existing_row.get("Gross Investment", 0.0))
            fees = money_input("Fees", existing_row.get("Fees", 0.0), help_text="You can type commas, for example 1,250")

        with c3:
            current_value = money_input("Current Value", existing_row.get("Current Value", 0.0))
            status = st.selectbox(
                "Status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(existing_status),
            )

        submitted = st.form_submit_button("Save Transaction")

    if not submitted:
        return None

    return {
        "Date": pd.to_datetime(date),
        "Company": company.strip(),
        "Instrument Type": instrument_type,
        "Round/Stage": round_stage.strip(),
        "Gross Investment": gross_investment,
        "Fees": fees,
        "Current Value": current_value,
        "Status": status,
    }


def template_csv_bytes() -> bytes:
    template_df = empty_df()
    return template_df.to_csv(index=False).encode("utf-8")


st.title("Angel Investment Tracker")

if "df" not in st.session_state:
    st.session_state.df = empty_df()

df = normalize_dataframe(st.session_state.df) if not st.session_state.df.empty else empty_df()
st.session_state.df = df

with st.sidebar:
    st.header("Instructions")
    st.markdown(
        """
        This app does not save data on the server.

        Your CSV file is the only source of truth.

        How to use it:
        1. Upload your current CSV in the Upload / Download tab.
        2. Add or edit investments during your session.
        3. Download the updated CSV before leaving.

        Fields used:
        Date
        Company
        Instrument Type
        Round/Stage
        Gross Investment
        Fees
        Current Value
        Status

        Total Invested is calculated automatically as Gross Investment + Fees.
        You can type dollar amounts with commas, for example 25,000.
        """
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Add Investment", "Edit Investments", "Upload / Download"]
)

with tab1:
    metrics = portfolio_metrics(df)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Gross Invested", format_currency(metrics["gross_investment"]))
    c2.metric("Fees", format_currency(metrics["fees"]))
    c3.metric("Total Invested", format_currency(metrics["total_invested"]))
    c4.metric("Current Value", format_currency(metrics["current_value"]))
    c5.metric("Gain / Loss", format_currency(metrics["gain_loss"]))

    st.caption(f'Portfolio companies: {metrics["positions"]:,}')

    st.subheader("Company Summary")
    comp = company_summary(df)
    if comp.empty:
        st.info("No investments loaded yet. Upload a CSV or add transactions manually.")
    else:
        display_comp = comp.copy()
        for col in ["gross_investment", "fees", "total_invested", "current_value", "gain_loss"]:
            display_comp[col] = display_comp[col].map(format_currency)
        display_comp["mom"] = display_comp["mom"].map(format_multiple)

        display_comp = display_comp.rename(
            columns={
                "deals": "Deals",
                "gross_investment": "Gross Invested",
                "fees": "Fees",
                "total_invested": "Total Invested",
                "current_value": "Current Value",
                "gain_loss": "Gain / Loss",
                "mom": "MoM",
                "latest_status": "Status",
                "latest_instrument": "Latest Instrument",
                "latest_round": "Latest Round/Stage",
            }
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
        for col in ["gross_investment", "fees", "total_invested", "current_value", "gain_loss"]:
            display_yearly[col] = display_yearly[col].map(format_currency)
        display_yearly["mom"] = display_yearly["mom"].map(format_multiple)

        display_yearly = display_yearly.rename(
            columns={
                "gross_investment": "Gross Invested",
                "fees": "Fees",
                "total_invested": "Total Invested",
                "current_value": "Current Value",
                "gain_loss": "Gain / Loss",
                "deal_count": "Deals",
                "mom": "MoM",
            }
        )

        st.dataframe(display_yearly, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Add New Investment")

    new_row = transaction_form(form_key="new_transaction_form")
    if new_row is not None:
        if not new_row["Company"]:
            st.error("Company is required.")
        else:
            updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            updated = normalize_dataframe(updated)
            updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
            st.session_state.df = updated
            st.success("Investment added to this session. Download your CSV to keep it.")
            st.rerun()

with tab3:
    st.subheader("Edit Existing Investments")

    if df.empty:
        st.info("No transactions available to edit.")
    else:
        edit_df = df.copy()
        edit_df["Delete"] = False
        edit_df["Date"] = pd.to_datetime(edit_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        edit_df["Gross Investment"] = edit_df["Gross Investment"].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        edit_df["Fees"] = edit_df["Fees"].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        edit_df["Current Value"] = edit_df["Current Value"].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

        edited_table = st.data_editor(
            edit_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Date": st.column_config.TextColumn("Date", help="Use YYYY-MM-DD"),
                "Company": st.column_config.TextColumn("Company", required=True),
                "Instrument Type": st.column_config.SelectboxColumn(
                    "Instrument Type",
                    options=INSTRUMENT_OPTIONS,
                    required=True,
                ),
                "Round/Stage": st.column_config.TextColumn("Round/Stage"),
                "Gross Investment": st.column_config.TextColumn(
                    "Gross Investment",
                    help="You can type commas, for example 25,000",
                ),
                "Fees": st.column_config.TextColumn(
                    "Fees",
                    help="You can type commas, for example 1,250",
                ),
                "Current Value": st.column_config.TextColumn(
                    "Current Value",
                    help="You can type commas, for example 32,500",
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=STATUS_OPTIONS,
                    required=True,
                ),
                "Delete": st.column_config.CheckboxColumn("Delete"),
            },
        )

        if st.button("Apply Table Updates"):
            try:
                updated = edited_table.copy()
                updated["Date"] = pd.to_datetime(updated["Date"], errors="coerce")

                for col in ["Gross Investment", "Fees", "Current Value"]:
                    updated[col] = updated[col].apply(parse_money)

                updated["Company"] = updated["Company"].fillna("").astype(str).str.strip()
                updated["Instrument Type"] = updated["Instrument Type"].fillna("").astype(str).str.strip()
                updated["Round/Stage"] = updated["Round/Stage"].fillna("").astype(str).str.strip()
                updated["Status"] = updated["Status"].fillna("Active").astype(str).str.strip()

                updated = updated[updated["Delete"] != True].copy()
                updated = updated.drop(columns=["Delete"])

                if updated["Company"].eq("").any():
                    st.error("Every row must have a company name.")
                else:
                    updated = normalize_dataframe(updated)
                    updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                    st.session_state.df = updated
                    st.success("Table updated in this session. Download your CSV to keep it.")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not apply updates: {e}")

    st.subheader("Current Session Data")
    display_raw = add_calculated_fields(df)
    if display_raw.empty:
        st.info("No data loaded.")
    else:
        display_raw = display_raw.copy()
        for col in ["Gross Investment", "Fees", "Total Invested", "Current Value", "Gain / Loss"]:
            display_raw[col] = display_raw[col].map(format_currency)
        display_raw["MoM"] = display_raw["MoM"].map(format_multiple)
        st.dataframe(display_raw, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Upload CSV")
    uploaded_csv = st.file_uploader("Import CSV", type=["csv"])

    if uploaded_csv is not None:
        try:
            imported = pd.read_csv(uploaded_csv)
            imported = normalize_dataframe(imported)
            st.session_state.df = imported
            st.success("CSV loaded into this session.")
            st.rerun()
        except Exception as e:
            st.error(f"CSV import failed: {e}")

    st.subheader("Download CSV")
    export_df = export_ready_df(st.session_state.df)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    today_str = datetime.today().strftime("%Y-%m-%d")
    file_name = f"angel_portfolio_{today_str}.csv"

    st.download_button(
        "Download Current Data",
        data=csv_bytes,
        file_name=file_name,
        mime="text/csv",
    )

    st.subheader("Download Blank Template")
    template_name = f"angel_portfolio_template_{today_str}.csv"
    st.download_button(
        "Download Blank CSV Template",
        data=template_csv_bytes(),
        file_name=template_name,
        mime="text/csv",
    )

    st.subheader("Session Status")
    if st.session_state.df.empty:
        st.info("No CSV loaded yet. You can upload one or start adding transactions and then download the file.")
    else:
        st.success("You have working data in this session. Download the CSV when you are done.")
