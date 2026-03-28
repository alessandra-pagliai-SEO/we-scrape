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
# PLACEHOLDER SERP
# ======================

serp_box = st.empty()

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

    blocked = [
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

        r = requests.post(url, json=payload, headers=headers)
        data = r.json()

        organic = data.get("organic", [])

        for item in organic:

            link = item.get("link")

            if not link:
                continue

            if any(b in link for b in blocked):
                continue

            competitors.append({
                "title": item.get("title"),
                "link": link
            })

            if len(competitors) >= num_results:
                break

        start += 10

    return competitors[:num_results]


def get_paa(keyword, key, hl, gl):

    headers = {
        "X-API-KEY": key,
        "Content-Type": "application/json"
    }

    payload = {
        "q": keyword,
        "gl": gl,
        "hl": hl
    }

    questions = []

    # prima chiamata
    r = requests.post(
        "https://google.serper.dev/search",
        json=payload,
        headers=headers
    )

    data = r.json()

    if "peopleAlsoAsk" in data:

        for q in data["peopleAlsoAsk"]:
            question = q.get("question")

            if question:
                questions.append(question)

    # fallback endpoint
    if not questions:

        r = requests.post(
            "https://google.serper.dev/related",
            json=payload,
            headers=headers
        )

        data = r.json()

        related = data.get("relatedSearches", [])

        for item in related:
            q = item.get("query")

            if q:
                questions.append(q)

    return questions[:10]


def fetch_page(url):

    try:

        r = requests.get(url, timeout=10)

        html = r.text

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(soup.get_text().split())

        return html, text[:18000]

    except:

        return "", ""


def extract_metadata(html):

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title else ""

    h1_tag = soup.find("h1")

    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    meta_desc = ""

    meta = soup.find("meta", attrs={"name": "description"})

    if meta and "content" in meta.attrs:
        meta_desc = meta["content"].strip()

    return title, h1, meta_desc


def generate_article(keyword, competitors, paa, openai_key, language):

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

    paa_block = "\n".join([f"- {q}" for q in paa])

    prompt = f"""
Scrivi un contenuto SEO completo per la keyword:

{keyword}

Lingua: {language}

Il risultato deve contenere:

TITLE TAG (max 60 caratteri)

META DESCRIPTION (max 155 caratteri)

ARTICOLO HTML (800-1500 parole)

Non includere <html>, <body>, <head>.

Le PAA devono servire come insight ma non essere riportate come Q&A.

PAA INSIGHTS:
{paa_block}

COMPETITOR DATA:
{merged}

Formato output:

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


def create_word_file(title, meta, article):

    doc = Document()

    doc.add_heading("Title Tag", level=2)
    doc.add_paragraph(title)

    doc.add_heading("Meta Description", level=2)
    doc.add_paragraph(meta)

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
        st.error("Inserisci entrambe le API key")
        st.stop()

    if not keyword:
        st.error("Inserisci una keyword")
        st.stop()

    with st.spinner("Recupero SERP..."):

        competitors_raw = get_competitors(
            keyword,
            num_results,
            SERPER_KEY,
            language,
            country
        )

        paa = get_paa(
            keyword,
            SERPER_KEY,
            language,
            country
        )

    # ======================
    # SERP INSIGHTS (persistenti)
    # ======================

    with serp_box.container():

        st.subheader("SERP Insights")

        st.write("### People Also Ask")

        for q in paa:
            st.write("-", q)

        st.write("### URL analizzate")

        for comp in competitors_raw:
            st.write("-", comp["link"])

    # ======================
    # SCRAPING
    # ======================

    competitors = []

    progress = st.progress(0)
    status = st.empty()

    total = len(competitors_raw)

    for i, comp in enumerate(competitors_raw):

        status.write(f"Scraping: {comp['link']}")

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

    # ======================
    # GENERAZIONE AI
    # ======================

    with st.spinner("Generazione articolo con AI..."):

        title_tag, meta_desc, article = generate_article(
            keyword,
            competitors,
            paa,
            OPENAI_KEY,
            language
        )

    # ======================
    # OUTPUT
    # ======================

    st.subheader("SEO Metadata")

    st.write("Title Tag")
    st.write(title_tag)

    st.write("Meta Description")
    st.write(meta_desc)

    st.subheader("Articolo HTML")

    st.code(article, language="html")

    word_file = create_word_file(title_tag, meta_desc, article)

    st.download_button(
        label="Scarica documento Word",
        data=word_file,
        file_name=f"{keyword.replace(' ','_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
