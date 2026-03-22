from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Angel Investment Tracker", layout="wide")

# --- CONFIGURATION & CONSTANTS ---
EXPECTED_COLUMNS = [
    "Date", "Company", "Instrument Type", "Round/Stage", "Gross Investment", 
    "Fees", "Current Value", "Distributions", "Status", 
    "Valuation/Cap at Investment", "Source of Deal", "Date Added", "Date Updated"
]

STATUS_OPTIONS = ["Active", "Exited", "Partial Realized", "Written Off", "Closed"]
ZERO_CURRENT_VALUE_STATUSES = {"Exited", "Partial Realized", "Written Off", "Closed"}
COMPANY_WIDE_EXIT_STATUSES = {"Exited", "Written Off", "Closed"}
INSTRUMENT_OPTIONS = ["SAFE", "Convertible Note", "Equity", "Loan", "SPV", "Fund", "Fee", "Other"]
METRIC_VIEW_OPTIONS = ["Total", "Realized", "Unrealized"]

# --- HELPER FUNCTIONS ---
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPECTED_COLUMNS)

def parse_money(value):
    if value is None or pd.isna(value): return 0.0
    if isinstance(value, (int, float)): return float(value)
    text = str(value).strip()
    if text == "" or text.upper() in {"N/A", "NA", "<NA>", "NONE", "NULL", "NAN"}: return 0.0
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace("$", "").replace(",", "").replace(" ", "").replace("USD", "").replace("usd", "")
    if text in {"", "-", ".", "-."}: return 0.0
    try:
        amount = float(text)
        return -amount if negative else amount
    except: return 0.0

def parse_nullable_money(value):
    if value is None or pd.isna(value): return pd.NA
    if isinstance(value, (int, float)): return float(value)
    text = str(value).strip()
    if text == "" or text.upper() in {"N/A", "NA", "<NA>", "NONE", "NULL", "NAN"}: return pd.NA
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace("$", "").replace(",", "").replace(" ", "").replace("USD", "").replace("usd", "")
    if text in {"", "-", ".", "-."}: return pd.NA
    try:
        amount = float(text)
        return -amount if negative else amount
    except: return pd.NA

def canonicalize_status(value) -> str:
    if value is None or pd.isna(value): return "Active"
    text = str(value).strip().lower()
    status_map = {
        "active": "Active", "exited": "Exited", "partial realized": "Partial Realized",
        "partially realized": "Partial Realized", "partial exit": "Partial Realized",
        "partially exited": "Partial Realized", "written off": "Written Off",
        "write off": "Written Off", "closed": "Closed", "converted": "Closed",
        "paused": "Closed", "other": "Closed"
    }
    return status_map.get(text, "Active")

def apply_status_value_rules(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    fee_mask = out["Instrument Type"].eq("Fee")
    out.loc[fee_mask, ["Gross Investment", "Current Value", "Distributions"]] = 0.0
    out.loc[fee_mask, "Valuation/Cap at Investment"] = pd.NA
    out.loc[fee_mask, ["Round/Stage", "Source of Deal"]] = ""
    out.loc[fee_mask, "Status"] = "Active"
    zero_value_mask = out["Status"].isin(list(ZERO_CURRENT_VALUE_STATUSES))
    out.loc[zero_value_mask, "Current Value"] = 0.0
    return out

def money_input(label: str, value=0.0, help_text=None, disabled: bool = False, key=None) -> float:
    default_text = f"{float(value):,.0f}" if value not in [None, ""] and not pd.isna(value) else ""
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled, key=key)
    return parse_money(raw)

def nullable_money_input(label: str, value=None, help_text=None, disabled: bool = False, key=None):
    default_text = f"{float(value):,.0f}" if value not in [None, ""] and not pd.isna(value) else ""
    raw = st.text_input(label, value=default_text, help=help_text, disabled=disabled, key=key)
    return parse_nullable_money(raw)

