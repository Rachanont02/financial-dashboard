import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuration ---
st.set_page_config(layout="wide", page_title="Simple Finance", page_icon="💰")
st.title("💰 Simple Financial Dashboard")

# --- Logic ---
def load_data(uploaded_file):
    df = None
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
    else:
        # Check for local 'statement.csv'
        try:
            df = pd.read_csv('statement.csv')
        except FileNotFoundError:
            pass

    if df is not None:
        # 1. smart Auto-Detection of columns
        # Find Date
        date_col = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), df.columns[0])
        
        # Find Description
        desc_col = next((c for c in df.columns if 'desc' in c.lower() or 'merchant' in c.lower() or 'name' in c.lower()), df.columns[2] if len(df.columns) > 2 else None)

        # Normalize basics
        df = df.rename(columns={date_col: 'Date', desc_col: 'Description'})

        # Find Amount (Debit/Expense) and Receive (Credit/Income)
        receive_col = next((c for c in df.columns if 'receive' in c.lower() or 'credit' in c.lower() or 'deposit' in c.lower()), None)
        amount_col = next((c for c in df.columns if c.lower() in ['amount', 'debit', 'withdraw', 'payment']), None)
        
        # Logic for two columns (Amount & Receive)
        if receive_col and amount_col:
             # Clean and Convert
             # astype(str) converts NaN to "nan", so we must handle that.
             # We use errors='coerce' in to_numeric to turn "nan" back to NaN (0).
             
             clean = lambda x: x.astype(str).str.lower().str.replace(',', '').str.replace('$', '').str.replace('kr', '').str.replace(' ', '')
             
             df[receive_col] = pd.to_numeric(clean(df[receive_col]), errors='coerce').fillna(0)
             df[amount_col] = pd.to_numeric(clean(df[amount_col]), errors='coerce').fillna(0)
             
             # Net Amount = Income (Receive) - Expense (Amount)
             # Assuming 'Amount' column lists positive numbers for expenses
             df['Amount'] = df[receive_col] - df[amount_col]
        else:
            # Fallback for single column
            target_amt = amount_col if amount_col else (df.columns[1] if len(df.columns) > 1 else None)
            df = df.rename(columns={target_amt: 'Amount'})

        # --- Auto-Categorization ---
        # Check if Category exists, if not, generate it
        cat_col = next((c for c in df.columns if 'cat' in c.lower()), None)
        if cat_col:
            df = df.rename(columns={cat_col: 'Category'})
        else:
            def categorize(desc):
                desc = str(desc).lower()
                # Keywords specific to Norway/General
                if 'kontoregulering' in desc and 'mobil overføring' in desc: return 'Savings 🏦'
                if any(x in desc for x in ['meny', 'rema', 'kiwi', 'bunnpris', 'coop', 'joker', 'dagligvare', 'extra', 'spar']): return 'Groceries 🛒'
                if any(x in desc for x in ['mcd', 'burger', 'sushi', 'pizza', 'restaurant', 'cafe', 'starbucks', 'boba', 'thai', 'vaffel', 'bakeri', 'espresso', 'tea']): return 'Food & Dining 🍔'
                if any(x in desc for x in ['ruter', 'vipps:ruter', 'vy', 'flytoget', 'uber', 'taxi', 'bolt', 'parkering', 'easypark', 'apcoa', 'voi', 'ryde', 'dott', 'buss']): return 'Transport 🚆'
                if any(x in desc for x in ['netflix', 'hbo', 'spotify', 'kino', 'steam', 'playstation', 'bio', 'disney']): return 'Entertainment 🎬'
                if any(x in desc for x in ['telia', 'telenor', 'nte', 'strøm', 'leie', 'husleie', 'forsikring', 'tryg']): return 'Bills & Utilities 💡'
                if any(x in desc for x in ['klarna', 'hm', 'zara', 'elkjøp', 'power', 'ikea', 'clas ohlson', 'normal', 'apotek', 'vitus', 'blomster']): return 'Shopping 🛍️'
                if any(x in desc for x in ['lønn', 'salary', 'deposit', 'overføring innland', 'vipps', 'straksoverføring']): return 'Income/Transfer 💰'
                return 'Other'

            df['Category'] = df['Description'].apply(categorize)
            
        return df

    # Default Sample Data
    data = {
        'Date': ['2023-12-01', '2023-12-02', '2023-12-05', '2023-12-08', '2023-12-10'],
        'Description': ['Grocery Store', 'Salary', 'Netflix', 'Gas Station', 'Restaurant'],
        'Category': ['Groceries 🛒', 'Income 💰', 'Entertainment 🎬', 'Transport 🚆', 'Food & Dining 🍔'],
        'Amount': [-150.00, 3000.00, -15.00, -45.00, -60.00] # Negative = Expense
    }
    return pd.DataFrame(data)

