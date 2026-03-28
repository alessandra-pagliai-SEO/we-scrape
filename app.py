import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from docx import Document
from io import BytesIO

# ======================
# SESSION STATE
# ======================

if "paa_questions" not in st.session_state:
    st.session_state.paa_questions = []

if "competitors_raw" not in st.session_state:
    st.session_state.competitors_raw = []

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
# LOGO
# ======================

st.image(
    "https://YOUR_LOGO_URL/logo.png",
    width=220
)

# ======================
# UI PRINCIPALE
# ======================

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

# ======================
# SERP DATA SEMPRE VISIBILI
# ======================

if st.session_state.paa_questions:

    st.write("### People Also Ask estratte dalla SERP")

    for q in st.session_state.paa_questions:
        st.write("-", q)


if st.session_state.competitors_raw:

    st.write("### Analisi contenuti competitor")

    st.write("#### Pagine utilizzate per l'analisi")

    for comp in st.session_state.competitors_raw:
        st.write("-", comp["link"])

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
Sei un content writer SEO esperto.

Scrivi un contenuto SEO completo per la keyword:

{keyword}

Lingua: {language}

TITLE TAG (max 60 caratteri)

META DESCRIPTION (max 155 caratteri)

ARTICOLO HTML (800-1500 parole)

Regole HTML:

- usa <h2> e <h3>
- usa <p>
- usa <ul> <ol>
- usa <strong>
- usa <table> se utile
- NON includere <html>, <body>, <head>

Le PAA devono servire come insight ma non essere riportate come Q&A.

PAA INSIGHTS:
{paa_block}

COMPETITOR DATA:
{merged}

Restituisci:

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

        st.session_state.competitors_raw = get_competitors(
            keyword,
            num_results,
            SERPER_KEY,
            language,
            country
        )

    if len(st.session_state.competitors_raw) == 0:

        st.error("Nessun competitor trovato")
        st.stop()

    with st.spinner("Recupero People Also Ask..."):

        st.session_state.paa_questions = get_people_also_ask(
            keyword,
            SERPER_KEY,
            language,
            country
        )

    competitors = []

    progress = st.progress(0)
    status = st.empty()

    total = len(st.session_state.competitors_raw)

    for i, comp in enumerate(st.session_state.competitors_raw):

        status.write(f"Analizzo: {comp['link']}")

        html, text = fetch_page(comp["link"])

        html_title, h1, meta_desc = extract_metadata(html)

        competitors.append({
            **comp,
            "html_title": html_title,
            "h1": h1,
            "meta_desc": meta_desc,
            "text": text
        })

        progress.progress((i + 1) / total)

    status.empty()

    with st.spinner("Generazione contenuto con AI..."):

        title_tag, meta_description, article = generate_article(
            keyword,
            competitors,
            st.session_state.paa_questions,
            OPENAI_KEY,
            language
        )

    st.subheader("SEO Metadata")

    st.write("**Title Tag**")
    st.write(title_tag)

    st.write("**Meta Description**")
    st.write(meta_description)

    st.subheader("Articolo HTML generato")

    st.code(article, language="html")

    word_file = create_word_file(
        title_tag,
        meta_description,
        article
    )

    st.download_button(
        label="Scarica documento Word",
        data=word_file,
        file_name=f"contenuto_{keyword.replace(' ','_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
