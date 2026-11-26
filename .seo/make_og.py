#!/usr/bin/env python3
"""Build a 1200x630 link-preview card for every page into og/<slug>.jpg.

* Pages with a social card (.social/queue.json url -> .social/cards/<id>.jpg) reuse that card.
* Other pages get a card in the same style: pill + page H1 + short line, and the
  page's own product image (or the brand logo) on the right.
Existing og/*.jpg files are kept, so a card is made once per page; pass --force to rebuild.
Run from the repo root (the SEO workflow runs it before postprocess.py). Needs Pillow.
"""
import html, json, os, re, shutil, sys
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "og")
NAVY = (19, 32, 61); TEAL = (38, 153, 137); ORANGE = (226, 112, 64); CREAM = (246, 243, 236); WHITE = (255, 255, 255)
FONT_DIRS = ["/usr/share/fonts/opentype/inter/", os.path.join(ROOT, ".seo/fonts/")]


def font(weight, size):
    for d in FONT_DIRS:
        p = os.path.join(d, f"Inter-{weight}.otf")
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    dv = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(dv, size) if os.path.exists(dv) else ImageFont.load_default()


def slug(url):
    return url.strip("/").replace("/", "-") or "home"


def pages():
    out = {}
    for d, _, files in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT).replace(os.sep, "/")
        if rel != "." and rel.startswith((".", "pins", "social-assets", "og")):
            continue
        if "index.html" in files:
            out["/" if rel == "." else "/" + rel + "/"] = os.path.join(d, "index.html")
    return out


def get(h, rx):
    m = re.search(rx, h, re.I | re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return [l for l in lines if l]


def mock(path):
    im = Image.open(path).convert("RGB")
    if im.size == (1000, 1500):  # portrait pin: skip its own headline
        im = im.crop((30, 575, 970, 1300))
    # trim flat background at the bottom/right so the mockup has no empty panel
    bg = Image.new("RGB", im.size, im.getpixel((im.width - 1, im.height - 1)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 18 else 0).getbbox()
    if box:
        im = im.crop((0, 0, min(im.width, box[2] + 20), min(im.height, box[3] + 20)))
    W, H = 560, 520
    im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS).crop((0, 0, W, min(H, int(im.height * W / im.width))))
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, *im.size], 22, fill=255)
    o = Image.new("RGBA", im.size, (0, 0, 0, 0)); o.paste(im, (0, 0), m)
    return o.rotate(2, expand=True, resample=Image.BICUBIC)


def logo():
    im = Image.open(os.path.join(ROOT, "social-assets/avatar-512.png")).convert("RGBA")
    return im.resize((300, 300), Image.LANCZOS)


# Hand-written text for pages where the H1 does not make a good card: url -> (pill, headline, line)
OVERRIDES = {
    "/limit-dzialalnosci-nierejestrowanej-2027/": ("DARMOWY KALKULATOR", "Limit działalności nierejestrowanej 2027",
                                                   "11 137,50 zł na kwartał. Ile jeszcze możesz zarobić?"),
    "/klub/": ("ABONAMENT", "Klub Arkuszy: wszystkie arkusze w jednym miejscu", "Budżet, długi, JDG · 7 dni za darmo"),
    "/club/": ("MEMBERSHIP", "Money Sheets Club", "Every money spreadsheet, new ones monthly"),
    "/": ("FREE MONEY TOOLS", "Practical money tools and spreadsheets", "Free calculators + Google Sheets & Excel templates"),
    "/embed/": ("FOR BLOGGERS", "Free money calculators for your blog", "Embed with one line of code, no ads"),
}


def pill_for(url, lang):
    if lang == "pl":
        return "DARMOWY KALKULATOR" if "kalkulator" in url or url.startswith("/limit-") else ("PO POLSKU" if url == "/pl/" else "PORADNIK")
    if lang == "de":
        return "KOSTENLOS"
    if url == "/":
        return "FREE MONEY TOOLS"
    if url.endswith("-calculator/") or url == "/calculator/":
        return "FREE CALCULATOR"
    if url.startswith("/templates/"):
        return "GOOGLE SHEETS + EXCEL"
    if url.startswith("/holiday/"):
        return "HOLIDAY MONEY GUIDE"
    if url.startswith("/guides/"):
        return "MONEY GUIDE"
    return "DIGITAL WORLDS LAB"


