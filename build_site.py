# -*- coding: utf-8 -*-
"""
アメリカ旅行しおりの「再成形」エンジン（これ1本で完結）。

やること:
  1) データ取得：Googleスプレッドシート(gviz CSV) か、未接続ならローカルのテンプレ.xlsx
  2) 「日程」「未決事項」「ガイド(_research.json)」のHTMLを生成
  3) _index_body.html / _howto_body.html に流し込み、共通デザイン(template.html)で包んで
     docs/index.html・docs/how-to.html を出力（最終更新日も自動で刻印）

再成形コマンド:
  uv run --with openpyxl python build_site.py

★スプシ接続（岡崎さんがスプシ作成後にここを埋める）★
  下の SHEET_ID と GID_DAYS / GID_TODO を入れると、自動でスプシ(gviz CSV)から読みます。
  空のままなら、同フォルダの 旅行データ_テンプレート.xlsx をデータ源にします。
"""
import io, csv, json, sys, re
from datetime import date
from urllib.parse import quote
from urllib.request import urlopen, Request

# ===== ここを設定（スプシ接続） =====
# スプシを正データにするときは、URLの /d/ と /edit の間のIDをここに貼るだけ。
# タブ名「日程」「未決事項」で読みに行くので、タブ名は変えないこと（gidは不要）。
# 空のままなら、同フォルダの 旅行データ_テンプレート.xlsx をデータ源にする。
SHEET_ID = ""
# ====================================

TEMPLATE = r"C:\Users\komug\OneDrive\Claude\0606‗HTMLでmyvaultを出力する\design-system\template.html"
XLSX = "旅行データ_テンプレート.xlsx"

# ---------- データ取得（dictのリストで返す：見出し名→値） ----------
def rows_from_gviz(sheet_name):
    url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq"
           "?tqx=out:csv&sheet=%s&headers=1") % (SHEET_ID, quote(sheet_name))
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    text = urlopen(req, timeout=30).read().decode("utf-8")
    if text.lstrip().startswith("<"):
        raise SystemExit("スプシを読めません（共有設定/タブ名を確認）。返ってきたのがHTMLでした。")
    reader = list(csv.reader(io.StringIO(text)))
    return rows_to_dicts(reader)

def rows_from_xlsx(sheet_name):
    from openpyxl import load_workbook
    wb = load_workbook(XLSX, data_only=True)
    ws = wb[sheet_name]
    grid = [[("" if c is None else str(c)) for c in row]
            for row in ws.iter_rows(values_only=True)]
    return rows_to_dicts(grid)

def rows_to_dicts(grid):
    if not grid:
        return []
    headers = [h.strip() for h in grid[0]]
    out = []
    for r in grid[1:]:
        if not any((c or "").strip() for c in r):
            continue  # 空行スキップ
        d = {}
        for i, h in enumerate(headers):
            d[h] = (r[i] if i < len(r) else "") or ""
        out.append(d)
    return out

def load(kind):
    """kind: 'days' or 'todo' """
    name = "日程" if kind == "days" else "未決事項"
    if SHEET_ID:
        return rows_from_gviz(name)
    return rows_from_xlsx(name)

# ---------- 共通 ----------
def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---------- 日程（日付ごとに縦タイムライン .vtl） ----------
KW_EMOJI = [  # 内容に含まれる語 → 絵文字（上から優先）
    ("就寝", "😴"), ("寝る", "😴"),
    ("カジノ", "🎰"),
    ("ディズニー", "🎢"), ("アドベンチャー", "🎢"), ("ランド", "🎢"),
    ("グランドキャニオン", "🏜️"),
    ("買い物", "🛒"), ("スーパー", "🛒"),
    ("フリー", "🆓"),
    ("飛行機", "✈️"), ("搭乗", "✈️"),
    ("チェックイン", "🏨"), ("ホテル", "🏨"),
    ("入国", "🛂"), ("税関", "🛂"),
]
KU_EMOJI = {"手続き": "🛂", "移動": "🚗", "観光": "📸", "宿": "🏨", "食事": "🍽️"}

def event_emoji(ku, naiyou):
    for kw, e in KW_EMOJI:
        if kw in naiyou:
            return e
    return KU_EMOJI.get(ku, "•")

