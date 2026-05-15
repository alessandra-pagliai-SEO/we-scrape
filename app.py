import os
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, abort, jsonify, render_template_string, request, send_file
from openai import OpenAI


app = Flask(__name__)

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://litellm.weroad.io/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4").strip() or "gpt-5.4"
MAX_WORKERS = int(os.getenv("JOB_WORKERS", "2"))
JOB_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)
JOB_LOCK = Lock()
JOBS = {}


PAGE_TEMPLATE = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WeScrape</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17211f;
      --muted: #60716d;
      --line: #d7dfdc;
      --surface: #ffffff;
      --band: #f3f6f4;
      --accent: #0f7c72;
      --accent-strong: #0a5f58;
      --danger: #b42318;
      --shadow: 0 18px 50px rgba(23, 33, 31, 0.1);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--band);
      line-height: 1.5;
    }
    header {
      background: #112320;
      color: #fff;
      padding: 30px 20px;
    }
    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .brand {
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 0;
    }
    .status {
      border: 1px solid rgba(255,255,255,0.22);
      border-radius: 8px;
      color: #dce8e5;
      padding: 8px 12px;
      font-size: 14px;
      white-space: nowrap;
    }
    .hero {
      padding-top: 54px;
      max-width: 780px;
    }
    h1 {
      margin: 0;
      font-size: clamp(38px, 7vw, 76px);
      line-height: 0.95;
      letter-spacing: 0;
    }
    .hero p {
      margin: 22px 0 0;
      max-width: 640px;
      color: #c9d8d4;
      font-size: 18px;
    }
    main { padding: 28px 0 48px; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 420px) minmax(0, 1fr);
      gap: 24px;
      align-items: start;
    }
    form, .result, .empty, .alert {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    form { padding: 22px; }
    .field { margin-bottom: 16px; }
    label {
      display: block;
      margin-bottom: 7px;
      font-weight: 700;
      font-size: 14px;
    }
    input, textarea {
      width: 100%;
      min-height: 44px;
      border: 1px solid #c8d2cf;
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }
    textarea {
      resize: vertical;
    }
    input:focus, textarea:focus {
      outline: 3px solid rgba(15, 124, 114, 0.18);
      border-color: var(--accent);
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    button, .download, .copy {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 44px;
      border: 0;
      border-radius: 8px;
      padding: 10px 16px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
    }
    button:hover, .download:hover, .copy:hover { background: var(--accent-strong); }
    button:disabled {
      background: #8aa5a0;
      cursor: wait;
    }
    .hint {
      color: var(--muted);
      font-size: 13px;
      margin: 12px 0 0;
    }
    .alert {
      border-color: #f1b8b2;
      color: var(--danger);
      padding: 16px;
      margin-bottom: 18px;
      box-shadow: none;
    }
    .empty {
      padding: 28px;
      color: var(--muted);
      min-height: 280px;
      display: flex;
      align-items: center;
    }
    .result { overflow: hidden; }
    .hidden { display: none; }
    .result-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      padding: 18px;
      border-bottom: 1px solid var(--line);
    }
    .result-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .result-head h2 {
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }
    pre {
      margin: 0;
      max-height: 760px;
      overflow: auto;
      padding: 18px;
      white-space: pre-wrap;
      word-break: break-word;
      font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #fbfcfb;
    }
    .steps {
      display: grid;
      gap: 10px;
      width: 100%;
    }
    .live-context {
      display: grid;
      gap: 16px;
      margin-top: 8px;
    }
    .live-panel {
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }
    .live-panel h3 {
      margin: 0 0 8px;
      color: var(--ink);
      font-size: 15px;
      letter-spacing: 0;
    }
    .image-card {
      border-top: 1px solid var(--line);
      padding: 18px;
      background: #fbfcfb;
    }
    .image-card h3 {
      margin: 0 0 12px;
      font-size: 16px;
    }
    .image-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .image-item img {
      display: block;
      width: 100%;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #eef3f1;
    }
    .image-item p {
      margin: 10px 0 0;
      font-size: 14px;
      color: var(--muted);
    }
    .image-alt {
      margin-top: 8px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #eef3f1;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.45;
    }
    .image-card a {
      color: var(--accent-strong);
    }
    .live-list {
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
      color: var(--ink);
      font-size: 14px;
    }
    .live-list a {
      color: var(--accent-strong);
      overflow-wrap: anywhere;
      text-decoration-thickness: 1px;
    }
    .live-meta {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-top: 2px;
    }
    .pulse {
      width: 100%;
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #dce6e3;
    }
    .pulse::before {
      content: "";
      display: block;
      width: 38%;
      height: 100%;
      border-radius: inherit;
      background: var(--accent);
      animation: slide 1.2s ease-in-out infinite;
    }
    @keyframes slide {
      0% { transform: translateX(-100%); }
      100% { transform: translateX(270%); }
    }
    @media (max-width: 860px) {
      .layout { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .grid { grid-template-columns: 1fr; }
      .image-grid { grid-template-columns: 1fr; }
      .result-head { align-items: stretch; flex-direction: column; }
      .result-actions { width: 100%; }
      .download, .copy { width: 100%; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="topbar">
        <div class="brand">WeScrape</div>
        <div class="status">Docker-ready</div>
      </div>
      <section class="hero">
        <h1>SEO Content Creator by Scraping</h1>
        <p>Analizza competitor organici, recupera le People Also Ask e produce un articolo HTML pronto per CMS.</p>
      </section>
    </div>
  </header>
  <main>
    <div class="wrap">
      <div id="alert" class="alert hidden"></div>
      <div class="layout">
        <form id="generator-form">
          <div class="field">
            <label for="keyword">Keyword</label>
            <input id="keyword" name="keyword" value="{{ form.keyword }}" required>
          </div>
          <div class="field">
            <label for="secondary_keywords">Secondary keywords</label>
            <textarea id="secondary_keywords" name="secondary_keywords" rows="3" placeholder="Es. weekend romantico, cosa vedere, itinerario">{{ form.secondary_keywords or '' }}</textarea>
          </div>
          <div class="field">
            <label for="article_title">H1 articolo</label>
            <input id="article_title" name="article_title" value="{{ form.article_title }}" required>
          </div>
          <div class="field">
            <label for="custom_prompt">Custom prompt</label>
            <textarea id="custom_prompt" name="custom_prompt" rows="5" placeholder="Indicazioni editoriali aggiuntive facoltative">{{ form.custom_prompt or '' }}</textarea>
          </div>
          <div class="grid">
            <div class="field">
              <label for="language">Lingua</label>
              <input id="language" name="language" value="{{ form.language or 'it' }}" maxlength="8" required>
            </div>
            <div class="field">
              <label for="country">Paese</label>
              <input id="country" name="country" value="{{ form.country or 'it' }}" maxlength="8" required>
            </div>
          </div>
          <div class="field">
            <label for="num_competitors">Competitor da analizzare</label>
            <input id="num_competitors" name="num_competitors" type="number" min="1" max="20" value="{{ form.num_competitors or 5 }}" required>
          </div>
          <button id="submit-button" type="submit">Genera articolo</button>
        </form>

        <section id="progress" class="empty">
          <div class="steps">
            <p id="progress-text">Compila i campi e avvia la generazione. Il processo puo richiedere qualche minuto mentre l'app legge SERP, PAA e pagine competitor.</p>
            <div id="progress-bar" class="pulse hidden"></div>
            <div id="live-context" class="live-context hidden">
              <div class="live-panel">
                <h3>Pagine in scraping</h3>
                <ul id="pages-list" class="live-list"></ul>
              </div>
              <div class="live-panel">
                <h3>People Also Ask</h3>
                <ul id="paa-list" class="live-list"></ul>
              </div>
            </div>
          </div>
        </section>

        <section id="result" class="result hidden">
          <div class="result-head">
            <h2>Output generato</h2>
            <div class="result-actions">
              <button id="copy-button" class="copy" type="button">Copia testo</button>
              <a id="download-link" class="download" href="#">Scarica TXT</a>
            </div>
          </div>
          <div id="image-card" class="image-card hidden">
            <h3>Immagini suggerite da Pexels</h3>
            <div id="image-grid" class="image-grid"></div>
          </div>
          <pre id="article-output"></pre>
        </section>
      </div>
    </div>
  </main>
  <script>
    const form = document.getElementById("generator-form");
    const button = document.getElementById("submit-button");
    const alertBox = document.getElementById("alert");
    const progress = document.getElementById("progress");
    const progressText = document.getElementById("progress-text");
    const progressBar = document.getElementById("progress-bar");
    const liveContext = document.getElementById("live-context");
    const pagesList = document.getElementById("pages-list");
    const paaList = document.getElementById("paa-list");
    const result = document.getElementById("result");
    const output = document.getElementById("article-output");
    const download = document.getElementById("download-link");
    const copyButton = document.getElementById("copy-button");
    const imageCard = document.getElementById("image-card");
    const imageGrid = document.getElementById("image-grid");
    let pollTimer = null;

    function showError(message) {
      alertBox.textContent = message;
      alertBox.classList.remove("hidden");
    }

    function clearError() {
      alertBox.textContent = "";
      alertBox.classList.add("hidden");
    }

    function setBusy(isBusy) {
      button.disabled = isBusy;
      button.textContent = isBusy ? "Generazione in corso" : "Genera articolo";
      progressBar.classList.toggle("hidden", !isBusy);
    }

    function renderLiveContext(payload) {
      const pages = payload.pages || [];
      const paa = payload.paa || [];

      pagesList.replaceChildren();
      paaList.replaceChildren();

      pages.forEach((page) => {
        const item = document.createElement("li");
        const link = document.createElement("a");
        const meta = document.createElement("span");

        link.href = page.link;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = page.title || page.link;
        meta.className = "live-meta";
        meta.textContent = page.status || "In attesa";

        item.append(link, meta);
        pagesList.append(item);
      });

      paa.forEach((question) => {
        const item = document.createElement("li");
        item.textContent = question;
        paaList.append(item);
      });

      liveContext.classList.toggle("hidden", pages.length === 0 && paa.length === 0);
    }

    function renderImages(images) {
      imageGrid.replaceChildren();

      if (!images || images.length === 0) {
        imageCard.classList.add("hidden");
        return;
      }

      images.forEach((image, index) => {
        if (!image || !image.url) {
          return;
        }

        const item = document.createElement("div");
        const link = document.createElement("a");
        const preview = document.createElement("img");
        const credit = document.createElement("p");

        item.className = "image-item";
        link.href = image.download_url || "#";
        link.download = "";
        preview.src = image.preview_url || image.download_url || image.url;
        preview.alt = image.alt || `Immagine Pexels suggerita ${index + 1}`;
        link.append(preview);

        if (image.photographer) {
          credit.textContent = `Foto ${index + 1} • ${image.photographer}`;
        } else {
          credit.textContent = `Foto ${index + 1}`;
        }
        item.append(link, credit);
        imageGrid.append(item);
      });

      imageCard.classList.toggle("hidden", imageGrid.childElementCount === 0);
    }

    async function pollJob(jobId) {
      const response = await fetch(`/jobs/${jobId}`);
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error || "Errore durante il controllo del job.");
      }

      progressText.textContent = payload.message || "Elaborazione in corso...";
      renderLiveContext(payload);

      if (payload.status === "done") {
        window.clearInterval(pollTimer);
        pollTimer = null;
        setBusy(false);
        output.textContent = payload.article;
        renderImages(payload.images);
        download.href = `/download?job_id=${jobId}`;
        progress.classList.add("hidden");
        result.classList.remove("hidden");
      }

      if (payload.status === "error") {
        window.clearInterval(pollTimer);
        pollTimer = null;
        setBusy(false);
        showError(payload.error || "La generazione non e riuscita.");
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError();
      setBusy(true);
      result.classList.add("hidden");
      imageCard.classList.add("hidden");
      progress.classList.remove("hidden");
      liveContext.classList.add("hidden");
      pagesList.replaceChildren();
      paaList.replaceChildren();
      progressText.textContent = "Job avviato. Preparazione della ricerca...";

      if (pollTimer) {
        window.clearInterval(pollTimer);
      }

      try {
        const response = await fetch("/jobs", {
          method: "POST",
          body: new FormData(form),
        });
        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.error || "Impossibile avviare la generazione.");
        }

        progressText.textContent = payload.message;
        pollTimer = window.setInterval(() => {
          pollJob(payload.job_id).catch((error) => {
            window.clearInterval(pollTimer);
            pollTimer = null;
            setBusy(false);
            showError(error.message);
          });
        }, 2500);
        await pollJob(payload.job_id);
      } catch (error) {
        setBusy(false);
        showError(error.message);
      }
    });

    copyButton.addEventListener("click", async () => {
      const text = output.textContent || "";

      if (!text) {
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
      } catch (error) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }

      copyButton.textContent = "Copiato";
      window.setTimeout(() => {
        copyButton.textContent = "Copia testo";
      }, 1800);
    });
  </script>
