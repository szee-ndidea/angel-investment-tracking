from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Angel Investment Tracker", layout="wide")

st.markdown(
    """
    <style>
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 10px !important;
        min-height: 42px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stFormSubmitButton"] > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button[data-testid="baseButton-primary"] {
        background-color: #16a34a !important;
        border: 1px solid #16a34a !important;
        color: white !important;
    }

    div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button[data-testid="baseButton-primary"]:hover {
        background-color: #15803d !important;
        border: 1px solid #15803d !important;
        color: white !important;
    }

    div[data-testid="stFormSubmitButton"] > button[kind="secondary"],
    div[data-testid="stFormSubmitButton"] > button[data-testid="baseButton-secondary"] {
        background-color: #dc2626 !important;
        border: 1px solid #dc2626 !important;
        color: white !important;
    }

    div[data-testid="stFormSubmitButton"] > button[kind="secondary"]:hover,
    div[data-testid="stFormSubmitButton"] > button[data-testid="baseButton-secondary"]:hover {
        background-color: #b91c1c !important;
        border: 1px solid #b91c1c !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    "Date Added",
    "Date Updated",
]

STATUS_OPTIONS = [
    "Active",
    "Exited",
    "Partial Realized",
    "Written Off",
    "Closed",
]

ZERO_CURRENT_VALUE_STATUSES = {"Exited", "Partial Realized", "Written Off", "Closed"}
COMPANY_WIDE_EXIT_STATUSES = {"Exited", "Written Off", "Closed"}

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

INVESTMENT_INSTRUMENT_OPTIONS = [x for x in INSTRUMENT_OPTIONS if x != "Fee"]
METRIC_VIEW_OPTIONS = ["Total", "Realized", "Unrealized"]

COLUMN_MAP = {
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
    "date added": "Date Added",
    "created at": "Date Added",
    "date created": "Date Added",
    "date updated": "Date Updated",
    "updated at": "Date Updated",
    "last updated": "Date Updated",
}


def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPECTED_COLUMNS)


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def canonicalize_status(value) -> str:
    if value is None or pd.isna(value):
        return "Active"

    text = str(value).strip()
    if text == "":
        return "Active"

    status_map = {
        "active": "Active",
        "exited": "Exited",
        "partial realized": "Partial Realized",
        "partially realized": "Partial Realized",
        "partial exit": "Partial Realized",
        "partially exited": "Partial Realized",
        "written off": "Written Off",
        "write off": "Written Off",
        "closed": "Closed",
        "converted": "Closed",
        "paused": "Closed",
        "other": "Closed",
    }

    return status_map.get(text.lower(), "Active")


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


def money_input(label: str, value=0.0, help_text=None, disabled: bool = False, key=None) -> float:
    default_text = f"{float(value):,.0f}" if value not in [None, ""] and not pd.isna(value) else ""
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled, key=key)
    try:
        return parse_money(raw)
    except Exception:
        st.error(f"{label} must be a valid dollar amount.")
        st.stop()


def nullable_money_input(label: str, value=None, help_text=None, disabled: bool = False, key=None):
    default_text = "" if value is None or pd.isna(value) else f"{float(value):,.0f}"
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled, key=key)
    try:
        return parse_nullable_money(raw)
    except Exception:
        st.error(f"{label} must be a valid dollar amount or blank.")
        st.stop()


def investment_only_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df["Instrument Type"].fillna("") != "Fee"].copy()


def fee_only_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df["Instrument Type"].fillna("") == "Fee"].copy()


def apply_status_value_rules(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    fee_mask = out["Instrument Type"].eq("Fee")
    out.loc[fee_mask, "Gross Investment"] = 0.0
    out.loc[fee_mask, "Current Value"] = 0.0
    out.loc[fee_mask, "Distributions"] = 0.0
    out.loc[fee_mask, "Valuation/Cap at Investment"] = pd.NA
    out.loc[fee_mask, "Round/Stage"] = ""
    out.loc[fee_mask, "Source of Deal"] = ""
    out.loc[fee_mask, "Status"] = "Active"

    zero_value_mask = out["Status"].isin(list(ZERO_CURRENT_VALUE_STATUSES))
    out.loc[zero_value_mask, "Current Value"] = 0.0

    return out


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename_dict = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in COLUMN_MAP:
            rename_dict[col] = COLUMN_MAP[key]

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
    df["Status"] = df["Status"].apply(canonicalize_status)
    df["Source of Deal"] = df["Source of Deal"].fillna("").astype(str).str.strip()
    df["Date Added"] = df["Date Added"].fillna("").astype(str).str.strip()
    df["Date Updated"] = df["Date Updated"].fillna("").astype(str).str.strip()

    df = apply_status_value_rules(df)
    df = df.dropna(how="all")
    return df


def export_ready_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not out.empty:
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def value_basis_series(df: pd.DataFrame, metric_view: str) -> pd.Series:
    if metric_view == "Realized":
        return df["Distributions"].fillna(0.0)
    if metric_view == "Unrealized":
        return df["Current Value"].fillna(0.0)
    return df["Current Value"].fillna(0.0) + df["Distributions"].fillna(0.0)


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

    summary["gain_loss"] = (
        summary["current_value"] + summary["distributions"] - summary["gross_investment"] - summary["fees"]
    )
    summary["moic"] = (
        (summary["current_value"] + summary["distributions"])
        / summary["gross_investment"].replace(0, pd.NA)
    )
    summary["tvpi"] = (
        (summary["current_value"] + summary["distributions"])
        / (summary["gross_investment"] + summary["fees"]).replace(0, pd.NA)
    )

    return summary.sort_values(["gross_investment", "Company"], ascending=[False, True])


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

    return summary.sort_values(["total_fees", "Company"], ascending=[False, True])


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

    fee_yearly = fee_df.groupby("Year", dropna=False).agg(fees_only=("Fees", "sum")).reset_index()

    yearly = pd.merge(invest_yearly, fee_yearly, on="Year", how="outer").sort_values("Year")
    yearly["gross_investment"] = yearly["gross_investment"].fillna(0.0)
    yearly["fees_on_investments"] = yearly["fees_on_investments"].fillna(0.0)
    yearly["fees_only"] = yearly["fees_only"].fillna(0.0)
    yearly["current_value"] = yearly["current_value"].fillna(0.0)
    yearly["distributions"] = yearly["distributions"].fillna(0.0)
    yearly["deal_count"] = yearly["deal_count"].fillna(0).astype(int)

    yearly["fees"] = yearly["fees_on_investments"] + yearly["fees_only"]
    yearly["gain_loss"] = (
        yearly["current_value"] + yearly["distributions"] - yearly["gross_investment"] - yearly["fees"]
    )
    yearly["moic"] = (
        (yearly["current_value"] + yearly["distributions"])
        / yearly["gross_investment"].replace(0, pd.NA)
    )
    yearly["tvpi"] = (
        (yearly["current_value"] + yearly["distributions"])
        / (yearly["gross_investment"] + yearly["fees"]).replace(0, pd.NA)
    )

    return yearly[
        [
            "Year",
            "gross_investment",
            "fees",
            "current_value",
            "distributions",
            "gain_loss",
            "deal_count",
            "moic",
            "tvpi",
        ]
    ]


def apply_company_exit_update(updated_df: pd.DataFrame, company: str, new_status: str) -> pd.DataFrame:
    if updated_df.empty or not company or new_status not in COMPANY_WIDE_EXIT_STATUSES:
        return updated_df

    out = updated_df.copy()
    company_mask = (out["Instrument Type"].fillna("") != "Fee") & out["Company"].eq(company)
    out.loc[company_mask, "Status"] = new_status
    out.loc[company_mask, "Current Value"] = 0.0
    out.loc[company_mask, "Date Updated"] = now_timestamp()
    return out


def sort_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(["Date", "Company"], ascending=[False, True], na_position="last").reset_index(drop=True)


def add_row_and_refresh(df: pd.DataFrame, new_row: dict, toast_message: str, success_message: str):
    updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    updated = normalize_dataframe(updated)
    updated = sort_portfolio_df(updated)
    st.session_state.df = updated
    st.toast(toast_message)
    st.success(success_message)
    st.rerun()


def build_edit_selection_table(filtered_df: pd.DataFrame, is_fee: bool = False) -> pd.DataFrame:
    temp = filtered_df.copy().reset_index()
    temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if is_fee:
        display = temp[["index", "Date", "Company", "Fees", "Date Added", "Date Updated"]].copy()
        display["Fees"] = display["Fees"].map(format_currency_blank)
        return display.rename(
            columns={
                "index": "Row ID",
                "Company": "Organization",
                "Fees": "Fee Amount",
            }
        )

    display = temp[
        [
            "index",
            "Date",
            "Company",
            "Instrument Type",
            "Gross Investment",
            "Fees",
            "Current Value",
            "Distributions",
            "Status",
            "Date Added",
            "Date Updated",
        ]
    ].copy()
    for col in ["Gross Investment", "Fees", "Current Value", "Distributions"]:
        display[col] = display[col].map(format_currency_blank)
    return display.rename(columns={"index": "Row ID"})


def validation_response(message: str) -> dict:
    return {"action": "validation_error", "message": message}


def build_action_buttons(show_delete: bool, save_label: str):
    if show_delete:
        action_left, action_right = st.columns(2)
        with action_left:
            save_clicked = st.form_submit_button(save_label, type="primary", use_container_width=True)
        with action_right:
            delete_clicked = st.form_submit_button("Delete", type="secondary", use_container_width=True)
        return save_clicked, delete_clicked

    save_clicked = st.form_submit_button(save_label, type="primary", use_container_width=True)
    return save_clicked, False


def investment_form(
    existing_row=None,
    form_key="investment_form",
    is_new=False,
    existing_companies=None,
    company_mode="new",
    require_confirmation=False,
    show_delete=False,
):
    if existing_row is None:
        existing_row = {}
    if existing_companies is None:
        existing_companies = []

    existing_date = existing_row.get("Date")
    if pd.isna(existing_date):
        existing_date = pd.Timestamp.today().date()
    elif hasattr(existing_date, "date"):
        existing_date = existing_date.date()

    existing_instrument = existing_row.get("Instrument Type", "SAFE")
    if existing_instrument not in INSTRUMENT_OPTIONS or existing_instrument == "Fee":
        existing_instrument = "SAFE"

    existing_status = canonicalize_status(existing_row.get("Status", "Active"))
    existing_company = (existing_row.get("Company", "") or "").strip()
    existing_round_stage = existing_row.get("Round/Stage", "") or ""
    existing_source = existing_row.get("Source of Deal", "") or ""

    with st.form(form_key, clear_on_submit=is_new):
        if is_new and company_mode == "follow_on":
            if existing_companies:
                default_company_index = (
                    existing_companies.index(existing_company)
                    if existing_company and existing_company in existing_companies
                    else 0
                )
                company = st.selectbox(
                    "Existing Company",
                    options=existing_companies,
                    index=default_company_index,
                    key=f"{form_key}_existing_company",
                )
            else:
                st.info("No existing investment companies yet. Add the first investment as a new company.")
                company = ""
        else:
            company = st.text_input(
                "Company",
                value=existing_company,
                key=f"{form_key}_{'company_new' if is_new else 'company_edit'}",
            )

        top1, top2 = st.columns(2)
        with top1:
            date = st.date_input("Date", value=existing_date, key=f"{form_key}_date")
        with top2:
            instrument_type = st.selectbox(
                "Instrument Type",
                options=INVESTMENT_INSTRUMENT_OPTIONS,
                index=INVESTMENT_INSTRUMENT_OPTIONS.index(existing_instrument),
                key=f"{form_key}_instrument_type",
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
            round_stage = st.text_input(
                "Round / Stage",
                value=existing_round_stage,
                key=f"{form_key}_round_stage",
            )

        valuation_help = (
            "For SAFE or convertible note deals, use the cap here when there is one. If there is no cap, leave this blank."
            if instrument_type in ["SAFE", "Convertible Note"]
            else "Leave blank if not applicable."
        )

        bot1, bot2 = st.columns(2)
        with bot1:
            valuation_cap = nullable_money_input(
                "Valuation / Cap at Investment ($)",
                existing_row.get("Valuation/Cap at Investment"),
                help_text=valuation_help,
                key=f"{form_key}_valuation_cap",
            )
        with bot2:
            source_of_deal = st.text_input(
                "Source of Deal",
                value=existing_source,
                key=f"{form_key}_source_of_deal",
            )

        if is_new:
            status = "Active"
            val1, val2 = st.columns(2)
            with val1:
                current_value = money_input(
                    "Current Value ($)",
                    existing_row.get("Gross Investment", 0.0),
                    help_text="For a new transaction this is set automatically to Gross Investment. Fees are separate and not part of value.",
                    disabled=True,
                    key=f"{form_key}_current_value_new",
                )
            with val2:
                distributions = money_input(
                    "Distributions ($)",
                    0.0,
                    help_text="Not used when adding a new investment transaction.",
                    disabled=True,
                    key=f"{form_key}_distributions_new",
                )
        else:
            status = st.selectbox(
                "Status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(existing_status),
                key=f"{form_key}_status",
            )

            disable_current_value = status in ZERO_CURRENT_VALUE_STATUSES
            current_value_display = 0.0 if disable_current_value else existing_row.get("Current Value", 0.0)
            current_value_help = (
                "Automatically reset to zero for Exited, Partial Realized, Written Off, and Closed."
                if disable_current_value
                else "Unrealized residual value still held."
            )

            val1, val2 = st.columns(2)
            with val1:
                current_value = money_input(
                    "Current Value ($)",
                    current_value_display,
                    help_text=current_value_help,
                    disabled=disable_current_value,
                    key=f"{form_key}_current_value_edit",
                )
            with val2:
                distributions = money_input(
                    "Distributions ($)",
                    existing_row.get("Distributions", 0.0),
                    help_text="Cash returned from the company, for example on a partial or full exit.",
                    key=f"{form_key}_distributions_edit",
                )

        confirm_action = True
        if require_confirmation:
            confirm_action = st.checkbox(
                "I confirm I want to save changes or delete this record.",
                key=f"{form_key}_confirm_action",
            )

        save_label = "Add Transaction" if is_new else "Save Changes"
        save_clicked, delete_clicked = build_action_buttons(show_delete=show_delete, save_label=save_label)

    if not save_clicked and not delete_clicked:
        return None

    if (save_clicked or delete_clicked) and require_confirmation and not confirm_action:
        return validation_response("Please confirm before saving or deleting this record.")

    if is_new:
        current_value = gross_investment
        distributions = 0.0

    if status in ZERO_CURRENT_VALUE_STATUSES:
        current_value = 0.0

    created_at = str(existing_row.get("Date Added", "") or "").strip() or now_timestamp()
    updated_at = now_timestamp() if (not is_new and save_clicked) else str(existing_row.get("Date Updated", "") or "").strip()

    out = {
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
        "Date Added": created_at,
        "Date Updated": updated_at,
    }

    out_df = pd.DataFrame([out])
    out_df["Status"] = out_df["Status"].apply(canonicalize_status)
    out_df = apply_status_value_rules(out_df)

    return {
        "action": "delete" if delete_clicked else "save",
        "row": out_df.iloc[0].to_dict(),
    }


def fee_form(existing_row=None, form_key="fee_form", is_new=False, require_confirmation=False, show_delete=False):
    if existing_row is None:
        existing_row = {}

    existing_date = existing_row.get("Date")
    if pd.isna(existing_date):
        existing_date = pd.Timestamp.today().date()
    elif hasattr(existing_date, "date"):
        existing_date = existing_date.date()

    with st.form(form_key, clear_on_submit=is_new):
        top1, top2, top3 = st.columns(3)
        with top1:
            date = st.date_input("Date", value=existing_date, key=f"{form_key}_date")
        with top2:
            organization = st.text_input(
                "Organization",
                value=existing_row.get("Company", "") or "",
                key=f"{form_key}_organization",
            )
        with top3:
            fee_amount = money_input(
                "Fee Amount ($)",
                existing_row.get("Fees", 0.0),
                key=f"{form_key}_fee_amount",
            )

        confirm_action = True
        if require_confirmation:
            confirm_action = st.checkbox(
                "I confirm I want to save changes or delete this record.",
                key=f"{form_key}_confirm_action",
            )

        save_label = "Add Fee Record" if is_new else "Save Fee Changes"
        save_clicked, delete_clicked = build_action_buttons(show_delete=show_delete, save_label=save_label)

    if not save_clicked and not delete_clicked:
        return None

    if (save_clicked or delete_clicked) and require_confirmation and not confirm_action:
        return validation_response("Please confirm before saving or deleting this record.")

    created_at = str(existing_row.get("Date Added", "") or "").strip() or now_timestamp()
    updated_at = now_timestamp() if (not is_new and save_clicked) else str(existing_row.get("Date Updated", "") or "").strip()

    out = {
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
        "Date Added": created_at,
        "Date Updated": updated_at,
    }

    return {
        "action": "delete" if delete_clicked else "save",
        "row": out,
    }


title_col, help_col = st.columns([20, 1])
with title_col:
    st.title("Angel Investment Tracker")
with help_col:
    with st.popover("?"):
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
            Use the follow-on option when adding another check into an existing company.
            Use the Organization Fee form for fees such as an angel group.
            Organization fees are stored in the same CSV, but handled separately in the UI.
            Gross Investment is your actual investment into the company.
            Fees are separate deal costs.
            Current Value is unrealized residual value.
            Distributions are realized cash back from the company.
            Total value logic is Current Value + Distributions.
            MOIC = selected value basis / Gross Investment
            TVPI = selected value basis / (Gross Investment + Fees)
            For Exited and Partial Realized, Current Value is reset to zero and value comes from Distributions.
            For Written Off and Closed, Current Value is reset to zero.
            When a company with follow-on rows is marked Exited, Written Off, or Closed, that status is applied across that company’s investment rows.
            Older statuses such as Converted, Paused, and Other are normalized into Closed.
            For SAFE or Convertible Note deals, use the cap as valuation when there is one.
            If there is no cap, leave valuation blank.
            """
        )

