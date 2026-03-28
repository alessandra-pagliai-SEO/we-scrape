import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from docx import Document
from io import BytesIO

# ======================
# SIDEBAR API CONFIG
# ======================

st.sidebar.title("API Configuration")

SERPER_KEY = st.sidebar.text_input(
    "Serper.dev API Key",
    type="password"
)

OPENAI_KEY = st.sidebar.text_input(
    "OpenAI API Key",
    type="password"
)

# ======================
# UI PRINCIPALE
# ======================

col_logo, col_title = st.columns([1, 4])

with col_logo:
    st.image(
        "https://cdn.prod.website-files.com/63d8c4e7b64a7e3b4fdf9b62/63d8c4e7b64a7e1f54df9b92_weroad-logo-black.svg",
        width=120
    )

with col_title:
    st.title("SEO Article Generator")

st.write(
    "Genera articoli SEO analizzando automaticamente i competitor nella SERP e le People Also Ask."
)

keyword = st.text_input("Main keyword")

num_results = st.number_input(
    "Numero contenuti su cui fare scraping",
    min_value=1,
    max_value=20,
    value=5
)

country = st.text_input(
    "Country code (gl)",
    value="it"
)

language = st.text_input(
    "Language code (hl)",
    value="it"
)

generate = st.button("Genera contenuto")