</body>
</html>
"""


def default_form():
    return {
        "keyword": "",
        "secondary_keywords": "",
        "article_title": "",
        "custom_prompt": "",
        "language": "it",
        "country": "it",
        "num_competitors": "10",
    }


def create_job(form):
    job_id = uuid4().hex

    with JOB_LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "message": "Job in coda...",
            "article": "",
            "error": "",
            "pages": [],
            "paa": [],
            "images": [],
            "keyword": form.get("keyword", "articolo").strip() or "articolo",
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }

    JOB_EXECUTOR.submit(run_job, job_id, dict(form))
    return job_id


def update_job(job_id, **values):
    with JOB_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(values)


def get_job(job_id):
    with JOB_LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def run_job(job_id, form):
    global LAST_ARTICLE

    try:
        update_job(job_id, status="running", message="Recupero competitor dalla SERP...")
        result = build_article(form, job_id=job_id)
        article = result["article"]
        LAST_ARTICLE = article
        update_job(
            job_id,
            status="done",
            message="Articolo pronto.",
            article=article,
            images=result["images"],
        )
    except Exception as exc:
        update_job(
            job_id,
            status="error",
            message="Generazione interrotta.",
            error=str(exc),
        )


LAST_ARTICLE = ""


def env_value(name):
    return os.getenv(name, "").strip()


def search_pexels_image(query, pexels_key):
    if not query or not pexels_key:
        return []

    response = requests.get(
        "https://api.pexels.com/v1/search",
        params={
            "query": query,
            "per_page": 18,
            "orientation": "landscape",
        },
        headers={"Authorization": pexels_key},
        timeout=30,
    )
    response.raise_for_status()

    photos = response.json().get("photos", [])

    if not photos:
        return []

    diverse = []
    fallback = []
    seen_photo_ids = set()
    seen_photographers = set()

    for photo in photos:
        photo_id = photo.get("id")
        photographer = (photo.get("photographer") or "").strip().lower()
        src = photo.get("src") or {}
        image_url = src.get("landscape") or src.get("large") or src.get("original")

        if not image_url:
            continue

        if photo_id in seen_photo_ids:
            continue

        item = {
            "id": photo_id,
            "url": image_url,
            "page_url": photo.get("url", ""),
            "photographer": photo.get("photographer", ""),
            "photographer_url": photo.get("photographer_url", ""),
            "alt": photo.get("alt", "") or query,
        }
        seen_photo_ids.add(photo_id)
        fallback.append(item)

        if photographer and photographer in seen_photographers:
            continue

        if photographer:
            seen_photographers.add(photographer)
        diverse.append(item)

        if len(diverse) >= 6:
            break

    if len(diverse) < 6:
        chosen_ids = {item.get("id") for item in diverse}
        for item in fallback:
            if item.get("id") in chosen_ids:
                continue
            diverse.append(item)
            chosen_ids.add(item.get("id"))
            if len(diverse) >= 6:
                break

    return diverse[:6]


def download_image_bytes(url):
    response = requests.get(
        url,
        timeout=45,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "image/jpeg")


def get_competitors(keyword, num_results, serper_key, hl, gl):
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": serper_key,
        "Content-Type": "application/json",
    }

    competitors = []
    seen_urls = set()
    start = 0
    blocked_domains = [
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "instagram.com",
        "facebook.com",
        "pinterest.com",
    ]

    while len(competitors) < num_results and start <= 90:
        payload = {
            "q": keyword,
            "gl": gl,
            "hl": hl,
            "num": min(num_results, 10),
            "start": start,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        organic = response.json().get("organic", [])

        if not organic:
            break

        for item in organic:
            link = item.get("link")

            if not link:
                continue

            normalized = link.strip().rstrip("/")

            if any(domain in normalized for domain in blocked_domains):
                continue

            if normalized in seen_urls:
                continue

            seen_urls.add(normalized)
            competitors.append({
                "title": item.get("title", ""),
                "link": normalized,
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
        "api_key": serpapi_key,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    questions = []
    seen = set()

    for item in response.json().get("related_questions", []):
        question = item.get("question")

        if not question:
            continue

        question = question.strip()

        if question in seen:
            continue

        seen.add(question)
        questions.append(question)

    return questions[:10]


def fetch_page(url):
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(soup.get_text().split())
        return html, text[:18000]
    except requests.RequestException:
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


def generate_article(
    keyword,
    article_title,
    competitors,
    paa,
    openai_key,
    language,
    secondary_keywords="",
    custom_prompt="",
):
    if OPENAI_MODEL.isdigit():
        raise RuntimeError(
            "OPENAI_MODEL non valido: sembra una porta. "
            "Imposta OPENAI_MODEL=gpt-5.4 oppure rimuovi la variabile."
        )

    client = OpenAI(api_key=openai_key, base_url=OPENAI_BASE_URL)
    merged = ""

    for comp in competitors:
        merged += f"""
