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

col_logo, col_title = st.columns([1,4])

with col_logo:
    st.image(
        "https://s3-eu-west-1.amazonaws.com/tpd/logos/62331cd876763552a17cd98b/0x0.png",
        width=120
    )

with col_title:
    st.title("WeScrape")

st.write(
    "Genera articoli SEO nel tone of voice di WeRoad analizzando automaticamente i competitor nella SERP e le People Also Ask."
)

keyword = st.text_input("Main keyword")

num_results = st.number_input(
    "Numero contenuti su cui fare scraping",
    min_value=1,
    max_value=20,
    value=10
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

# ======================
# FUNZIONI
# ======================

def get_competitors(keyword: str, num_results: int, serper_key: str, hl: str, gl: str):

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": serper_key,
        "Content-Type": "application/json"
    }

    competitors = []
    start = 0

    blocked_domains = [
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "pinterest.com",
        "facebook.com",
        "instagram.com"
    ]

    while len(competitors) < num_results and start < 40:

        payload = {
            "q": keyword,
            "gl": gl,
            "hl": hl,
            "num": 10,
            "start": start
        }

        response = requests.post(url, json=payload, headers=headers)

        data = response.json()

        organic = data.get("organic", [])

        for item in organic:

            link = item.get("link")

            if not link:
                continue

            if any(domain in link for domain in blocked_domains):
                continue

            competitors.append({
                "title": item.get("title"),
                "link": link
            })

            if len(competitors) >= num_results:
                break

        start += 10

    return competitors[:num_results]


def get_people_also_ask(keyword: str, serper_key: str, hl: str, gl: str):

    url = "https://google.serper.dev/search"

    payload = {
        "q": keyword,
        "gl": gl,
        "hl": hl
    }

    headers = {
        "X-API-KEY": serper_key,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    data = response.json()

    questions = data.get("peopleAlsoAsk", [])

    paa = []

    for q in questions:

        question = q.get("question")

        if question:
            paa.append(question)

    return paa


def fetch_page(url: str):

    try:

        resp = requests.get(url, timeout=10)

        html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(soup.get_text().split())

        return html, text[:18000]

    except Exception:

        return "", ""


def extract_metadata(html: str):

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title else ""

    h1_tag = soup.find("h1")

    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    meta_desc = ""

    meta = soup.find("meta", attrs={"name": "description"})

    if meta and "content" in meta.attrs:

        meta_desc = meta["content"].strip()

    return title, h1, meta_desc


def generate_article(keyword: str, competitors: list, paa: list, openai_key: str, language: str):

    client = OpenAI(api_key=openai_key)

    merged = ""

    for i, comp in enumerate(competitors, start=1):

        merged += f"""
COMPETITOR {i}

URL: {comp['link']}

TITLE: {comp['html_title']}
H1: {comp['h1']}
META: {comp['meta_desc']}

CONTENUTO:
{comp['text']}

------------------------------------
"""

    paa_block = ""

    if paa:
        paa_block = "\n".join([f"- {q}" for q in paa])

    prompt = f"""
Sei un content writer SEO esperto. Siamo nel 2026.

Scrivi un contenuto SEO completo per la keyword:

{keyword}

Language code della ricerca: {language}

Il risultato deve contenere:

TITLE TAG (max 60 caratteri), contenente la keyword princiapale del contenuto

META DESCRIPTION (max 155 caratteri), con keyword principale e soft CTA

ARTICOLO HTML (800-1500 parole)

-L'articolo deve essere scritto in HTML pronto per un editor CMS. Ricco e discorsivo, non deve contenere paragrafi schematici.
-Inizia il testo (sotto ogni heading) con una risposta diretta di circa 50 parole. In queste porzioni di testo non usare il "tone of voice" simpatico e scherzoso.
-Se fai dei confronti, e.g. piazze, monumenti, punti di interesse usa una tabella. Le misure delle tabelline devono essere ottimali per un ViewPort mobile e quindi essere leggibili per esempio da uno smartphone
-Evidenzia con grassetti le entità chiave, e.g. nomi delle destinazioni, punti di interesse, meteo e temperature, etc.
-Evita testo di riempimento. Se un passaggio non aggiunge valore informativo non lo inserire.
-Utilizza grammatica e sintassi della localizzazione Google di riferimento.
-Riferisciti a usi e costumi del paese del target per cui stai scrivendo.

TONE OF VOICE:
Simpatico e scherzoso, puoi usare come riferimenti i seguenti URL:
* https://stories.weroad.it/citta-italiane-visitare-2-giorni/
* https://stories.weroad.it/viaggi-digital-detox/
* https://stories.weroad.it/lista-cose-portare-viaggio/

Regole HTML:

- usa <h2> e <h3> per i sottotitoli
- usa <p> per i paragrafi
- usa <ul> <ol> per liste
- usa <strong> per enfasi
- usa <table> se utile per confronti
- NON includere <html>, <body>, <head>


IMPORTANTE:

Le domande People Also Ask NON devono essere riportate come Q&A.
Devono essere usate solo per capire i sotto-temi.

PAA INSIGHTS:
{paa_block}

COMPETITOR DATA:
{merged}

Restituisci il risultato nel formato:

TITLE TAG:
...

META DESCRIPTION:
...

ARTICLE HTML:
...
"""

    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    content = response.choices[0].message.content

    title = ""
    meta = ""
    article = content

    if "TITLE TAG:" in content:

        parts = content.split("TITLE TAG:")[1]

        if "META DESCRIPTION:" in parts:
            title = parts.split("META DESCRIPTION:")[0].strip()

        if "ARTICLE HTML:" in parts:
            meta = parts.split("META DESCRIPTION:")[1].split("ARTICLE HTML:")[0].strip()
            article = parts.split("ARTICLE HTML:")[1].strip()

    return title, meta, article


def create_word_file(title_tag, meta_description, article):

    doc = Document()

    doc.add_heading("Title Tag", level=2)
    doc.add_paragraph(title_tag)

    doc.add_heading("Meta Description", level=2)
    doc.add_paragraph(meta_description)

    doc.add_heading("HTML Article", level=2)
    doc.add_paragraph(article)

    buffer = BytesIO()

    doc.save(buffer)

    buffer.seek(0)

    return buffer


# ======================
# ESECUZIONE
# ======================

if generate:

    if not SERPER_KEY or not OPENAI_KEY:

        st.error("Inserisci entrambe le API key nella sidebar")
        st.stop()

    if not keyword:

        st.error("Inserisci una keyword")
        st.stop()

    with st.spinner("Recupero competitor dalla SERP..."):

        competitors_raw = get_competitors(
            keyword,
            num_results,
            SERPER_KEY,
            language,
            country
        )
