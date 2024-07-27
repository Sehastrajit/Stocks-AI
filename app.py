import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Stocks AI", layout="wide")

def get_api_key(key_name):
    try:
        return st.secrets[key_name]
    except KeyError:
        st.error(f"Missing API key: {key_name}. Please set this in your Streamlit secrets.")
        st.info("To set up secrets in Streamlit Cloud:")
        st.code("""
1. Go to your app's page on Streamlit Cloud
2. Click on "Settings" (⚙️ icon)
3. Go to "Secrets" section
4. Add your API keys:
   gemini_api = "your_gemini_api_key"
   polygon_api_key = "your_polygon_api_key"
        """)
        st.stop()

gemini_api_key = get_api_key("gemini_api")
polygon_api_key = get_api_key("polygon_api_key")

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

def fetch_stocks_data(symbol="AAPL", timespan="minute", multiplier=5, from_date="2024-07-26", to_date="2024-07-27"):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}?apiKey={polygon_api_key}"
    response = requests.get(url)
    data = response.json()
    
    if 'results' not in data:
        st.error(f"Could not fetch stock data. API response: {data}")
        return pd.DataFrame()
    
    df = pd.DataFrame(data['results'])
    df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
    df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
    return df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]

def create_stock_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, subplot_titles=('Stock Price', 'Volume'),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=df['timestamp'],
                                 open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'],
                                 name='Price'),
                  row=1, col=1)

    fig.add_trace(go.Bar(x=df['timestamp'], y=df['Volume'], name='Volume', marker_color='rgba(0, 0, 255, 0.5)'),
                  row=2, col=1)

    fig.update_layout(height=600, title_text="Stock Data", xaxis_rangeslider_visible=False)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

def main():
    st.title("STOCK AI")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        symbol = st.text_input("Enter stock symbol", value="AAPL")
        timespan = st.selectbox("Select timespan", ["minute", "hour", "day", "week", "month", "quarter", "year"], index=0)
        multiplier = st.number_input("Multiplier", min_value=1, value=5)
        from_date = st.date_input("From date")
        to_date = st.date_input("To date")
        fetch_button = st.button("Fetch Data")

    if fetch_button:
        df = fetch_stocks_data(symbol, timespan, multiplier, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d"))

        if not df.empty:
            fig = create_stock_chart(df)
            st.plotly_chart(fig, use_container_width=True)

            search = st.text_input("Search by Timestamp")
            if search:
                df = df[df['timestamp'].astype(str).str.contains(search, case=False)]

            st.dataframe(df.style.format({
                'Open': '{:.2f}',
                'High': '{:.2f}',
                'Low': '{:.2f}',
                'Close': '{:.2f}',
                'Volume': '{:,.0f}'
            }))

            prompt = st.text_area("Ask AI about the stock data")
            if st.button("Get AI Insights"):
                context = f"Stock: {symbol}\nTimespan: {timespan}\nDate range: {from_date} to {to_date}\n\nData summary:\n{df.describe().to_string()}"
                response = model.generate_content(f"Context: {context}\n\nUser question: {prompt}")
                st.write(response.text)
        else:
            st.write("No data to display. Please check the API response.")

if __name__ == "__main__":
    main()