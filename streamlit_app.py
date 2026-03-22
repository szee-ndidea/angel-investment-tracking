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
    "Distributions",
    "Status",
    "Valuation/Cap at Investment",
    "Source of Deal",
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
    "Fee",
    "Other",
]

METRIC_VIEW_OPTIONS = ["Total", "Realized", "Unrealized"]


def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPECTED_COLUMNS)


def parse_money(value):
    if value is None or pd.isna(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if text == "" or text.upper() in {"N/A", "NA", "<NA>", "NONE", "NULL", "NAN"}:
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


def parse_nullable_money(value):
    if value is None or pd.isna(value):
        return pd.NA

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if text == "" or text.upper() in {"N/A", "NA", "<NA>", "NONE", "NULL", "NAN"}:
        return pd.NA

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
        return pd.NA

    amount = float(text)
    return -amount if negative else amount


def money_input(label: str, value=0.0, help_text=None, disabled: bool = False, key=None) -> float:
    default_text = f"{float(value):,.0f}" if value not in [None, ""] and not pd.isna(value) else ""
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled, key=key)
    try:
        return parse_money(raw)
    except Exception:
        st.error(f"{label} must be a valid dollar amount.")
        st.stop()


def nullable_money_input(label: str, value=None, help_text=None, disabled: bool = False, key=None):
    if value is None or pd.isna(value):
        default_text = ""
    else:
        default_text = f"{float(value):,.0f}"
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled, key=key)
    try:
        return parse_nullable_money(raw)
    except Exception:
        st.error(f"{label} must be a valid dollar amount or blank.")
        st.stop()


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    column_map = {
        "date": "Date",
        "company": "Company",
        "company name": "Company",
        "organization": "Company",
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
        "distributions": "Distributions",
        "distribution": "Distributions",
        "realized distributions": "Distributions",
        "cash distributions": "Distributions",
        "status": "Status",
        "company value at investment": "Valuation/Cap at Investment",
        "valuation at investment": "Valuation/Cap at Investment",
        "company valuation": "Valuation/Cap at Investment",
        "valuation/cap at investment": "Valuation/Cap at Investment",
        "cap at investment": "Valuation/Cap at Investment",
        "source of deal": "Source of Deal",
        "deal source": "Source of Deal",
        "source": "Source of Deal",
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

    for col in ["Gross Investment", "Fees", "Current Value", "Distributions"]:
        df[col] = df[col].apply(parse_money)

    df["Valuation/Cap at Investment"] = df["Valuation/Cap at Investment"].apply(parse_nullable_money)
    df["Company"] = df["Company"].fillna("").astype(str).str.strip()
    df["Instrument Type"] = df["Instrument Type"].fillna("").astype(str).str.strip()
    df["Round/Stage"] = df["Round/Stage"].fillna("").astype(str).str.strip()
    df["Status"] = df["Status"].fillna("Active").astype(str).str.strip()
    df["Source of Deal"] = df["Source of Deal"].fillna("").astype(str).str.strip()

    fee_mask = df["Instrument Type"].eq("Fee")
    df.loc[fee_mask, "Gross Investment"] = 0.0
    df.loc[fee_mask, "Current Value"] = 0.0
    df.loc[fee_mask, "Distributions"] = 0.0
    df.loc[fee_mask, "Valuation/Cap at Investment"] = pd.NA
    df.loc[fee_mask, "Round/Stage"] = ""
    df.loc[fee_mask, "Source of Deal"] = ""
    df.loc[fee_mask, "Status"] = "Active"

    df = df.dropna(how="all")
    return df


def export_ready_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not out.empty:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def format_currency(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"


def format_currency_blank(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"${value:,.0f}"


def format_multiple(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}x"


def investment_only_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df["Instrument Type"].fillna("") != "Fee"].copy()


def fee_only_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df["Instrument Type"].fillna("") == "Fee"].copy()


def value_basis_series(df: pd.DataFrame, metric_view: str) -> pd.Series:
    if metric_view == "Realized":
        return df["Distributions"].fillna(0.0)
    if metric_view == "Unrealized":
        return df["Current Value"].fillna(0.0)
    return df["Current Value"].fillna(0.0) + df["Distributions"].fillna(0.0)


def add_calculated_fields(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out["Total Paid"] = out["Gross Investment"] + out["Fees"]
    out["Total Value"] = out["Current Value"] + out["Distributions"]
    out["Gain / Loss"] = out["Total Value"] - out["Total Paid"]
    out["MOIC"] = out["Total Value"] / out["Gross Investment"].replace(0, pd.NA)
    out["TVPI"] = out["Total Value"] / out["Total Paid"].replace(0, pd.NA)
    return out


def portfolio_metrics(df: pd.DataFrame, metric_view: str = "Total") -> dict:
    if df.empty:
        return {
            "gross_investment": 0.0,
            "fees": 0.0,
            "current_value": 0.0,
            "distributions": 0.0,
            "display_value": 0.0,
            "gain_loss": 0.0,
            "positions": 0,
            "moic": pd.NA,
            "tvpi": pd.NA,
        }

    invest_df = investment_only_df(df)

    gross_investment = invest_df["Gross Investment"].fillna(0).sum()
    fees = df["Fees"].fillna(0).sum()
    total_paid = gross_investment + fees
    current_value = invest_df["Current Value"].fillna(0).sum()
    distributions = invest_df["Distributions"].fillna(0).sum()
    total_value = current_value + distributions
    display_value = value_basis_series(invest_df, metric_view).sum()
    gain_loss = total_value - total_paid
    positions = invest_df["Company"].replace("", pd.NA).dropna().nunique()
    moic = display_value / gross_investment if gross_investment != 0 else pd.NA
    tvpi = display_value / total_paid if total_paid != 0 else pd.NA

    return {
        "gross_investment": gross_investment,
        "fees": fees,
        "current_value": current_value,
        "distributions": distributions,
        "display_value": display_value,
        "gain_loss": gain_loss,
        "positions": positions,
        "moic": moic,
        "tvpi": tvpi,
    }


def company_summary(df: pd.DataFrame) -> pd.DataFrame:
    df = investment_only_df(df)
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
            current_value=("Current Value", "sum"),
            distributions=("Distributions", "sum"),
            latest_status=("Status", "last"),
            latest_instrument=("Instrument Type", "last"),
            latest_round=("Round/Stage", "last"),
            latest_valuation_cap=("Valuation/Cap at Investment", "last"),
            latest_source_of_deal=("Source of Deal", "last"),
        )
        .reset_index()
    )

    summary["total_paid"] = summary["gross_investment"] + summary["fees"]
    summary["total_value"] = summary["current_value"] + summary["distributions"]
    summary["gain_loss"] = summary["total_value"] - summary["total_paid"]
    summary["moic"] = summary["total_value"] / summary["gross_investment"].replace(0, pd.NA)
    summary["tvpi"] = summary["total_value"] / summary["total_paid"].replace(0, pd.NA)

    summary = summary.sort_values(["gross_investment", "Company"], ascending=[False, True])
    return summary


