#!/usr/bin/env python3
"""Rendu des visuels madebylba (gabarit SlideReseaux de la Charte LBA v2).

Usage : python3 rendre.py post.json dossier_sortie
post.json : {"id": "...", "format": "carrousel" | "story" | "couverture", "slides": [
  {"type": "fort" | "clair" | "photo", "surtitre": "...", "titre": "Texte avec *mot clé*",
   "texte": "...", "photo": "chemin/vers/photo.jpg (type photo seulement)"}
]}
Sort : <id>-1.png, <id>-2.png, ... (1080x1350 ou 1080x1920) et planche.png pour vérifier.
Format « couverture » : couverture de story à la une (1080x1920), un seul champ utile par slide : "titre",
un mot court (12 caractères au plus), centré dans un disque citron sur fond marine ; Instagram ne garde que le cercle central.
"""
import html, json, os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ICI = Path(__file__).resolve().parent
F = (ICI / "fonts").as_uri()
CSS = """
@font-face{font-family:Brico;src:url(%(F)s/Bricolage.ttf)}
@font-face{font-family:InterV;src:url(%(F)s/Inter.ttf)}
@font-face{font-family:Serif;font-style:italic;src:url(%(F)s/InstrumentSerif-Italic.ttf)}
*{box-sizing:border-box}html,body{margin:0}
.s{width:1080px;height:%(H)spx;padding:76px 84px 96px;display:flex;flex-direction:column;position:relative;overflow:hidden;font-family:InterV,Inter,sans-serif}
.fort{background:#13265C;color:#F4F6EE;background-image:radial-gradient(rgba(244,246,238,.10) 5px,transparent 5px);background-size:96px 96px}
.clair{background:#F4F6EE;color:#0B1533}
.photo{background:#0B1533 center/cover no-repeat;color:#F4F6EE}
.photo::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,21,51,0) 40%%,rgba(11,21,51,.82))}
.top{display:flex;justify-content:space-between;font-size:40px;line-height:1.2;position:relative;z-index:1}
.clair .top{color:#4A5470}
.ring{position:absolute;right:-240px;top:-240px;width:690px;height:690px;border-radius:50%%;border:7px solid rgba(200,240,60,.35)}
.b{margin-top:auto;display:flex;flex-direction:column;gap:40px;position:relative;z-index:1}
.trait{width:140px;height:14px;background:#C8F03C}
.sur{margin:0;font-weight:600;font-size:36px;letter-spacing:.3em;text-transform:uppercase}
.fort .sur,.photo .sur{color:#C8F03C}.clair .sur{color:#13265C}
.t{margin:0;font-family:Brico,sans-serif;font-weight:800;font-size:%(T)spx;line-height:1.02;letter-spacing:-.03em;text-wrap:balance}
.clair .t{color:#13265C}
.fort .t em,.photo .t em{font-style:normal;color:#C8F03C}
.clair .t em{font-style:normal;background:#C8F03C;padding:0 .12em;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.p{margin:0;font-size:46px;line-height:1.45;max-width:880px}
.clair .p{color:#0B1533}
.couv{background:#13265C;background-image:radial-gradient(rgba(244,246,238,.10) 5px,transparent 5px);background-size:96px 96px;align-items:center;justify-content:center;padding:0}
.disque{width:920px;height:920px;border-radius:50%%;background:#C8F03C;display:flex;align-items:center;justify-content:center;text-align:center;padding:60px}
.disque span{font-family:Brico,sans-serif;font-weight:800;color:#13265C;line-height:1;letter-spacing:-.03em}
"""


def titre_html(t):
    t = html.escape(t or "")
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)


def couverture_html(s):
    mot = (s.get("titre") or "").replace("*", "")
    taille = 220 if len(mot) <= 5 else 168 if len(mot) <= 8 else 140
    return '<section class="s couv"><div class="disque"><span style="font-size:%dpx">%s</span></div></section>' % (taille, html.escape(mot)), len(mot) > 12


def slide_html(s, i, n, H):
    typ = s.get("type", "clair")
    style = ""
    if typ == "photo" and s.get("photo"):
        style = ' style="background-image:url(%s)"' % Path(s["photo"]).resolve().as_uri()
    long_titre = len(re.sub(r"\*", "", s.get("titre", ""))) > 42
    parts = ['<div class="ring"></div>' if typ == "fort" else "",
             '<div class="top"><span>%d/%d</span><span>@madebylba</span></div>' % (i, n) if n > 1 else
             '<div class="top"><span></span><span>@madebylba</span></div>',
             '<div class="b">']
    if typ == "fort":
        parts.append('<div class="trait"></div>')
    if s.get("surtitre"):
        parts.append('<p class="sur">%s</p>' % html.escape(s["surtitre"]))
    if s.get("titre"):
        parts.append('<h2 class="t">%s</h2>' % titre_html(s["titre"]))
    if s.get("texte"):
        parts.append('<p class="p">%s</p>' % html.escape(s["texte"]).replace("\n", "<br>"))
    parts.append("</div>")
    return '<section class="s %s"%s>%s</section>' % (typ, style, "".join(parts)), long_titre


def main():
    post = json.load(open(sys.argv[1], encoding="utf-8"))
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    H = 1920 if post.get("format") in ("story", "couverture") else 1350
    slides = post["slides"]
    fichiers = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1080, "height": H})
        for i, s in enumerate(slides, 1):
            if post.get("format") == "couverture":
                corps, long_titre = couverture_html(s)
            else:
                corps, long_titre = slide_html(s, i, len(slides), H)
            css = CSS % {"F": F, "H": H, "T": 88 if long_titre else 112}
            tmp = out / "_slide.html"
            tmp.write_text("<!doctype html><html lang=fr><head><meta charset=utf-8><style>%s</style></head><body>%s</body></html>" % (css, corps), encoding="utf-8")
            pg.goto(tmp.resolve().as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            debord = pg.evaluate("(()=>{const b=document.querySelector('.b');const t=document.querySelector('.top');if(b&&t)return b.getBoundingClientRect().top<t.getBoundingClientRect().bottom+20;const d=document.querySelector('.disque span');return !!d&&d.getBoundingClientRect().width>820})()") or (post.get("format") == "couverture" and long_titre)
            f = out / ("%s-%d.png" % (post["id"], i))
            pg.screenshot(path=str(f))
            fichiers.append(f)
            if debord:
                print("ATTENTION : texte trop long sur la slide %d (il touche le haut). Raccourcis." % i)
        b.close()
    (out / "_slide.html").unlink(missing_ok=True)
    # planche de contrôle
    from PIL import Image
    w, h = 360, H // 3
    pl = Image.new("RGB", (w * len(fichiers) + 10 * (len(fichiers) + 1), h + 20), "white")
    for k, f in enumerate(fichiers):
        pl.paste(Image.open(f).convert("RGB").resize((w, h)), (10 + k * (w + 10), 10))
    pl.save(out / "planche.png")
    print("\n".join(str(f) for f in fichiers))
    print(out / "planche.png")


if __name__ == "__main__":
    main()