URL: {comp['link']}
TITLE: {comp['html_title']}
H1: {comp['h1']}
META: {comp['meta_desc']}
CONTENUTO: {comp['text']}
-------------------------
"""

    paa_block = "\n".join([f"- {q}" for q in paa]) if paa else "Nessuna PAA disponibile."
    secondary_keywords = secondary_keywords.strip()
    custom_prompt = custom_prompt.strip()
    secondary_keywords_block = secondary_keywords or "Nessuna keyword secondaria fornita."
    custom_prompt_block = custom_prompt or "Nessuna indicazione editoriale aggiuntiva fornita."

    prompt = f"""
Sei un content writer SEO esperto.

Scrivi un contenuto SEO completo che abbia come focus la keyword:

{keyword}

L'H1 dell'articolo e gia definito e NON deve essere modificato:

{article_title}

Language code della ricerca: {language}

Keyword secondarie facoltative da usare solo come contesto aggiuntivo:
{secondary_keywords_block}

Il risultato deve contenere:

TITLE TAG (max 60 caratteri, differenziato in ottica SEO dall'H1)
META DESCRIPTION (max 155 caratteri, naturale e con soft CTA)
ARTICOLO HTML (800-1500 parole)

L'articolo deve iniziare con questo H1:

<h1>{article_title}</h1>

NON creare un nuovo H1.

L'articolo deve essere scritto in HTML pronto per CMS.

Regole HTML:
- usa <h2> e <h3>
- usa <p>
- usa <ul> <ol>
- usa <strong>
- usa <table> se utile (con attributi <figure class="wp-block-table"><table class="has-fixed-layout">)
- NON includere <html> <body>

Le PAA NON devono comparire come Q&A.

# Requisiti editoriali

- Utilizza un tone of voice simpatico e scherzoso nei passaggi narrativi.
- Introduci prima un contesto naturale, poi integra la main keyword all'interno del paragrafo di apertura in modo naturale e grammaticalmente corretto, rispettando le regole della lingua in cui stai lavorando.
- Inizia il testo sotto ogni heading con una risposta diretta di circa 50 parole.
- In queste porzioni iniziali NON usare il tone of voice simpatico e scherzoso.
- Usa gli heading (H2, H3) per strutturare al meglio il contenuto e - solo se opportuno - formulare quesiti espliciti
- Non formulare tutti gli headings sotto forma di domanda, solo se funzionale
- Anche negli heading non usare il tone of voice simpatico e scherzoso.
- Non mettere lettere maiuscole ovunque: usa la capitalizzazione corretta secondo la lingua.
- Inserisci sempre la maiuscola a inizio frase.
- Utilizza elenchi puntati o numerati quando utile.
- Quando fai confronti tra luoghi, monumenti o punti di interesse usa una tabella.
- Le tabelle devono essere ottimizzate per viewport mobile.
- Evidenzia con <strong> le entita chiave.
- Evita testo di riempimento.
- Evita paragrafi composti solo da elenchi.
- Non essere troppo didascalico, l'articolo deve essere caldo e coinvolgente.
- Non chiamare mai il paragrafo conclusivo "Conclusioni".
- Prima di chiudere l'articolo, inserisci una frase che inviti a scoprire i viaggi di gruppo WeRoad per la destinazione di riferimento.

Indicazioni editoriali aggiuntive facoltative da integrare alle regole sopra, senza sostituirle:
{custom_prompt_block}

Al termine dell'articolo:
- Excerpt di intro articolo, massimo 160 caratteri spazi inclusi.
- indica, in una sezione denominata Summary, un massimo di 5 punti elenco <ul> che riassumano in maniera estesa e dettagliata le informazioni del contenuto (no introduzione, solo punti elenco). Non deve essere una replica dell'indice dell'articolo, ma una sintesi delle info contenute (stile AI Overview). Usa il grassetto per i passaggi chiave.
- Suggerisci almeno 4 FAQ in formato Q&A con rispettiva risposta, non devono combaciare necessariamente con le PAA, solo se rispettano il contesto del contenuto.

PAA:
{paa_block}

DATI COMPETITOR:
{merged}

Restituisci l'output ESATTAMENTE in questo formato:

TITLE TAG:
[titolo]

META DESCRIPTION:
[meta description]

ARTICLE HTML:
[contenuto html completo]
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
    )

    return response.choices[0].message.content


