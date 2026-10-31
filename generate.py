#!/usr/bin/env python3
"""YAASAP Géostratégie — générateur de notes.

Usage :
    python3 generate.py data/notes/<fichier>.json     # rend une note + reconstruit l'accueil
    python3 generate.py --rebuild                     # reconstruit toutes les notes et l'accueil

Une note = un fichier JSON (voir PROTOCOLE.md pour le schéma). Le HTML est écrit dans
notes/<même nom>.html ; index.html et data/index.json sont régénérés à chaque appel.
Le contenu des champs « p », « html », « hl », etc. est du HTML de confiance (balises <strong>, <em>, <a>).
"""
import hashlib
import html as H
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
NOTES_DIR = ROOT / "notes"
DATA_DIR = ROOT / "data" / "notes"
SITE = "https://yaasap.github.io/yaasap-geostrategie"
MAIN_SITE = "https://yaasap.github.io/dailywatch"
TZ = ZoneInfo("Europe/Paris")
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
MONTHS_S = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
            "sept.", "oct.", "nov.", "déc."]
DISCLAIMER = ("Ne constitue pas un conseil en investissement. "
              "Par Yacine AOUABED · YAASAP Géostratégie · yaasap.github.io/yaasap-geostrategie")

def _asset_version():
    h = hashlib.md5()
    for n in ("style.css", "app.js", "banner.jpg"):
        f = ROOT / "assets" / n
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()[:8]


ASSET_V = _asset_version()

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500'
         '&family=Playfair+Display:ital,wght@0,500;0,700;1,400;1,500'
         '&family=Source+Sans+3:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">')


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


def page_head(title, desc, canonical, og_title=None):
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
<meta name="robots" content="index,follow">
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


def banner(prefix):
    return (f'<div class="banner glass"><img src="{prefix}assets/banner.jpg?v={ASSET_V}" width="1672" height="941" '
            'alt="YAASAP : analyses géostratégiques" fetchpriority="high"></div>')


def masthead(prefix):
    return f"""<canvas id="bg"></canvas>
<div class="page">
<div class="masthead">
  <a class="pub-name" href="{prefix}index.html" style="text-decoration:none">YAASAP <em>Géostratégie</em></a>
  <div class="mast-r"><span class="mast-date" id="mastDate"></span><div id="qr-mast"></div></div>
</div>"""


def footer(prefix, recent):
    links = "".join(f'<a href="{prefix}notes/{e(n["file"])}">{e(n["nav"])}</a>' for n in recent)
    return f"""<footer>
  <div class="f-nav">
    <a href="{prefix}index.html">Accueil</a>
    {links}
    <a href="{prefix}index.html#archives">Archives</a>
    <a href="{MAIN_SITE}/">YAASAP Notes</a>
  </div>
  <div class="f-note">YAASAP Géostratégie · Yacine AOUABED · yaasap.github.io/yaasap-geostrategie<br>Ne constitue pas un conseil en investissement.</div>
</footer>
</div>"""


def newsletter():
    return """<div class="nl glass">
    <div class="nl-hl">Recevoir les prochaines analyses YAASAP</div>
    <div class="nl-row">
      <input class="nl-input" type="email" id="nlEmail" placeholder="votre@email.com">
      <button class="nl-btn" onclick="nlSubmit()">S'ABONNER →</button>
    </div>
    <div class="nl-ok" id="nlOk">✓ Inscrit — vérifiez votre boite mail</div>
  </div>"""


