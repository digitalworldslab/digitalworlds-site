#!/usr/bin/env python3
"""SEO post-processor for digitalworlds.cc (static site).

Idempotent: safe to run after any page generator. Run from the repo root:
    python3 .seo/postprocess.py
It runs automatically on every push to main (.github/workflows/seo.yml).

What it does on every page (index.html files; skips /pins/ and verification files):
  * shortens <title> over 65 chars by dropping the " | Digital Worlds Lab" suffix
  * extends meta descriptions shorter than 120 chars on template pages
  * fills missing Open Graph / Twitter tags (og:title, og:description, og:url,
    og:type, og:image from the first page image, twitter:card)
  * adds hreflang alternates for pages that exist in more than one language
  * adds BreadcrumbList JSON-LD
  * adds a "Related" block of internal links built from topic clusters (CLUSTERS)
  * homepage: WebSite + Organization JSON-LD, links to PL/DE hubs and /embed/
  * rebuilds sitemap.xml (every page, lastmod = last git commit of the file)

New pages: add their path to a cluster below so they get linked in.
Generated blocks sit between <!--seo:NAME--> and <!--/seo:NAME--> markers.
"""
import html, json, os, re, subprocess, sys
from datetime import date

SITE = "https://digitalworlds.cc"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_IMG = SITE + "/social-assets/banner.jpg"
BRAND_SUFFIX = re.compile(r"\s*[|–-]\s*Digital Worlds Lab\s*$")

# Pages that are the same content in another language.
HREFLANG = [
    {"en": "/club/", "pl": "/klub/"},
    {"en": "/guides/debt-snowball-vs-avalanche/", "pl": "/kula-sniezna-czy-lawina/"},
    {"en": "/guides/52-week-savings-challenge/", "pl": "/wyzwanie-52-tygodni/"},
    {"pl": "/pl/", "de": "/de/"},
]

# Topic clusters for related links. Order inside a cluster = priority.
CLUSTERS = {
    "budget": ["/budget-calculator/", "/guides/50-30-20-budget-example/", "/guides/zero-based-budget-example/",
               "/holiday/budget-by-paycheck/", "/guides/bill-payment-calendar/", "/guides/split-bills-as-a-couple/",
               "/guides/notion-budget-template-free/", "/holiday/new-year-budget-reset-2027/"],
    "debt": ["/debt-snowball-calculator/", "/guides/debt-snowball-vs-avalanche/",
             "/guides/credit-card-minimum-payment/", "/guides/debt-payoff-coloring-chart/"],
    "savings": ["/sinking-funds-calculator/", "/guides/sinking-funds-list/", "/guides/how-much-emergency-fund/",
                "/guides/52-week-savings-challenge/", "/holiday/january-savings-challenge/",
                "/holiday/save-10k-2027/", "/guides/how-to-calculate-net-worth/", "/guides/notion-net-worth-tracker/"],
    "wedding": ["/wedding-budget-calculator/", "/guides/wedding-budget-breakdown/", "/guides/cut-wedding-guest-list/"],
    "holiday": ["/guides/christmas-budget/", "/holiday/christmas-market-pricing/",
                "/holiday/new-year-budget-reset-2027/", "/holiday/january-savings-challenge/", "/holiday/save-10k-2027/"],
    "selfemp": ["/self-employed-tax-calculator/", "/guides/self-employed-tax-set-aside/",
                "/guides/freelance-bookkeeping-spreadsheet/", "/calculator/", "/guides/etsy-fees-per-sale/",
                "/holiday/christmas-market-pricing/"],
    "home": ["/house-affordability-calculator/", "/rent-vs-buy-calculator/", "/car-affordability-calculator/",
             "/holiday/save-10k-2027/"],
    "pl": ["/pl/", "/limit-dzialalnosci-nierejestrowanej-2027/", "/budzet-domowy-excel/", "/metoda-kopertowa/", "/kula-sniezna-czy-lawina/",
           "/wyzwanie-52-tygodni/", "/klub/", "/arkusz-jdg/", "/ryczalt-czy-liniowy/",
           "/skladka-zdrowotna-jdg/", "/dzialalnosc-nierejestrowana-limit-2026/"],
    "de": ["/de/"],
}
# Product (template) pages point to the guides/calculators of their topic.
TEMPLATE_TOPIC = {
    "budget": "budget", "billcal": "budget", "paycheck": "budget", "zerobased": "budget", "simple": "budget",
    "couples": "budget", "grocery": "budget", "student": "budget", "first-apartment": "budget", "calorie": "budget",
    "debt": "debt", "creditcard": "debt", "debtcolor": "debt",
    "savings": "savings", "emergency": "savings", "challenge": "savings", "networth": "savings",
    "wedding": "wedding", "weddingbudget": "wedding", "guestlist": "wedding", "christmas": "holiday",
    "freelancer": "selfemp", "selfemp": "selfemp", "invoice": "selfemp", "etsyseller": "selfemp",
    "pricing": "selfemp", "profit-loss": "selfemp", "order-tracker": "selfemp", "mileage": "selfemp",
    "timesheet": "selfemp", "gig-driver": "selfemp", "job-tracker": "selfemp", "bundle": "budget",
}
SECTIONS = {"guides": ("Money guides", "/guides/"), "holiday": ("Holiday money guides", "/holiday/"),
            "templates": ("Money templates", "/templates/")}
