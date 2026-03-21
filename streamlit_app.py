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


def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPECTED_COLUMNS)


def parse_money(value):
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


def parse_nullable_money(value):
    if value is None:
        return pd.NA

    if isinstance(value, (int, float)):
        if pd.isna(value):
            return pd.NA
        return float(value)

    text = str(value).strip()
    if text == "" or text.upper() == "N/A":
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


def money_input(label: str, value=0.0, help_text=None, disabled: bool = False) -> float:
    default_text = f"{float(value):,.0f}" if value not in [None, ""] and not pd.isna(value) else ""
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled)
    try:
        return parse_money(raw)
    except Exception:
        st.error(f"{label} must be a valid dollar amount.")
        st.stop()


def nullable_money_input(label: str, value=None, help_text=None, disabled: bool = False):
    if value is None or pd.isna(value):
        default_text = ""
    else:
        default_text = f"{float(value):,.0f}"
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled)
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

    for col in ["Gross Investment", "Fees", "Current Value"]:
        df[col] = df[col].apply(parse_money)

    df["Valuation/Cap at Investment"] = df["Valuation/Cap at Investment"].apply(parse_nullable_money)
    df["Company"] = df["Company"].fillna("").astype(str).str.strip()
    df["Instrument Type"] = df["Instrument Type"].fillna("").astype(str).str.strip()
    df["Round/Stage"] = df["Round/Stage"].fillna("").astype(str).str.strip()
    df["Status"] = df["Status"].fillna("Active").astype(str).str.strip()
    df["Source of Deal"] = df["Source of Deal"].fillna("").astype(str).str.strip()

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


def add_calculated_fields(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out["Total Paid"] = out["Gross Investment"] + out["Fees"]
    out["Gain / Loss"] = out["Current Value"] - out["Total Paid"]
    out["MOIC"] = out["Current Value"] / out["Total Paid"].replace(0, pd.NA)
    out["TVPI"] = out["Current Value"] / out["Total Paid"].replace(0, pd.NA)
    return out


def portfolio_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "gross_investment": 0.0,
            "fees": 0.0,
            "total_paid": 0.0,
            "current_value": 0.0,
            "gain_loss": 0.0,
            "positions": 0,
            "transactions": 0,
            "moic": pd.NA,
            "tvpi": pd.NA,
        }

    invest_df = investment_only_df(df)

    gross_investment = invest_df["Gross Investment"].fillna(0).sum()
    fees = df["Fees"].fillna(0).sum()
    total_paid = gross_investment + fees
    current_value = invest_df["Current Value"].fillna(0).sum()
    gain_loss = current_value - total_paid
    positions = invest_df["Company"].replace("", pd.NA).dropna().nunique()
    transactions = len(df)
    moic = current_value / total_paid if total_paid != 0 else pd.NA
    tvpi = current_value / total_paid if total_paid != 0 else pd.NA

    return {
        "gross_investment": gross_investment,
        "fees": fees,
        "total_paid": total_paid,
        "current_value": current_value,
        "gain_loss": gain_loss,
        "positions": positions,
        "transactions": transactions,
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
            latest_status=("Status", "last"),
            latest_instrument=("Instrument Type", "last"),
            latest_round=("Round/Stage", "last"),
            latest_valuation_cap=("Valuation/Cap at Investment", "last"),
            latest_source_of_deal=("Source of Deal", "last"),
        )
        .reset_index()
    )

    summary["total_paid"] = summary["gross_investment"] + summary["fees"]
    summary["gain_loss"] = summary["current_value"] - summary["total_paid"]
    summary["moic"] = summary["current_value"] / summary["total_paid"].replace(0, pd.NA)
    summary["tvpi"] = summary["current_value"] / summary["total_paid"].replace(0, pd.NA)

    summary = summary.sort_values(["gross_investment", "Company"], ascending=[False, True])
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
            deal_count=("Company", "count"),
        )
        .reset_index()
    )

    fee_yearly = (
        fee_df.groupby("Year", dropna=False)
        .agg(fees_only=("Fees", "sum"))
        .reset_index()
    )

    yearly = pd.merge(invest_yearly, fee_yearly, on="Year", how="outer").sort_values("Year")
    yearly["gross_investment"] = yearly["gross_investment"].fillna(0.0)
    yearly["fees_on_investments"] = yearly["fees_on_investments"].fillna(0.0)
    yearly["fees_only"] = yearly["fees_only"].fillna(0.0)
    yearly["current_value"] = yearly["current_value"].fillna(0.0)
    yearly["deal_count"] = yearly["deal_count"].fillna(0).astype(int)

    yearly["fees"] = yearly["fees_on_investments"] + yearly["fees_only"]
    yearly["total_paid"] = yearly["gross_investment"] + yearly["fees"]
    yearly["gain_loss"] = yearly["current_value"] - yearly["total_paid"]
    yearly["moic"] = yearly["current_value"] / yearly["total_paid"].replace(0, pd.NA)
    yearly["tvpi"] = yearly["current_value"] / yearly["total_paid"].replace(0, pd.NA)

    return yearly[
        ["Year", "gross_investment", "fees", "total_paid", "current_value", "gain_loss", "deal_count", "moic", "tvpi"]
    ]