def org_fee_summary(df: pd.DataFrame) -> pd.DataFrame:
    fees = fee_only_df(df)
    if fees.empty:
        return pd.DataFrame()

    temp = fees.copy()
    temp["Date_Sort"] = pd.to_datetime(temp["Date"], errors="coerce")
    temp = temp.sort_values(["Company", "Date_Sort"])

    summary = (
        temp.groupby("Company", dropna=False)
        .agg(
            fee_records=("Company", "count"),
            total_fees=("Fees", "sum"),
            latest_date=("Date_Sort", "last"),
        )
        .reset_index()
    )

    summary = summary.sort_values(["total_fees", "Company"], ascending=[False, True])
    return summary


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["Year"] = pd.to_datetime(temp["Date"], errors="coerce").dt.year

    invest_df = investment_only_df(temp)
    fee_df = fee_only_df(temp)

    invest_yearly = (
        invest_df.groupby("Year", dropna=False)
        .agg(
            gross_investment=("Gross Investment", "sum"),
            fees_on_investments=("Fees", "sum"),
            current_value=("Current Value", "sum"),
            distributions=("Distributions", "sum"),
            deal_count=("Company", "count"),
        )
        .reset_index()
    )

    fee_yearly = (
        fee_df.groupby("Year", dropna=False)
        .agg(
            fees_only=("Fees", "sum"),
        )
        .reset_index()
    )

    yearly = pd.merge(invest_yearly, fee_yearly, on="Year", how="outer").sort_values("Year")
    yearly["gross_investment"] = yearly["gross_investment"].fillna(0.0)
    yearly["fees_on_investments"] = yearly["fees_on_investments"].fillna(0.0)
    yearly["fees_only"] = yearly["fees_only"].fillna(0.0)
    yearly["current_value"] = yearly["current_value"].fillna(0.0)
    yearly["distributions"] = yearly["distributions"].fillna(0.0)
    yearly["deal_count"] = yearly["deal_count"].fillna(0).astype(int)

    yearly["fees"] = yearly["fees_on_investments"] + yearly["fees_only"]
    yearly["total_paid"] = yearly["gross_investment"] + yearly["fees"]
    yearly["total_value"] = yearly["current_value"] + yearly["distributions"]
    yearly["gain_loss"] = yearly["total_value"] - yearly["total_paid"]
    yearly["moic"] = yearly["total_value"] / yearly["gross_investment"].replace(0, pd.NA)
    yearly["tvpi"] = yearly["total_value"] / yearly["total_paid"].replace(0, pd.NA)

    return yearly[
        [
            "Year",
            "gross_investment",
            "fees",
            "total_paid",
            "current_value",
            "distributions",
            "total_value",
            "gain_loss",
            "deal_count",
            "moic",
            "tvpi",
        ]
    ]


