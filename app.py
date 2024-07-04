import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import requests
import base64
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Stocks AI", layout="wide")

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("gemini_api")
stocks_api_key = os.getenv("stocks_api")

if not api_key or not stocks_api_key:
    st.error("Failed to retrieve API keys. Make sure they're set in your Streamlit Cloud settings.")
    st.stop()

# Configure Google Generative AI
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

# Function to encode the image
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Function to set background image
def set_bg_hack(main_bg):
    bin_str = get_base64_of_bin_file(main_bg)
    page_bg_img = '''
    <style>
    .stApp {
        background-image: url("data:image/png;base64,%s");
        background-size: cover;
    }
    .stApp::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%%;
        height: 100%%;
        background-color: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(5px);
        z-index: -1;
    }
    .styled-table {
        border-collapse: separate;
        border-spacing: 0;
        width: 100%%;
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
    }
    .styled-table thead tr {
        background-color: #1E3D59;
        color: #ffffff;
        text-align: left;
    }
    .styled-table th,
    .styled-table td {
        padding: 12px 15px;
    }
    .styled-table tbody tr {
        border-bottom: 1px solid #dddddd;
    }
    .styled-table tbody tr:nth-of-type(even) {
        background-color: rgba(240, 240, 240, 0.5);
    }
    .styled-table tbody tr:last-of-type {
        border-bottom: 2px solid #1E3D59;
    }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

# Set the background image
set_bg_hack('D:\\Projects\\Stocks-AI\\assets\\iceberg.jpg')

def fetch_stocks_data(symbol="IBM", interval="5min"):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={stocks_api_key}'
    r = requests.get(url)
    data = r.json()
    
    time_series_key = next((key for key in data.keys() if key.startswith("Time Series")), None)
    
    if not time_series_key:
        st.error("Could not find time series data in the API response.")
        return pd.DataFrame()
    
    time_series = data.get(time_series_key, {})
    
    df = pd.DataFrame.from_dict(time_series, orient='index')
    df.index.name = 'Timestamp'
    df.reset_index(inplace=True)
    
    df.columns = ['Timestamp'] + [col.split('. ')[-1].capitalize() for col in df.columns[1:]]
    
    for col in df.columns[1:]:
        df[col] = df[col].str.replace(r'^\d+\.\s*', '', regex=True)
    
    return df

def create_stock_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=('Stock Price', 'Volume'),
                        row_heights=[0.7, 0.3])

    # Candlestick chart
    fig.add_trace(go.Candlestick(x=df['Timestamp'],
                                 open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'],
                                 name='Price'),
                  row=1, col=1)

    # Volume chart
    fig.add_trace(go.Bar(x=df['Timestamp'], y=df['Volume'], name='Volume', marker_color='rgba(0, 0, 255, 0.5)'),
                  row=2, col=1)

    fig.update_layout(height=600, title_text=f"Stock Data", xaxis_rangeslider_visible=False)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

def main():
    st.markdown("""
        <h1 style='text-align: center; color: #1E3D59; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);'>STOCK AI</h1>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        symbol = st.text_input("Enter stock symbol", value="IBM")
        interval = st.selectbox("Select interval", ["1min", "5min", "15min", "30min", "60min"], index=1)
        fetch_button = st.button("Fetch Data")

    if fetch_button:
        df = fetch_stocks_data(symbol, interval)

        if not df.empty:
            numeric_columns = df.columns.drop('Timestamp')
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Create and display the chart
            fig = create_stock_chart(df)
            st.plotly_chart(fig, use_container_width=True)

            # Search functionality
            search = st.text_input("Search by Timestamp")
            if search:
                df = df[df['Timestamp'].str.contains(search, case=False)]

            # Display styled table
            st.markdown("<div class='styled-table'>", unsafe_allow_html=True)
            st.table(df.style.format({col: '{:.2f}' for col in numeric_columns if col != 'Volume'})
                              .format({'Volume': '{:,.0f}'}))
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.write("No data to display. Please check the API response.")

if __name__ == "__main__":
    main()