def transaction_form(existing_row=None, form_key="transaction_form", is_new=False):
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
        top1, top2, top3 = st.columns(3)
        with top1:
            date = st.date_input("Date", value=existing_date)
        with top2:
            company = st.text_input(
                "Company / Organization" if existing_instrument == "Fee" else "Company",
                value=existing_row.get("Company", "") or "",
            )
        with top3:
            instrument_type = st.selectbox(
                "Instrument Type",
                options=INSTRUMENT_OPTIONS,
                index=INSTRUMENT_OPTIONS.index(existing_instrument),
            )

        mid1, mid2, mid3 = st.columns(3)
        with mid1:
            gross_investment = money_input("Gross Investment ($)", existing_row.get("Gross Investment", 0.0))
        with mid2:
            fees = money_input(
                "Fees ($)",
                existing_row.get("Fees", 0.0),
                help_text="You can type commas, for example 1,250",
            )
        with mid3:
            round_stage = st.text_input("Round / Stage", value=existing_row.get("Round/Stage", "") or "")

        if instrument_type in ["SAFE", "Convertible Note"]:
            valuation_help = "For SAFE or convertible note deals, use the cap here when there is one. If there is no cap, leave this blank."
        elif instrument_type == "Fee":
            valuation_help = "Leave blank for fee records."
        else:
            valuation_help = "Leave blank if not applicable."

        bot1, bot2 = st.columns(2)
        with bot1:
            valuation_cap = nullable_money_input(
                "Valuation / Cap at Investment ($)",
                existing_row.get("Valuation/Cap at Investment"),
                help_text=valuation_help,
                disabled=(instrument_type == "Fee"),
            )
        with bot2:
            source_of_deal = st.text_input("Source of Deal", value=existing_row.get("Source of Deal", "") or "")

        val1, val2 = st.columns(2)
        with val1:
            if is_new:
                auto_current_value = 0.0 if instrument_type == "Fee" else gross_investment
                current_value = money_input(
                    "Current Value ($)",
                    auto_current_value,
                    help_text="For a new transaction this is set automatically to Gross Investment. Fees are separate and not part of value.",
                    disabled=True,
                )
            else:
                default_current = existing_row.get("Current Value", 0.0)
                if instrument_type == "Fee":
                    current_value = money_input(
                        "Current Value ($)",
                        0.0,
                        help_text="Fee records stay at zero value.",
                        disabled=True,
                    )
                else:
                    current_value = money_input("Current Value ($)", default_current)
        with val2:
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
        current_value = 0.0 if instrument_type == "Fee" else gross_investment
    elif instrument_type == "Fee":
        current_value = 0.0

    return {
        "Date": pd.to_datetime(date),
        "Company": company.strip(),
        "Instrument Type": instrument_type,
        "Round/Stage": round_stage.strip(),
        "Gross Investment": gross_investment,
        "Fees": fees,
        "Current Value": current_value,
        "Status": status,
        "Valuation/Cap at Investment": valuation_cap,
        "Source of Deal": source_of_deal.strip(),
    }