def render_days(rows):
    # 日付順（出現順）にグループ化
    order, groups = [], {}
    for r in rows:
        d = r.get("日付", "").strip() or "（日付未定）"
        if d not in groups:
            groups[d] = []
            order.append(d)
        groups[d].append(r)
    out = []
    for i, d in enumerate(order, start=1):
        out.append('<h3>%s <span class="daymark">Day %d</span></h3>' % (esc(d), i))
        out.append('<ul class="vtl">')
        for r in groups[d]:
            t = esc(r.get("時刻", "").strip() or "—")
            ku = r.get("区分", "").strip()
            naiyou = r.get("内容", "").strip()
            emo = event_emoji(ku, naiyou)
            memo_html = ""
            yoyaku = r.get("予約状況", "").strip()
            memo = r.get("メモ", "").strip()
            if memo:
                cls = "memo todo" if "★" in memo else "memo"
                memo_html += '<span class="%s">%s</span>' % (cls, esc(memo))
            if yoyaku and "★" in yoyaku:
                memo_html += '<span class="memo todo">★ 予約: %s</span>' % esc(yoyaku)
            link = r.get("リンク", "").strip()
            link_html = ('<span class="evlink memo">🔗 <a href="%s" target="_blank" rel="noopener">リンク</a></span>'
                         % esc(link)) if link.startswith("http") else ""
            out.append('  <li><span class="t">%s</span><span class="ev">%s %s%s%s</span></li>'
                       % (t, emo, esc(naiyou), memo_html, link_html))
        out.append('</ul>')
    return "\n".join(out)

# ---------- 未決事項（表＋状態ピル） ----------
def status_pill(s):
    s = (s or "").strip()
    if "決定" in s:
        cls, txt = "success", s or "決定"
    elif "相談" in s:
        cls, txt = "", s or "相談中"
    elif "出発前" in s or "必須" in s:
        cls, txt = "failed", s or "出発前必須"
    else:
        cls, txt = "pending", s or "未着手"
    return '<span class="pill %s"><span class="dot"></span>%s</span>' % (cls, esc(txt))

def render_todo(rows):
    out = ['<div class="table-wrap"><table>',
           '<thead><tr><th>項目</th><th>状態</th><th>担当</th><th>メモ</th></tr></thead><tbody>']
    for r in rows:
        item = esc(r.get("項目", "").strip())
        tan = esc(r.get("担当", "").strip() or "—")
        memo = r.get("メモ", "").strip()
        kettei = r.get("決定内容", "").strip()
        kigen = r.get("期限", "").strip()
        parts = []
        if kigen:
            parts.append('<strong style="color:var(--danger)">⏰ 期限: %s</strong>' % esc(kigen))
        if memo:
            parts.append(esc(memo))
        if kettei:
            parts.append('<strong>→ 決定: %s</strong>' % esc(kettei))
        memo_full = '　'.join(parts)
        out.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (item, status_pill(r.get("状態", "")), tan, memo_full))
    out.append('</tbody></table></div>')
    return "\n".join(out)

# ---------- ガイド（_research.json から） ----------
GUIDE_EMOJI = {
    "荷物・スーツケース・洗濯": "🧳", "両替・現金・チップ": "💵",
    "支払い：カードのブランド（アメックスのみ問題ない？）": "💳",
    "カメラ・充電・電圧プラグ": "📷", "ホテルの作法": "🏨",
    "服装・10月の気候": "🧥", "時差ボケ": "😴", "通信（スマホ/ネット）": "📶",
    "空港の段取り（到着LAX・帰国LAS→LAX→成田）": "🛫",
    "アナハイム→ラスベガスの移動手段": "🚌",
    "ラスベガス→グランドキャニオンの行き方": "🏜️",
    "ディズニー（OBB・チケット・お土産・荷物）": "🎢",
    "ラスベガスのカジノ基礎": "🎰",
}
def host(u):
    try:
        from urllib.parse import urlparse
        h = urlparse(u).netloc
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return u

def teaser(summary, n=44):
    s = re.split(r'[。\n]', (summary or "").strip())[0].strip()
    return (s[:n] + "…") if len(s) > n else s

def _inline_numbered(text):
    parts = re.split(r'(?=[\(（]\s*\d+\s*[\)）])', text)
    lead = parts[0].strip()
    items = [re.sub(r'^[\(（]\s*\d+\s*[\)）]\s*', '', p).strip() for p in parts[1:] if p.strip()]
    return lead, items