# --- Main App ---
st.write("### 📂 Upload your Bank Statement")
uploaded_file = st.file_uploader("Drag and drop your CSV file here", type=['csv'])

df = load_data(uploaded_file)

# Ensure types
df['Date'] = pd.to_datetime(df['Date'])
# Clean global amount column if needed (for fallback path)
if df['Amount'].dtype == 'object':
    df['Amount'] = df['Amount'].astype(str).str.lower().str.replace(',', '').str.replace('$', '').str.replace('kr', '').str.replace(' ', '')
df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

# --- Date Filter ---
df['Month_Year'] = df['Date'].dt.strftime('%Y-%m')
available_months = sorted(df['Month_Year'].unique(), reverse=True)

st.sidebar.header("Filter")
selected_month = st.sidebar.selectbox("Select Month", ["All"] + available_months)

if selected_month != "All":
    df = df[df['Month_Year'] == selected_month]

# Metrics
total_balance = df['Amount'].sum()
income = df[df['Amount'] > 0]['Amount'].sum()
expense = df[df['Amount'] < 0]['Amount'].sum()

# Top Row
col1, col2, col3 = st.columns(3)
col1.metric("Net Balance", f"{total_balance:,.2f} kr")
col2.metric("Total Income", f"{income:,.2f} kr", delta_color="normal")
col3.metric("Total Expenses", f"{expense:,.2f} kr", delta_color="inverse")

st.markdown("---")

# Charts
c1, c2 = st.columns(2)

# Chart 1: Daily Trend
daily = df.groupby('Date')['Amount'].sum().reset_index()
daily['Type'] = daily['Amount'].apply(lambda x: 'Income 🟢' if x > 0 else 'Expense 🔴')
fig1 = px.bar(daily, x='Date', y='Amount', title="Daily Money Flow", 
              color='Type', 
              color_discrete_map={'Income 🟢': '#00CC96', 'Expense 🔴': '#EF553B'})
c1.plotly_chart(fig1, use_container_width=True)

# Chart 2: Spending by Category (Pie Chart)
# Filter for expenses only (negative amounts)
expenses_df = df[df['Amount'] < 0]
if not expenses_df.empty:
    # Convert to positive for the chart
    expenses_df = expenses_df.copy()
    expenses_df['AbsAmount'] = expenses_df['Amount'].abs()
    # Group by Category to sum up duplicates
    cat_summary = expenses_df.groupby('Category')['AbsAmount'].sum().reset_index()
    
    fig2 = px.pie(cat_summary, values='AbsAmount', names='Category', 
                  title="Spending by Category 🍕", hole=0.4,
                  # Use a nice color sequence
                  color_discrete_sequence=px.colors.qualitative.Pastel)
    c2.plotly_chart(fig2, use_container_width=True)
else:
    c2.info("No expenses found to categorize.")

# Recent Transactions Table
st.subheader("Recent Transactions")

# Custom Sort: Date Descending, then Salary Priority Ascending (so Salary is bottom of that day)
df['IsPriority'] = df['Description'].astype(str).str.contains('Lønn Hector Trd AS', case=False, na=False)
df = df.sort_values(by=['Date', 'IsPriority'], ascending=[False, True])

# Style the dataframe: Green for positive, Red for negative
def color_amount(val):
    color = '#00CC96' if val > 0 else '#EF553B'
    return f'color: {color}'

# Display styled dataframe
# Note: we formatted the amount to 2 decimal places as well for better look
st.dataframe(
    df[['Date', 'Category', 'Description', 'Amount']]
    .style.map(color_amount, subset=['Amount'])
    .format({'Amount': '{:,.2f} kr', 'Date': lambda x: x.strftime('%Y-%m-%d')}),
    use_container_width=True
)
