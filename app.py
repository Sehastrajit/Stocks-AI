import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
import os
import pandas as pd
import io
import json


st.set_page_config(page_title="Stocks AI", layout="wide")

api_key = os.getenv("gemini_api")

if not api_key:
    st.error("Failed to retrieve the gemini_api environment variable. Make sure it's set in your Streamlit Cloud settings.")
    st.stop()

# Configure Google Generative AI
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

st.write("API key retrieved successfully. Your app is now configured to use Google Generative AI.")