def format_detail(text):
    """本文を読みやすく：行頭の『・』『(1)』を箇条書き(<ul>)に、それ以外は段落に。
    語中の『・』(例: FlixBus・Greyhound)は行頭でないので分割しない。"""
    text = (text or "").strip()
    if not text:
        return ''
    # 改行が無く、文中に (1)(2)… がある旧データ → その場で箇条書き化
    if '\n' not in text and re.search(r'[\(（]\s*1\s*[\)）]', text):
        lead, items = _inline_numbered(text)
        h = ('<p>%s</p>' % esc(lead)) if lead else ''
        if items:
            h += '<ul>' + ''.join('<li>%s</li>' % esc(i) for i in items) + '</ul>'
        return h
    # 行単位：行頭が『・/･』または『(n)』なら箇条書き、それ以外は段落
    out, ul = [], []
    def flush_ul():
        if ul:
            out.append('<ul>' + ''.join('<li>%s</li>' % esc(x) for x in ul) + '</ul>')
            ul.clear()
    for raw in text.split('\n'):
        l = raw.strip()
        if not l:
            continue
        m = re.match(r'^[・･]\s*(.*)$', l) or re.match(r'^[\(（]\s*\d+\s*[\)）]\s*(.*)$', l)
        if m:
            ul.append(m.group(1).strip())
        else:
            flush_ul()
            out.append('<p>%s</p>' % esc(l))
    flush_ul()
    return ''.join(out) if out else ('<p>%s</p>' % esc(text))

def render_topics(topics, note_label='⚠️ 予約・購入・出発前に各自確認'):
    out = []
    for t in topics:
        emo = GUIDE_EMOJI.get(t["topic"], "📌")
        tz = teaser(t.get("summary", ""))
        out.append('<details><summary>%s %s%s</summary><div class="details-body">'
                   % (emo, esc(t["topic"]), (' — <span class="muted">%s</span>' % esc(tz)) if tz else ''))
        out.append('<div class="callout tldr"><span class="ico">📝</span><div class="body">'
                   '<div class="label">まとめ</div><p>%s</p></div></div>' % esc(t["summary"]))
        for p in t["points"]:
            out.append('<h4>%s</h4>' % esc(p["heading"]))
            out.append(format_detail(p["detail"]))
            srcs = p.get("sources") or []
            if srcs:
                links = "・".join('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(u), esc(host(u))) for u in srcs)
                out.append('<p class="src">📚 出典: %s</p>' % links)
        dec = t.get("decisions") or []
        if dec:
            out.append('<div class="callout warn"><span class="ico">🤝</span><div class="body">'
                       '<div class="label">3人で決めること</div><ul style="margin:.2em 0 0">')
            for d in dec:
                out.append('<li>%s</li>' % esc(d))
            out.append('</ul></div></div>')
        cav = t.get("caveats") or []
        if cav:
            out.append('<div class="note"><span class="note-label">%s</span><ul>' % note_label)
            for c in cav:
                out.append('<li>%s</li>' % esc(c))
            out.append('</ul></div>')
        out.append('</div></details>')
    return "\n".join(out)

def render_guide():
    try:
        with io.open("_research.json", encoding="utf-8") as f:
            topics = json.load(f)
    except FileNotFoundError:
        return '<p class="muted">（ガイドは次回の再成形で生成されます）</p>'
    return render_topics(topics)

def render_proposals():
    try:
        with io.open("_proposals.json", encoding="utf-8") as f:
            topics = json.load(f)
    except FileNotFoundError:
        return '<p class="muted">（★段取りの提案は次回の相談で追記されます）</p>'
    return render_topics(topics, note_label='⚠️ 予約・確定前に各自確認')

# ---------- 共通デザインで包む ----------
def wrap(body, title):
    with io.open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    import re
    head = tpl[:tpl.index("</head>") + len("</head>")]
    tail = tpl[tpl.index("<!-- ===== EFFECTIVE-JS:START"):]
    head = re.sub(r"<title>.*?</title>", "<title>%s</title>" % title, head, count=1, flags=re.S)
    return head + "\n" + body.strip() + "\n\n" + tail

def build_index():
    with io.open("_index_body.html", encoding="utf-8") as f:
        body = f.read()
    body = body.replace("<!-- DAYS_SECTION -->", render_days(load("days")))
    body = body.replace("<!-- TODO_SECTION -->", render_todo(load("todo")))
    body = body.replace("<!-- PROPOSALS_SECTION -->", render_proposals())
    body = body.replace("<!-- GUIDE_SECTION -->", render_guide())
    body = body.replace("{{UPDATED}}", date.today().strftime("%Y/%m/%d"))
    body = body.replace("瑠威さん", "岡崎さん")  # 共有サイトでは本人呼称を統一
    html = wrap(body, "アメリカ旅行しおり 2026.10")
    with io.open("docs/index.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

def build_howto():
    with io.open("_howto_body.html", encoding="utf-8") as f:
        body = f.read()
    html = wrap(body, "つかいかた｜アメリカ旅行しおり")
    with io.open("docs/how-to.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

if __name__ == "__main__":
    src = "Googleスプレッドシート(gviz)" if SHEET_ID else ("ローカル: " + XLSX)
    build_index()
    build_howto()
    print("再成形完了 / データ源:", src, "/ 更新日:", date.today().strftime("%Y/%m/%d"))
