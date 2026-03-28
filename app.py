import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from docx import Document
from io import BytesIO

# ======================
# SESSION STATE
# ======================

if "paa" not in st.session_state:
    st.session_state.paa = []

if "competitors" not in st.session_state:
    st.session_state.competitors = []

if "competitors_enriched" not in st.session_state:
    st.session_state.competitors_enriched = []

if "article" not in st.session_state:
    st.session_state.article = ""

if "title_tag" not in st.session_state:
    st.session_state.title_tag = ""

if "meta_desc" not in st.session_state:
    st.session_state.meta_desc = ""

if "serp_ready" not in st.session_state:
    st.session_state.serp_ready = False

if "generate_step" not in st.session_state:
    st.session_state.generate_step = False


# ======================
# FUNZIONI
# ======================

def get_competitors(keyword, num_results, key, hl, gl):

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": key,
        "Content-Type": "application/json"
    }

    payload = {
        "q": keyword,
        "gl": gl,
        "hl": hl,
        "num": num_results
    }

    r = requests.post(url, json=payload, headers=headers)

    data = r.json()

    organic = data.get("organic", [])

    results = []

    blocked = [
        "youtube.com",
        "tiktok.com",
        "instagram.com",
        "facebook.com",
        "pinterest.com"
    ]

    for item in organic:

        link = item.get("link")

        if not link:
            continue

        if any(b in link for b in blocked):
            continue

        results.append({
            "title": item.get("title"),
            "link": link
        })

    return results[:num_results]


def get_people_also_ask(keyword, key, hl, gl):

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": key,
        "Content-Type": "application/json"
    }

    payload = {
        "q": keyword,
        "gl": gl,
        "hl": hl,
        "num": 10
    }

    r = requests.post(url, json=payload, headers=headers)

    data = r.json()

    questions = []

    if "peopleAlsoAsk" in data:

        for q in data["peopleAlsoAsk"]:

            question = q.get("question")

            if question:
                questions.append(question)

    return questions


def fetch_page(url):

    try:

        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

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


def generate_article(keyword, competitors, paa, key, language):

    client = OpenAI(api_key=key)

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
Scrivi un articolo SEO per la keyword:

{keyword}

Lingua: {language}

TITLE TAG (max 60 caratteri)
META DESCRIPTION (max 155 caratteri)
ARTICOLO HTML (800-1500 parole)

Regole HTML:

usa <h2> e <h3>
usa <p>
usa <ul> <ol>
usa <strong>

Non includere <html> o <body>.

PAA INSIGHTS:
{paa_block}

COMPETITOR DATA:
{merged}

Formato:

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


def create_word(title, meta, article):

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
# SIDEBAR
# ======================

st.sidebar.title("API Configuration")

SERPER_KEY = st.sidebar.text_input("Serper API Key", type="password")

OPENAI_KEY = st.sidebar.text_input("OpenAI API Key", type="password")

# ======================
# LOGO
# ======================

st.image("https://YOUR_LOGO_URL/logo.png", width=220)

# ======================
# UI
# ======================

st.title("SEO Article Generator")

keyword = st.text_input("Keyword")

num_results = st.slider("Numero competitor", 1, 10, 5)

country = st.text_input("Country", "it")

language = st.text_input("Language", "it")

generate = st.button("Genera contenuto")


# ======================
# STEP 1 — SERP
# ======================

if generate:

    with st.spinner("Recupero SERP..."):

        st.session_state.competitors = get_competitors(
            keyword,
            num_results,
            SERPER_KEY,
            language,
            country
        )

        st.session_state.paa = get_people_also_ask(
            keyword,
            SERPER_KEY,
            language,
            country
        )

        st.session_state.serp_ready = True
        st.session_state.generate_step = True

    st.rerun()


# ======================
# SERP INSIGHTS
# ======================

if st.session_state.serp_ready:

    st.subheader("SERP Insights")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### People Also Ask")

        for q in st.session_state.paa:
            st.write("-", q)

    with col2:

        st.markdown("### URL scrapate")

        for comp in st.session_state.competitors:
            st.write("-", comp["link"])

    st.divider()


# ======================
# STEP 2 — SCRAPING
# ======================

if st.session_state.generate_step:

    competitors = []

    progress = st.progress(0)

    total = len(st.session_state.competitors)

    for i, comp in enumerate(st.session_state.competitors):

        html, text = fetch_page(comp["link"])

        title, h1, meta = extract_metadata(html)

        competitors.append({
            **comp,
            "html_title": title,
            "h1": h1,
            "meta_desc": meta,
            "text": text
        })

        progress.progress((i + 1) / total)

    st.session_state.competitors_enriched = competitors

    with st.spinner("Generazione articolo AI..."):

        title, meta, article = generate_article(
            keyword,
            competitors,
            st.session_state.paa,
            OPENAI_KEY,
            language
        )

        st.session_state.title_tag = title
        st.session_state.meta_desc = meta
        st.session_state.article = article

    st.session_state.generate_step = False

    st.rerun()


# ======================
# OUTPUT
# ======================

if st.session_state.article:

    st.subheader("SEO Metadata")

    st.write("Title Tag")
    st.write(st.session_state.title_tag)

    st.write("Meta Description")
    st.write(st.session_state.meta_desc)

    st.subheader("Articolo HTML")

    st.code(st.session_state.article, language="html")

    file = create_word(
        st.session_state.title_tag,
        st.session_state.meta_desc,
        st.session_state.article
    )

    st.download_button(
        "Scarica Word",
        data=file,
        file_name="articolo_seo.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