if "df" not in st.session_state:
    st.session_state.df = empty_df()

if "overview_metric_view" not in st.session_state:
    st.session_state.overview_metric_view = "Total"

df = normalize_dataframe(st.session_state.df) if not st.session_state.df.empty else empty_df()
st.session_state.df = df

existing_investment_companies = sorted(
    [c for c in investment_only_df(df)["Company"].dropna().unique().tolist() if c != ""]
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Add Transaction", "Edit Transaction", "Upload / Download"]
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
        for col in ["gross_investment", "fees", "current_value", "distributions", "gain_loss"]:
            display_yearly[col] = display_yearly[col].map(format_currency)
        display_yearly["moic"] = display_yearly["moic"].map(format_multiple)
        display_yearly["tvpi"] = display_yearly["tvpi"].map(format_multiple)

        display_yearly = display_yearly.rename(
            columns={
                "gross_investment": "Gross Investment",
                "fees": "Fees",
                "current_value": "Current Value",
                "distributions": "Distributions",
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
            "current_value",
            "distributions",
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
                "current_value": "Current Value",
                "distributions": "Distributions",
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
        display_fee_summary["latest_date"] = pd.to_datetime(
            display_fee_summary["latest_date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

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

    add_new_investment_tab, add_follow_on_tab, add_fee_tab = st.tabs(
        ["New Investment", "New Follow-on", "New Organizational Fee"]
    )

    with add_new_investment_tab:
        result = investment_form(
            form_key="new_company_investment_form",
            is_new=True,
            existing_companies=existing_investment_companies,
            company_mode="new",
            show_delete=False,
        )
        if result is not None:
            if result["action"] == "validation_error":
                st.error(result["message"])
            elif result["action"] == "save":
                new_row = result["row"]
                if not new_row["Company"]:
                    st.error("Company is required.")
                else:
                    add_row_and_refresh(
                        df,
                        new_row,
                        toast_message="Investment added",
                        success_message=(
                            f"Added new investment for {new_row['Company']} with Status = Active, Current Value = "
                            f"{format_currency_blank(new_row['Current Value'])}, and Distributions = $0."
                        ),
                    )

    with add_follow_on_tab:
        if not existing_investment_companies:
            st.info("No existing investment companies yet. Add the first investment as a new company.")
        else:
            result = investment_form(
                form_key="follow_on_investment_form",
                is_new=True,
                existing_companies=existing_investment_companies,
                company_mode="follow_on",
                show_delete=False,
            )
            if result is not None:
                if result["action"] == "validation_error":
                    st.error(result["message"])
                elif result["action"] == "save":
                    follow_on_row = result["row"]
                    if not follow_on_row["Company"]:
                        st.error("Existing Company is required.")
                    else:
                        add_row_and_refresh(
                            df,
                            follow_on_row,
                            toast_message="Follow-on added",
                            success_message=(
                                f"Added follow-on investment for {follow_on_row['Company']} with Status = Active, Current Value = "
                                f"{format_currency_blank(follow_on_row['Current Value'])}, and Distributions = $0."
                            ),
                        )

    with add_fee_tab:
        result = fee_form(form_key="new_fee_form", is_new=True, show_delete=False)
        if result is not None:
            if result["action"] == "validation_error":
                st.error(result["message"])
            elif result["action"] == "save":
                new_fee_row = result["row"]
                if not new_fee_row["Company"]:
                    st.error("Organization is required.")
                else:
                    add_row_and_refresh(
                        df,
                        new_fee_row,
                        toast_message="Fee record added",
                        success_message="Fee record added. Download your CSV to keep it.",
                    )

with tab3:
    st.subheader("Edit Transactions")

    edit_investments_tab, edit_fees_tab = st.tabs(["Edit Investments", "Edit Organization Fees"])

    with edit_investments_tab:
        investment_df = investment_only_df(df)

        if investment_df.empty:
            st.info("No investment transactions available to edit.")
        else:
            f1, f2, f3 = st.columns(3)
            with f1:
                company_options = ["All"] + sorted(
                    [c for c in investment_df["Company"].dropna().unique().tolist() if c != ""]
                )
                company_filter = st.selectbox("Company", company_options, key="investment_company_filter")
            with f2:
                instrument_filter = st.selectbox(
                    "Instrument Type",
                    ["All"] + INVESTMENT_INSTRUMENT_OPTIONS,
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
                filtered = filtered.copy()
                filtered["Date_Sort"] = pd.to_datetime(filtered["Date"], errors="coerce")
                filtered = filtered.sort_values(["Date_Sort", "Company"], ascending=[False, True]).drop(columns=["Date_Sort"])

                selection_table = build_edit_selection_table(filtered, is_fee=False)
                st.dataframe(selection_table, use_container_width=True, hide_index=True)

                selected_row_index = st.number_input(
                    "Row ID to edit",
                    min_value=int(selection_table["Row ID"].min()),
                    max_value=int(selection_table["Row ID"].max()),
                    value=int(selection_table["Row ID"].iloc[0]),
                    step=1,
                    key="selected_investment_row_id",
                )

                selected_row = df.loc[selected_row_index].to_dict()

                selected_date = pd.to_datetime(selected_row.get("Date"), errors="coerce")
                selected_date_str = selected_date.strftime("%Y-%m-%d") if pd.notna(selected_date) else "N/A"
                selected_total_paid = parse_money(selected_row.get("Gross Investment", 0)) + parse_money(
                    selected_row.get("Fees", 0)
                )

                company_name = selected_row.get("Company", "") or ""
                company_investment_rows = investment_df[investment_df["Company"] == company_name]
                has_follow_ons = len(company_investment_rows) > 1

                st.markdown("#### Selected Investment")
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Date", selected_date_str)
                s2.metric("Company", selected_row.get("Company", "") or "N/A")
                s3.metric("Instrument", selected_row.get("Instrument Type", "") or "N/A")
                s4.metric("Status", selected_row.get("Status", "") or "N/A")

                s5, s6, s7, s8 = st.columns(4)
                s5.metric("Gross Investment", format_currency_blank(selected_row.get("Gross Investment", 0)) or "$0")
                s6.metric("Fees", format_currency_blank(selected_row.get("Fees", 0)) or "$0")
                s7.metric("Current Value", format_currency_blank(selected_row.get("Current Value", 0)) or "$0")
                s8.metric("Distributions", format_currency_blank(selected_row.get("Distributions", 0)) or "$0")

                st.caption(f"Total Paid: {format_currency_blank(selected_total_paid) or '$0'}")
                st.caption(f"Date Added: {selected_row.get('Date Added', '') or 'N/A'}")
                st.caption(f"Date Updated: {selected_row.get('Date Updated', '') or 'N/A'}")
                st.markdown("#### Edit Investment")

                result = investment_form(
                    existing_row=selected_row,
                    form_key="edit_investment_form",
                    is_new=False,
                    existing_companies=existing_investment_companies,
                    require_confirmation=True,
                    show_delete=True,
                )

                if result is not None:
                    if result["action"] == "validation_error":
                        st.error(result["message"])
                    elif result["action"] == "delete":
                        updated = df.drop(index=selected_row_index).reset_index(drop=True)
                        updated = normalize_dataframe(updated) if not updated.empty else empty_df()
                        st.session_state.df = updated
                        st.toast("Investment deleted")
                        st.success("Investment deleted. Download your CSV to keep it.")
                        st.rerun()
                    else:
                        edited_row = result["row"]
                        if not edited_row["Company"]:
                            st.error("Company is required.")
                        else:
                            updated = df.copy()
                            for key, value in edited_row.items():
                                updated.at[selected_row_index, key] = value

                            updated = apply_company_exit_update(
                                updated,
                                company=edited_row["Company"],
                                new_status=canonicalize_status(edited_row["Status"]),
                            )

                            updated = normalize_dataframe(updated)
                            updated = sort_portfolio_df(updated)
                            st.session_state.df = updated
                            st.toast("Investment updated")

                            if canonicalize_status(edited_row["Status"]) in COMPANY_WIDE_EXIT_STATUSES and has_follow_ons:
                                st.success(
                                    f"Investment updated. {edited_row['Status']} was applied across all {company_name} investment rows."
                                )
                            else:
                                st.success("Investment updated. Download your CSV to keep it.")
                            st.rerun()

    with edit_fees_tab:
        fee_df = fee_only_df(df)

        if fee_df.empty:
            st.info("No organization fee records available to edit.")
        else:
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
                filtered = filtered.copy()
                filtered["Date_Sort"] = pd.to_datetime(filtered["Date"], errors="coerce")
                filtered = filtered.sort_values(["Date_Sort", "Company"], ascending=[False, True]).drop(columns=["Date_Sort"])

                selection_table = build_edit_selection_table(filtered, is_fee=True)
                st.dataframe(selection_table, use_container_width=True, hide_index=True)

                selected_row_index = st.number_input(
                    "Row ID to edit",
                    min_value=int(selection_table["Row ID"].min()),
                    max_value=int(selection_table["Row ID"].max()),
                    value=int(selection_table["Row ID"].iloc[0]),
                    step=1,
                    key="selected_fee_row_id",
                )

                selected_row = df.loc[selected_row_index].to_dict()

                selected_date = pd.to_datetime(selected_row.get("Date"), errors="coerce")
                selected_date_str = selected_date.strftime("%Y-%m-%d") if pd.notna(selected_date) else "N/A"

                st.markdown("#### Selected Fee Record")
                s1, s2, s3 = st.columns(3)
                s1.metric("Date", selected_date_str)
                s2.metric("Organization", selected_row.get("Company", "") or "N/A")
                s3.metric("Fee Amount", format_currency_blank(selected_row.get("Fees", 0)) or "$0")

                st.caption(f"Date Added: {selected_row.get('Date Added', '') or 'N/A'}")
                st.caption(f"Date Updated: {selected_row.get('Date Updated', '') or 'N/A'}")
                st.markdown("#### Edit Fee Record")

                result = fee_form(
                    existing_row=selected_row,
                    form_key="edit_fee_form",
                    is_new=False,
                    require_confirmation=True,
                    show_delete=True,
                )

                if result is not None:
                    if result["action"] == "validation_error":
                        st.error(result["message"])
                    elif result["action"] == "delete":
                        updated = df.drop(index=selected_row_index).reset_index(drop=True)
                        updated = normalize_dataframe(updated) if not updated.empty else empty_df()
                        st.session_state.df = updated
                        st.toast("Fee record deleted")
                        st.success("Fee record deleted. Download your CSV to keep it.")
                        st.rerun()
                    else:
                        edited_fee_row = result["row"]
                        if not edited_fee_row["Company"]:
                            st.error("Organization is required.")
                        else:
                            updated = df.copy()
                            for key, value in edited_fee_row.items():
                                updated.at[selected_row_index, key] = value
                            updated = normalize_dataframe(updated)
                            updated = sort_portfolio_df(updated)
                            st.session_state.df = updated
                            st.toast("Fee record updated")
                            st.success("Fee record updated. Download your CSV to keep it.")
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
