# -*- coding: utf-8 -*-
"""
Googleスプレッドシートの「日程」タブを読んで、行ごとのClaudeコメントを
docs/fb.csv に書き出す。

スプシ側は N1 に次の式を1回入れるだけ：
  =IMPORTDATA("https://ruirui135.github.io/us-trip-2026-oct-9k2x/fb.csv")

Googleが定期的に読みに来るので、このCSVを更新すると列が自動で書き変わる。

実行:  uv run python build_fb.py
"""
import io
import os
import re
import sys
import csv
from datetime import datetime
from urllib.request import urlopen, Request

sys.stdout.reconfigure(encoding="utf-8")

SHEET_ID = "1WCC-qSCHjM1MfIuk5ZHt-979mI_6RE_x52rmlYYPSyM"
GID = "1404711197"
OUT = os.path.join("docs", "fb.csv")


def fetch_grid():
    url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq"
           "?tqx=out:csv&gid=%s" % (SHEET_ID, GID))
    t = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read().decode("utf-8")
    if t.lstrip().startswith("<"):
        raise SystemExit("スプシを読めません（共有設定を確認）")
    return list(csv.reader(io.StringIO(t)))


def parse_time(s):
    if not s:
        return None
    m = re.search(r"(\d{1,2})\s*[:：]\s*(\d{2})", str(s))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return h * 60 + mi if h < 24 and mi < 60 else None


