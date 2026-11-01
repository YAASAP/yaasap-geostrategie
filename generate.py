#!/usr/bin/env python3
"""YAASAP Géostratégie — générateur de notes.

Usage :
    python3 generate.py data/notes/<fichier>.json     # rend une note, archive les précédentes, reconstruit l'accueil
    python3 generate.py --rebuild                     # reconstruit toutes les notes et l'accueil

Seule l'analyse offerte (FREE) est en accès libre ; les autres sont chiffrées (AES-GCM) avec la clé du dépôt
privé et déplacées dans ce dépôt (dossier notes/). Nécessite le paquet « cryptography » dès qu'une
note est verrouillée.

Une note = un fichier JSON (voir PROTOCOLE.md pour le schéma). Le HTML est écrit dans
notes/<même nom>.html ; index.html et data/index.json sont régénérés à chaque appel.
Le contenu des champs « p », « html », « hl », etc. est du HTML de confiance (balises <strong>, <em>, <a>).
"""
import base64
import hashlib
import html as H
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
NOTES_DIR = ROOT / "notes"
DATA_DIR = ROOT / "data" / "notes"
SITE = "https://yaasap.github.io/yaasap-geostrategie"
# Seule analyse en accès libre (découverte) ; toutes les autres sont réservées aux abonnés
FREE = {"20261031-1958-ormuz-doha-brent"}
STRIPE_URL = "https://buy.stripe.com/cNi8wP6GHh0o5eWekCgIo0m"
PRICE = "3 € / mois"
# Dépôt privé : clé de chiffrement, abonnés et sources des analyses archivées
PRIV = Path(os.environ.get("YAASAP_PRIVE") or ROOT.parent / "yaasap-geostrategie-prive")
TZ = ZoneInfo("Europe/Paris")
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
MONTHS_S = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
            "sept.", "oct.", "nov.", "déc."]
DISCLAIMER = ("Ne constitue pas un conseil en investissement. "
              "Par Yacine AOUABED · YAASAP Géostratégie · yaasap.github.io/yaasap-geostrategie")

def _asset_version():
    h = hashlib.md5()
    for n in ("style.css", "app.js", "acces.js", "banner.jpg", "banner-cartes.jpg", "dia-de-los-muertos.jpg"):
        f = ROOT / "assets" / n
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()[:8]


ASSET_V = _asset_version()

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500'
         '&family=Playfair+Display:ital,wght@0,500;0,700;1,400;1,500'
         '&family=Source+Sans+3:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">')


KEYWORDS = ("analyse géostratégique, géopolitique, analyse géopolitique, géostratégie, risque géopolitique, "
            "marchés financiers, pétrole, Brent, détroit d'Ormuz, Iran, Ukraine, Taïwan, sanctions, énergie, YAASAP")


def ld_tag(obj):
    if not obj:
        return ""
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def e(s):
    return H.escape(str(s), quote=True)


def check_safe(label, s):
    if re.search(r"<\s*/?\s*(script|iframe|object|embed)\b", str(s), re.I) or re.search(r"<[^>]*\son\w+\s*=", str(s), re.I):
        raise ValueError(f"Contenu non autorisé dans « {label} » (script / iframe / gestionnaire d'événement)")
    return str(s)


def raw(label, s):
    return check_safe(label, s)


