import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="Stocks AI", layout="wide")

if 'data' not in st.session_state:
    st.session_state.data = None
if 'symbol' not in st.session_state:
    st.session_state.symbol = ""

popular_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "FB", "TSLA", "NVDA", "JPM", "JNJ", "V", "Other"]

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

def get_ai_insights(df, symbol, prompt):
    try:
        context = f"""
        Stock: {symbol}
        Date range: Last 30 days

        Data summary:
        {df.describe().to_string()}

        Recent price movements:
        {df[['timestamp', 'Close']].tail().to_string(index=False)}

        User question: {prompt}
        """
        
        response = model.generate_content(context)
        
        if response.text:
            return response.text
        else:
            return "The AI model didn't provide a response. Please try asking a different question."
    except Exception as e:
        return f"An error occurred while getting AI insights: {str(e)}"

def main():
    st.title("STOCK AI ")
    st.write("This app uses the Polygon.io API Free Tier, which provides daily data for the last 30 days.")

    # Sidebar with LinkedIn badge
    with st.sidebar:
        st.subheader("Developer")
        st.components.v1.html("""
        <script src="https://platform.linkedin.com/badges/js/profile.js" async defer type="text/javascript"></script>
        <div id="badge-wrapper">
            <div class="badge-base LI-profile-badge" data-locale="en_US" data-size="medium" data-theme="dark" data-type="VERTICAL" data-vanity="sehastrajit-s-0a84b8203" data-version="v1">
            </div>
        </div>
        <style>
            #badge-wrapper * {
                background-color: transparent !important;
                background: none !important;
                box-shadow: none !important;
            }
            .badge-base {
                min-height: 350px;
                position: relative;
            }
            .bdiframe {
                background-color: transparent !important;
            }
            #badge-wrapper::after {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(38,39,48,255) !important;
                z-index: -1;
            }
        </style>
        """, height=400)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        selected_symbol = st.selectbox("Choose a stock symbol", popular_symbols, index=popular_symbols.index(st.session_state.symbol) if st.session_state.symbol in popular_symbols else len(popular_symbols) - 1)
        
        if selected_symbol == "Other":
            custom_symbol = st.text_input("Enter custom stock symbol")
            if custom_symbol:
                st.session_state.symbol = custom_symbol.upper()
        else:
            st.session_state.symbol = selected_symbol

        fetch_button = st.button("Fetch Data")

    if fetch_button and st.session_state.symbol:
        st.session_state.data = fetch_stocks_data(st.session_state.symbol)

    if st.session_state.data is not None and not st.session_state.data.empty:
        fig = create_stock_chart(st.session_state.data)
        st.plotly_chart(fig, use_container_width=True)

        _, table_col, _ = st.columns([1, 3, 1])
        with table_col:
            st.dataframe(
                st.session_state.data.style.format({
                    'Open': '{:.2f}',
                    'High': '{:.2f}',
                    'Low': '{:.2f}',
                    'Close': '{:.2f}',
                    'Volume': '{:,.0f}'
                }),
                use_container_width=True
            )

        prompt = st.text_area("Ask AI about the stock data")
        if st.button("Get AI Insights"):
            if prompt:
                with st.spinner("Getting AI insights..."):
                    ai_response = get_ai_insights(st.session_state.data, st.session_state.symbol, prompt)
                    st.write("AI Insights:")
                    st.write(ai_response)
            else:
                st.warning("Please enter a question for the AI.")
    elif st.session_state.data is not None:
        st.write("No data to display. Please check the API response.")

if __name__ == "__main__":
    main()