def fmt(x):
    return "%d:%02d" % (x // 60, x % 60)


# ---- 内容に応じた「読んで効く」コメント（キーワード → コメント）----
# 前の行から順に見て、最初に当たったものを使う
RULES = [
    # 10/8
    (lambda d, c, r: d == "10/8" and "In-N-Out" in c and "食事" in r.get("区分", ""),
     "🧳 ここまでスーツケース3個を持ったままです。先にホテルへ寄って置いてから食べに出る案も検討を（遠回りにはなります）"),
    (lambda d, c, r: d == "10/8" and "ランディーズ" in c and "移動" not in c,
     "🧳 荷物を持ったままドーナツ店へ。Uber2回の積み下ろしが発生します"),
    (lambda d, c, r: d == "10/8" and "MOCA" in c,
     "🔎 MOCAは今は常時無料のはず（「木曜無料」は古い情報かも）。それより閉館時刻の方が問題。木曜20時までなら16:30チェックイン後でも間に合います。要確認"),
    (lambda d, c, r: d == "10/8" and "入国" in c,
     "⏱ 入国に2時間かかると14:30出発になります。以降が全部30分ズレる前提で"),
    (lambda d, c, r: d == "10/8" and "就寝" in c,
     "😴 時差ボケ対策としてこの時刻は正解。早寝すると明け方に目が覚めて逆効果です"),
    (lambda d, c, r: "ザ・ブロードの予約" in c,
     "🎫 最優先タスク。ブロードは日時指定の事前予約制＋インフィニティミラールームは別枠。予約開始日を今すぐ確認を"),

    # 10/9
    (lambda d, c, r: d == "10/9" and "ホテルで朝食" in c or (d == "10/9" and "朝食" in c),
     "💰 $25クレジットが余ります（施設利用料の見返りなので使わないと損）。10/8の夜か10/10の朝に回すのがおすすめ"),
    (lambda d, c, r: d == "10/9" and "ザ・ブロード" in c and "移動" not in c,
     "🎫 要事前予約。13:00開始だとここが1日の折り返しになります"),
    (lambda d, c, r: d == "10/9" and "Grand Avenue Arts" in c,
     "🚇 要確認：この駅はA/E Line。Hollywood/HighlandはB Lineなので7th St/Metro Centerでの乗り換えが要るかも。所要が想定より延びる可能性"),
    (lambda d, c, r: d == "10/9" and "チャイニーズシアター" in c,
     "🔴 「〜15:00」は成立しません。ブロード13:00→14:00、コンサートホール→14:30、地下鉄で15:10着。ここから1時間ほど全部後ろにズレます"),
    (lambda d, c, r: d == "10/9" and "Pink" in c,
     "🔁 Pink'sは西側、次のVermont/Sunset駅は東側で逆走になります。順番を入れ替えるか、どちらか削るか要検討"),
    (lambda d, c, r: d == "10/9" and "グリフィス天文台" in c and "移動" not in c,
     "🌇 金曜は12:00開館・22:00閉館。日没は18:30頃で夕景狙いなら混みます。帰りのバスも並ぶので、ここは2時間見ておくと安全"),
    (lambda d, c, r: d == "10/9" and "帰り" in c,
     "🕘 ここまで来ると帰着は21:30頃。朝8時発なので13時間半行動です。時差ボケ2日目としてはかなりハード"),
    (lambda d, c, r: "ウォルト・ディズニー・コンサートホール" in c,
     "📅 日付が空欄のままです。10/9に入れてください（ブロードの隣なので流れは完璧）"),

    # 10/10
    (lambda d, c, r: d == "10/10" and not c.strip(),
     "💡 提案：10/9のハリウッド＋グリフィス天文台をこの日に移すと両日とも楽になります。土曜は天文台が10:00開館なので、実はこちらの方が都合がいいです"),
    (lambda d, c, r: d == "10/10" and "朝食" in c,
     "💰 10/9で使わなかった$25クレジットをここで使うのはどうですか"),

    # 10/11
    (lambda d, c, r: d == "10/11" and "荷物を預ける" in c,
     "⚠️ チェックイン標準15:00とDCA早入り15:00が正面衝突。荷物だけ預けてパーク直行が現実解です"),
    (lambda d, c, r: d == "10/11" and "Oogie" in c,
     "🎃 23:00終了。翌日もディズニーなので、この夜は寄り道せず真っ直ぐ帰るのが無難"),

    # 10/12
    (lambda d, c, r: d == "10/12" and "入園" in c,
     "🕐 開園時刻が未確認のままです。Lightning Laneは入園直後に1本目を取るのがコツなので、開園時刻は押さえておきたい"),
    (lambda d, c, r: d == "10/12" and "お土産" in c,
     "🛍 閉園間際が最も空きます。かさばる物はこの日に買うと、翌日の移動が楽（ベガスへ6時間バスなので）"),

    # 10/13
    (lambda d, c, r: d == "10/13" and "ラスベガス" in c and "移動" in r.get("区分", ""),
     "🔴 最重要：11時チェックアウト→6時間だと17時着で、ベガスがほぼ潰れます。朝8時台に出れば14時着で午後〜夜がまるまる使えます。前夜にチェックアウト手続きを済ませておくのが手"),
    (lambda d, c, r: d == "10/13" and "Excalibur" in c and "チェックイン" in c,
     "💳 リゾートフィー約51ドル/泊＋デポジットがカードに一時的にかかります。デビットではなくクレジットカードで"),
    (lambda d, c, r: d == "10/13" and "就寝" in c,
     "😴 翌朝5:00〜5:30に送迎。逆算すると4時起きなので、22時就寝でも睡眠6時間です"),

    # 10/14
    (lambda d, c, r: d == "10/14" and "ピックアップ" in c,
     "🎫 ツアーがまだ未予約です。ウエストリム日帰りバスは早期に埋まります。防寒着も忘れずに（朝は氷点下近く）"),
    (lambda d, c, r: d == "10/14" and "帰着" in c,
     "⏱ 帰着16〜17時。翌朝3時ホテル発なので、ここから使えるのは実質5〜6時間です"),
    (lambda d, c, r: d == "10/14" and "就寝" in c,
     "🔴 翌3時ホテル発。カジノをやるなら22時には切り上げて仮眠4時間、が限界ラインです"),

    # 10/15
    (lambda d, c, r: d == "10/15" and ("LAS発" in c or "搭乗" in c),
     "🔴 便名と正確な時刻が未確定。ここが決まらないと10/14の夜が決められません。最優先で確認を"),
    (lambda d, c, r: d == "10/15" and "チェックアウト" in c,
     "🕒 6:00発なら空港着3:30、ホテル発3:00が目安です"),
    (lambda d, c, r: d == "10/15" and "LAX" in c and "乗継" in c,
     "🧳 荷物は成田まで通し預けの見込み。当日タグの行き先がNRTになっているか目視確認を"),

    # 10/16
    (lambda d, c, r: d == "10/16" and "成田" in c and "着" in c,
     "📱 Visit Japan Webは入国と税関の両方を登録しないとQRが無効になります"),
]


def build_fb(grid):
    header = [h.strip() for h in grid[0]]
    idx = {h: i for i, h in enumerate(header) if h}

    def g(row, name):
        i = idx.get(name)
        return (row[i].strip() if i is not None and i < len(row) else "")

    out = ["🤖 ClaudeFB（自動更新）"]
    prev_time = None
    prev_day = None
    used = set()          # 同じ日に同じコメントを繰り返さない

    for row in grid[1:]:
        d = g(row, "日付")
        c = g(row, "内容")
        notes = []

        if d and d != prev_day:
            prev_time = None
            used = set()   # 日が変わったらリセット

        # 内容にひもづくコメント（1日1回だけ）
        for cond, msg in RULES:
            try:
                if cond(d, c, {"区分": g(row, "区分")}):
                    if msg not in used:
                        notes.append(msg)
                        used.add(msg)
                    break
            except Exception:
                pass

        # 未記入の枠
        if d and not c.strip():
            if not notes:
                notes.append("⬜ ここがまだ空です")

        # 時刻の逆行
        t = parse_time(g(row, "時刻"))
        if t is not None and prev_time is not None and t < prev_time and t >= 5 * 60:
            notes.append("⚠️ 前の予定（%s）より時刻が戻っています" % fmt(prev_time))
        if t is not None:
            prev_time = t

        prev_day = d if d else prev_day
        prev_content = c
        out.append("　".join(notes))

    return out


def main():
    grid = fetch_grid()
    col = build_fb(grid)
    os.makedirs("docs", exist_ok=True)
    # Googleスプレッドシートが読むので UTF-8（BOMなし）
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for line in col:
            w.writerow([line])
    n = sum(1 for x in col[1:] if x.strip())
    print("%s  行数=%d / コメントあり=%d  (%s)" % (
        OUT, len(col), n, datetime.now().strftime("%H:%M")))


if __name__ == "__main__":
    main()
