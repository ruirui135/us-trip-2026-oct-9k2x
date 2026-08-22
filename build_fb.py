# -*- coding: utf-8 -*-
"""
Googleスプレッドシートの「日程」タブを読んで、行ごとのClaudeコメントを
docs/fb.csv に書き出す。

スプシ側は N1 に次の式を1回入れるだけ：
  =IMPORTDATA("https://ruirui135.github.io/us-trip-2026-oct-9k2x/fb.csv")

■ 設計方針（2026-08-22 改訂）
  コメントを2種類に分ける。
  (A) 計算で出すもの … 時刻・所要をその場で読んで判定する。予定を変えれば自動で変わる。
  (B) 文章で持つもの … 施設の性質・持ち物・予約の注意など、時刻に依存しない知識。
  → 「◯時だと間に合わない」のような“数字の主張”は必ず(A)で作る。
     (B)に数字を書き込むと、予定を変えた時に古いまま残ってしまう。

実行:  uv run python build_fb.py
"""
import io
import os
import re
import sys
import csv
import time
from datetime import datetime, timedelta
from urllib.request import urlopen, Request

sys.stdout.reconfigure(encoding="utf-8")

SHEET_ID = "1WCC-qSCHjM1MfIuk5ZHt-979mI_6RE_x52rmlYYPSyM"
GID = "1404711197"
OUT = os.path.join("docs", "fb.csv")


def fetch_grid():
    # headers=1 は必須。付けないとgvizが見出し行を勝手に判定して、
    # FB列(長文)のせいで複数行を見出しにまとめてしまう
    url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq"
           "?tqx=out:csv&gid=%s&headers=1" % (SHEET_ID, GID))
    last = None
    for attempt in range(4):          # 無人実行なので通信エラーは数回リトライ
        try:
            t = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                        timeout=60).read().decode("utf-8")
            if t.lstrip().startswith("<"):
                raise RuntimeError("スプシを読めません（共有設定を確認）")
            return list(csv.reader(io.StringIO(t)))
        except Exception as e:
            last = e
            if attempt < 3:
                time.sleep(5 * (attempt + 1))
    raise SystemExit("取得に失敗: %s" % last)


# ============================================================
# (A) 時刻・所要を読む道具
# ============================================================
def parse_times(cell):
    """セルから開始・終了を取り出す。
    '13：30～15：30' → (810, 930) / '〜11:00' → (None, 660) / '8:00頃' → (480, None)
    """
    s = (cell or "").replace("\n", "").replace("：", ":").replace("　", "")
    found = re.findall(r"(\d{1,2}):(\d{2})", s)
    vals = [int(h) * 60 + int(m) for h, m in found if int(h) < 24 and int(m) < 60]
    if not vals:
        return (None, None)
    if len(vals) == 1:
        # 「〜11:00」のように終わりだけ書いてある形
        if re.match(r"^\s*[〜～~]", s):
            return (None, vals[0])
        return (vals[0], None)
    return (vals[0], vals[-1])


def parse_duration(cell):
    """'2時間'→120 / '18分'→18 / '約2.5時間'→150 / '5〜7分'→7（長い方で安全側に）"""
    s = (cell or "").replace("約", "").replace("　", "")
    if not s.strip():
        return None
    total, found = 0.0, False
    for a, b in re.findall(r"(\d+(?:\.\d+)?)(?:\s*[〜～~]\s*(\d+(?:\.\d+)?))?\s*時間", s):
        total += float(b or a) * 60
        found = True
    for a, b in re.findall(r"(\d+)(?:\s*[〜～~]\s*(\d+))?\s*分", s):
        total += float(b or a)
        found = True
    return int(total) if found else None