def build_record_label(row) -> str:
    date_val = pd.to_datetime(row["Date"], errors="coerce")
    date_str = date_val.strftime("%Y-%m-%d") if pd.notna(date_val) else "No Date"
    gross = format_currency_blank(row.get("Gross Investment", 0))
    fees = format_currency_blank(row.get("Fees", 0))
    instrument = row.get("Instrument Type", "")
    company = row.get("Company", "")
    return f"{date_str} | {company} | {instrument} | Gross {gross} | Fees {fees}"


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
        2. Add or edit transactions during your session.
        3. Download the updated CSV before leaving.

        Notes:
        Use Instrument Type = Fee for organization fees such as Irish Angels.
        For SAFE or Convertible Note deals, use the cap as valuation when there is one.
        If there is no cap, leave valuation blank.
        Gross Investment is your actual investment into the company.
        Fees are separate deal costs.
        Total Paid = Gross Investment + Fees
        Current Value excludes fees.
        MOIC and TVPI are currently shown against Total Paid in this version.
        """
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Add Investment", "Edit Investments", "Upload / Download"]
)

with tab1:
    metrics = portfolio_metrics(df)

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.metric("Gross Investment", format_currency_blank(metrics["gross_investment"]))
    r1c2.metric("Fees", format_currency_blank(metrics["fees"]))
    r1c3.metric("Total Paid", format_currency_blank(metrics["total_paid"]))
    r1c4.metric("Current Value", format_currency_blank(metrics["current_value"]))

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("Gain / Loss", format_currency_blank(metrics["gain_loss"]))
    r2c2.metric("MOIC", format_multiple(metrics["moic"]))
    r2c3.metric("TVPI", format_multiple(metrics["tvpi"]))
    r2c4.metric("Portfolio Companies", f'{metrics["positions"]:,}')

    st.caption("Current Value excludes fees. MOIC and TVPI are currently calculated as Current Value divided by Total Paid.")

    st.subheader("Yearly Summary")
    yearly = yearly_summary(df)
    if not yearly.empty:
        display_yearly = yearly.copy()
        for col in ["gross_investment", "fees", "total_paid", "current_value", "gain_loss"]:
            display_yearly[col] = display_yearly[col].map(format_currency)
        display_yearly["moic"] = display_yearly["moic"].map(format_multiple)
        display_yearly["tvpi"] = display_yearly["tvpi"].map(format_multiple)

        display_yearly = display_yearly.rename(
            columns={
                "gross_investment": "Gross Investment",
                "fees": "Fees",
                "total_paid": "Total Paid",
                "current_value": "Current Value",
                "gain_loss": "Gain / Loss",
                "deal_count": "Deals",
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

with tab2:
    st.subheader("Add New Investment")

    new_row = transaction_form(form_key="new_transaction_form", is_new=True)
    if new_row is not None:
        if not new_row["Company"]:
            st.error("Company or organization is required.")
        else:
            updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            updated = normalize_dataframe(updated)
            updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
            st.session_state.df = updated
            st.toast("Transaction added")
            st.success("Transaction added. Download your CSV to keep it.")
            st.rerun()

with tab3:
    st.subheader("Edit Existing Investments")

    if df.empty:
        st.info("No transactions available to edit.")
    else:
        st.caption("Filter first, then choose one transaction to edit.")

        f1, f2, f3 = st.columns(3)
        with f1:
            company_options = ["All"] + sorted([c for c in df["Company"].dropna().unique().tolist() if c != ""])
            company_filter = st.selectbox("Company / Organization", company_options)
        with f2:
            instrument_filter = st.selectbox("Instrument Type", ["All"] + INSTRUMENT_OPTIONS)
        with f3:
            status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS)

        filtered = df.copy()
        if company_filter != "All":
            filtered = filtered[filtered["Company"] == company_filter]
        if instrument_filter != "All":
            filtered = filtered[filtered["Instrument Type"] == instrument_filter]
        if status_filter != "All":
            filtered = filtered[filtered["Status"] == status_filter]

        if filtered.empty:
            st.info("No transactions match your filters.")
        else:
            filtered = filtered.copy().reset_index()
            filtered["label"] = filtered.apply(build_record_label, axis=1)

            c1, c2 = st.columns([1, 1])
            with c1:
                st.metric("Matching Transactions", f"{len(filtered):,}")
            with c2:
                st.metric("Total Transactions", f"{len(df):,}")

            selected_label = st.selectbox(
                "Transaction to Edit",
                filtered["label"].tolist(),
                label_visibility="visible",
            )
            selected_row_index = filtered.loc[filtered["label"] == selected_label, "index"].iloc[0]
            selected_row = df.loc[selected_row_index].to_dict()

            selected_date = pd.to_datetime(selected_row.get("Date"), errors="coerce")
            selected_date_str = selected_date.strftime("%Y-%m-%d") if pd.notna(selected_date) else "N/A"
            selected_total_paid = parse_money(selected_row.get("Gross Investment", 0)) + parse_money(selected_row.get("Fees", 0))

            st.markdown("#### Selected Transaction")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Date", selected_date_str)
            s2.metric("Company / Org", selected_row.get("Company", "") or "N/A")
            s3.metric("Instrument", selected_row.get("Instrument Type", "") or "N/A")
            s4.metric("Status", selected_row.get("Status", "") or "N/A")

            s5, s6, s7, s8 = st.columns(4)
            s5.metric("Gross Investment", format_currency_blank(selected_row.get("Gross Investment", 0)) or "$0")
            s6.metric("Fees", format_currency_blank(selected_row.get("Fees", 0)) or "$0")
            s7.metric("Current Value", format_currency_blank(selected_row.get("Current Value", 0)) or "$0")
            s8.metric("Total Paid", format_currency_blank(selected_total_paid) or "$0")

            st.divider()
            st.markdown("#### Edit Transaction")

            edited_row = transaction_form(
                existing_row=selected_row,
                form_key="edit_transaction_form",
                is_new=False,
            )

            if edited_row is not None:
                if not edited_row["Company"]:
                    st.error("Company or organization is required.")
                else:
                    updated = df.copy()
                    for key, value in edited_row.items():
                        updated.at[selected_row_index, key] = value
                    updated = normalize_dataframe(updated)
                    updated = updated.sort_values(["Date", "Company"], na_position="last").reset_index(drop=True)
                    st.session_state.df = updated
                    st.toast("Transaction updated")
                    st.success("Transaction updated. Download your CSV to keep it.")
                    st.rerun()

            st.divider()

            with st.expander("Delete Transaction"):
                st.write("This removes the selected transaction from the current session.")
                confirm_delete = st.checkbox("I understand and want to delete this transaction")
                if st.button("Delete Selected Transaction", type="secondary", disabled=not confirm_delete):
                    updated = df.drop(index=selected_row_index).reset_index(drop=True)
                    updated = normalize_dataframe(updated) if not updated.empty else empty_df()
                    st.session_state.df = updated
                    st.toast("Transaction deleted")
                    st.success("Transaction deleted. Download your CSV to keep it.")
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
