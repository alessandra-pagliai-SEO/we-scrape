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

if "scraped_urls" not in st.session_state:
    st.session_state.scraped_urls = []

if "article" not in st.session_state:
    st.session_state.article = ""

if "title_tag" not in st.session_state:
    st.session_state.title_tag = ""

if "meta_description" not in st.session_state:
    st.session_state.meta_description = ""

# ======================
# FUNZIONI
# ======================

def get_competitors(keyword, num_results, serper_key, hl, gl):

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": serper_key,
        "Content-Type": "application/json"
    }

    competitors = []
    start = 0

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

            competitors.append({
                "title": item.get("title"),
                "link": link
            })

            if len(competitors) >= num_results:
                break

        start += 10

    return competitors[:num_results]


def get_people_also_ask(keyword, serpapi_key, hl, gl):

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google",
        "q": keyword,
        "hl": hl,
        "gl": gl,
        "api_key": serpapi_key
    }

    response = requests.get(url, params=params)
    data = response.json()

    questions = []

    for item in data.get("related_questions", []):
        q = item.get("question")
        if q:
            questions.append(q)

    return questions[:10]


def fetch_page(url):

    try:

        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(soup.get_text().split())

        return html, text[:18000]

    except Exception:
        return "", ""


def extract_metadata(html):

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})

    if meta and "content" in meta.attrs:
        meta_desc = meta["content"].strip()

    return title, h1, meta_desc


def generate_article(keyword, competitors, paa, openai_key):

    client = OpenAI(api_key=openai_key)

    merged = ""

    for comp in competitors:

        merged += f"""

URL: {comp['link']}

TITLE: {comp['html_title']}
H1: {comp['h1']}
META: {comp['meta_desc']}

CONTENUTO:
{comp['text']}

-------------------------
"""

    paa_block = "\n".join([f"- {q}" for q in paa])

    prompt = f"""
Scrivi un articolo SEO completo per la keyword:

{keyword}

Usa queste PAA come insight:
{paa_block}

Dati competitor:
{merged}

Output:

TITLE TAG:
META DESCRIPTION:
ARTICLE HTML:
"""

    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


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
# SIDEBAR API
# ======================

st.sidebar.title("API Configuration")

st.sidebar.header("SERP scraping")
SERPER_KEY = st.sidebar.text_input(
    "Serper.dev API Key",
    type="password",
    help="Usata per recuperare i risultati organici della SERP"
)

st.sidebar.header("People Also Ask")
SERPAPI_KEY = st.sidebar.text_input(
    "SerpAPI Key",
    type="password",
    help="Usata per recuperare le PAA"
)

st.sidebar.header("AI generation")
OPENAI_KEY = st.sidebar.text_input(
    "OpenAI API Key",
    type="password",
    help="Usata per generare l'articolo SEO"
)

# ======================
# UI
# ======================

st.title("SEO Article Generator")

keyword = st.text_input("Keyword")

num_results = st.slider("Numero competitor", 1, 20, 5)

country = st.text_input("Country code", "it")

language = st.text_input("Language code", "it")

generate = st.button("Genera contenuto")


# ======================
# GENERAZIONE
# ======================

if generate:

    if not SERPER_KEY or not SERPAPI_KEY or not OPENAI_KEY:

        st.error("Inserisci tutte le API key nella sidebar")
        st.stop()

    st.subheader("SERP Insights")

    paa_box = st.container()
    url_box = st.container()

    progress = st.progress(0)

    with st.spinner("Recupero SERP..."):

        competitors = get_competitors(
            keyword,
            num_results,
            SERPER_KEY,
            language,
            country
        )

        paa = get_people_also_ask(
            keyword,
            SERPAPI_KEY,
            language,
            country
        )

        with paa_box:
            st.write("### People Also Ask")
            for q in paa:
                st.write("-", q)

    scraped = []

    enriched = []

    for i, comp in enumerate(competitors):

        scraped.append(comp["link"])

        with url_box:
            st.write("### URL scrapate")
            for u in scraped:
                st.write("-", u)

        html, text = fetch_page(comp["link"])

        html_title, h1, meta_desc = extract_metadata(html)

        enriched.append({
            **comp,
            "html_title": html_title,
            "h1": h1,
            "meta_desc": meta_desc,
            "text": text
        })

        progress.progress((i + 1) / len(competitors))

    with st.spinner("Generazione articolo..."):

        article = generate_article(
            keyword,
            enriched,
            paa,
            OPENAI_KEY
        )

    st.session_state.article = article


# ======================
# OUTPUT
# ======================

if st.session_state.article:

    st.subheader("Articolo generato")

    st.code(st.session_state.article)

    word_file = create_word_file(
        st.session_state.title_tag,
        st.session_state.meta_description,
        st.session_state.article
    )

    st.download_button(
        label="Scarica Word",
        data=word_file,
        file_name="articolo_seo.docx"
    )
