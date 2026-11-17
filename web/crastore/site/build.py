#!/usr/bin/env python3
"""株式会社Crastore 複数ページ版ホームページのビルド

src/ の共通部品（CSS・ヘッダー・フッター・JS）と src/pages/*.html の本文を組み合わせて、
  dist/wp-<slug>.html     … WordPressの「カスタムHTML」ブロックに貼り付ける完成品
  preview/<slug>.html     … ブラウザで直接開いて確認するためのプレビュー（ページ間リンクもローカルで動く）
を書き出す。共通部分を直したら、このスクリプトを実行して全ページを作り直す。

  python3 build.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
PREVIEW = ROOT / "preview"

SITE = "https://crastore.xyz"
FORM = "https://staffpro.jp/"
LINE = "https://lin.ee/qeO2S0T"
LINE_IMG = "https://scdn.line-apps.com/n/line_add_friends/btn/ja.png"
INSTAGRAM = "https://www.instagram.com/crastore_inc/"
TEL = "050-3700-3996"
TEL_LINK = "tel:05037003996"
HOURS = "受付 9:00〜17:00"
NEW_WIN = '<span class="sr-only">（別ウィンドウで開きます）</span>'

# ページの定義。slug は WordPress の固定ページの「URLスラッグ」と一致させる
PAGES = [
    dict(key="home", slug="", nav=None, name="ホーム",
         title="大阪の建設会社｜建築・船の内装工事・錆止め・除菌消臭｜株式会社Crastore",
         desc="大阪・船場の建設会社、株式会社Crastore（クラストア）。建物の改修・修繕、火災保険を使った修繕、船の内装・外装工事、錆を変化させて再発を抑える錆止め、室内の除菌・消臭に対応。写真1枚から無料でお見積りします。"),
    dict(key="building", slug="building", nav="建築", name="建築工事・リフォーム",
         title="建築工事・リフォーム・原状回復｜大阪の株式会社Crastore",
         desc="大阪の建築工事・リフォームなら株式会社Crastore。内装・外装、水まわり、原状回復、壁一か所の部分補修まで。他社で断られた工事もご相談ください。写真1枚から無料でお見積り。",
         service="建築工事・リフォーム"),
    dict(key="fire-insurance", slug="fire-insurance", nav="火災保険", name="火災保険を使った修繕",
         title="火災保険を使った修繕（台風・雨漏り）｜大阪の株式会社Crastore",
         desc="台風・大雨・雪などで壊れた屋根・外壁・雨樋の修繕。保険金を決めるのは保険会社です。株式会社Crastoreは被害調査と、事実に基づく写真・所見・修理見積書の作成、施工を行います。成功報酬はいただきません。",
         service="火災保険を活用した建物の修繕"),
    dict(key="ship-interior", slug="ship-interior", nav="船の内装", name="船の内装工事",
         title="船の内装工事・船室リフォーム｜大阪の株式会社Crastore",
         desc="船の内装工事・船室のリフォームなら大阪の株式会社Crastore。床・壁・天井の張り替え、収納の取り付け、部分補修から船の外部の工事まで。湿気・揺れ・狭い空間など船ならではの条件に合わせて施工します。",
         service="船の内装工事・船室のリフォーム"),
    dict(key="rust-proofing", slug="rust-proofing", nav="錆止め", name="錆止め",
         title="錆止め工事 5,500円/㎡（税別）｜錆を変化させて再発を抑える｜株式会社Crastore",
         desc="塗装の下塗りではなく、錆そのものを変化させて再発を抑える錆止め。鉄骨階段・手すり・門扉・トタン屋根などに。錆止めだけのご依頼OK。1㎡あたり5,500円（税込6,050円）。大阪の株式会社Crastore。",
         service="錆止め施工"),
    dict(key="deodorize", slug="deodorize", nav="除菌・消臭", name="室内の除菌・消臭",
         title="室内の除菌・消臭（タバコ・ペット・カビの臭い）｜大阪の株式会社Crastore",
         desc="壁紙や床に染みついたタバコ・ペット・カビの臭い、退去後や長く閉め切った部屋の除菌・消臭。原因と建材の状態を確認して方法をご提案し、必要に応じて内装工事と組み合わせます。大阪の株式会社Crastore。",
         service="室内の除菌・消臭"),
    dict(key="company", slug="company", nav="会社概要", name="会社概要",
         title="会社概要｜株式会社Crastore（大阪市中央区）",
         desc="株式会社Crastore（クラストア）の会社概要。大阪市中央区北久宝寺町の建設会社です。建築・船舶・錆止め・除菌消臭の4つの事業を行っています。"),
    dict(key="contact", slug="contact", nav="お問い合わせ", name="お問い合わせ",
         title="お問い合わせ・無料見積り｜株式会社Crastore",
         desc="株式会社Crastoreへのお問い合わせ。フォーム（24時間受付）・お電話・LINEで、写真1枚からご相談いただけます。相談・現地調査・お見積りまで無料です。"),
]
BY_KEY = {p["key"]: p for p in PAGES}

ICONS = {
    "building": '<path d="M3 11l9-7 9 7"/><path d="M5 9.5V20h14V9.5"/><path d="M10 20v-6h4v6"/>',
    "ship-interior": '<path d="M2 15h20l-3 5H5z"/><path d="M12 3v12"/><path d="M12 4l7 8h-7"/>',
    "rust-proofing": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "deodorize": '<path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/><path d="M18 14.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/>',
    "fire-insurance": '<path d="M12 3a9 9 0 0 1 9 9H3a9 9 0 0 1 9-9z"/><path d="M12 12v6.5a2 2 0 0 0 4 0"/>',
}


def url(key):
    p = BY_KEY[key]
    return f"{SITE}/{p['slug']}/" if p["slug"] else f"{SITE}/"


def icon(name):
    return ('<span class="svc-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg></span>')


def line_cta(text="ちょっと聞きたいだけなら、LINEでも気軽にどうぞ。"):
    return (f'<p class="line-cta"><span>{text}</span><a href="{LINE}" target="_blank" rel="noopener">'
            f'<img src="{LINE_IMG}" alt="LINEで友だち追加" height="36" border="0"></a></p>')


def sec_cta(label):
    return (f'<div class="sec-cta">\n        <a class="btn-primary" href="{FORM}" target="_blank" rel="noopener">{label}{NEW_WIN}</a>\n'
            f'        {line_cta()}\n      </div>')


def cta_band(title, lead):
    return f'''<section class="contact" id="contact" aria-labelledby="contactTitle">
    <div class="wrap">
      <p class="sec-label">Contact</p>
      <h2 class="sec-title" id="contactTitle">{title}</h2>
      <p class="sec-lead">{lead}</p>
      <div class="contact-actions">
        <a class="btn-primary" href="{FORM}" target="_blank" rel="noopener">写真を送って無料見積り（24時間受付）{NEW_WIN}</a>
        <a class="contact-tel" href="{TEL_LINK}">
          <span class="num">{TEL}</span>
          <span class="hours">{HOURS}</span>
        </a>
      </div>
      {line_cta("LINEでも、写真を送って気軽にご相談いただけます。")}
      <p class="cta-note">
        <span><span class="ck" aria-hidden="true">✓</span>相談・現地調査・見積りまで無料</span>
        <span><span class="ck" aria-hidden="true">✓</span>見積り後のお断りOK</span>
        <span><span class="ck" aria-hidden="true">✓</span>しつこい営業なし</span>
      </p>
    </div>
  </section>'''


RELATED_TEXT = {
    "building": "改修・リフォーム・原状回復",
    "fire-insurance": "台風・雨漏りの被害の修繕",
    "ship-interior": "船室の床・壁・天井、外部の工事",
    "rust-proofing": "5,500円／㎡（税込6,050円）",
    "deodorize": "タバコ・ペット・カビの臭い",
}


def related(current):
    keys = [k for k in ("building", "fire-insurance", "ship-interior", "rust-proofing", "deodorize") if k != current]
    items = "\n".join(
        f'        <a href="{url(k)}">{icon(k)}<span>{BY_KEY[k]["name"]}<small>{RELATED_TEXT[k]}</small></span></a>'
        for k in keys)
    return f'''<section class="related-sec" aria-labelledby="relTitle">
    <div class="wrap">
      <p class="sec-label">Other Services</p>
      <h2 class="sec-title" id="relTitle">ほかの事業も、ひとつの窓口で</h2>
      <div class="related">
{items}
      </div>
    </div>
  </section>'''


def flow(lead="どの工事も、最初の一歩は写真を1枚送るだけです。", first="フォーム・LINE・お電話で。気になる箇所の写真を送っていただくとスムーズです。"):
    return f'''<section id="flow" aria-labelledby="flowTitle">
    <div class="wrap">
      <p class="sec-label">Flow</p>
      <h2 class="sec-title" id="flowTitle">ご依頼の流れ</h2>
      <p class="sec-lead">{lead}</p>
      <div class="flow-grid">
        <div class="flow-step is-first reveal">
          <span class="tag">まずはここから</span>
          <h3>写真を送ってご相談</h3>
          <p>{first}</p>
        </div>
        <div class="flow-step reveal">
          <span class="tag">ここまで無料</span>
          <h3>現地調査・お見積り</h3>
          <p>内訳の分かるお見積りをご提示します。金額を見てお断りいただいて構いません。</p>
        </div>
        <div class="flow-step reveal">
          <h3>ご契約・施工</h3>
          <p>ご納得いただいてから着工します。日程は事前にご相談のうえ決めます。</p>
        </div>
        <div class="flow-step reveal">
          <h3>お引き渡し</h3>
          <p>仕上がりを一緒にご確認いただいて完了です。施工後のご相談も歓迎です。</p>
        </div>
      </div>
    </div>
  </section>'''


def header(page):
    links = []
    for p in PAGES:
        if not p["nav"]:
            continue
        cur = ' aria-current="page"' if p["key"] == page["key"] else ""
        links.append(f'      <a href="{url(p["key"])}"{cur}>{p["nav"]}</a>')
    return f'''<header class="cl-header">
  <div class="wrap header-inner">
    <a href="{SITE}/" class="logotype" aria-label="株式会社Crastore ホーム">CRA<span class="s">S</span>TORE</a>
    <button class="menu-btn" id="clMenuBtn" type="button" aria-label="メニューを開く" aria-expanded="false" aria-controls="clGnav"><span></span><span></span><span></span></button>
    <nav class="gnav" id="clGnav" aria-label="メインメニュー">
{chr(10).join(links)}
      <a class="head-tel" href="{TEL_LINK}">
        <span class="num">{TEL}</span>
        <span class="sub">{HOURS}</span>
      </a>
      <a class="btn-cta" href="{FORM}" target="_blank" rel="noopener">無料見積り{NEW_WIN}</a>
    </nav>
  </div>
</header>'''


def footer():
    nav = "\n".join(f'      <a href="{url(p["key"])}">{p["name"]}</a>' for p in PAGES)
    return f'''<footer class="cl-footer">
  <div class="wrap footer-inner">
    <div>
      <p class="logotype">CRA<span class="s">S</span>TORE</p>
      <p class="footer-info">
        株式会社Crastore（クラストア）<br>
        〒541-0057 大阪市中央区北久宝寺町2-6-10-404<br>
        TEL <a href="{TEL_LINK}">{TEL}</a>（{HOURS}）<br>
        Instagram <a href="{INSTAGRAM}" target="_blank" rel="noopener">@crastore_inc</a>
      </p>
      <p class="footer-copy">&copy; <span id="clYear">2026</span> 株式会社Crastore</p>
    </div>
    <nav class="footer-nav" aria-label="フッターメニュー">
{nav}
    </nav>
  </div>
</footer>

<!-- スマホ用の追従ボタン（電話 / LINE / 見積り） -->
<div class="sticky-cta">
  <a class="s-tel" href="{TEL_LINK}">電話で相談<span class="sub">{TEL}</span></a>
  <a class="s-line" href="{LINE}" target="_blank" rel="noopener">LINE<span class="sub">気軽に相談</span></a>
  <a class="s-form" href="{FORM}" target="_blank" rel="noopener">無料見積り<span class="sub">写真を送る・24時間</span></a>
</div>'''


ORG = {
    "@type": "GeneralContractor",
    "@id": f"{SITE}/#org",
    "name": "株式会社Crastore",
    "alternateName": "株式会社クラストア",
    "url": f"{SITE}/",
    "telephone": "+81-50-3700-3996",
    "sameAs": [INSTAGRAM],
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "北久宝寺町2-6-10-404",
        "addressLocality": "大阪市中央区",
        "addressRegion": "大阪府",
        "postalCode": "541-0057",
        "addressCountry": "JP",
    },
    "areaServed": {"@type": "AdministrativeArea", "name": "大阪府"},
}


def jsonld(page):
    if page["key"] == "home":
        org = dict(ORG)
        org["description"] = page["desc"]
        org["openingHoursSpecification"] = [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            "opens": "09:00", "closes": "17:00"}]
        data = {"@context": "https://schema.org", **org}
    else:
        graph = []
        if page.get("service"):
            svc = {"@type": "Service", "name": page["service"], "description": page["desc"],
                   "areaServed": ORG["areaServed"], "provider": ORG, "url": url(page["key"])}
            if page["key"] == "rust-proofing":
                svc["offers"] = {"@type": "Offer", "priceSpecification": {
                    "@type": "UnitPriceSpecification", "price": 5500, "priceCurrency": "JPY",
                    "unitText": "㎡", "valueAddedTaxIncluded": False}}
            graph.append(svc)
        elif page["key"] == "company":
            graph.append(ORG)
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": page["name"], "item": url(page["key"])}]})
        data = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(data, ensure_ascii=False, indent=2)


def crumb(page):
    return (f'<nav class="crumb" aria-label="パンくずリスト"><a href="{SITE}/">ホーム</a>'
            f'<span aria-hidden="true">›</span><span>{page["name"]}</span></nav>')


def expand(body, page):
    """本文中の {{...}} を部品に置き換える"""
    def rep(m):
        name, _, arg = m.group(1).partition(":")
        args = arg.split("||") if arg else []
        if name == "url":
            return url(args[0])
        if name == "icon":
            return icon(args[0])
        if name == "form":
            return FORM
        if name == "newwin":
            return NEW_WIN
        if name == "line":
            return line_cta(*args)
        if name == "seccta":
            return sec_cta(args[0])
        if name == "cta":
            return cta_band(args[0], args[1])
        if name == "related":
            return related(page["key"])
        if name == "flow":
            return flow(*args)
        if name == "crumb":
            return crumb(page)
        if name in ("tel", "tellink", "hours", "lineurl", "lineimg", "instagram"):
            return {"tel": TEL, "tellink": TEL_LINK, "hours": HOURS, "lineurl": LINE,
                    "lineimg": LINE_IMG, "instagram": INSTAGRAM}[name]
        raise KeyError(f"unknown token {m.group(0)} in {page['key']}")
    return re.sub(r"\{\{([^}]+)\}\}", rep, body)


JS = (SRC / "script.js").read_text(encoding="utf-8")
CSS = (SRC / "base.css").read_text(encoding="utf-8")
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@700;800'
         '&family=Zen+Kaku+Gothic+New:wght@400;500;700;900&family=Archivo:wght@600;700;800&display=swap" rel="stylesheet">')


def render(page):
    body = expand((SRC / "pages" / f"{page['key']}.html").read_text(encoding="utf-8"), page)
    where = (f"{SITE}/{page['slug']}/" if page["slug"] else f"{SITE}/（設定 → 表示設定 →「ホームページ」に指定）")
    note = f'''<!-- ============================================================
  株式会社Crastore ホームページ ／ {page["name"]}
  公開URL : {where}
  ページタイトル : {page["name"]}
  URLスラッグ   : {page["slug"] or "（自由。表示設定でホームページに指定）"}

  ▼ 検索結果に出る文言（SEOプラグインや「抜粋」欄があれば設定）
  タイトル : {page["title"]}
  説明文   : {page["desc"]}

  このファイルは build.py で自動生成しています。直接直さず src/ を直して作り直してください。
  「要確認」で検索すると、事実の確認・追記が必要な箇所が見つかります。
============================================================ -->'''
    return f'''<!-- wp:html -->
{note}
{FONTS}
<style>
{CSS}</style>

<div id="crastore-lp">

{header(page)}

<main>
{body.rstrip()}
</main>

{footer()}

</div>

<script type="application/ld+json">
{jsonld(page)}
</script>

<script>
{JS.rstrip()}
</script>
<!-- /wp:html -->
'''


def to_preview(html, page):
    """本番URLをローカルのプレビューファイル名に置き換える"""
    def rep(m):
        slug = m.group(1)
        return f"{slug or 'index'}.html"
    html = re.sub(r"https://crastore\.xyz/([a-z-]*)/?(?=[\"#])", rep, html)
    return (f'<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{page["title"]}</title>\n<meta name="description" content="{page["desc"]}">\n'
            f'<style>body{{margin:0}}</style>\n</head>\n<body>\n{html}</body>\n</html>\n')


def main():
    DIST.mkdir(exist_ok=True)
    PREVIEW.mkdir(exist_ok=True)
    for page in PAGES:
        html = render(page)
        name = page["slug"] or "home"
        (DIST / f"wp-{name}.html").write_text(html, encoding="utf-8")
        (PREVIEW / f"{page['slug'] or 'index'}.html").write_text(to_preview(html, page), encoding="utf-8")
        print(f"wp-{name}.html  {len(html.encode()):>7,} bytes")


if __name__ == "__main__":
    main()