LABEL = {"en": "Related free guides and calculators", "pl": "Powiązane poradniki i arkusze",
         "de": "Weitere kostenlose Vorlagen"}
HOME_LABEL = {"en": "Home", "pl": "Strona główna", "de": "Startseite"}


def pages():
    out = {}
    for d, _, files in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT).replace(os.sep, "/")
        if rel != "." and rel.startswith((".", "pins", "social-assets")):
            continue
        if "index.html" in files:
            url = "/" if rel == "." else "/" + rel + "/"
            out[url] = os.path.join(d, "index.html")
    return out


def get(h, rx):
    m = re.search(rx, h, re.I | re.S)
    return m.group(1).strip() if m else None


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def attr(s):
    return html.escape(s, quote=True)


def block(h, name, content, before):
    """Insert or replace a marked block. `before` = tag to insert in front of."""
    start, end = f"<!--seo:{name}-->", f"<!--/seo:{name}-->"
    new = f"{start}{content}{end}" if content else ""
    if start in h:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda m: new, h, flags=re.S)
    if not new:
        return h
    i = h.lower().rfind(before) if before != "</head>" else h.lower().find(before)
    return h[:i] + new + h[i:] if i >= 0 else h


def git_lastmod(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        return out or date.today().isoformat()
    except Exception:
        return date.today().isoformat()


def main():
    P = pages()
    meta = {}
    for url, f in P.items():
        h = open(f, encoding="utf-8").read()
        meta[url] = {
            "lang": (get(h, r'<html[^>]*\blang="([a-z]{2})') or "en"),
            "h1": text(get(h, r"<h1[^>]*>(.*?)</h1>")) or text(get(h, r"<title>(.*?)</title>")),
            "noindex": bool(re.search(r'name="robots"[^>]*noindex', h, re.I)),
        }
    alt = {}
    for g in HREFLANG:
        if all(u in P for u in g.values()):
            for u in g.values():
                alt[u] = g

    changed = 0
    for url, f in P.items():
        h0 = open(f, encoding="utf-8").read()
        # drop our own head block so checks see only the generator's tags
        h = re.sub(r"<!--seo:head-->.*?<!--/seo:head-->", "", h0, flags=re.S)
        m = meta[url]
        lang = m["lang"]
        canon = SITE + url

        # 1. title length
        t = get(h, r"<title>(.*?)</title>") or ""
        if len(html.unescape(t)) > 65 and BRAND_SUFFIX.search(t):
            nt = BRAND_SUFFIX.sub("", t)
            h = h.replace(f"<title>{t}</title>", f"<title>{nt}</title>", 1)
            t = nt
        # 2. short meta descriptions on template pages
        d = get(h, r'<meta name="description" content="(.*?)"') or ""
        if url.startswith("/templates/") and url != "/templates/" and len(html.unescape(d)) < 120:
            base = html.unescape(d).rstrip()
            nd = f"{base} {m['h1']} for Google Sheets and Excel, instant download."
            if len(nd) > 160:
                nd = f"{base} Google Sheets and Excel template, instant download."
            h = h.replace(f'<meta name="description" content="{d}"', f'<meta name="description" content="{attr(nd)}"', 1)
            d = attr(nd)
        # 3. Open Graph / Twitter
        tags = []
        if url == "/":
            h = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', h)
            h = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">', h)
        if 'property="og:title"' not in h:
            tags.append(f'<meta property="og:title" content="{t}">')
        if 'property="og:description"' not in h and d:
            tags.append(f'<meta property="og:description" content="{d}">')
        if 'property="og:url"' not in h:
            tags.append(f'<meta property="og:url" content="{canon}">')
        if 'property="og:type"' not in h:
            tags.append(f'<meta property="og:type" content="{"website" if url in ("/", "/pl/", "/de/") else "article"}">')
        if 'property="og:locale"' not in h:
            tags.append(f'<meta property="og:locale" content="{ {"en": "en_GB", "pl": "pl_PL", "de": "de_DE"}.get(lang, "en_GB") }">')
        if 'property="og:image"' not in h:
            img = get(h, r'<img[^>]+src="(/[^"]+\.(?:jpg|jpeg|png|webp))"')
            tags.append(f'<meta property="og:image" content="{SITE + img if img else DEFAULT_IMG}">')
        if 'name="twitter:card"' not in h:
            tags.append('<meta name="twitter:card" content="summary_large_image">')
        # 4. hreflang
        if url in alt:
            g = alt[url]
            hl = "".join(f'<link rel="alternate" hreflang="{l}" href="{SITE + u}">' for l, u in g.items())
            first = "en" if "en" in g else next(iter(g))
            hl += f'<link rel="alternate" hreflang="x-default" href="{SITE + g[first]}">'
            tags.append(hl)
        # 5. breadcrumbs
        crumbs = []
        if url != "/":
            crumbs.append((HOME_LABEL.get(lang, "Home"), SITE + "/"))
            sec = url.strip("/").split("/")[0]
            if sec in SECTIONS and url != SECTIONS[sec][1]:
                crumbs.append((SECTIONS[sec][0], SITE + SECTIONS[sec][1]))
            elif lang == "pl" and url not in ("/pl/",) and "/pl/" in P:
                crumbs.append(("Po polsku", SITE + "/pl/"))
            crumbs.append((m["h1"], canon))
            bl = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]}
            tags.append('<script type="application/ld+json">' + json.dumps(bl, ensure_ascii=False) + "</script>")
        else:
            ws = {"@context": "https://schema.org", "@graph": [
                {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": "Digital Worlds Lab",
                 "inLanguage": ["en", "pl", "de"], "publisher": {"@id": SITE + "/#org"}},
                {"@type": "Organization", "@id": SITE + "/#org", "name": "Digital Worlds Lab", "url": SITE + "/",
                 "logo": SITE + "/social-assets/avatar-512.png",
                 "sameAs": ["https://digitalworldslab.etsy.com", "https://digitallab8.gumroad.com",
                            "https://pl.pinterest.com/digitalworldslab/",
                            "https://bsky.app/profile/digitalworldslab.bsky.social",
                            "https://mastodon.social/@digitalworldslab"]}]}
            tags.append('<script type="application/ld+json">' + json.dumps(ws, ensure_ascii=False) + "</script>")
        h = block(h, "head", "".join(tags), "</head>")

        # 6. related links
        rel = []
        parts = url.strip("/").split("/")
        topics = [c for c, us in CLUSTERS.items() if url in us]
        if parts[0] == "templates" and len(parts) == 2 and parts[1] in TEMPLATE_TOPIC:
            topics = [TEMPLATE_TOPIC[parts[1]]]
        for c in topics:
            for u in CLUSTERS[c]:
                if u != url and u in P and u not in rel and meta[u]["lang"] == lang:
                    rel.append(u)
        rel = rel[:6]
        if rel:
            items = "".join(f'<li><a href="{u}">{attr(meta[u]["h1"])}</a></li>' for u in rel)
            sect = (f'<section class="related" style="margin-top:32px"><h2>{LABEL.get(lang, LABEL["en"])}</h2>'
                    f'<ul>{items}</ul></section>')
            h = block(h, "related", sect, "</main>" if "</main>" in h.lower() else "</body>")

        # 7. homepage: language hubs + embed
        if url == "/":
            hub = ('<section class="card"><h2>Po polsku · Auf Deutsch</h2>'
                   '<p>Free budget spreadsheets and guides in Polish and German, in złoty and euro.</p>'
                   '<a class="ghost" href="/pl/" hreflang="pl" lang="pl">Darmowy budżet domowy 2027</a>'
                   '<a class="ghost" href="/budzet-domowy-excel/" hreflang="pl" lang="pl">Budżet domowy w Excelu</a>'
                   '<a class="ghost" href="/metoda-kopertowa/" hreflang="pl" lang="pl">Metoda kopertowa</a>'
                   '<a class="ghost" href="/kula-sniezna-czy-lawina/" hreflang="pl" lang="pl">Spłata długów</a>'
                   '<a class="ghost" href="/arkusz-jdg/" hreflang="pl" lang="pl">Arkusz JDG 2027</a>'
                   '<a class="ghost" href="/limit-dzialalnosci-nierejestrowanej-2027/" hreflang="pl" lang="pl">Limit działalności nierejestrowanej 2027</a>'
                   '<a class="ghost" href="/de/" hreflang="de" lang="de">Kostenloses Haushaltsbuch 2027</a>'
                   '<a class="ghost" href="/embed/">Embed our calculators on your blog</a></section>')
            h = block(h, "home-hubs", hub, "<footer")

        if h != h0:
            open(f, "w", encoding="utf-8").write(h)
            changed += 1

    # 8. sitemap
    rows = []
    for url in sorted(P, key=lambda u: (u != "/", u)):
        if meta[url]["noindex"]:
            continue
        rel = os.path.relpath(P[url], ROOT)
        pr = "1.0" if url == "/" else "0.8" if url.count("/") == 2 else "0.6"
        rows.append(f"  <url><loc>{SITE}{url}</loc><lastmod>{git_lastmod(rel)}</lastmod><priority>{pr}</priority></url>")
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n")
    old = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    if old != sm:
        open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
        changed += 1
    print(f"seo postprocess: {changed} files changed, {len(rows)} URLs in sitemap")


if __name__ == "__main__":
    main()
