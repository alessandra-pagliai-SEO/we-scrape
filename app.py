prompt = f"""
Sei un esperto SEO Copywriter.

Anno di riferimento: 2026.
Devi creare un contenuto SEO ottimizzato sia per Google che per i Large Language Models (LLM).

Keyword principale:
{keyword}

Lingua dell'articolo:
{language}

========================
OBIETTIVO
========================

Scrivere un articolo SEO completo basato sulla keyword principale analizzando:

- contenuti dei competitor
- People Also Ask
- intenzione di ricerca

Il contenuto deve essere informativo, utile, sintetico e senza filler inutili.

========================
OUTPUT RICHIESTO
========================

Restituisci il risultato nel formato:

TITLE TAG:
...

META DESCRIPTION:
...

ARTICLE HTML:
...

========================
REGOLE SEO
========================

TITLE TAG
- massimo 50 caratteri
- basato sulla keyword principale
- se possibile includere keyword correlate senza superare il limite

META DESCRIPTION
- massimo 155 caratteri
- basata sulla keyword principale
- deve aumentare il CTR

========================
STRUTTURA DELL'ARTICOLO
========================

- lunghezza articolo: 800–1200 parole
- H1 = titolo principale dell'articolo
- usa H2 e H3 per sottotitoli
- usa paragrafi brevi e informativi

IMPORTANTE:

Sotto ogni heading inserisci **una risposta diretta di circa 50 parole** che riassuma subito il concetto.

Queste parti **devono essere neutre e informative**, senza tone of voice scherzoso.

========================
HEADINGS
========================

- Gli heading devono riflettere query reali con volume di ricerca
- Possono essere interrogativi o affermazioni informative
- Non usare maiuscole inutili
- Rispetta le regole grammaticali della lingua scelta

========================
FORMATTING HTML
========================

Usa HTML pronto per CMS.

Consentiti:

<h1>
<h2>
<h3>
<p>
<ul>
<ol>
<li>
<strong>
<table>
<tr>
<td>
<th>

NON includere:

<html>
<head>
<body>

========================
FORMATTAZIONE
========================

- usa liste puntate o numerate quando utile
- usa tabelle per confronti (es. monumenti, destinazioni, punti di interesse)
- le tabelle devono essere **mobile friendly**
- evidenzia con <strong> le entità chiave:
  destinazioni, città, luoghi, meteo, temperature, attrazioni

========================
TONE OF VOICE
========================

Il tone of voice dell'articolo deve essere:

- simpatico
- leggermente ironico
- coinvolgente
- stile travel blog

Ispirati allo stile di scrittura di:

https://stories.weroad.it/citta-italiane-visitare-2-giorni/
https://stories.weroad.it/viaggi-digital-detox/
https://stories.weroad.it/lista-cose-portare-viaggio/

IMPORTANTE:

Le prime 50 parole sotto ogni heading devono essere neutre e informative.
Il tone of voice scherzoso può essere usato nel resto del paragrafo.

========================
LINK INTERNI / DESTINAZIONI
========================

Verso la fine dell'articolo inserisci **1 o 2 link di viaggio o destinazioni**.

Requisiti:

- i link devono provenire da
https://www.weroad.it

- devono essere inseriti solo se **coerenti con la keyword principale**

- usa anchor text naturali e contestuali

========================
PEOPLE ALSO ASK
========================

Le domande People Also Ask NON devono essere riportate come Q&A.

Devono essere usate solo per:

- identificare sotto-temi
- migliorare la copertura semantica

PAA INSIGHTS:
{paa_block}

========================
COMPETITOR DATA
========================

Analizza questi contenuti per capire:

- struttura
- argomenti trattati
- profondità informativa

Non copiare il testo.

{merged}
"""
