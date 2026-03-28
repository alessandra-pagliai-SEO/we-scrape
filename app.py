import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from docx import Document
from io import BytesIO
from urllib.parse import urlparse

# ======================
# DOMINI DA ESCLUDERE
# ======================

EXCLUDED_DOMAINS = [
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "pinterest.com",
    "reddit.com"
]

# ======================
# SIDEBAR API CONFIG
# ======================

st.sidebar.title("API Configuration")

SERPAPI_KEY = st.sidebar.text_input(
    "SerpAPI Key",
    type="password"
)

OPENAI_KEY = st.sidebar.text_input(
    "OpenAI API Key",
    type="password"
)

# ======================
# UI PRINCIPALE
# ======================

st.title("WeScrape")

st.write(
    "Genera articoli SEO nel tone of voice di WeRoad analizzando automaticamente i competitor nella SERP e le People Also Ask."
)

keyword = st.text_input("Main keyword")

num_results = st.number_input(
    "Numero contenuti su cui fare scraping",
    min_value=1,
    max_value=20,
    value=3
)

country = st.text_input(
    "Country code (gl)",
    value="it"
)

language = st.text_input(
    "Language code (hl)",
    value="it"
)

sitemap_site = st.text_input("Sitemap Sito Web")
sitemap_blog = st.text_input("Sitemap Blog")

generate = st.button("Genera contenuto")

# ======================
# FUNZIONI
# ======================

def get_competitors(keyword: str, num_results: int, serp_key: str, hl: str, gl: str):

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google",
        "q": keyword,
        "hl": hl,
        "gl": gl,
        "num": num_results * 3,
        "api_key": serp_key
    }

    response = requests.get(url, params=params)

    data = response.json()

    organic = data.get("organic_results", [])

    competitors = []

    for item in organic:

        link = item.get("link")

        if not link:
            continue

        domain = urlparse(link).netloc.lower()

        if any(excluded in domain for excluded in EXCLUDED_DOMAINS):
            continue

        competitors.append({
            "title": item.get("title"),
            "link": link
        })

        if len(competitors) >= num_results:
            break

    return competitors


def get_people_also_ask(keyword: str, serp_key: str, hl: str, gl: str):

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google",
        "q": keyword,
        "hl": hl,
        "gl": gl,
        "api_key": serp_key
    }

    response = requests.get(url, params=params)

    data = response.json()

    questions = data.get("related_questions", [])

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


def generate_article(keyword: str, competitors: list, paa: list, openai_key: str, language: str, sitemap_site: str, sitemap_blog: str):

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
Sei un esperto SEO Copywriter.

Anno di riferimento: 2026.

Keyword principale:
{keyword}

Lingua dell'articolo:
{language}

Sitemap Sito Web:
{sitemap_site}

Sitemap Blog:
{sitemap_blog}

========================
OBIETTIVO
========================

Scrivere un articolo SEO completo basato sulla keyword principale analizzando:

- contenuti dei competitor
- People Also Ask
- intenzione di ricerca

Il contenuto deve essere informativo e utile.

========================
OUTPUT RICHIESTO
========================

TITLE TAG:
...

META DESCRIPTION:
...

ARTICLE HTML:
...

========================
STILE DI SCRITTURA
========================

Il testo deve sembrare scritto da un travel editor umano.

Evita una struttura troppo schematica o ripetitiva.

Alterna:
- paragrafi narrativi
- liste
- micro approfondimenti

Ogni sezione deve iniziare con una breve risposta introduttiva (40-60 parole) che introduca il tema.

Successivamente sviluppa il contenuto in modo naturale e discorsivo.

========================
LINK INTERNI BLOG
========================

All'interno del contenuto suggerisci massimo 5 link verso contenuti affini, da inserire in anchor-text fortemente in target dal punto di vista semantico.

Regole:

- verifica se esistono articoli pertinenti nella Sitemap Blog
- suggerisci link solo se realmente pertinenti
- non inventare URL
- usa anchor text naturali
- usa HTML <a>

========================
LINK DESTINAZIONI
========================

Verso la fine dell'articolo inserisci 1 o 2 link di viaggi o destinazioni.

Regole:

- usa URL presenti nella Sitemap Sito Web
- inserisci i link solo se coerenti con la keyword
- non inventare URL
- usa anchor text naturali
- usa HTML <a>

========================
PEOPLE ALSO ASK
========================

Usa le domande PAA solo per individuare sotto-topic.

PAA INSIGHTS:
{paa_block}

========================
COMPETITOR DATA
========================

Analizza questi contenuti per comprendere:

- struttura
- profondità
- copertura dei topic

Non copiarli.

{merged}
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

    if not SERPAPI_KEY or not OPENAI_KEY:

        st.error("Inserisci entrambe le API key nella sidebar")
        st.stop()

    if not keyword:

        st.error("Inserisci una keyword")
        st.stop()

    with st.spinner("Recupero competitor dalla SERP..."):

        competitors_raw = get_competitors(
            keyword,
            num_results,
            SERPAPI_KEY,
            language,
            country
        )

    if len(competitors_raw) == 0:

        st.error("Nessun competitor trovato")
        st.stop()

    with st.spinner("Recupero insight dalla SERP (People Also Ask)..."):

        paa_questions = get_people_also_ask(
            keyword,
            SERPAPI_KEY,
            language,
            country
        )

    if paa_questions:

        st.write("### People Also Ask estratte dalla SERP")

        for q in paa_questions:
            st.write("-", q)

    st.write("### Analisi contenuti competitor")

    for comp in competitors_raw:
        st.write("-", comp["link"])

    competitors = []

    progress = st.progress(0)
    status = st.empty()

    total = len(competitors_raw)

    for i, comp in enumerate(competitors_raw):

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
            paa_questions,
            OPENAI_KEY,
            language,
            sitemap_site,
            sitemap_blog
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