def card(url, path, dest):
    h = open(path, encoding="utf-8").read()
    lang = (re.search(r'<html[^>]*\blang="([a-z]{2})', h) or [None, "en"])[1]
    head = get(h, r"<h1[^>]*>(.*?)</h1>") or get(h, r"<title>(.*?)</title>")
    pill = pill_for(url, lang)
    if url in OVERRIDES:
        pill, head, sub = OVERRIDES[url]
    elif len(head) > 45 and ":" in head:
        head, rest = head.split(":", 1)
        sub = rest.strip()
    else:
        sub = re.split(r"(?<=[a-z]{3})\. ", get(h, r'<meta name="description" content="(.*?)"'))[0]
    if len(sub) > 70:
        sub = sub[:68].rsplit(" ", 1)[0] + "…"
    img = None
    for src in re.findall(r'<img[^>]+src="(/[^"]+\.(?:jpg|jpeg|png))"', h):
        p = os.path.join(ROOT, src.lstrip("/"))
        if os.path.exists(p):
            img = p; break
    c = Image.new("RGBA", (1200, 630), CREAM + (255,)); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 1200, 10], fill=NAVY)
    mk = mock(img) if img else logo()
    x = 1200 - mk.width - (40 if img else 90); y = max(30, (630 - mk.height) // 2)
    if img:
        sh = Image.new("RGBA", (mk.width + 100, mk.height + 100), (0, 0, 0, 0))
        s = Image.new("RGBA", mk.size, (0, 0, 0, 255)); s.putalpha(mk.split()[3].point(lambda v: int(v * .45)))
        sh.paste(s, (50, 65), s); sh = sh.filter(ImageFilter.GaussianBlur(22)); c.alpha_composite(sh, (x - 50, y - 50))
    c.alpha_composite(mk, (x, y))
    pf = font("Bold", 24); pw = d.textlength(pill, font=pf)
    d.rounded_rectangle([56, 64, 56 + pw + 40, 108], 22, fill=TEAL); d.text((76, 71), pill, font=pf, fill=WHITE)
    width = 470 if img else 640
    size = 64
    while True:
        hf = font("ExtraBold", size); lines = wrap(d, head, hf, width)
        if len(lines) <= 3 or size <= 44:
            break
        size -= 4
    yy = 150
    for l in lines[:4]:
        d.text((56, yy), l, font=hf, fill=NAVY); yy += int(size * 1.12)
    yy += 14
    sf = font("SemiBold", 30)
    for l in wrap(d, sub, sf, width)[:2]:
        d.text((56, yy), l, font=sf, fill=ORANGE); yy += 40
    d.text((56, 548), "digitalworlds.cc", font=font("ExtraBold", 30), fill=NAVY)
    c.convert("RGB").save(dest, quality=86, optimize=True)


def main(force=False):
    os.makedirs(OUT, exist_ok=True)
    mapped = {}
    qp = os.path.join(ROOT, ".social/queue.json")
    if os.path.exists(qp):
        for it in json.load(open(qp, encoding="utf-8")):
            u = it.get("url", "").split("?")[0].split("#")[0]
            if not u.startswith("https://digitalworlds.cc") or it["id"].startswith("bf"):
                continue  # Black Friday cards are temporary
            u = u.replace("https://digitalworlds.cc", "") or "/"
            card_path = os.path.join(ROOT, ".social/cards", it["id"] + ".jpg")
            if os.path.exists(card_path):
                mapped.setdefault(u, card_path)
    made = 0
    for url, path in pages().items():
        dest = os.path.join(OUT, slug(url) + ".jpg")
        if os.path.exists(dest) and not force:
            continue
        if url in mapped:
            shutil.copyfile(mapped[url], dest)
        else:
            card(url, path, dest)
        made += 1
    print(f"og cards: {made} made, {len(os.listdir(OUT))} total")


if __name__ == "__main__":
    main("--force" in sys.argv)