def investment_form(existing_row=None, form_key="investment_form", is_new=False):
    if existing_row is None:
        existing_row = {}

    existing_date = existing_row.get("Date")
    if pd.isna(existing_date):
        existing_date = pd.Timestamp.today().date()
    elif hasattr(existing_date, "date"):
        existing_date = existing_date.date()

    existing_instrument = existing_row.get("Instrument Type", "SAFE")
    if existing_instrument not in INSTRUMENT_OPTIONS or existing_instrument == "Fee":
        existing_instrument = "SAFE"

    existing_status = existing_row.get("Status", "Active")
    if existing_status not in STATUS_OPTIONS:
        existing_status = "Other"

    existing_company = existing_row.get("Company", "") or ""
    existing_round_stage = existing_row.get("Round/Stage", "") or ""
    existing_source = existing_row.get("Source of Deal", "") or ""

    existing_companies = []
    if "df" in st.session_state and not st.session_state.df.empty:
        temp_df = normalize_dataframe(st.session_state.df)
        existing_companies = sorted([c for c in temp_df["Company"].dropna().unique().tolist() if c != ""])

    with st.form(form_key, clear_on_submit=False):
        top1, top2, top3 = st.columns(3)
        with top1:
            date = st.date_input("Date", value=existing_date)
        with top2:
            is_follow_on = st.checkbox(
                "This is a follow-on investment",
                value=(is_new and existing_company in existing_companies and existing_company != ""),
                help="Use this when adding another check into an existing portfolio company.",
                key=f"{form_key}_is_follow_on",
            )
        with top3:
            investment_instruments = [x for x in INSTRUMENT_OPTIONS if x != "Fee"]
            instrument_type = st.selectbox(
                "Instrument Type",
                options=investment_instruments,
                index=investment_instruments.index(existing_instrument),
            )

        if is_follow_on and existing_companies:
            selected_default = existing_company if existing_company in existing_companies else existing_companies[0]
            company = st.selectbox(
                "Company",
                options=existing_companies,
                index=existing_companies.index(selected_default),
                help="Selecting an existing company keeps the company name consistent for portfolio counts and summaries.",
                key=f"{form_key}_company_follow_on",
            )
        else:
            company = st.text_input(
                "Company",
                value=existing_company,
                key=f"{form_key}_company_new",
            )

        mid1, mid2, mid3 = st.columns(3)
        with mid1:
            gross_investment = money_input(
                "Gross Investment ($)",
                existing_row.get("Gross Investment", 0.0),
                key=f"{form_key}_gross_investment",
            )
        with mid2:
            fees = money_input(
                "Fees ($)",
                existing_row.get("Fees", 0.0),
                help_text="You can type commas, for example 1,250",
                key=f"{form_key}_fees",
            )
        with mid3:
            round_stage = st.text_input("Round / Stage", value=existing_round_stage)

        if instrument_type in ["SAFE", "Convertible Note"]:
            valuation_help = "For SAFE or convertible note deals, use the cap here when there is one. If there is no cap, leave this blank."
        else:
            valuation_help = "Leave blank if not applicable."

        bot1, bot2 = st.columns(2)
        with bot1:
            valuation_cap = nullable_money_input(
                "Valuation / Cap at Investment ($)",
                existing_row.get("Valuation/Cap at Investment"),
                help_text=valuation_help,
                key=f"{form_key}_valuation_cap",
            )
        with bot2:
            source_of_deal = st.text_input("Source of Deal", value=existing_source)

        val1, val2, val3 = st.columns(3)
        with val1:
            if is_new:
                current_value = money_input(
                    "Current Value ($)",
                    gross_investment,
                    help_text="For a new transaction this is set automatically to Gross Investment. Fees are separate and not part of value.",
                    disabled=True,
                    key=f"{form_key}_current_value_new",
                )
            else:
                current_value = money_input(
                    "Current Value ($)",
                    existing_row.get("Current Value", 0.0),
                    help_text="Use this for unrealized residual value still held.",
                    key=f"{form_key}_current_value_edit",
                )
        with val2:
            distributions = money_input(
                "Distributions ($)",
                existing_row.get("Distributions", 0.0),
                help_text="Cash returned from the company, for example on a partial or full exit.",
                key=f"{form_key}_distributions",
            )
        with val3:
            if not is_new:
                status = st.selectbox(
                    "Status",
                    options=STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(existing_status),
                )
            else:
                status = "Active"
                st.text_input("Status", value="Active", disabled=True)

        submitted = st.form_submit_button("Add Transaction" if is_new else "Save Changes")

    if not submitted:
        return None

    if is_new:
        current_value = gross_investment

    return {
        "Date": pd.to_datetime(date),
        "Company": company.strip(),
        "Instrument Type": instrument_type,
        "Round/Stage": round_stage.strip(),
        "Gross Investment": gross_investment,
        "Fees": fees,
        "Current Value": current_value,
        "Distributions": distributions,
        "Status": status,
        "Valuation/Cap at Investment": valuation_cap,
        "Source of Deal": source_of_deal.strip(),
    }


