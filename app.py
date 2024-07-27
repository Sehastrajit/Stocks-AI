import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

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
   stocks_api = "your_polygon_api_key"
        """)
        st.stop()

gemini_api_key = get_api_key("gemini_api")
polygon_api_key = get_api_key("stocks_api")

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

def fetch_stocks_data(symbol="AAPL"):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}?apiKey={polygon_api_key}"
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

    fig.update_layout(height=600, title_text="Stock Data (Last 30 Days)", xaxis_rangeslider_visible=False)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig

def main():
    st.title("STOCK AI (Free Tier)")
    st.write("This app uses the Polygon.io API Free Tier, which provides daily data for the last 30 days.")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        symbol = st.text_input("Enter stock symbol", value="AAPL")
        fetch_button = st.button("Fetch Data")

    if fetch_button:
        df = fetch_stocks_data(symbol)

        if not df.empty:
            fig = create_stock_chart(df)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df.style.format({
                'Open': '{:.2f}',
                'High': '{:.2f}',
                'Low': '{:.2f}',
                'Close': '{:.2f}',
                'Volume': '{:,.0f}'
            }))

            prompt = st.text_area("Ask AI about the stock data")
            if st.button("Get AI Insights"):
                context = f"Stock: {symbol}\nDate range: Last 30 days\n\nData summary:\n{df.describe().to_string()}"
                response = model.generate_content(f"Context: {context}\n\nUser question: {prompt}")
                st.write(response.text)
        else:
            st.write("No data to display. Please check the API response.")

if __name__ == "__main__":
    main()