def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    column_map = {
        "date": "Date", "company": "Company", "company name": "Company", "organization": "Company",
        "instrument": "Instrument Type", "instrument type": "Instrument Type", "security": "Instrument Type",
        "round": "Round/Stage", "round/stage": "Round/Stage", "gross investment": "Gross Investment",
        "investment amount": "Gross Investment", "amount": "Gross Investment", "fees": "Fees",
        "current value": "Current Value", "value": "Current Value", "distributions": "Distributions",
        "status": "Status", "valuation at investment": "Valuation/Cap at Investment",
        "valuation/cap at investment": "Valuation/Cap at Investment", "cap at investment": "Valuation/Cap at Investment",
        "source of deal": "Source of Deal", "date added": "Date Added", "date updated": "Date Updated"
    }
    rename_dict = {col: column_map[col.strip().lower()] for col in df.columns if col.strip().lower() in column_map}
    df = df.rename(columns=rename_dict)
    for col in EXPECTED_COLUMNS:
        if col not in df.columns: df[col] = None
    df = df[EXPECTED_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Gross Investment", "Fees", "Current Value", "Distributions"]:
        df[col] = df[col].apply(parse_money)
    df["Valuation/Cap at Investment"] = df["Valuation/Cap at Investment"].apply(parse_nullable_money)
    df["Status"] = df["Status"].apply(canonicalize_status)
    df = apply_status_value_rules(df)
    return df.dropna(how="all")

def format_currency_blank(value) -> str:
    if value is None or pd.isna(value) or value == 0: return ""
    return f"${value:,.0f}"

def format_multiple(value) -> str:
    if value is None or pd.isna(value): return "N/A"
    return f"{value:.2f}x"

def investment_only_df(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Instrument Type"] != "Fee"].copy() if not df.empty else df

def fee_only_df(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Instrument Type"] == "Fee"].copy() if not df.empty else df

def portfolio_metrics(df: pd.DataFrame, metric_view: str = "Total") -> dict:
    if df.empty: return {"gross_investment": 0.0, "fees": 0.0, "display_value": 0.0, "gain_loss": 0.0, "positions": 0, "moic": pd.NA, "tvpi": pd.NA, "distributions": 0.0}
    inv = investment_only_df(df)
    gross = inv["Gross Investment"].sum()
    fees = df["Fees"].sum()
    dist = inv["Distributions"].sum()
    curr = inv["Current Value"].sum()
    
    if metric_view == "Realized": val = dist
    elif metric_view == "Unrealized": val = curr
    else: val = curr + dist
    
    return {
        "gross_investment": gross, "fees": fees, "distributions": dist,
        "display_value": val, "gain_loss": (curr + dist) - (gross + fees),
        "positions": inv["Company"].nunique(),
        "moic": val / gross if gross != 0 else pd.NA,
        "tvpi": val / (gross + fees) if (gross + fees) != 0 else pd.NA
    }

def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    temp = df.copy()
    temp["Year"] = pd.to_datetime(temp["Date"]).dt.year
    yearly = temp.groupby("Year").agg(
        gross_investment=("Gross Investment", "sum"),
        fees=("Fees", "sum"),
        current_value=("Current Value", "sum"),
        distributions=("Distributions", "sum"),
        deal_count=("Company", "count")
    ).reset_index()
    yearly["gain_loss"] = (yearly["current_value"] + yearly["distributions"]) - (yearly["gross_investment"] + yearly["fees"])
    yearly["moic"] = (yearly["current_value"] + yearly["distributions"]) / yearly["gross_investment"].replace(0, pd.NA)
    yearly["tvpi"] = (yearly["current_value"] + yearly["distributions"]) / (yearly["gross_investment"] + yearly["fees"]).replace(0, pd.NA)
    return yearly

# --- FORMS ---
def investment_form(existing_row=None, form_key="inv_form", is_new=False, existing_companies=None, company_mode="new", require_confirmation=False, show_delete=False):
    row = existing_row or {}
    with st.form(form_key, clear_on_submit=is_new):
        if is_new and company_mode == "follow_on" and existing_companies:
            company = st.selectbox("Existing Company", options=existing_companies)
        else:
            company = st.text_input("Company", value=row.get("Company", ""))
            
        col1, col2 = st.columns(2)
        date = col1.date_input("Date", value=pd.to_datetime(row.get("Date", datetime.now())).date())
        inst_opts = [x for x in INSTRUMENT_OPTIONS if x != "Fee"]
        inst_type = col2.selectbox("Instrument", options=inst_opts, index=inst_opts.index(row.get("Instrument Type", "SAFE")) if row.get("Instrument Type") in inst_opts else 0)
        
        m1, m2, m3 = st.columns(3)
        gross = m1.number_input("Gross Investment ($)", value=float(row.get("Gross Investment", 0.0)))
        fees = m2.number_input("Fees ($)", value=float(row.get("Fees", 0.0)))
        round_stg = m3.text_input("Round/Stage", value=row.get("Round/Stage", ""))
        
        status = st.selectbox("Status", options=STATUS_OPTIONS, index=STATUS_OPTIONS.index(canonicalize_status(row.get("Status", "Active"))))
        
        v1, v2 = st.columns(2)
        curr_val = v1.number_input("Current Value ($)", value=float(row.get("Current Value", gross if is_new else 0.0)))
        dist = v2.number_input("Distributions ($)", value=float(row.get("Distributions", 0.0)))

        confirm_edit = st.checkbox("Confirm changes", value=True) if require_confirmation else True
        confirm_del = st.checkbox("Confirm delete", value=False) if show_delete else False

        # --- FIX: Dynamically handle button columns ---
        if show_delete:
            action_left, action_right = st.columns([5, 1])
            with action_left:
                save_clicked = st.form_submit_button("Save Changes", use_container_width=True, type="primary", disabled=not confirm_edit)
            with action_right:
                delete_clicked = st.form_submit_button("Delete", use_container_width=True, type="secondary", disabled=not confirm_del)
        else:
            save_clicked = st.form_submit_button("Add Transaction" if is_new else "Save Changes", use_container_width=True, type="primary", disabled=not confirm_edit)
            delete_clicked = False

    if not save_clicked and not delete_clicked: return None
    
    out_row = {
        "Date": pd.to_datetime(date), "Company": company, "Instrument Type": inst_type, "Round/Stage": round_stg,
        "Gross Investment": gross, "Fees": fees, "Current Value": 0.0 if status in ZERO_CURRENT_VALUE_STATUSES else curr_val,
        "Distributions": dist, "Status": status, "Date Added": row.get("Date Added", now_timestamp()), "Date Updated": now_timestamp() if not is_new else ""
    }
    return {"action": "delete" if delete_clicked else "save", "row": out_row}

def fee_form(existing_row=None, form_key="fee_form", is_new=False, show_delete=False):
    row = existing_row or {}
    with st.form(form_key, clear_on_submit=is_new):
        col1, col2, col3 = st.columns(3)
        date = col1.date_input("Date", value=pd.to_datetime(row.get("Date", datetime.now())).date())
        org = col2.text_input("Organization", value=row.get("Company", ""))
        fee_amt = col3.number_input("Fee Amount ($)", value=float(row.get("Fees", 0.0)))
        
        # --- FIX: Dynamically handle button columns ---
        if show_delete:
            action_left, action_right = st.columns([5, 1])
            with action_left:
                save_clicked = st.form_submit_button("Save Fee Changes", use_container_width=True, type="primary")
            with action_right:
                delete_clicked = st.form_submit_button("Delete", use_container_width=True, type="secondary")
        else:
            save_clicked = st.form_submit_button("Add Fee Record", use_container_width=True, type="primary")
            delete_clicked = False

    if not save_clicked and not delete_clicked: return None
    out_row = {
        "Date": pd.to_datetime(date), "Company": org, "Instrument Type": "Fee", "Fees": fee_amt,
        "Status": "Active", "Date Added": row.get("Date Added", now_timestamp()), "Date Updated": now_timestamp() if not is_new else ""
    }
    return {"action": "delete" if delete_clicked else "save", "row": out_row}

# --- MAIN APP LOGIC ---
if "df" not in st.session_state: st.session_state.df = empty_df()

df = normalize_dataframe(st.session_state.df)
existing_companies = sorted(investment_only_df(df)["Company"].unique().tolist())

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Add Transaction", "Edit Transaction", "Upload / Download"])

with tab1:
    st.title("Angel Investment Tracker")
    metric_view = st.segmented_control("Metric View", options=METRIC_VIEW_OPTIONS, default="Total")
    metrics = portfolio_metrics(df, metric_view)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross Invested", format_currency_blank(metrics["gross_investment"]))
    c2.metric("Total Fees", format_currency_blank(metrics["fees"]))
    c3.metric(f"{metric_view} Value", format_currency_blank(metrics["display_value"]))
    c4.metric("Net Gain/Loss", format_currency_blank(metrics["gain_loss"]))

    st.subheader("Yearly Summary")
    yearly = yearly_summary(df)
    if not yearly.empty:
        # Finalizing the formatting cut off in the previous snippet
        disp_yearly = yearly.copy()
        for col in ["gross_investment", "fees", "current_value", "distributions", "gain_loss"]:
            disp_yearly[col] = disp_yearly[col].map(format_currency_blank)
        disp_yearly["moic"] = disp_yearly["moic"].map(format_multiple)
        disp_yearly["tvpi"] = disp_yearly["tvpi"].map(format_multiple)
        st.dataframe(disp_yearly, use_container_width=True, hide_index=True)

with tab2:
    mode = st.radio("Transaction Type", ["New Company", "Follow-on Investment", "Org Fee"], horizontal=True)
    if mode == "Org Fee":
        res = fee_form(is_new=True)
    else:
        res = investment_form(is_new=True, existing_companies=existing_companies, company_mode="follow_on" if mode == "Follow-on Investment" else "new")
    
    if res and res["action"] == "save":
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([res["row"]])], ignore_index=True)
        st.success("Transaction added!")
        st.rerun()

with tab3:
    if df.empty:
        st.info("No data to edit.")
    else:
        edit_idx = st.selectbox("Select Transaction to Edit", options=df.index, format_func=lambda x: f"{df.loc[x, 'Date'].date()} - {df.loc[x, 'Company']} ({df.loc[x, 'Instrument Type']})")
        selected_row = df.loc[edit_idx].to_dict()
        
        if selected_row["Instrument Type"] == "Fee":
            res = fee_form(existing_row=selected_row, show_delete=True)
        else:
            res = investment_form(existing_row=selected_row, show_delete=True)
            
        if res:
            if res["action"] == "delete":
                st.session_state.df = st.session_state.df.drop(edit_idx)
                st.warning("Deleted.")
            else:
                for k, v in res["row"].items(): st.session_state.df.at[edit_idx, k] = v
                st.success("Updated.")
            st.rerun()

with tab4:
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        new_df = pd.read_csv(uploaded_file)
        st.session_state.df = normalize_dataframe(new_df)
        st.success("File loaded!")
        st.rerun()
    
    if not st.session_state.df.empty:
        csv = st.session_state.df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Portfolio CSV", data=csv, file_name="angel_tracker_export.csv", mime="text/csv")