def fee_form(existing_row=None, form_key="fee_form", is_new=False):
    if existing_row is None:
        existing_row = {}

    existing_date = existing_row.get("Date")
    if pd.isna(existing_date):
        existing_date = pd.Timestamp.today().date()
    elif hasattr(existing_date, "date"):
        existing_date = existing_date.date()

    with st.form(form_key, clear_on_submit=False):
        top1, top2, top3 = st.columns(3)
        with top1:
            date = st.date_input("Date", value=existing_date)
        with top2:
            organization = st.text_input("Organization", value=existing_row.get("Company", "") or "")
        with top3:
            fee_amount = money_input(
                "Fee Amount ($)",
                existing_row.get("Fees", 0.0),
                help_text="Use this for organization fees such as Irish Angels.",
                key=f"{form_key}_fee_amount",
            )

        submitted = st.form_submit_button("Add Fee Record" if is_new else "Save Fee Changes")

    if not submitted:
        return None

    return {
        "Date": pd.to_datetime(date),
        "Company": organization.strip(),
        "Instrument Type": "Fee",
        "Round/Stage": "",
        "Gross Investment": 0.0,
        "Fees": fee_amount,
        "Current Value": 0.0,
        "Distributions": 0.0,
        "Status": "Active",
        "Valuation/Cap at Investment": pd.NA,
        "Source of Deal": "",
    }