def build_article(form, job_id=None):
    serper = env_value("SERPER_API_KEY")
    serpapi = env_value("SERPAPI_API_KEY")
    openai_key = env_value("OPENAI_API_KEY")
    pexels_key = env_value("PEXELS_API_KEY")

    missing = [
        name
        for name, value in {
            "SERPER_API_KEY": serper,
            "SERPAPI_API_KEY": serpapi,
            "OPENAI_API_KEY": openai_key,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError("Variabili d'ambiente mancanti: " + ", ".join(missing))

    keyword = form["keyword"].strip()
    secondary_keywords = form.get("secondary_keywords", "").strip()
    article_title = form["article_title"].strip()
    custom_prompt = form.get("custom_prompt", "").strip()
    language = form["language"].strip().lower()
    country = form["country"].strip().lower()
    num_competitors = min(max(int(form["num_competitors"]), 1), 20)

    if job_id:
        update_job(job_id, message="Recupero competitor dalla SERP...")

    competitors = get_competitors(keyword, num_competitors, serper, language, country)
    pages = [
        {
            "title": comp.get("title") or comp.get("link", ""),
            "link": comp.get("link", ""),
            "status": "In attesa",
        }
        for comp in competitors
    ]

    if job_id:
        update_job(
            job_id,
            message="Recupero People Also Ask...",
            pages=pages,
        )

    paa = get_people_also_ask(keyword, serpapi, language, country)

    if job_id:
        update_job(job_id, paa=paa)

    enriched = []

    for index, comp in enumerate(competitors, start=1):
        if job_id:
            pages[index - 1]["status"] = "Scraping in corso"
            update_job(
                job_id,
                message=f"Scraping competitor {index} di {len(competitors)}...",
                pages=list(pages),
            )

        html, text = fetch_page(comp["link"])
        html_title, h1, meta_desc = extract_metadata(html)

        if job_id:
            pages[index - 1]["status"] = "Letta" if text else "Non leggibile"
            update_job(job_id, pages=list(pages))

        enriched.append({
            **comp,
            "html_title": html_title,
            "h1": h1,
            "meta_desc": meta_desc,
            "text": text,
        })

    if job_id:
        update_job(job_id, message="Generazione articolo con AI...")

    article = generate_article(
        keyword,
        article_title,
        enriched,
        paa,
        openai_key,
        language,
        secondary_keywords=secondary_keywords,
        custom_prompt=custom_prompt,
    )

    images = []
    if pexels_key:
        if job_id:
            update_job(job_id, message="Ricerca immagini su Pexels...")
        try:
            images = search_pexels_image(article_title, pexels_key)
            if images:
                for index, image in enumerate(images):
                    image["preview_url"] = f"/jobs/{job_id}/images/{index}/preview" if job_id else image["url"]
                    image["download_url"] = f"/jobs/{job_id}/images/{index}/download" if job_id else image["url"]
        except requests.RequestException:
            images = []

    return {
        "article": article,
        "images": images,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


@app.get("/")
def index():
    return render_template_string(PAGE_TEMPLATE, form=default_form())


@app.post("/jobs")
def start_job():
    form = request.form.to_dict()

    try:
        if not form.get("keyword", "").strip():
            raise ValueError("La keyword e obbligatoria.")
        if not form.get("article_title", "").strip():
            raise ValueError("L'H1 articolo e obbligatorio.")

        form["num_competitors"] = str(
            min(max(int(form.get("num_competitors", "5")), 1), 20)
        )
        job_id = create_job(form)
        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "message": "Job avviato. Puoi lasciare aperta questa pagina mentre l'app lavora.",
        }), 202
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/jobs/<job_id>")
def job_status(job_id):
    job = get_job(job_id)

    if not job:
        return jsonify({"error": "Job non trovato."}), 404

    return jsonify(job)


@app.get("/jobs/<job_id>/images/<int:image_index>/preview")
def image_preview(job_id, image_index):
    job = get_job(job_id)

    if not job:
        abort(404)

    images = job.get("images", [])
    if image_index < 0 or image_index >= len(images):
        abort(404)

    image = images[image_index]
    source_url = image.get("url")
    if not source_url:
        abort(404)
    try:
        image_bytes, content_type = download_image_bytes(source_url)
    except requests.RequestException:
        abort(404)

    return send_file(
        BytesIO(image_bytes),
        mimetype=content_type,
    )


@app.get("/jobs/<job_id>/images/<int:image_index>/download")
def image_download(job_id, image_index):
    job = get_job(job_id)

    if not job:
        abort(404)

    images = job.get("images", [])
    if image_index < 0 or image_index >= len(images):
        abort(404)

    image = images[image_index]
    source_url = image.get("url")
    if not source_url:
        abort(404)
    try:
        image_bytes, content_type = download_image_bytes(source_url)
    except requests.RequestException:
        abort(404)

    extension = "jpg"
    if "png" in content_type:
        extension = "png"
    elif "webp" in content_type:
        extension = "webp"

    download_name = f"pexels-image-{image_index + 1}.{extension}"
    return send_file(
        BytesIO(image_bytes),
        mimetype=content_type,
        as_attachment=True,
        download_name=download_name,
    )


@app.get("/download")
def download():
    job_id = request.args.get("job_id", "").strip()
    job = get_job(job_id) if job_id else None
    article = job.get("article", "") if job else LAST_ARTICLE
    keyword = (job.get("keyword") if job else request.args.get("keyword", "articolo"))
    keyword = (keyword or "articolo").strip() or "articolo"
    safe_keyword = "".join(char if char.isalnum() else "_" for char in keyword).strip("_")
    filename = f"{safe_keyword or 'articolo'}_articolo.txt"
    return Response(
        article,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
