# -*- coding: utf-8 -*-
"""
Googleスプレッドシートの「日程」タブを読んで、行ごとのClaudeコメントを
docs/fb.csv に書き出す。

スプシ側は N1 に次の式を1回入れるだけ：
  =IMPORTDATA("https://ruirui135.github.io/us-trip-2026-oct-9k2x/fb.csv")

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
    # headers=1 は必須。付けないとgvizが見出し行を勝手に判定して、
    # FB列(長文)のせいで複数行を見出しにまとめてしまう
    url = ("https://docs.google.com/spreadsheets/d/%s/gviz/tq"
           "?tqx=out:csv&gid=%s&headers=1" % (SHEET_ID, GID))
    import time
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


# ============================================================
# ルール定義
#   (判定関数, コメント, 1日1回だけか)
#   判定関数の引数: d=日付 / c=内容 / f=その行の全項目(dict)
# ============================================================
def R(cond, msg, once=False):
    return (cond, msg, once)


RULES = [
    # ===================== 10/8（到着日） =====================
    R(lambda d, c, f: d == "10/8" and "仙台" in c and "成田" in c,
      "🚄 成田発の時刻から逆算を。国内線なら乗継2時間以上、新幹線＋成田エクスプレスなら仙台を5〜6時間前に出る計算です。前泊も検討の余地あり"),
    R(lambda d, c, f: d == "10/8" and "成田 → ロサンゼルス" in c,
      "✈️ 機内が時差ボケ対策の勝負どころ。LAが夜の時間帯だけ寝て、LAが昼の間は起きておくと着いてから楽です。水をこまめに、酒とカフェインは控えめに"),
    R(lambda d, c, f: d == "10/8" and "入国" in c,
      "⏱ 12:30着でも外に出るのは14:00〜14:30。入国が2時間かかると以降が全部30分ズレます。3人は審査レーンでバラバラになるので、税関を出た到着ロビーで合流と決めておくと安心"),
    R(lambda d, c, f: d == "10/8" and "入国" in c,
      "🛂 3人とも初めての米国入国なのでスマホのMPCアプリは使えません。APCキオスク（日本語表示あり）か有人窓口＋初回は指紋採取、が前提です"),
    R(lambda d, c, f: d == "10/8" and "シャトル" in c,
      "🚌 Economy Parking行きシャトルはターミナル前から出ます。配車専用の「LAX-it」とは別物なので、乗り場を間違えないように"),
    R(lambda d, c, f: d == "10/8" and "徒歩" in c and "In-N-Out" in c,
      "🧳 スーツケースを引いての徒歩5〜7分です。歩道の状況次第では15分見た方が安全"),
    R(lambda d, c, f: d == "10/8" and "In-N-Out" in c and "食事" in f.get("区分", ""),
      "🧳 ここまで荷物3個を持ったままです。「先にホテルへ置く→身軽に食べに出る」案と、どちらが楽か3人で決めておくと当日迷いません"),
    R(lambda d, c, f: d == "10/8" and "In-N-Out" in c and "食事" in f.get("区分", ""),
      "🍔 初アメリカの定番。注文は「Double-Double」「Animal Style」などが有名。現金不要でカード可"),
    R(lambda d, c, f: d == "10/8" and "ランディーズ" in c and "移動" not in c,
      "🍩 巨大ドーナツの看板が名所。Uberの積み下ろしが2回増えるので、荷物と相談を"),
    R(lambda d, c, f: d == "10/8" and "ランディーズ" in c and "ホテル" in c,
      "💰 空港の外から乗るので空港利用料が乗りません。この判断は正解です"),
    R(lambda d, c, f: d == "10/8" and "チェックイン" in c,
      "💳 チェックイン時にカードへデポジット（保証金の一時的な枠取り）が約100ドル/泊かかります。デビットだと返金に2週間かかることがあるのでクレジットカードで"),
    R(lambda d, c, f: d == "10/8" and "チェックイン" in c,
      "🕒 標準チェックインは15:00。16:00なら問題なく入れます。もし早く着いたらベルデスクに荷物だけ預けられます"),
    R(lambda d, c, f: d == "10/8" and "MOCA" in c,
      "🔎 要確認：MOCAは今は常時無料のはず（「木曜無料」は古い情報かも）。むしろ閉館時刻が問題で、木曜20時までなら16:30チェックイン後でも間に合います"),
    R(lambda d, c, f: d == "10/8" and "散策" in c,
      "🛒 ラルフズは一般的なスーパー、ホールフーズは少し高いがデリ（惣菜量り売り）が便利。初日の夕食はここで買って部屋で食べるのが体力的に楽です"),
    R(lambda d, c, f: d == "10/8" and "夕食" in c and f.get("区分", "") == "食事",
      "🍽 到着日は外食より買って帰る方が無難。iHopは深夜までやっている店が多いですが、初日は無理しない方が翌日効きます"),
    R(lambda d, c, f: d == "10/8" and "就寝" in c,
      "😴 この時刻は正解です。早寝すると明け方3〜4時に目が覚めて逆に長引きます。眠くても現地22時までは粘るのが定石"),
    R(lambda d, c, f: "ザ・ブロードの予約" in c,
      "🎫 最優先タスク。ブロードは日時指定の事前予約制で、インフィニティミラールームは別枠の整理券が要ります。予約開始日を今すぐ確認して、10/9の13:00枠を押さえてください"),

    # ===================== 10/9 =====================
    R(lambda d, c, f: d == "10/9" and "朝食" in c,
      "💰 $25クレジットが余ります（施設利用料の見返りなので使わないと損）。10/8の夜か10/10の朝に回すのがおすすめ"),
    R(lambda d, c, f: d == "10/9" and "ホテル出発" in c,
      "🚶 徒歩11分の判断は正解。DTLAはこの距離なら地下鉄より速いです。ただし朝の人通りが少ない道は避けて大通り沿いで"),
    R(lambda d, c, f: d == "10/9" and "ブラッドベリー" in c,
      "📷 見学できるのは1階ロビーと階段の途中まで（上階はオフィス）。5〜10分は妥当な見積もりです。無料ですが営業時間は要確認"),
    R(lambda d, c, f: d == "10/9" and "グランド・セントラル" in c,
      "🍳 8時開店なのはマーケット全体で、個々の店は開店時刻がバラバラです。朝から開いている店を1つ決めておくと確実"),
    R(lambda d, c, f: d == "10/9" and "Last Bookstore" in c,
      "📚 2階の本のトンネルが人気の写真スポット。開店直後が一番空いています。11:00開店に合わせたこの並びは good"),
    R(lambda d, c, f: d == "10/9" and "ザ・ブロードへ移動" in c,
      "🚡 エンジェルス・フライト（短いケーブルカー）は片道1ドル程度の名物。乗るなら現金や運行時間を要確認。徒歩18分でも行けます"),
    R(lambda d, c, f: d == "10/9" and "ザ・ブロード" in c and "移動" not in c,
      "🎫 要事前予約。ここが1日の折り返し地点になるので、13:00の枠が取れるかで午後の組み方が変わります"),
    R(lambda d, c, f: "ウォルト・ディズニー・コンサートホール" in c,
      "📅 日付が空欄のままです。10/9に入れてください（ブロードの真向かいなので流れは完璧）。外観の見学は無料、中に入るなら公演かツアーが要ります"),
    R(lambda d, c, f: d == "10/9" and "Grand Avenue Arts" in c,
      "🚇 要確認：この駅はA/E Lineで、Hollywood/HighlandはB Line。7th St/Metro Centerでの乗り換えが要る可能性が高く、想定より15〜20分余計にかかるかも"),
    R(lambda d, c, f: d == "10/9" and "チャイニーズシアター" in c,
      "🔴 「〜15:00」は成立しません。ブロード13:00→14:00、コンサートホール→14:30、地下鉄で15:10着。ここから1時間ほど全部後ろにズレます"),
    R(lambda d, c, f: d == "10/9" and "チャイニーズシアター" in c,
      "👣 ウォーク・オブ・フェイムは道沿いに延々と続くので、探す星を決めておかないと時間が溶けます"),
    R(lambda d, c, f: d == "10/9" and "Pink" in c,
      "🔁 Pink'sは西側、次のVermont/Sunset駅は東側で逆走になります。順番を入れ替えるか、どちらか削るか要検討"),
    R(lambda d, c, f: d == "10/9" and "Pink" in c,
      "🌭 行列ができる店なので、待ち時間を20〜30分見ておくと安全です"),
    R(lambda d, c, f: d == "10/9" and "グリフィス" in c and "移動" in f.get("区分", ""),
      "🚌 DASH Observatoryバスは本数が限られます。運行時間と最終便を必ず確認してください（帰れなくなると配車も捕まりにくい場所です）"),
    R(lambda d, c, f: d == "10/9" and "グリフィス天文台" in c and "移動" not in c,
      "🌇 金曜は12:00開館・22:00閉館（要確認）。日没は18:30頃で夕景狙いは混みます。ここは2時間見ておくと安全"),
    R(lambda d, c, f: d == "10/9" and "グリフィス天文台" in c and "移動" not in c,
      "🧥 標高が高く夜は冷えます。10月のLAは夜13〜17℃まで下がるので、羽織りものを持って出てください"),
    R(lambda d, c, f: d == "10/9" and "帰り" in c,
      "🕘 帰着は21:30頃。朝8時発なので13時間半行動です。時差ボケ2日目としてはかなりハード。翌日に響かないか要検討"),

    # ===================== 10/10 =====================
    R(lambda d, c, f: d == "10/10" and not c.strip(),
      "💡 提案：10/9のハリウッド＋グリフィス天文台をこの日に移すと両日とも楽になります。土曜は天文台が10:00開館なので、実はこちらの方が都合がいいです", True),
    R(lambda d, c, f: d == "10/10" and "朝食" in c,
      "💰 10/9で使わなかった$25クレジットをここで使うのはどうですか"),

    # ===================== 10/11 =====================
    R(lambda d, c, f: d == "10/11" and "チェックアウト" in c,
      "🧳 チェックアウト後もベルデスクで荷物を預かってもらえます。午前をDTLAで使うならこの手が有効"),
    R(lambda d, c, f: d == "10/11" and "アナハイム" in c and "移動" in f.get("区分", ""),
      "🚗 配車だと1時間前後＋料金は高め。電車（メトロリンク等）だと安いが乗り換えが要ります。荷物3個なので配車が現実的かも。手段をここで決めてください"),
    R(lambda d, c, f: d == "10/11" and "荷物を預ける" in c,
      "⚠️ チェックイン標準15:00とDCA早入り15:00が正面衝突します。荷物だけ預けてパーク直行が現実解。Clarionに「チェックイン前に荷物を預けられるか」を事前に確認しておくと当日慌てません"),
    R(lambda d, c, f: d == "10/11" and "入園" in c,
      "🎟 OBBチケットは通常の入園券とは別物です。3人分がそれぞれのMyDisneyアカウントに紐づいているか、出発前に確認を"),
    R(lambda d, c, f: d == "10/11" and "Oogie" in c,
      "🎃 18:00〜23:00の5時間。トリックオアトリートのルート、ヴィランとの撮影、ショーは全部は回りきれないので、優先順位を決めておくのがおすすめ"),
    R(lambda d, c, f: d == "10/11" and "Oogie" in c,
      "👗 大人も仮装できるのはこのイベントの特典。ただし14歳以上は顔を覆うマスク不可、引きずる衣装も不可。仮装するなら軽装で"),
    R(lambda d, c, f: d == "10/11" and "戻る" in c,
      "🌙 23:00終了で人が一斉に出ます。徒歩圏とはいえ夜道なので3人で固まって移動を"),

    # ===================== 10/12 =====================
    R(lambda d, c, f: d == "10/12" and "朝食" in c,
      "🥐 開園に間に合わせるなら前夜にスーパーで買っておくのが確実。パーク内で食べると高くつきます"),
    R(lambda d, c, f: d == "10/12" and "入園" in c,
      "🕐 開園時刻が未確認のままです。Lightning Laneは入園直後に1本目を取るのがコツなので、開園時刻は押さえておきたい"),
    R(lambda d, c, f: d == "10/12" and "入園" in c,
      "⚡ Lightning Lane Multi Passは「使ったら次が取れる／取得から2時間で次が取れる」の繰り返し。朝イチで1本取ってから並ぶのが定石です"),
    R(lambda d, c, f: d == "10/12" and "昼" in f.get("時間帯", "") and "ディズニー" in c,
      "🍽 昼食はモバイルオーダー（アプリで注文）が並ばずに済みます。使うなら朝のうちに店と時間を押さえておくと楽"),
    R(lambda d, c, f: d == "10/12" and "お土産" in c,
      "🛍 閉園間際が最も空きます。かさばる物はこの日に買うと翌日の移動（ベガスへ6時間バス）が楽。アプリのMobile Checkoutならレジに並ばず会計できます"),
    R(lambda d, c, f: d == "10/12" and "夜" in f.get("時間帯", "") and not c.strip(),
      "🌃 Downtown Disneyは入園券なしで入れるショッピングエリア。閉園後に寄るならここ。ただし翌朝は移動日なので早めに切り上げを"),

    # ===================== 10/13 =====================
    R(lambda d, c, f: d == "10/13" and "チェックアウト" in c,
      "📦 チェックアウト後の荷物預かりが可能か、Clarionに要確認。バス出発まで時間が空くなら必須です"),
    R(lambda d, c, f: d == "10/13" and "ラスベガス" in c and "移動" in f.get("区分", ""),
      "🔴 最重要：11時チェックアウト→6時間だと17時着で、ベガスがほぼ潰れます。朝8時台に出れば14時着で午後〜夜がまるまる使えます。前夜にチェックアウト手続きを済ませておくのが手"),
    R(lambda d, c, f: d == "10/13" and "ラスベガス" in c and "移動" in f.get("区分", ""),
      "🎫 FlixBus/Greyhoundは早めに取るほど安いです（1人$44〜52の目安）。乗り場はアナハイムのARTIC。予約したら便名と出発時刻をこの行に書いてください"),
    R(lambda d, c, f: d == "10/13" and "到着" in c,
      "🚕 ベガス側の降車場所はストリップから離れています（FlixBusは2026年1月に移転）。Excaliburまで配車が要るので、その分の時間と料金を見ておいてください"),
    R(lambda d, c, f: d == "10/13" and "Excalibur" in c and "チェックイン" in c,
      "💳 リゾートフィー約51ドル/泊＋デポジットが別途かかります（部屋代とは別）。予算に入れておいてください。支払いはクレジットカードで"),
    R(lambda d, c, f: d == "10/13" and "夕方" in f.get("時間帯", "") and not c.strip(),
      "🎰 ベガス観光はこの日が本番です。ただし火曜なのでモール系は20〜21時閉店。買い物をするなら明るいうちに、夜はショー・夜景・カジノ系に寄せるのが定石"),
    R(lambda d, c, f: d == "10/13" and "夜" in f.get("時間帯", "") and not c.strip(),
      "🃏 カジノは21歳以上＋パスポート現物が必須（コピー・スマホ画像は不可）。Excaliburは$5から遊べる台があるので初心者向きです"),
    R(lambda d, c, f: d == "10/13" and "就寝" in c,
      "😴 翌朝5:00〜5:30に送迎。逆算すると4時起きなので、22時就寝でも睡眠6時間です。ベガスの夜は誘惑が多いですが翌日が本番なので割り切りを"),

    # ===================== 10/14 =====================
    R(lambda d, c, f: d == "10/14" and "ピックアップ" in c,
      "🎫 ツアーがまだ未予約です。ウエストリムの日帰りバスは早期に埋まります。表示価格に入場料と燃料費（約20ドル/人）が別途乗ることが多いので総額で比較を"),
    R(lambda d, c, f: d == "10/14" and "ピックアップ" in c,
      "🧥 グランドキャニオンは標高が高く、10月の朝は氷点下近くまで下がります。防寒着・手袋・ニット帽を前夜に用意しておいてください"),
    R(lambda d, c, f: d == "10/14" and "グランドキャニオン" in c and "移動" in f.get("区分", ""),
      "🚐 ウエストリムなら片道2.5時間。サウスリムを選ぶと片道4.5〜5時間になり日帰りはかなり厳しくなります。どちらに行くかで、この日の形が変わります"),
    R(lambda d, c, f: d == "10/14" and "滞在" in c,
      "📸 見どころを事前に絞っておくと4時間が有効に使えます。スカイウォークは橋の上にカメラ・バッグを持ち込めない（携帯のみ）ので注意"),
    R(lambda d, c, f: d == "10/14" and "帰着" in c,
      "⏱ 帰着16〜17時。翌朝3時ホテル発なので、ここから使えるのは実質5〜6時間です"),
    R(lambda d, c, f: d == "10/14" and "夜" in f.get("時間帯", "") and not c.strip(),
      "🎰 ここが最大の判断ポイント。「カジノで遊ぶ」か「寝る」か。11時間ツアーの後なので、体力次第では素直に寝る方が帰国が楽です"),
    R(lambda d, c, f: d == "10/14" and ("就寝" in c or "寝ない" in c),
      "🔴 翌3時ホテル発。カジノをやるなら22時には切り上げて仮眠4時間、が限界ラインです。荷造りも前夜に済ませておいてください"),

    # ===================== 10/15 =====================
    R(lambda d, c, f: d == "10/15" and "チェックアウト" in c,
      "🕒 6:00発なら空港着3:30、ホテル発3:00が目安。深夜のチェックアウトになるので、前夜にフロントへ伝えておくとスムーズです"),
    R(lambda d, c, f: d == "10/15" and "空港" in c and "移動" in f.get("区分", ""),
      "🚕 深夜3時台は配車が捕まりにくいことがあります。ホテルのタクシー乗り場も選択肢に入れておいてください"),
    R(lambda d, c, f: d == "10/15" and ("LAS発" in c or "搭乗" in c),
      "🔴 便名と正確な時刻が未確定。ここが決まらないと10/14の夜が決められません。最優先で確認を"),
    R(lambda d, c, f: d == "10/15" and ("LAS発" in c or "搭乗" in c),
      "🧴 液体のお土産を預け荷物に入れる最後のチャンスがこのチェックインです。LAX乗継中には荷物を開けられません"),
    R(lambda d, c, f: d == "10/15" and "乗継" in c,
      "🧳 荷物は成田まで通し預けの見込み。LASのカウンターで「行き先はNRTか」を口頭確認＋タグを目視確認してください"),
    R(lambda d, c, f: d == "10/15" and "乗継" in c,
      "🚶 United国内線はLAXのT7/T8着、成田行きはTBIT発。保安検査のやり直しは不要ですが、徒歩でそこそこ距離があります。乗継2時間以上あると安心"),
    R(lambda d, c, f: d == "10/15" and "機内" in c,
      "😴 帰りは体内時計を「早める」方向で一番きつい向きです。機内でしっかり寝ておくと帰国後が楽。モバイルバッテリーは機内で使用禁止なので空港で充電を"),

    # ===================== 10/16 =====================
    R(lambda d, c, f: d == "10/16" and "成田" in c and "着" in c,
      "📱 Visit Japan Webは「入国」と「税関」の両方を登録しないとQRが無効になります。3人とも出発前に済ませておいてください"),
    R(lambda d, c, f: d == "10/16" and "成田" in c and "着" in c,
      "🥩 肉・肉エキス入りの食品は日本に持ち込めません（ジャーキー、レトルト等）。お土産を買う時点で気をつけて"),
    R(lambda d, c, f: d == "10/16" and "仙台" in c,
      "🚄 16時成田着＋入国審査1時間で、動けるのは17時以降。仙台着は夜遅くなります。翌日の予定は空けておいた方が無難"),
]


# ---- どの行にも当てはめる汎用チェック ----
def generic_checks(d, c, f):
    out = []
    kubun = f.get("区分", "")
    if d and not c.strip():
        out.append("⬜ ここがまだ空です")
    if kubun == "移動" and c.strip() and not f.get("移動手段", "").strip():
        out.append("🚕 移動手段が未記入です")
    book = f.get("予約状況", "")
    if "★" in book:
        out.append("🎫 予約・確認がまだです（%s）" % book.replace("★", ""))
    return out


def build_fb(grid):
    header = [h.strip() for h in grid[0]]
    idx = {h: i for i, h in enumerate(header) if h}

    def g(row, name):
        i = idx.get(name)
        return (row[i].strip() if i is not None and i < len(row) else "")

    out = ["🤖 ClaudeFB（30分ごとに自動更新）"]
    prev_time = None
    prev_day = None
    used_once = set()

    for row in grid[1:]:
        d = g(row, "日付")
        c = g(row, "内容")
        f = {k: g(row, k) for k in ("区分", "時間帯", "移動手段", "所要", "予約状況", "場所", "メモ")}
        notes = []

        if d and d != prev_day:
            prev_time = None
            used_once = set()

        # 内容ルール（当てはまるものを全部・1日1回指定のものは重複させない）
        for cond, msg, once in RULES:
            try:
                if not cond(d, c, f):
                    continue
            except Exception:
                continue
            if once:
                if msg in used_once:
                    continue
                used_once.add(msg)
            if msg not in notes:
                notes.append(msg)

        # 汎用チェック（内容ルールが無い行だけ。うるさくしない）
        if not notes:
            notes.extend(generic_checks(d, c, f))
        else:
            book = f.get("予約状況", "")
            if "★" in book and not any("予約" in n for n in notes):
                notes.append("🎫 予約・確認がまだです（%s）" % book.replace("★", ""))

        # 時刻の逆行
        t = parse_time(g(row, "時刻"))
        if t is not None and prev_time is not None and t < prev_time and t >= 5 * 60:
            notes.append("⚠️ 前の予定（%s）より時刻が戻っています" % fmt(prev_time))
        if t is not None:
            prev_time = t

        if d:
            prev_day = d
        out.append("　／　".join(notes))

    return out


def main():
    grid = fetch_grid()
    col = build_fb(grid)
    os.makedirs("docs", exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        for line in col:
            w.writerow([line])
    n = sum(1 for x in col[1:] if x.strip())
    print("%s  行数=%d / コメントあり=%d  (%s)" % (
        OUT, len(col), n, datetime.now().strftime("%H:%M")))


if __name__ == "__main__":
    main()