def fmt(x):
    return "%d:%02d" % (x // 60, x % 60)


def timing_notes(rows):
    """日ごとに時刻の辻褄を計算して、行番号→コメントの辞書を返す。
    ここで出す数字は毎回シートから計算するので、予定を変えれば自動で追従する。
    """
    notes = {}
    by_day = {}
    for i, r in enumerate(rows):
        d = r["日付"]
        if d:
            by_day.setdefault(d, []).append(i)

    for d, idxs in by_day.items():
        # その日の「時刻が分かる行」だけを順番に取り出す
        timed = []
        for i in idxs:
            r = rows[i]
            st, en = parse_times(r["時刻"])
            dur = parse_duration(r["所要"])
            if st is None and en is None:
                continue
            # 終わりが書いてなければ 開始＋所要 で見積もる
            end = en if en is not None else (st + dur if (st is not None and dur) else None)
            timed.append((i, st, end, dur))

        for k in range(len(timed) - 1):
            i, st, end, dur = timed[k]
            j, nst, nend, ndur = timed[k + 1]
            if end is None or nst is None:
                continue
            if end > nst:
                gap = end - nst
                notes.setdefault(j, []).append(
                    "⏱ 前の「%s」は%s終了の見込みですが、ここは%s開始になっています（%d分足りません）"
                    % (rows[i]["内容"].replace("\n", " ")[:18], fmt(end), fmt(nst), gap))

        # 1日の拘束時間が長すぎないか（最初の開始〜最後の終わり）
        starts = [t[1] for t in timed if t[1] is not None]
        ends = [t[2] for t in timed if t[2] is not None]
        if starts and ends:
            span = max(ends) - min(starts)
            if span >= 13 * 60:
                notes.setdefault(timed[0][0], []).append(
                    "🕘 この日は%s〜%sで約%d時間半の行動になります。かなりハードなので削る候補を決めておくと安心"
                    % (fmt(min(starts)), fmt(max(ends)), span // 60))
    return notes


# ============================================================
# (B) 時刻に依存しない知識（ここに数字の主張を書かないこと）
# ============================================================
def R(cond, msg, once=False):
    return (cond, msg, once)


RULES = [
    # ===================== 10/8 =====================
    R(lambda d, c, f: d == "10/8" and "仙台" in c and "成田" in c,
      "🚄 成田発の時刻から逆算を。国内線なら乗継2時間以上、新幹線＋成田エクスプレスなら仙台を5〜6時間前に出る計算です。前泊も検討の余地あり"),
    R(lambda d, c, f: d == "10/8" and "ロサンゼルス" in c and "移動" in f.get("区分", ""),
      "✈️ 機内が時差ボケ対策の勝負どころ。LAが夜の時間帯だけ寝て、昼の間は起きておくと着いてから楽です。水をこまめに、酒とカフェインは控えめに"),
    R(lambda d, c, f: d == "10/8" and "入国" in c,
      "🛂 3人とも初めての米国入国なのでスマホのMPCアプリは使えません。APCキオスク（日本語表示あり）か有人窓口＋初回は指紋採取が前提。審査レーンでバラバラになるので、税関を出た到着ロビーで合流と決めておくと安心"),
    R(lambda d, c, f: d == "10/8" and "シャトル" in c,
      "🚌 Economy Parking行きシャトルはターミナル前から出ます。配車専用の「LAX-it」とは別物なので乗り場を間違えないように"),
    R(lambda d, c, f: d == "10/8" and "徒歩" in c and "In-N-Out" in c,
      "🧳 スーツケースを引いての徒歩です。歩道の状況次第では見積もりの倍を見ておくと安全"),
    R(lambda d, c, f: d == "10/8" and "In-N-Out" in c and "食事" in f.get("区分", ""),
      "🧳 ここまで荷物3個を持ったままです。「先にホテルへ置く→身軽に食べに出る」案と、どちらが楽か3人で決めておくと当日迷いません"),
    R(lambda d, c, f: d == "10/8" and "In-N-Out" in c and "食事" in f.get("区分", ""),
      "🍔 初アメリカの定番。「Double-Double」「Animal Style」などが有名。カードで払えます"),
    R(lambda d, c, f: d == "10/8" and "ランディーズ" in c and "ホテル" not in c,
      "🍩 巨大ドーナツの看板が名所。Uberの積み下ろしが増えるので荷物と相談を"),
    R(lambda d, c, f: d == "10/8" and "ランディーズ" in c and "ホテル" in c,
      "💰 空港の外から乗るので空港利用料が乗りません。この判断は正解です"),
    R(lambda d, c, f: d == "10/8" and "チェックイン" in c,
      "💳 カードへデポジット（保証金の一時的な枠取り）がかかります。デビットだと返金に2週間かかることがあるのでクレジットカードで。標準チェックインは15:00、それ以前に着いたらベルデスクに荷物だけ預けられます"),
    R(lambda d, c, f: d == "10/8" and "MOCA" in c,
      "🔎 要確認：MOCAは今は常時無料のはず（「木曜無料」は古い情報かも）。むしろ閉館時刻の方が問題なので、当日の営業時間を見てから行くか決めるのが安全"),
    R(lambda d, c, f: d == "10/8" and "散策" in c,
      "🛒 ラルフズは普通のスーパー、ホールフーズは少し高いがデリ（惣菜量り売り）が便利。初日の夕食はここで買って部屋で食べるのが体力的に楽です"),
    R(lambda d, c, f: d == "10/8" and "夕食" in c and f.get("区分", "") == "食事",
      "🍽 到着日は外食より買って帰る方が無難。初日に無理をすると翌日に効きます"),
    R(lambda d, c, f: d == "10/8" and "就寝" in c,
      "😴 早寝せず現地時間の夜まで起きておくのが時差ボケ対策の定石。早く寝ると明け方に目が覚めて逆に長引きます"),
    R(lambda d, c, f: "ザ・ブロードの予約" in c,
      "🎫 最優先タスク。ブロードは日時指定の事前予約制で、インフィニティミラールームは別枠の整理券が要ります。予約開始日を今すぐ確認してください"),

    # ===================== 10/9 =====================
    R(lambda d, c, f: d == "10/9" and "ホテル出発" in c,
      "🚶 徒歩の判断は正解。DTLAはこの距離なら地下鉄より速いです。ただし朝は人通りの少ない道を避けて大通り沿いで"),
    R(lambda d, c, f: d == "10/9" and "ブラッドベリー" in c,
      "📷 見学できるのは1階ロビーと階段の途中まで（上階はオフィス）。無料ですが営業時間は要確認"),
    R(lambda d, c, f: d == "10/9" and "グランド・セントラル" in c,
      "🍳 8時開店なのはマーケット全体で、個々の店は開店時刻がバラバラです。朝から開いている店を1つ決めておくと確実"),
    R(lambda d, c, f: d == "10/9" and "ザ・ブロードへ移動" in c,
      "🚡 エンジェルス・フライト（短いケーブルカー）は片道1ドル程度の名物。乗るなら運行時間と支払い方法を要確認"),
    R(lambda d, c, f: d == "10/9" and "ザ・ブロード" in c and "移動" not in c,
      "🎫 日時指定の事前予約制です。インフィニティミラールームに入るなら当日の別整理券も要ります"),
    R(lambda d, c, f: "ウォルト・ディズニー・コンサートホール" in c,
      "🏛 ブロードの真向かいなのでこの並びは効率的。外観と公開エリアは無料、中のホールに入るなら公演かツアーが要ります"),
    R(lambda d, c, f: "Last Bookstore" in c,
      "📚 2階の本のトンネルが人気の写真スポット。開店直後が一番空いています"),
    R(lambda d, c, f: d == "10/9" and "Pershing" in c and "Hollywood" in c,
      "🚇 この経路は正しいです（Pershing SquareもHollywood/HighlandもB Line、乗り換えなし）。ただしB Lineは本数が読みにくいので余裕を"),
    R(lambda d, c, f: "チャイニーズシアター" in c,
      "👣 ウォーク・オブ・フェイムは道沿いに延々と続くので、探す星を決めておかないと時間が溶けます。手形・足形は劇場前の中庭で無料、劇場内に入るには別途チケット"),
    R(lambda d, c, f: "Pink" in c,
      "🌭 行列ができる店なので待ち時間を20〜30分見ておくと安全。ここからVermont/Sunset駅へは東へ戻る形になるので、移動時間は地図で確認を"),
    R(lambda d, c, f: "DASH" in f.get("移動手段", "") or ("DASH" in c),
      "🚌 DASH Observatoryバスは本数が限られます。運行時間と最終便を必ず確認してください（帰れなくなると配車も捕まりにくい場所です）"),
    R(lambda d, c, f: "グリフィス天文台" in c and "移動" not in f.get("区分", ""),
      "🌇 開館時刻は曜日で変わります（平日は昼から）。日没前後は展望も駐車場も混雑。夜は冷えるので羽織りものを持って出てください"),
    R(lambda d, c, f: d == "10/9" and "帰り" in c,
      "🌙 天文台からの帰りはバス待ちの行列ができます。最終便の時刻だけは先に調べておくと安心"),

    # ===================== 10/10 =====================
    R(lambda d, c, f: d == "10/10" and not c.strip(),
      "💡 ここが丸1日空いています。10/9が朝から夜まで詰まっているので、行きたい所をこの日に分けると全体が楽になります（3人で相談を）", True),

    # ===================== 10/11 =====================
    R(lambda d, c, f: d == "10/11" and "チェックアウト" in c,
      "🧳 チェックアウト後もベルデスクで荷物を預かってもらえます。午前をDTLAで使うならこの手が有効"),
    R(lambda d, c, f: d == "10/11" and "アナハイム" in c and "移動" in f.get("区分", ""),
      "🚗 手段が未記入です。配車は速いが高め、電車（メトロリンク等）は安いが乗り換えあり。荷物3個なので配車が現実的かも"),
    R(lambda d, c, f: d == "10/11" and "荷物を預け" in c,
      "⚠️ ホテルの標準チェックインとパーク入園の時刻が重なります。荷物だけ預けてパーク直行が現実解。「チェックイン前に預けられるか」をClarionに事前確認しておくと当日慌てません"),
    R(lambda d, c, f: "アドベンチャー" in c and "入園" in c,
      "🎟 OBBチケットは通常の入園券とは別物です。3人分がそれぞれのMyDisneyアカウントに紐づいているか出発前に確認を"),
    R(lambda d, c, f: "Oogie" in c,
      "🎃 トリックオアトリートのルート、ヴィランとの撮影、ショーは全部は回りきれません。優先順位を決めておくのがおすすめ。大人も仮装できますが、14歳以上は顔を覆うマスク不可・引きずる衣装も不可"),
    R(lambda d, c, f: d == "10/11" and "戻る" in c,
      "🌙 終演で人が一斉に出ます。徒歩圏とはいえ夜道なので3人で固まって移動を"),

    # ===================== 10/12 =====================
    R(lambda d, c, f: d == "10/12" and "ディズニーランド" in c and "入園" in c,
      "⚡ 開園時刻が未記入です。Lightning Lane Multi Passは入園直後に1本目を取るのが定石なので、開園時刻は押さえておきたい"),
    R(lambda d, c, f: d == "10/12" and f.get("時間帯", "") == "昼" and "ディズニーランド" in c,
      "🍽 昼食はモバイルオーダー（アプリで事前注文）が並ばずに済みます。使うなら午前のうちに店と時間を押さえておくと楽"),
    R(lambda d, c, f: d == "10/12" and f.get("時間帯", "") == "夜" and not c.strip(),
      "🛍 お土産は閉園間際が最も空きます。翌日はベガスへ長時間移動なので、かさばる物はこの日にまとめて。Downtown Disneyは入園券なしで入れます"),

    # ===================== 10/13 =====================
    R(lambda d, c, f: d == "10/13" and "チェックアウト" in c,
      "📦 バス出発まで時間が空くなら、荷物を預かってもらえるかClarionに要確認"),
    R(lambda d, c, f: d == "10/13" and "ラスベガス" in c and "移動" in f.get("区分", ""),
      "🎫 FlixBus/Greyhoundは早く取るほど安いです（1人$44〜52が目安）。乗り場はアナハイムのARTIC。予約したら便名と出発時刻をこの行に書いてください"),
    R(lambda d, c, f: d == "10/13" and "到着" in c,
      "🚕 ベガス側の降車場所はストリップから離れています。ホテルまで配車が要るので、その分の時間と料金を見ておいてください"),
    R(lambda d, c, f: d == "10/13" and "Excalibur" in c and "チェックイン" in c,
      "💳 リゾートフィー（1泊50ドル前後）とデポジットが部屋代とは別にかかります。予算に入れておいてください"),
    R(lambda d, c, f: d == "10/13" and f.get("時間帯", "") in ("夕方", "夜") and not c.strip(),
      "🎰 ベガス観光はこの日が本番です。火曜なのでモール系は早めに閉まります。買い物は明るいうちに、夜はショー・夜景・カジノ系に寄せるのが定石。カジノは21歳以上＋パスポート現物が必須（コピー・スマホ画像は不可）"),
    R(lambda d, c, f: d == "10/13" and "就寝" in c,
      "😴 翌朝はツアーの早朝送迎です。逆算するとかなり早い就寝になるので、ベガスの夜は割り切りを"),

    # ===================== 10/14 =====================
    R(lambda d, c, f: d == "10/14" and "ピックアップ" in c,
      "🎫 ツアーが未予約です。ウエストリムの日帰りバスは早期に埋まります。表示価格に入場料と燃料費（約20ドル/人）が別途乗ることが多いので総額で比較を"),
    R(lambda d, c, f: d == "10/14" and "ピックアップ" in c,
      "🧥 グランドキャニオンは標高が高く10月の朝は氷点下近くまで下がります。防寒着・手袋・ニット帽を前夜に用意しておいてください"),
    R(lambda d, c, f: d == "10/14" and "グランドキャニオン" in c and "移動" in f.get("区分", ""),
      "🚐 この所要はウエストリム前提の数字です。サウスリムに変えると片道4.5〜5時間になり日帰りはかなり厳しくなります"),
    R(lambda d, c, f: d == "10/14" and "滞在" in c,
      "📸 見どころを事前に絞っておくと限られた滞在が有効に使えます。スカイウォークは橋の上にカメラ・バッグを持ち込めない（携帯のみ）ので注意"),
    R(lambda d, c, f: d == "10/14" and f.get("時間帯", "") == "夜" and not c.strip(),
      "🎰 ここが判断ポイント。長時間ツアーの後なので、体力次第では素直に寝る方が翌日の移動が楽です"),
    R(lambda d, c, f: d == "10/14" and "就寝" in c,
      "🔴 翌朝が早朝発です。カジノをやるなら切り上げ時刻を先に決めて、荷造りも前夜に済ませておいてください"),

    # ===================== 10/15 =====================
    R(lambda d, c, f: d == "10/15" and "チェックアウト" in c,
      "🕒 深夜〜早朝のチェックアウトになるので、前夜にフロントへ伝えておくとスムーズです"),
    R(lambda d, c, f: d == "10/15" and "空港" in c and "移動" in f.get("区分", ""),
      "🚕 深夜〜早朝は配車が捕まりにくいことがあります。ホテルのタクシー乗り場も選択肢に入れておいてください"),
    R(lambda d, c, f: d == "10/15" and ("LAS発" in c or "搭乗" in c),
      "🧴 液体のお土産を預け荷物に入れる最後のチャンスがこのチェックインです。乗継中には荷物を開けられません"),
    R(lambda d, c, f: d == "10/15" and "乗継" in c,
      "🧳 荷物は成田まで通し預けの見込み。出発地のカウンターで「行き先はNRTか」を口頭確認＋タグを目視確認してください"),
    R(lambda d, c, f: d == "10/15" and "乗継" in c,
      "🚶 United国内線はLAXのT7/T8着、成田行きはTBIT発。保安検査のやり直しは不要ですが徒歩でそこそこ距離があります"),
    R(lambda d, c, f: d == "10/15" and "機内" in c,
      "😴 帰りは体内時計を早める向きで一番きつい方向です。機内で寝ておくと帰国後が楽。モバイルバッテリーは機内で使用禁止なので空港で充電を"),

    # ===================== 10/16 =====================
    R(lambda d, c, f: d == "10/16" and "成田" in c and "移動" not in f.get("区分", ""),
      "📱 Visit Japan Webは「入国」と「税関」の両方を登録しないとQRが無効になります。3人とも出発前に済ませておいてください"),
    R(lambda d, c, f: d == "10/16" and "成田" in c,
      "🥩 肉・肉エキス入りの食品は日本に持ち込めません（ジャーキー、レトルト等）。お土産を買う時点で気をつけて"),
    R(lambda d, c, f: d == "10/16" and "仙台" in c,
      "🚄 成田着＋入国審査で夕方以降になります。仙台着は夜遅くなるので、翌日の予定は空けておいた方が無難"),
]


def generic_checks(d, c, f):
    out = []
    if d and not c.strip():
        out.append("⬜ ここがまだ空です")
    if f.get("区分", "") == "移動" and c.strip() and not f.get("移動手段", "").strip():
        out.append("🚕 移動手段が未記入です")
    return out


def build_fb(grid):
    header = [h.strip() for h in grid[0]]
    idx = {h: i for i, h in enumerate(header) if h}
    keys = ("日付", "時間帯", "時刻", "区分", "内容", "場所", "移動手段", "所要", "予約状況", "メモ")

    rows = []
    for row in grid[1:]:
        rec = {}
        for k in keys:
            i = idx.get(k)
            rec[k] = (row[i].strip() if i is not None and i < len(row) else "")
        rows.append(rec)

    tnotes = timing_notes(rows)          # ← (A) 計算で出すコメント

    out = ["__HEADER__"]
    prev_day, used_once = None, set()

    for i, r in enumerate(rows):
        d, c = r["日付"], r["内容"]
        notes = []

        if d and d != prev_day:
            used_once = set()

        # (B) 知識コメント
        for cond, msg, once in RULES:
            try:
                if not cond(d, c, r):
                    continue
            except Exception:
                continue
            if once:
                if msg in used_once:
                    continue
                used_once.add(msg)
            if msg not in notes:
                notes.append(msg)

        # (A) 計算コメント（時刻の辻褄）は常に最優先で先頭へ
        notes = tnotes.get(i, []) + notes

        # 予約の★
        book = r["予約状況"]
        if "★" in book:
            notes.append("🎫 予約・確認がまだです（%s）" % book.replace("★", ""))

        # 空欄など
        if not notes:
            notes.extend(generic_checks(d, c, r))

        if d:
            prev_day = d
        out.append("　／　".join(notes))

    return out


STAMP_RE = re.compile(r"(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})")


def read_existing():
    """今あるCSVの本文と、ヘッダに書かれた最終更新時刻を返す"""
    if not os.path.exists(OUT):
        return None, None
    try:
        rows = list(csv.reader(io.open(OUT, encoding="utf-8")))
    except Exception:
        return None, None
    if not rows:
        return None, None
    head = rows[0][0] if rows[0] else ""
    body = [r[0] if r else "" for r in rows[1:]]
    m = STAMP_RE.search(head)
    stamp = None
    if m:
        mo, da, hh, mi = (int(x) for x in m.groups())
        try:
            stamp = datetime.now().replace(month=mo, day=da, hour=hh,
                                           minute=mi, second=0, microsecond=0)
        except ValueError:
            stamp = None
    return body, stamp


def main():
    grid = fetch_grid()
    col = build_fb(grid)
    now = datetime.now()
    body = col[1:]

    old_body, old_stamp = read_existing()
    fresh = old_stamp is not None and timedelta(0) <= (now - old_stamp) < timedelta(hours=6)
    if body == old_body and fresh:
        # 中身も同じ・鮮度印も新しい → 触らない（無駄なpushを避ける）
        print("変更なし（%d行 / 最終更新 %s）" % (len(col), old_stamp.strftime("%m/%d %H:%M")))
        return

    col[0] = "🤖 ClaudeFB（自動更新 %d/%d %s 時点）" % (
        now.month, now.day, now.strftime("%H:%M"))

    os.makedirs("docs", exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for line in col:
            w.writerow([line])

    n = sum(1 for x in body if x.strip())
    print("%s  行数=%d / コメントあり=%d  (%s)" % (
        OUT, len(col), n, now.strftime("%H:%M")))
if __name__ == "__main__":
    main()