def render_note(note, stem, index_entries):
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
    head = page_head(f'YAASAP Géostratégie · {note["title"]}', note["deck"], canonical, note["title"]).replace("{PREFIX}", prefix)
    src_names = " · ".join(s["t"] for s in note.get("sources", []))
    page = f"""{head}
<body>
{masthead(prefix)}
<div class="shell">

{banner(prefix)}

<section class="hero glass">
  {ORB}
  <div class="hero-in">
    <div class="eyebrow">{tags}<span class="tag">{e(date_short(dt))} · {dt.strftime('%H:%M')}</span></div>
    <h1>{e(note["title"])}</h1>
    <p class="deck">{e(note["deck"])}</p>
  </div>
</section>

<div class="kpi-strip">
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

  {newsletter()}

</div>
</div>
</div>

{footer(prefix, recent)}

<script>window.NOTE_META={json.dumps(meta, ensure_ascii=False)};window.NOTE_CHARTS={json.dumps(charts, ensure_ascii=False).replace("</", "<\\/")};window.NOTE_TIMELINES={json.dumps(timelines, ensure_ascii=False).replace("</", "<\\/")};</script>
<script src="{prefix}assets/app.js?v={ASSET_V}"></script>
</body>
</html>
"""
    (NOTES_DIR / f"{stem}.html").write_text(page, encoding="utf-8")


def entry_from(note, stem):
    dt = parse_dt(note)
    return {
        "file": f"{stem}.html",
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
                     "risques et canaux de marché. Par Yacine AOUABED.", f"{SITE}/").replace("{PREFIX}", prefix)
    head = head.replace('<meta property="og:type" content="article">', '<meta property="og:type" content="website">')
    cards = []
    for n in entries:
        dt = datetime.fromisoformat(n["published"]).astimezone(TZ)
        tags = "".join(f'<span class="tag{" hot" if t.get("hot") else ""}">{e(t["t"])}</span>' for t in n["tags"])
        cards.append(
            f'<a class="ncard glass" href="notes/{e(n["file"])}"><div class="eyebrow">{tags}</div>'
            f'<h2>{e(n["title"])}</h2><p>{e(n["deck"])}</p>'
            f'<div class="nc-d">{e(date_long(dt))} · {dt.strftime("%H:%M")}</div></a>')
    cards_html = "\n".join(cards) if cards else '<div class="empty glass">Première analyse à venir.</div>'
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
    <p class="deck">Faits sourcés, positions de chaque acteur, risques et canaux de marché. Même format que YAASAP Notes : chiffres d'abord, verdict tranché, sources citées.</p>
    <div class="home-meta">{last}<span class="tag">{len(entries)} analyse{'s' if len(entries) > 1 else ''} publiée{'s' if len(entries) > 1 else ''}</span></div>
  </div>
</section>
<div class="wrap" id="archives">
  <div class="sec-rule"><span class="sec-rule-txt">Dernières analyses</span></div>
  <div class="ncards">
{cards_html}
  </div>
  {newsletter()}
</div>
</div>
{footer(prefix, [{"file": x["file"], "nav": x["nav"]} for x in entries[:3]])}
<script>window.NOTE_META={{"dateShort":""}};window.NOTE_CHARTS=[];window.NOTE_TIMELINES=[];</script>
<script src="assets/app.js?v={ASSET_V}"></script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


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
    if argv and argv[0] == "--rebuild":
        files = sorted(DATA_DIR.glob("*.json"))
    elif argv:
        files = [Path(argv[0]).resolve()]
    else:
        print(__doc__)
        return 1
    # 1) entrées d'index de toutes les notes existantes
    all_json = sorted(DATA_DIR.glob("*.json"))
    notes = {}
    for f in set(all_json) | set(files):
        n = json.loads(f.read_text(encoding="utf-8"))
        validate(n)
        notes[f.stem] = n
    entries = [entry_from(n, s) for s, n in notes.items()]
    entries.sort(key=lambda x: x["published"], reverse=True)
    # 2) rendu des notes demandées
    to_render = list(notes) if argv[0] == "--rebuild" else [files[0].stem]
    for s in to_render:
        render_note(notes[s], s, entries)
        print("OK  notes/%s.html" % s)
    # 3) accueil + index JSON
    render_index(entries)
    (ROOT / "data" / "index.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK  index.html (%d analyses)" % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