def build_record_label(row) -> str:
    date_val = pd.to_datetime(row["Date"], errors="coerce")
    date_str = date_val.strftime("%Y-%m-%d") if pd.notna(date_val) else "No Date"
    instrument = row.get("Instrument Type", "")
    company = row.get("Company", "")

    if instrument == "Fee":
        fees = format_currency_blank(row.get("Fees", 0))
        return f"{date_str} | {company} | Fee | {fees}"

    gross = format_currency_blank(row.get("Gross Investment", 0))
    distributions = format_currency_blank(row.get("Distributions", 0))
    return f"{date_str} | {company} | {instrument} | Gross {gross} | Dist {distributions}"


st.title("Angel Investment Tracker")

if "df" not in st.session_state:
    st.session_state.df = empty_df()

if "overview_metric_view" not in st.session_state:
    st.session_state.overview_metric_view = "Total"

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
        2. Add or edit transactions during your session.
        3. Download the updated CSV before leaving.

        Notes:
        Use the Investment form for company investments.
        Use the follow-on checkbox when adding another check into an existing company.
        Use the Organization Fee form for fees such as Irish Angels.
        Organization fees are stored in the same CSV, but handled separately in the UI.
        Gross Investment is your actual investment into the company.
        Fees are separate deal costs.
        Current Value is unrealized residual value.
        Distributions are realized cash back from the company.
        Total Value = Current Value + Distributions
        MOIC = selected value basis / Gross Investment
        TVPI = selected value basis / (Gross Investment + Fees)
        For SAFE or Convertible Note deals, use the cap as valuation when there is one.
        If there is no cap, leave valuation blank.
        """
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Add Investment", "Edit Investments", "Upload / Download"]
)

with tab1:
    metric_view = st.segmented_control(
        "Metric View",
        options=METRIC_VIEW_OPTIONS,
        selection_mode="single",
        default=st.session_state.overview_metric_view,
    )
    if metric_view is None:
        metric_view = st.session_state.overview_metric_view
    st.session_state.overview_metric_view = metric_view

    metrics = portfolio_metrics(df, metric_view=metric_view)

    view_label_map = {
        "Total": "Total Value",
        "Realized": "Realized Value",
        "Unrealized": "Unrealized Value",
    }
    display_value_label = view_label_map.get(metric_view, "Value")

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.metric("Gross Investment", format_currency_blank(metrics["gross_investment"]))
    r1c2.metric("Fees", format_currency_blank(metrics["fees"]))
    r1c3.metric(display_value_label, format_currency_blank(metrics["display_value"]))
    r1c4.metric("Total Gain / Loss", format_currency_blank(metrics["gain_loss"]))

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("Distributions", format_currency_blank(metrics["distributions"]))
    r2c2.metric("Portfolio Companies", f'{metrics["positions"]:,}')
    r2c3.metric("MOIC", format_multiple(metrics["moic"]))
    r2c4.metric("TVPI", format_multiple(metrics["tvpi"]))

    st.subheader("Yearly Summary")
    yearly = yearly_summary(df)
    if not yearly.empty:
        display_yearly = yearly.copy()
        for col in [
            "gross_investment",
            "fees",
            "total_paid",
            "current_value",
            "distributions",
            "total_value",
            "gain_loss",
        ]:
            display_yearly[col] = display_yearly[col].map(format_currency)
        display_yearly["moic"] = display_yearly["moic"].map(format_multiple)
        display_yearly["tvpi"] = display_yearly["tvpi"].map(format_multiple)

        display_yearly = display_yearly.rename(
            columns={
                "gross_investment": "Gross Investment",
                "fees": "Fees",
                "total_paid": "Total Paid",
                "current_value": "Current Value",
                "distributions": "Distributions",
                "total_value": "Total Value",
                "gain_loss": "Gain / Loss",
                "deal_count": "Investment Deals",
                "moic": "MOIC",
                "tvpi": "TVPI",
            }
        )

        st.dataframe(display_yearly, use_container_width=True, hide_index=True)
    else:
        st.info("No yearly data yet.")

    st.subheader("Company Summary")
    comp = company_summary(df)
    if comp.empty:
        st.info("No investment records loaded yet. Upload a CSV or add transactions manually.")
    else:
        display_comp = comp.copy()
        for col in [
            "gross_investment",
            "fees",
            "total_paid",
            "current_value",
            "distributions",
            "total_value",
            "gain_loss",
            "latest_valuation_cap",
        ]:
            display_comp[col] = display_comp[col].map(format_currency)
        display_comp["moic"] = display_comp["moic"].map(format_multiple)
        display_comp["tvpi"] = display_comp["tvpi"].map(format_multiple)

        display_comp = display_comp.rename(
            columns={
                "deals": "Deals",
                "gross_investment": "Gross Investment",
                "fees": "Fees",
                "total_paid": "Total Paid",
                "current_value": "Current Value",
                "distributions": "Distributions",
                "total_value": "Total Value",
                "gain_loss": "Gain / Loss",
                "moic": "MOIC",
                "tvpi": "TVPI",
                "latest_status": "Status",
                "latest_instrument": "Latest Instrument",
                "latest_round": "Latest Round/Stage",
                "latest_valuation_cap": "Valuation / Cap at Investment",
                "latest_source_of_deal": "Source of Deal",
            }
        )

        st.dataframe(display_comp, use_container_width=True, hide_index=True)

    st.subheader("Organization Fee Summary")
    fee_summary = org_fee_summary(df)
    if fee_summary.empty:
        st.info("No organization fee records yet.")
    else:
        display_fee_summary = fee_summary.copy()
        display_fee_summary["total_fees"] = display_fee_summary["total_fees"].map(format_currency)
        display_fee_summary["latest_date"] = pd.to_datetime(display_fee_summary["latest_date"], errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )

        display_fee_summary = display_fee_summary.rename(
            columns={
                "Company": "Organization",
                "fee_records": "Fee Records",
                "total_fees": "Total Fees",
                "latest_date": "Latest Date",
            }
        )

        st.dataframe(display_fee_summary, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Add Transactions")

    add_investment_tab, add_fee_tab = st.tabs(["Add Investment", "Add Organization Fee"])

    with add_investment_tab:
        new_row = investment_form(form_key="new_investment_form", is_new=True)
        if new_row is not None:
            if not new_row["Company"]:
                st.error("Company is required.")
            else:
                updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                updated = normalize_dataframe(updated)
                updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                st.session_state.df = updated
                st.toast("Investment added")
                st.success("Investment added. Download your CSV to keep it.")
                st.rerun()

    with add_fee_tab:
        st.caption("Use this for non investment organization fees such as Irish Angels.")
        new_fee_row = fee_form(form_key="new_fee_form", is_new=True)
        if new_fee_row is not None:
            if not new_fee_row["Company"]:
                st.error("Organization is required.")
            else:
                updated = pd.concat([df, pd.DataFrame([new_fee_row])], ignore_index=True)
                updated = normalize_dataframe(updated)
                updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                st.session_state.df = updated
                st.toast("Fee record added")
                st.success("Fee record added. Download your CSV to keep it.")
                st.rerun()

with tab3:
    st.subheader("Edit Transactions")

    edit_investments_tab, edit_fees_tab = st.tabs(["Edit Investments", "Edit Organization Fees"])

    with edit_investments_tab:
        investment_df = investment_only_df(df)

        if investment_df.empty:
            st.info("No investment transactions available to edit.")
        else:
            st.caption("Filter first, then choose one investment transaction to edit.")

            f1, f2, f3 = st.columns(3)
            with f1:
                company_options = ["All"] + sorted(
                    [c for c in investment_df["Company"].dropna().unique().tolist() if c != ""]
                )
                company_filter = st.selectbox("Company", company_options, key="investment_company_filter")
            with f2:
                instrument_filter = st.selectbox(
                    "Instrument Type",
                    ["All"] + [x for x in INSTRUMENT_OPTIONS if x != "Fee"],
                    key="investment_instrument_filter",
                )
            with f3:
                status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS, key="investment_status_filter")

            filtered = investment_df.copy()
            if company_filter != "All":
                filtered = filtered[filtered["Company"] == company_filter]
            if instrument_filter != "All":
                filtered = filtered[filtered["Instrument Type"] == instrument_filter]
            if status_filter != "All":
                filtered = filtered[filtered["Status"] == status_filter]

            if filtered.empty:
                st.info("No investment transactions match your filters.")
            else:
                filtered = filtered.copy().reset_index()
                filtered["label"] = filtered.apply(build_record_label, axis=1)

                c1, c2 = st.columns([1, 1])
                with c1:
                    st.metric("Matching Investments", f"{len(filtered):,}")
                with c2:
                    st.metric("Total Investments", f"{len(investment_df):,}")

                selected_label = st.selectbox(
                    "Investment Transaction to Edit",
                    filtered["label"].tolist(),
                    key="selected_investment_label",
                )
                selected_row_index = filtered.loc[filtered["label"] == selected_label, "index"].iloc[0]
                selected_row = df.loc[selected_row_index].to_dict()

                selected_date = pd.to_datetime(selected_row.get("Date"), errors="coerce")
                selected_date_str = selected_date.strftime("%Y-%m-%d") if pd.notna(selected_date) else "N/A"
                selected_total_paid = parse_money(selected_row.get("Gross Investment", 0)) + parse_money(
                    selected_row.get("Fees", 0)
                )
                selected_total_value = parse_money(selected_row.get("Current Value", 0)) + parse_money(
                    selected_row.get("Distributions", 0)
                )

                st.markdown("#### Selected Investment")
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Date", selected_date_str)
                s2.metric("Company", selected_row.get("Company", "") or "N/A")
                s3.metric("Instrument", selected_row.get("Instrument Type", "") or "N/A")
                s4.metric("Status", selected_row.get("Status", "") or "N/A")

                s5, s6, s7, s8, s9 = st.columns(5)
                s5.metric("Gross Investment", format_currency_blank(selected_row.get("Gross Investment", 0)) or "$0")
                s6.metric("Fees", format_currency_blank(selected_row.get("Fees", 0)) or "$0")
                s7.metric("Current Value", format_currency_blank(selected_row.get("Current Value", 0)) or "$0")
                s8.metric("Distributions", format_currency_blank(selected_row.get("Distributions", 0)) or "$0")
                s9.metric("Total Value", format_currency_blank(selected_total_value) or "$0")

                st.caption(f"Total Paid: {format_currency_blank(selected_total_paid) or '$0'}")

                st.divider()
                st.markdown("#### Edit Investment")

                edited_row = investment_form(
                    existing_row=selected_row,
                    form_key="edit_investment_form",
                    is_new=False,
                )

                if edited_row is not None:
                    if not edited_row["Company"]:
                        st.error("Company is required.")
                    else:
                        updated = df.copy()
                        for key, value in edited_row.items():
                            updated.at[selected_row_index, key] = value
                        updated = normalize_dataframe(updated)
                        updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                        st.session_state.df = updated
                        st.toast("Investment updated")
                        st.success("Investment updated. Download your CSV to keep it.")
                        st.rerun()

                st.divider()

                with st.expander("Delete Investment Transaction"):
                    st.write("This removes the selected investment transaction from the current session.")
                    confirm_delete = st.checkbox(
                        "I understand and want to delete this investment transaction",
                        key="confirm_delete_investment",
                    )
                    if st.button(
                        "Delete Selected Investment",
                        type="secondary",
                        disabled=not confirm_delete,
                        key="delete_investment_button",
                    ):
                        updated = df.drop(index=selected_row_index).reset_index(drop=True)
                        updated = normalize_dataframe(updated) if not updated.empty else empty_df()
                        st.session_state.df = updated
                        st.toast("Investment deleted")
                        st.success("Investment deleted. Download your CSV to keep it.")
                        st.rerun()

    with edit_fees_tab:
        fee_df = fee_only_df(df)

        if fee_df.empty:
            st.info("No organization fee records available to edit.")
        else:
            st.caption("Filter first, then choose one fee record to edit.")

            f1, f2 = st.columns(2)
            with f1:
                org_options = ["All"] + sorted([c for c in fee_df["Company"].dropna().unique().tolist() if c != ""])
                org_filter = st.selectbox("Organization", org_options, key="fee_org_filter")
            with f2:
                date_filter = st.selectbox(
                    "Date",
                    ["All"] + sorted(
                        pd.to_datetime(fee_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d").dropna().unique().tolist()
                    ),
                    key="fee_date_filter",
                )

            filtered = fee_df.copy()
            if org_filter != "All":
                filtered = filtered[filtered["Company"] == org_filter]
            if date_filter != "All":
                filtered_dates = pd.to_datetime(filtered["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
                filtered = filtered[filtered_dates == date_filter]

            if filtered.empty:
                st.info("No fee records match your filters.")
            else:
                filtered = filtered.copy().reset_index()
                filtered["label"] = filtered.apply(build_record_label, axis=1)

                c1, c2 = st.columns([1, 1])
                with c1:
                    st.metric("Matching Fee Records", f"{len(filtered):,}")
                with c2:
                    st.metric("Total Fee Records", f"{len(fee_df):,}")

                selected_label = st.selectbox(
                    "Fee Record to Edit",
                    filtered["label"].tolist(),
                    key="selected_fee_label",
                )
                selected_row_index = filtered.loc[filtered["label"] == selected_label, "index"].iloc[0]
                selected_row = df.loc[selected_row_index].to_dict()

                selected_date = pd.to_datetime(selected_row.get("Date"), errors="coerce")
                selected_date_str = selected_date.strftime("%Y-%m-%d") if pd.notna(selected_date) else "N/A"

                st.markdown("#### Selected Fee Record")
                s1, s2, s3 = st.columns(3)
                s1.metric("Date", selected_date_str)
                s2.metric("Organization", selected_row.get("Company", "") or "N/A")
                s3.metric("Fee Amount", format_currency_blank(selected_row.get("Fees", 0)) or "$0")

                st.divider()
                st.markdown("#### Edit Fee Record")

                edited_fee_row = fee_form(
                    existing_row=selected_row,
                    form_key="edit_fee_form",
                    is_new=False,
                )

                if edited_fee_row is not None:
                    if not edited_fee_row["Company"]:
                        st.error("Organization is required.")
                    else:
                        updated = df.copy()
                        for key, value in edited_fee_row.items():
                            updated.at[selected_row_index, key] = value
                        updated = normalize_dataframe(updated)
                        updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                        st.session_state.df = updated
                        st.toast("Fee record updated")
                        st.success("Fee record updated. Download your CSV to keep it.")
                        st.rerun()

                st.divider()

                with st.expander("Delete Fee Record"):
                    st.write("This removes the selected fee record from the current session.")
                    confirm_delete = st.checkbox(
                        "I understand and want to delete this fee record",
                        key="confirm_delete_fee",
                    )
                    if st.button(
                        "Delete Selected Fee Record",
                        type="secondary",
                        disabled=not confirm_delete,
                        key="delete_fee_button",
                    ):
                        updated = df.drop(index=selected_row_index).reset_index(drop=True)
                        updated = normalize_dataframe(updated) if not updated.empty else empty_df()
                        st.session_state.df = updated
                        st.toast("Fee record deleted")
                        st.success("Fee record deleted. Download your CSV to keep it.")
                        st.rerun()

with tab4:
    st.subheader("Upload CSV")
    uploaded_csv = st.file_uploader("Import CSV", type=["csv"])

    if uploaded_csv is not None:
        try:
            imported = pd.read_csv(uploaded_csv)
            imported = normalize_dataframe(imported)
            st.session_state.df = imported
            st.toast("CSV uploaded")
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

    st.subheader("Session Status")
    if st.session_state.df.empty:
        st.info("No CSV loaded yet. You can upload one or start adding transactions and then download the file.")
    else:
        st.success("You have working data in this session. Download the CSV when you are done.")