def parse_dt(note):
    dt = datetime.fromisoformat(note["published"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def date_long(dt):
    return f"{dt.day} {MONTHS[dt.month - 1]} {dt.year}"


def date_short(dt):
    return f"{dt.day} {MONTHS_S[dt.month - 1]} {dt.year}"


def kpi_html(k):
    cls = k.get("cls", "neu")
    attrs = ""
    if "to" in k:
        attrs = f' data-to="{e(k["to"])}" data-dec="{e(k.get("dec", 0))}"'
        if k.get("pre"):
            attrs += f' data-pre="{e(k["pre"])}"'
        if k.get("suf"):
            attrs += f' data-suf="{e(k["suf"])}"'
        if k.get("plus"):
            attrs += ' data-plus="1"'
    return (f'<div class="kpi glass"><span class="kpi-v {e(cls)}"{attrs}>{e(k["v"])}</span>'
            f'<span class="kpi-l">{e(k["l"])}</span></div>')


def kicker_html(k):
    return (f'<div class="kk glass"><div class="kk-l">{e(k["l"])}</div><div class="kk-v">{e(k["v"])}</div>'
            f'<div class="kk-n">{e(k.get("n", ""))}</div></div>')


def render_blocks(blocks, charts, timelines, toc):
    out = []
    for b in blocks:
        t = b["type"]
        if t == "sec":
            sid = f"s{len(toc) + 1}"
            toc.append((sid, b["title"]))
            out.append(f'<div class="sec-rule" id="{sid}"><span class="sec-rule-txt">{e(b["title"])}</span></div>')
        elif t == "p":
            out.append(f'<p class="body-p">{raw("p", b["html"])}</p>')
        elif t == "pull":
            out.append(f'<div class="pull glass"><div class="pull-t">{raw("pull", b["t"])}</div>'
                       f'<div class="pull-a">{e(b.get("a", ""))}</div></div>')
        elif t == "chart":
            i = len(charts)
            charts.append({k: b[k] for k in ("kind", "labels", "datasets", "unit", "center") if k in b})
            out.append(
                '<div class="chart-card glass">'
                f'<div class="chart-hd"><div class="chart-t">{e(b["title"])}</div></div>'
                f'<div class="chart-box"><canvas id="ch{i}"></canvas></div>'
                + (f'<div class="chart-src">{raw("src", b["src"])}</div>' if b.get("src") else "")
                + '</div>')
        elif t == "table":
            head = "".join(f"<th>{e(c)}</th>" for c in b["cols"])
            rows = "".join("<tr>" + "".join(f"<td>{raw('cell', c)}</td>" for c in r) + "</tr>" for r in b["rows"])
            out.append(
                '<div class="tbl-card glass">'
                f'<div class="tbl-hd"><div class="tbl-hd-t">{e(b["title"])}</div></div>'
                f'<div class="tbl-scroll"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
                + (f'<div class="chart-src" style="padding:0 16px 12px">{raw("src", b["src"])}</div>' if b.get("src") else "")
                + '</div>')
        elif t == "pos":
            cards = "".join(
                f'<div class="pos glass"><h4>{e(p["h"])}</h4><p>{raw("pos", p["p"])}</p>'
                + (f'<div class="by">{e(p["by"])}</div>' if p.get("by") else "") + '</div>'
                for p in b["items"])
            out.append(f'<div class="pos-grid">{cards}</div>')
        elif t == "timeline":
            i = len(timelines)
            timelines.append(b["events"])
            out.append(
                '<div class="chart-card glass">'
                f'<div class="chart-hd"><div class="chart-t">{e(b.get("title", "Repères · cliquez sur une date"))}</div></div>'
                f'<div class="tl" id="tl{i}"></div><div class="detail" id="tlDetail{i}"></div></div>')
        elif t == "html":
            out.append(raw("html", b["html"]))
        else:
            raise ValueError(f"Type de bloc inconnu : {t}")
    return "\n".join(out)


def page_head(title, desc, canonical, og_title=None, jsonld=None):
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(og_title or title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<meta name="keywords" content="{e(KEYWORDS)}">
<meta name="author" content="Yacine AOUABED">
<meta property="og:site_name" content="YAASAP Géostratégie">
<meta property="og:locale" content="fr_FR">
<meta property="og:image" content="{SITE}/assets/banner.jpg">
<meta name="twitter:card" content="summary_large_image">
{ld_tag(jsonld)}
{FONTS}
<link rel="stylesheet" href="{{PREFIX}}assets/style.css?v={ASSET_V}">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
</head>"""


ORB = """<svg class="orb" viewBox="0 0 300 300" aria-hidden="true">
    <defs><radialGradient id="og" cx="38%" cy="34%" r="75%">
      <stop offset="0" stop-color="#d4af5f" stop-opacity=".5"/><stop offset=".6" stop-color="#1c3466" stop-opacity=".4"/>
      <stop offset="1" stop-color="#060e1d" stop-opacity=".2"/></radialGradient></defs>
    <circle cx="150" cy="150" r="118" fill="url(#og)" stroke="#e9d6a0" stroke-opacity=".55"/>
    <g class="spin" fill="none" stroke="#f1e4c3" stroke-opacity=".35" stroke-width=".8">
      <ellipse cx="150" cy="150" rx="118" ry="38"/><ellipse cx="150" cy="150" rx="118" ry="78"/>
      <ellipse cx="150" cy="150" rx="40" ry="118"/><ellipse cx="150" cy="150" rx="82" ry="118"/></g>
    <g class="spin2" fill="none" stroke="#d9b873" stroke-opacity=".6" stroke-width="1" stroke-dasharray="2 7">
      <circle cx="150" cy="150" r="138"/><circle cx="150" cy="150" r="148"/></g>
    <g fill="#fbf3dc"><circle cx="104" cy="108" r="2.2"/><circle cx="168" cy="92" r="1.8"/><circle cx="196" cy="140" r="2.4"/>
      <circle cx="134" cy="176" r="1.8"/><circle cx="176" cy="198" r="2"/><circle cx="92" cy="156" r="1.6"/></g>
    <g stroke="#f1e4c3" stroke-opacity=".5" stroke-width=".8" fill="none">
      <path d="M104 108 L168 92 L196 140 L176 198 L134 176 L92 156 Z"/><path d="M168 92 L134 176"/></g>
  </svg>"""


def banner(prefix, full=False, img="banner.jpg", size=(1672, 941)):
    return (f'<div class="banner glass{" full" if full else ""}"><img src="{prefix}assets/{img}?v={ASSET_V}" width="{size[0]}" height="{size[1]}" '
            'alt="YAASAP : analyses géostratégiques" fetchpriority="high"></div>')


AD_CONTACT = ""  # lien de contact annonceurs (ex. "mailto:..."); vide = pas de bouton


def ad_slot(fmt="300 × 250"):
    btn = f'<a class="btn-gold" href="{AD_CONTACT}">Réserver cet espace</a>' if AD_CONTACT else ""
    return (f'<div class="ad slot"><span class="ad-k">Espace publicitaire</span><b>Votre annonce ici</b>'
            f'<span>Format {fmt} · visible sur toutes les pages</span>{btn}</div>')


def promo_cards():
    return (
        '<a class="promo" href="https://yaasap.github.io/dailywatch/" target="_blank" rel="noopener">'
        '<span class="ad-k">Publication YAASAP</span><b>YAASAP Notes</b>'
        '<span>Analyses financières indépendantes en français : marchés, valeurs suivies, verdict argumenté.</span>'
        '<i>Lire les notes →</i></a>'
        '<a class="promo" href="https://yaasap.github.io/SAP-FICO-EXPERT/" target="_blank" rel="noopener">'
        '<span class="ad-k">Site YAASAP</span><b>SAP FICO EXPERT</b>'
        '<span>Fiches et astuces du jour pour consultants SAP FI-CO : transactions, paramétrage, pièges. Fiches dès 2,90 € TTC.</span>'
        '<i>Voir les fiches →</i></a>')


def promo_band():
    return f'<section class="promo-band">{promo_cards()}{ad_slot()}</section>'


def masthead(prefix):
    return f"""<canvas id="bg"></canvas>
<div class="page">
<div class="masthead">
  <a class="pub-name" href="{prefix}index.html" style="text-decoration:none">YAASAP <em>Géostratégie</em></a>
  <div class="mast-r"><span class="mast-date" id="mastDate"></span><div id="qr-mast"></div></div>
</div>
<div class="side side-l">
<aside class="sub-pop" id="subPop" aria-label="Abonnement YAASAP Géostratégie">
  <button class="sub-x" type="button" aria-label="Fermer" onclick="try{{sessionStorage.setItem('subPopX','1')}}catch(e){{}};this.parentNode.style.display='none'">×</button>
  <div class="sub-p"><span class="sub-n">3 €</span><span class="sub-u">par mois, TTC</span></div>
  <ul class="sub-l">
    <li>Toutes les analyses en version complète</li>
    <li>Une nouvelle analyse toutes les 2 heures</li>
    <li>Paiement sécurisé par Stripe</li>
  </ul>
  <a class="btn-gold sub-b" href="{prefix}abonnement.html">S'abonner · 3 € / mois</a>
</aside>
  <figure class="ad dia"><img src="{prefix}assets/dia-de-los-muertos.jpg?v={ASSET_V}" width="640" height="700" alt="Día de los Muertos, dimanche 1er novembre" loading="lazy"><figcaption>Día de los Muertos · 1er novembre</figcaption></figure>
  {ad_slot()}
</div>
<div class="side side-r">
  {promo_cards()}
  {ad_slot("300 × 250")}
</div>
<script>try{{if(sessionStorage.getItem('subPopX')==='1')document.getElementById('subPop').style.display='none'}}catch(e){{}}</script>"""


def footer(prefix, recent):
    links = "".join(f'<a href="{prefix}notes/{e(n["file"])}">{e(n["nav"])}</a>' for n in recent)
    return f"""{promo_band()}
<footer>
  <div class="f-nav">
    <a href="{prefix}index.html">Accueil</a>
    {links}
    <a href="{prefix}index.html#archives">Analyses abonnés</a>
    <a href="{prefix}points-strategiques.html">Points stratégiques</a>
    <a href="{prefix}abonnement.html">Abonnement</a>
  </div>
  <div class="f-note">YAASAP Géostratégie · Yacine AOUABED · yaasap.github.io/yaasap-geostrategie<br>Ne constitue pas un conseil en investissement.</div>
</footer>
</div>"""


BREVO_FORM = "https://7e6e1dec.sibforms.com/v2/serve/MUIFAC4TBoAJsEjOID6O4MuoQJ0P--3AueU4ptl4DgI1mIHSz7VnvHEvGODq_Ze-g8HizTa3ZA0Bl2l6Aq8P3RRwpfpPiWgPXrjlo2ZZD999bcKcrAiDD4m0WMqwW-A88pziynZluGOa7k558_NzpMut4S5y6VW76yWvfJndOLk4_Q2EzcCXglPM7qh2F0pYwWtoKx59UxraNx7oIA=="


def newsletter():
    return f"""<div class="nl glass">
    <div class="nl-hl">Recevoir les prochaines analyses YAASAP</div>
    <iframe class="nl-frame" src="{BREVO_FORM}" title="Inscription à la newsletter YAASAP Géostratégie" loading="lazy" frameborder="0" scrolling="auto" allowfullscreen></iframe>
  </div>"""


def load_key():
    k = os.environ.get("YAASAP_KEY")
    if not k:
        f = PRIV / "cle.json"
        if not f.exists():
            raise SystemExit("Clé de chiffrement introuvable : dépôt privé absent (%s)" % PRIV)
        k = json.loads(f.read_text(encoding="utf-8"))["k"]
    return base64.b64decode(k)


def encrypt_payload(key, obj):
    """AES-256-GCM ; format iv(12) + chiffré + tag, compatible WebCrypto."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv = os.urandom(12)
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(iv + AESGCM(key).encrypt(iv, data, None)).decode()


def login_form():
    return """<form class="login" id="loginForm" autocomplete="on">
      <div class="login-t">Déjà abonné ? Entrez votre accès</div>
      <div class="login-row">
        <input type="email" id="lgEmail" placeholder="E-mail d'abonné" required autocomplete="email">
        <input type="text" id="lgCode" placeholder="Code d'accès" required autocomplete="off" spellcheck="false">
        <button type="submit" class="btn-gold">Débloquer</button>
      </div>
      <div class="login-msg" id="lgMsg" role="status"></div>
    </form>"""


def gate_html(prefix):
    return f"""<section class="gate glass" id="gate">
  <div class="gate-lock">🔒</div>
  <h2>Analyse réservée aux abonnés</h2>
  <p>L'analyse sur Ormuz est offerte en découverte ; toutes les autres analyses sont réservées aux abonnés ({PRICE}).</p>
  <div class="gate-cta"><a class="btn-gold" href="{STRIPE_URL}" target="_blank" rel="noopener">S'abonner · {PRICE}</a><a class="btn-ghost" href="{prefix}abonnement.html">Détails de l'abonnement</a></div>
  {login_form()}
</section>"""


def render_note(note, stem, index_entries, locked=False):
    dt = parse_dt(note)
    charts, timelines = [], []
    prefix = "../"
    recent = [{"file": x["file"], "nav": x["nav"]} for x in index_entries if x["file"] != f"{stem}.html"][:3]
    toc = []
    body = render_blocks(note["blocks"], charts, timelines, toc)
    toc_all = [("lead", "Synthèse")] + toc + [("verdict", "Verdict"), ("sources", "Sources")]
    toc_html = "".join(
        f'<a href="#{i}" data-t="{i}"><span class="n">{k + 1:02d}</span><span class="t">{e(t.split(" · ")[0])}</span></a>'
        for k, (i, t) in enumerate(toc_all))
    tags = "".join(f'<span class="tag{" hot" if t.get("hot") else ""}">{e(t["t"])}</span>' for t in note["tags"])
    kpis = "\n  ".join(kpi_html(k) for k in note["kpis"])
    kick = "\n  ".join(kicker_html(k) for k in note.get("kicker", []))
    v = note["verdict"]
    vitems = "\n".join(f'<div class="v-li"><span>{raw("verdict", it)}</span></div>' for it in v["items"])
    srcs = " · ".join(
        f'<a href="{e(s["u"])}" target="_blank" rel="noopener">{e(s["t"])}</a>' for s in note.get("sources", []))
    src_note = note.get("sources_note", "")
    canonical = f"{SITE}/notes/{stem}.html"
    meta = {"dateShort": date_short(dt)}
    art = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": note["title"][:110],
           "description": note["deck"], "datePublished": dt.isoformat(), "dateModified": dt.isoformat(),
           "inLanguage": "fr", "mainEntityOfPage": canonical, "image": f"{SITE}/assets/banner.jpg",
           "author": {"@type": "Person", "name": "Yacine AOUABED"},
           "publisher": {"@type": "Organization", "name": "YAASAP Géostratégie", "url": f"{SITE}/"},
           "isAccessibleForFree": not locked}
    if locked:
        art["hasPart"] = {"@type": "WebPageElement", "isAccessibleForFree": False, "cssSelector": "#locked-slot"}
    head = page_head(f'YAASAP Géostratégie · {note["title"]}', note["deck"], canonical, note["title"], art).replace("{PREFIX}", prefix)
    src_names = " · ".join(s["t"] for s in note.get("sources", []))
    inner = f"""<div class="kpi-strip">
  {kpis}
</div>

<div class="kicker"><div class="kicker-inner">
  {kick}
</div></div>

<div class="layout">
<aside class="toc glass" aria-label="Sommaire">
  <div class="toc-t">Sommaire</div>
  <nav id="toc">{toc_html}</nav>
  <div class="toc-bar"><i id="tocBar"></i></div>
</aside>
<div class="wrap">

  <div class="lead-hl" id="lead">{e(note["lead"]["hl"])}</div>
  <div class="lead-deck">{raw("lead", note["lead"]["deck"])}</div>

{body}

  <div class="verdict glass" id="verdict">
    <span class="v-tag">Verdict YAASAP · Yacine AOUABED · {e(date_long(dt))}</span>
    <div class="v-hl">{raw("verdict", v["hl"])}</div>
    <div class="v-list">
{vitems}
    </div>
    <div class="v-disc">Sources : {e(src_names)} · {e(date_long(dt))}. {e(DISCLAIMER)}</div>
  </div>

  <div class="src" id="sources">Sources : {srcs}.{(" " + raw("sources_note", src_note)) if src_note else ""}</div>

  {cta_band(prefix)}

  {newsletter()}

</div>
</div>"""
    if locked:
        payload = encrypt_payload(load_key(), {"inner": inner, "charts": charts, "timelines": timelines})
        middle = (gate_html(prefix) + '\n<div id="locked-slot"></div>\n'
                  f'<script id="payload" type="application/json">{{"v":1,"d":"{payload}"}}</script>')
        charts, timelines = [], []
    else:
        middle = inner.replace("  <newsletter-slot/>", "")
    page = f"""{head}
<body{' class="is-locked"' if locked else ''}>
{masthead(prefix)}
<div class="shell">

{banner(prefix)}

<section class="hero glass">
  {ORB}
  <div class="hero-in">
    <div class="eyebrow">{tags}<span class="tag">{e(date_short(dt))} · {dt.strftime('%H:%M')}</span>{'<span class="tag lk">🔒 Abonnés</span>' if locked else '<span class="tag hot">Accès libre</span>'}</div>
    <h1>{e(note["title"])}</h1>
    <p class="deck">{e(note["deck"])}</p>
  </div>
</section>

{middle}
</div>

{footer(prefix, recent)}

<script>window.YA_PREFIX="{prefix}";window.NOTE_META={json.dumps(meta, ensure_ascii=False)};window.NOTE_CHARTS={json.dumps(charts, ensure_ascii=False).replace("</", "<\\/")};window.NOTE_TIMELINES={json.dumps(timelines, ensure_ascii=False).replace("</", "<\\/")};</script>
<script src="{prefix}assets/app.js?v={ASSET_V}"></script>
<script src="{prefix}assets/acces.js?v={ASSET_V}"></script>
</body>
</html>
"""
    (NOTES_DIR / f"{stem}.html").write_text(page, encoding="utf-8")


def entry_from(note, stem, locked=False):
    dt = parse_dt(note)
    return {
        "file": f"{stem}.html",
        "locked": locked,
        "published": dt.isoformat(),
        "title": note["title"],
        "deck": note["deck"],
        "tags": note["tags"],
        "nav": note.get("nav") or (note["title"][:28].rstrip() + "…" if len(note["title"]) > 29 else note["title"]),
    }


def render_index(entries):
    prefix = "./"
    head = page_head("YAASAP Géostratégie · analyses géostratégiques indépendantes",
                     "Une analyse géostratégique indépendante toutes les 2 heures : faits sourcés, positions des acteurs, "
                     "risques et canaux de marché. Par Yacine AOUABED.", f"{SITE}/", jsonld=site_ld()).replace("{PREFIX}", prefix)
    head = head.replace('<meta property="og:type" content="article">', '<meta property="og:type" content="website">')
    def card(n):
        dt = datetime.fromisoformat(n["published"]).astimezone(TZ)
        tags = "".join(f'<span class="tag{" hot" if t.get("hot") else ""}">{e(t["t"])}</span>' for t in n["tags"])
        badge = ('<span class="tag lk"><span class="lk-off">🔒 Abonnés</span><span class="lk-on">✓ Abonné</span></span>'
                 if n.get("locked") else '<span class="tag hot">Accès libre</span>')
        return (f'<a class="ncard glass{" locked" if n.get("locked") else ""}" href="notes/{e(n["file"])}">'
                f'<div class="eyebrow">{tags}{badge}</div>'
                f'<h2>{e(n["title"])}</h2><p>{e(n["deck"])}</p>'
                f'<div class="nc-d">{e(date_long(dt))} · {dt.strftime("%H:%M")}</div></a>')
    free = [n for n in entries if not n.get("locked")]
    arch = [n for n in entries if n.get("locked")]
    cards_html = "\n".join(card(n) for n in free) if free else '<div class="empty glass">Première analyse à venir.</div>'
    arch_html = ""
    if arch:
        arch_html = ('<div class="sec-rule" id="archives"><span class="sec-rule-txt">Analyses réservées aux abonnés</span></div>\n'
                     + cta_band() + '\n<div class="ncards">\n' + "\n".join(card(n) for n in arch) + '\n</div>')
    else:
        arch_html = '<div id="archives"></div>' + cta_band()
    last = ""
    if entries:
        dt = datetime.fromisoformat(entries[0]["published"]).astimezone(TZ)
        last = f'<span class="tag hot">Dernière analyse · {e(date_short(dt))} {dt.strftime("%H:%M")}</span>'
    page = f"""{head}
<body>
{masthead(prefix)}
<div class="shell">
{banner(prefix)}
<section class="hero glass home-hero">
  {ORB}
  <div class="hero-in">
    <div class="eyebrow"><span class="tag">Géostratégie</span><span class="tag">Indépendant</span><span class="tag">Toutes les 2 h</span></div>
    <h1>Une analyse géostratégique indépendante, toutes les 2 heures</h1>
    <p class="deck">Faits sourcés, positions de chaque acteur, risques et canaux de marché. Chiffres d'abord, verdict tranché, sources citées.</p>
    <div class="home-meta">{last}<span class="tag">{len(entries)} analyse{'s' if len(entries) > 1 else ''} publiée{'s' if len(entries) > 1 else ''}</span></div>
  </div>
</section>
<div class="wrap">
  <div class="cta-band glass pts-band"><div><div class="cta-t">Carte des points stratégiques</div><div class="cta-s">Ormuz, Malacca, Suez, Bab el-Mandeb… : pays riverains, droits de passage, trafic pétrolier et hors pétrole. Accès libre.</div></div><div class="cta-b"><a class="btn-ghost" href="points-strategiques.html">Voir la carte</a></div></div>
  <div class="sec-rule"><span class="sec-rule-txt">Analyse offerte · accès libre</span></div>
  <div class="ncards">
{cards_html}
  </div>
  {arch_html}
  {newsletter()}
</div>
</div>
{footer(prefix, [{"file": x["file"], "nav": x["nav"]} for x in entries[:3]])}
<script>window.YA_PREFIX="./";window.NOTE_META={{"dateShort":""}};window.NOTE_CHARTS=[];window.NOTE_TIMELINES=[];</script>
<script src="assets/app.js?v={ASSET_V}"></script>
<script src="assets/acces.js?v={ASSET_V}"></script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def site_ld():
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "YAASAP Géostratégie", "url": f"{SITE}/", "inLanguage": "fr",
         "description": "Une analyse géostratégique indépendante toutes les 2 heures : faits sourcés, positions des acteurs, risques et marchés."},
        {"@type": "Organization", "name": "YAASAP", "url": f"{SITE}/", "logo": f"{SITE}/assets/banner.jpg",
         "founder": {"@type": "Person", "name": "Yacine AOUABED"}}]}


def write_seo(entries):
    urls = [(f"{SITE}/", max((x["published"] for x in entries), default=None)), (f"{SITE}/abonnement.html", None), (f"{SITE}/points-strategiques.html", None)]
    urls += [(f"{SITE}/notes/{x['file']}", x["published"]) for x in entries]
    body = "".join(f"<url><loc>{e(u)}</loc>" + (f"<lastmod>{d[:10]}</lastmod>" if d else "") + "</url>" for u, d in urls)
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                      + body + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")


def render_points(entries):
    prefix = "./"
    pts = json.loads((ROOT / "data" / "points.json").read_text(encoding="utf-8"))
    mp = json.loads((ROOT / "data" / "carte.json").read_text(encoding="utf-8"))
    canonical = f"{SITE}/points-strategiques.html"
    desc = ("Carte et fiches des points de passage stratégiques du commerce mondial : Ormuz, Malacca, Suez, Bab el-Mandeb, "
            "détroits turcs et danois, Panama, Cap. Pays riverains, droits de passage, trafic pétrolier et hors pétrole.")
    head = page_head("YAASAP Géostratégie · points stratégiques et droits de passage", desc, canonical,
                     "Points stratégiques : pétrole, GNL et trafic maritime", {
                         "@context": "https://schema.org", "@type": "Article", "headline": "Points stratégiques : pays, droits de passage et trafic maritime",
                         "description": desc, "inLanguage": "fr", "author": {"@type": "Person", "name": "Yacine AOUABED"},
                         "mainEntityOfPage": canonical}).replace("{PREFIX}", prefix)
    head = head.replace('<meta property="og:type" content="article">', '<meta property="og:type" content="website">')
    marks = "".join(
        f'<g class="mk t-{e(p["tension"].lower())}" data-id="{p["id"]}" tabindex="0"><circle class="halo" cx="{mp["points"][p["id"]][0]}" cy="{mp["points"][p["id"]][1]}" r="{8 + p["petrole"] * 0.55:.1f}"/>'
        f'<circle class="dot" cx="{mp["points"][p["id"]][0]}" cy="{mp["points"][p["id"]][1]}" r="4.5"/>'
        f'<text x="{mp["points"][p["id"]][0] + 11}" y="{mp["points"][p["id"]][1] + 4}">{e(p["nom"].split(" (")[0].replace("Détroit d\'", "").replace("Détroit de ", "").replace("Canal de ", "").replace("Canal de Suez et SUMED", "Suez"))}</text></g>'
        for p in pts)
    def pcard(p):
        return (
        f'<article class="pcard glass" id="p-{p["id"]}"><div class="pc-h"><span class="tag t-{e(p["tension"].lower())}">{e(p["tension"])}</span><h3>{e(p["nom"])}</h3>'
        f'<div class="pc-m">{e(p["mer"])}</div></div>'
        f'<div class="pc-k"><div><b>{p["petrole"]:.1f}</b><span>mb/j pétrole</span></div><div><b>{p["gnl"]:.1f}</b><span>Gpi³/j GNL</span></div></div>'
        f'<dl><dt>Pays riverains</dt><dd>{e(" · ".join(p["pays"]))}</dd>'
        f'<dt>Droit de passage</dt><dd>{e(p["regime"])}</dd>'
        f'<dt>Poids</dt><dd>{e(p["poids"])}</dd>'
        f'<dt>Hors pétrole</dt><dd>{e(p["hors"])}</dd>'
        f'<dt>Contournement</dt><dd>{e(p["alt"])}</dd>'
        f'<dt>Lecture YAASAP</dt><dd>{e(p["lecture"])}</dd></dl></article>')
    CONT = [("moyen-orient", "Moyen-Orient et Golfe", ["ormuz"]),
            ("afrique", "Afrique et mer Rouge", ["suez", "babelmandeb", "cap"]),
            ("asie", "Asie", ["malacca"]),
            ("europe", "Europe", ["turcs", "danois"]),
            ("ameriques", "Amériques", ["panama"])]
    byid = {p["id"]: p for p in pts}
    cont_html = "".join(
        f'<div class="sec-rule" id="c-{cid}"><span class="sec-rule-txt">{e(cn)}</span></div>'
        f'<div class="pgrid">{"".join(pcard(byid[i]) for i in ids)}</div>' for cid, cn, ids in CONT)
    toc_items = [(f"c-{cid}", cn, len(ids)) for cid, cn, ids in CONT] + [("trafic", "Pétrole et hors pétrole", 0), ("sources", "Sources", 0)]
    toc_html = "".join(
        f'<a href="#{i}" data-t="{i}"><span class="n">{k + 1:02d}</span><span class="t">{e(t)}</span>'
        + (f'<span class="ct">{n}</span>' if n else "") + '</a>' for k, (i, t, n) in enumerate(toc_items))
    oil = sorted(
        [("Malacca", 23.2), ("Ormuz", 20.9), ("Cap de Bonne-Espérance", 9.1), ("Suez + SUMED", 4.9), ("Détroits danois", 4.9),
         ("Bab el-Mandeb", 4.2), ("Dardanelles", 3.7), ("Bosphore", 3.3), ("Panama (exercice 2025)", 2.3)], key=lambda x: -x[1])
    lng = [("Ormuz", 11.4), ("Malacca", 9.2), ("Cap de Bonne-Espérance", 5.7), ("Détroits danois", 1.6), ("Suez + SUMED", 0.9), ("Dardanelles", 0.6)]
    charts, timelines, toc = [], [], []
    blocks = [
        {"type": "chart", "title": "Pétrole transitant par chaque point · millions de barils par jour (1er semestre 2025)", "kind": "bar",
         "labels": [x[0] for x in oil], "datasets": [{"label": "mb/j", "data": [x[1] for x in oil]}], "unit": "mb/j",
         "src": "EIA, World Oil Transit Chokepoints (mise à jour 3 mars 2026), estimations fondées sur le suivi des pétroliers Vortexa. Avant la guerre actuelle : les flux d'Ormuz ont depuis chuté."},
        {"type": "chart", "title": "GNL transitant par chaque point · milliards de pieds cubes par jour (1er semestre 2025)", "kind": "bar",
         "labels": [x[0] for x in lng], "datasets": [{"label": "Gpi³/j", "data": [x[1] for x in lng]}], "unit": "Gpi³/j",
         "src": "EIA, World Oil Transit Chokepoints (mise à jour 3 mars 2026)."},
        {"type": "table", "title": "Poids de chaque point hors pétrole · part du commerce maritime mondial, toutes marchandises",
         "cols": ["Point", "Part du commerce maritime", "Autres repères", "Source"],
         "rows": [["Malacca", "24 %", "26 % des voitures transportées par mer", "UNCTAD (RMT 2024), via Down To Earth"],
                  ["Suez", "10 %", "Passages : ≈ 26 000 (2023) → ≈ 13 000 (2024)", "UNCTAD ; The Conversation, via Down To Earth"],
                  ["Détroits danois", "≈ 6 %", "Brut russe en hausse de ≈ 60 % depuis 2021", "EIA"],
                  ["Détroits turcs", "≈ 5 %", "≈ 60 % du flux est du brut", "EIA"],
                  ["Panama", "≈ 2,5 %", "≈ 40 % des conteneurs vers les États-Unis", "Down To Earth ; FMC (Congrès américain)"],
                  ["Ormuz", "n.d.", "≈ 19 % du commerce mondial de gaz naturel", "UNCTAD (RMT 2024), via Down To Earth"]],
         "src": "Les parts « toutes marchandises » incluent le pétrole ; elles ne sont pas strictement comparables d'une source à l'autre (périmètres UNCTAD et EIA différents)."},
    ]
    chart_html = render_blocks(blocks, charts, timelines, toc)
    page = f"""{head}
<body>
{masthead(prefix)}
<div class="shell">
{banner(prefix, full=True, img="banner-cartes.jpg", size=(1399, 597))}
<section class="hero glass home-hero">
  {ORB}
  <div class="hero-in">
    <div class="eyebrow"><span class="tag hot">Cartes</span><span class="tag">Accès libre</span><span class="tag">Pétrole · GNL · commerce</span></div>
    <h1>Points stratégiques, droits de passage et trafic maritime</h1>
    <p class="deck">Huit passages dont dépend le commerce mondial : qui les borde, quel droit s'y applique, ce qu'ils transportent (pétrole, GNL, autres marchandises) et par où contourner.</p>
  </div>
</section>
<div class="wrap wide">
  <div class="mapbox glass">
    <svg class="wmap" viewBox="0 0 {mp["w"]} {mp["h"]}" role="img" aria-label="Carte des points stratégiques maritimes">
      <path class="land" d="{mp["land"]}"/>{marks}
    </svg>
    <div class="map-legend"><span><i class="lg lg-critique"></i>Critique</span><span><i class="lg lg-élevée"></i>Élevée</span><span><i class="lg lg-surveillé"></i>Surveillé</span><span><i class="lg lg-structurel"></i>Structurel</span><span><i class="lg lg-modérée"></i>Modérée</span><span><i class="lg lg-refuge"></i>Refuge</span><span class="lg-n">Taille du cercle : volume de pétrole</span></div>
  </div>
</div>
<div class="layout">
<aside class="toc glass" aria-label="Sommaire par continent">
  <div class="toc-t">Par continent</div>
  <nav id="toc">{toc_html}</nav>
  <div class="toc-bar"><i id="tocBar"></i></div>
</aside>
<div class="wrap">
  {cont_html}
  <div class="sec-rule" id="trafic"><span class="sec-rule-txt">Trafic pétrolier et hors pétrole</span></div>
  {chart_html}
  <div class="src" id="sources">Sources : <a href="https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints" target="_blank" rel="noopener">EIA · World Oil Transit Chokepoints (3 mars 2026)</a> · <a href="https://www.downtoearth.org.in/economy/from-the-strait-of-hormuz-to-malacca-global-trade-relies-almost-entirely-on-these-five-narrow-waterways" target="_blank" rel="noopener">Down To Earth · chokepoints (18 mars 2026), d'après l'UNCTAD</a>. Les régimes juridiques sont rappelés d'après les conventions citées (CNUDM, Constantinople 1888, Montreux 1936, Copenhague 1857, traité de neutralité du Panama 1977). Les niveaux de tension sont la lecture de YAASAP, pas une donnée sourcée. Les flux d'Ormuz sont ceux d'avant la guerre actuelle : voir l'<a href="notes/20261031-1958-ormuz-doha-brent.html">analyse sur Ormuz</a>.</div>
  {cta_band(prefix)}
  <div class="v-disc" style="margin-top:18px">{e(DISCLAIMER)}</div>
  {newsletter()}
</div>
</div>
</div>
{footer(prefix, [{"file": x["file"], "nav": x["nav"]} for x in entries[:3]])}
<script>window.YA_PREFIX="./";window.NOTE_META={{"dateShort":""}};window.NOTE_CHARTS={json.dumps(charts, ensure_ascii=False)};window.NOTE_TIMELINES=[];</script>
<script src="assets/app.js?v={ASSET_V}"></script>
<script src="assets/acces.js?v={ASSET_V}"></script>
<script>(function(){{var m=document.querySelectorAll('.wmap .mk');function go(id){{var c=document.getElementById('p-'+id);if(!c)return;[].forEach.call(document.querySelectorAll('.pcard'),function(x){{x.classList.remove('on')}});c.classList.add('on');c.scrollIntoView({{behavior:'smooth',block:'center'}});}}[].forEach.call(m,function(g){{g.addEventListener('click',function(){{go(g.dataset.id)}});g.addEventListener('keydown',function(ev){{if(ev.key==='Enter')go(g.dataset.id)}});}});}})();</script>
</body>
</html>
"""
    (ROOT / "points-strategiques.html").write_text(page, encoding="utf-8")


def cta_band(prefix=""):
    return (f'<div class="cta-band glass"><div><div class="cta-t">Toutes les analyses, pour {PRICE}</div>'
            '<div class="cta-s">Seule l\'analyse sur Ormuz est offerte. Abonnez-vous pour lire chaque analyse en entier, dès sa publication.</div></div>'
            f'<div class="cta-b"><a class="btn-gold" href="{STRIPE_URL}" target="_blank" rel="noopener">S\'abonner</a>'
            f'<a class="btn-ghost" href="{prefix}abonnement.html">Déjà abonné ?</a></div></div>')


def render_abonnement(entries):
    prefix = "./"
    head = page_head("YAASAP Géostratégie · abonnement",
                     "Accès à toutes les analyses géostratégiques YAASAP : 3 € par mois. "
                     "L'analyse sur Ormuz est offerte en découverte.", f"{SITE}/abonnement.html").replace("{PREFIX}", prefix)
    head = head.replace('<meta property="og:type" content="article">', '<meta property="og:type" content="website">')
    n_arch = len([x for x in entries if x.get("locked")])
    arch_txt = (f" ({n_arch} à ce jour, une de plus toutes les 2 heures)" if n_arch else " : une de plus toutes les 2 heures")
    page = f"""{head}
<body>
{masthead(prefix)}
<div class="shell">
{banner(prefix)}
<section class="hero glass home-hero">
  {ORB}
  <div class="hero-in">
    <div class="eyebrow"><span class="tag hot">Abonnement</span><span class="tag">{PRICE}</span></div>
    <h1>Toutes les analyses YAASAP Géostratégie</h1>
    <p class="deck">L'analyse sur Ormuz est offerte en découverte. L'abonnement ouvre toutes les autres{arch_txt}.</p>
  </div>
</section>
<div class="wrap">
  <div class="offer glass">
    <div class="offer-p"><span class="offer-n">3 €</span><span class="offer-u">par mois, TTC</span></div>
    <ul class="offer-l">
      <li>Accès à toutes les analyses, en version complète : chiffres, graphiques, positions des acteurs, scénarios, verdict, sources</li>
      <li>Chaque nouvelle analyse (toutes les 2 heures) est accessible dès sa publication</li>
      <li>Paiement sécurisé par Stripe</li>
    </ul>
    <a class="btn-gold btn-big" href="{STRIPE_URL}" target="_blank" rel="noopener">S'abonner · {PRICE}</a>
  </div>
  <div class="sec-rule"><span class="sec-rule-txt">Comment ça marche</span></div>
  <div class="steps">
    <div class="step glass"><span class="step-n">1</span><p>Abonnez-vous avec le bouton ci-dessus, en indiquant votre e-mail.</p></div>
    <div class="step glass"><span class="step-n">2</span><p>Vous recevez votre <strong>code d'accès personnel</strong> par e-mail, sous 24 h.</p></div>
    <div class="step glass"><span class="step-n">3</span><p>Saisissez votre e-mail et votre code ci-dessous : les analyses s'ouvrent sur cet appareil.</p></div>
  </div>
  <div class="sec-rule"><span class="sec-rule-txt">Accès abonné</span></div>
  <div class="gate glass" id="loginBox">
    {login_form()}
    <div class="login-ok" id="lgOk"><strong>✓ Accès activé.</strong> <a href="index.html#archives">Ouvrir les analyses →</a> · <a href="#" id="logout">Se déconnecter</a></div>
  </div>
  <div class="v-disc" style="margin-top:18px">{e(DISCLAIMER)}</div>
</div>
</div>
{footer(prefix, [{"file": x["file"], "nav": x["nav"]} for x in entries[:3]])}
<script>window.YA_PREFIX="./";window.NOTE_META={{"dateShort":""}};window.NOTE_CHARTS=[];window.NOTE_TIMELINES=[];</script>
<script src="assets/app.js?v={ASSET_V}"></script>
<script src="assets/acces.js?v={ASSET_V}"></script>
</body>
</html>
"""
    (ROOT / "abonnement.html").write_text(page, encoding="utf-8")


def validate(note):
    for k in ("slug", "published", "title", "deck", "tags", "kpis", "lead", "blocks", "verdict"):
        if k not in note:
            raise ValueError(f"Champ obligatoire manquant : {k}")
    if len(note["kpis"]) != 6:
        raise ValueError("Il faut exactement 6 KPI")
    if not (5 <= len(note["verdict"]["items"]) <= 8):
        raise ValueError("Le verdict doit contenir 5 à 8 puces")
    if not note.get("sources"):
        raise ValueError("Au moins une source est obligatoire")
    for f in ("title", "deck"):
        check_safe(f, note[f])


def main(argv):
    NOTES_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not argv:
        print(__doc__)
        return 1
    rebuild = argv[0] == "--rebuild"
    priv_dir = PRIV / "notes"
    # 1) toutes les notes : publiques (data/notes) + archivées (dépôt privé)
    pub = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        pub[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    if not rebuild:
        f = Path(argv[0]).resolve()
        pub[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    arch = {}
    if priv_dir.exists():
        for f in sorted(priv_dir.glob("*.json")):
            arch[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    notes = {**arch, **pub}
    for n in notes.values():
        validate(n)
    latest = max(notes, key=lambda s: notes[s]["published"])
    # 2) archivage : tout sauf l'analyse offerte (FREE) passe dans le dépôt privé et est chiffré
    moved = [s for s in pub if s not in FREE]
    if moved:
        if not PRIV.exists():
            raise SystemExit("Dépôt privé introuvable (%s) : impossible d'archiver." % PRIV)
        priv_dir.mkdir(parents=True, exist_ok=True)
        for s in moved:
            (priv_dir / f"{s}.json").write_text(json.dumps(notes[s], ensure_ascii=False, indent=1), encoding="utf-8")
            (DATA_DIR / f"{s}.json").unlink(missing_ok=True)
            print("ARCHIVÉ  data/notes/%s.json -> dépôt privé" % s)
    entries = [entry_from(n, s, locked=(s not in FREE)) for s, n in notes.items()]
    entries.sort(key=lambda x: x["published"], reverse=True)
    # 3) rendu
    to_render = list(notes) if rebuild else sorted(set(moved) | (set(pub) & FREE))
    for s in to_render:
        render_note(notes[s], s, entries, locked=(s not in FREE))
        print("OK  notes/%s.html%s" % (s, "  (verrouillée)" if s not in FREE else ""))
    render_index(entries)
    render_abonnement(entries)
    render_points(entries)
    write_seo(entries)
    (ROOT / "data" / "index.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK  index.html + abonnement.html (%d analyses)" % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
