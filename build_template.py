# -*- coding: utf-8 -*-
"""
アメリカ旅行データのGoogleスプレッドシート用テンプレ(.xlsx)を生成する。
・「つかいかた」「日程」「未決事項」の3シート
・日程/未決事項は1行目=見出し固定（サイト側がこの見出し名で読むため変えない）
再生成したいときは:  uv run --with openpyxl python build_template.py
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ACCENT = "D97757"   # デザインのアクセント色（テラコッタ）
SOFT   = "F6EBE4"

wb = Workbook()

# ---------- シート1: つかいかた ----------
ws0 = wb.active
ws0.title = "つかいかた"
guide = [
    ("アメリカ旅行 共有データ — つかいかた", True),
    ("", False),
    ("このスプレッドシートは、旅行サイト（しおり）の「プラン」部分の元データです。", False),
    ("ここを直すと、岡崎さんがサイトを作り直したとき（再成形）に反映されます。", False),
    ("", False),
    ("■ みんなで編集していいところ", True),
    ("・「日程」タブ … 時刻・場所・宿・予約状況・メモを自由に編集／行を足してOK", False),
    ("・「未決事項」タブ … まだ決まってないこと（★）。状態や決定内容を埋めていく", False),
    ("", False),
    ("■ お願い（これだけ守って）", True),
    ("① タブの名前を変えない（日程 / 未決事項 のまま）", False),
    ("② 各タブの1行目（見出し）を消さない・並べ替えない（列は増やしてOK）", False),
    ("③ パスポート番号・カード番号・自宅住所など、人に見られて困る情報は書かない", False),
    ("   （サイトは『リンクを知っている人は閲覧可』の公開設定のため）", False),
    ("", False),
    ("■ 編集が終わったら", True),
    ("・特別な操作は不要。編集があった日に岡崎さんへ通知メールが届くようにしてあります。", False),
    ("・岡崎さんがClaudeに『サイト更新して』と頼むと、最新版に作り直されます。", False),
]
for i, (text, bold) in enumerate(guide, start=1):
    c = ws0.cell(row=i, column=1, value=text)
    c.font = Font(bold=bold, size=14 if (bold and i == 1) else (12 if bold else 11),
                  color=ACCENT if bold else "1F1B16")
    c.alignment = Alignment(wrap_text=False, vertical="center")
ws0.column_dimensions["A"].width = 90
ws0.sheet_view.showGridLines = False

# ---------- 共通: 見出し付きシートを作る ----------
def make_sheet(title, headers, rows, widths, wrap_cols):
    ws = wb.create_sheet(title)
    head_fill = PatternFill("solid", fgColor=ACCENT)
    head_font = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="E8E1D8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    # 見出し（1行目）
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=col, value=h)
        c.fill = head_fill
        c.font = head_font
        c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        c.border = border
    # データ
    for r, row in enumerate(rows, start=2):
        for col, val in enumerate(row, start=1):
            c = ws.cell(row=r, column=col, value=val)
            c.alignment = Alignment(vertical="top",
                                    wrap_text=(headers[col-1] in wrap_cols))
            c.border = border
            if r % 2 == 0:
                c.fill = PatternFill("solid", fgColor="FBF8F5")
    # 列幅
    for col, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = w
    # 見出し固定＋フィルタ
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows)+1}"
    return ws

# ---------- シート2: 日程 ----------
nittei_headers = ["日付", "時刻", "区分", "内容", "場所", "予約状況", "メモ", "リンク"]
nittei_rows = [
    ["10/8", "12:30頃", "手続き", "ロサンゼルス国際空港(LAX)着・入国/税関", "LAX", "", "★空港を出るまでの段取り未整理", ""],
    ["10/8", "14:00頃", "移動", "空港を出る", "LAX", "", "", ""],
    ["10/8", "午後", "観光", "空港周辺で軽く観光・食事", "LA", "", "★行き先未定／候補:ランディーズドーナッツ・イン&アウト", ""],
    ["10/8", "", "移動", "Uberでホテルへ", "", "", "", ""],
    ["10/8", "16:00頃", "宿", "The Wayfarer Downtown LA チェックイン", "ダウンタウンLA", "★要記入", "★入る時刻未定／荷物を預けたい", ""],
    ["10/8", "夕方", "観光", "ホテル周辺・近所のスーパーで買い物＆夕食", "ダウンタウンLA", "", "★何時までうろつけるか", ""],
    ["10/8", "夜", "宿", "就寝（初日は早め）", "", "", "★時差ボケ対策", ""],

    ["10/9", "終日", "観光", "完全フリー", "LA", "", "★やること未定（観光は後日3人で決める）", ""],
    ["10/9", "夜", "宿", "The Wayfarer Downtown LA（連泊）", "ダウンタウンLA", "", "", ""],

    ["10/10", "終日", "観光", "フリー（9日と同様）", "LA", "", "★やること未定", ""],
    ["10/10", "夜", "宿", "The Wayfarer Downtown LA（連泊）", "ダウンタウンLA", "", "", ""],

    ["10/11", "朝", "移動", "アナハイムへ移動", "→アナハイム", "", "★荷物の一時預け先を知りたい", ""],
    ["10/11", "入園前", "観光", "入園前にできること（パーク外）", "アナハイム", "", "", ""],
    ["10/11", "15:00〜", "観光", "ディズニー・カリフォルニア・アドベンチャー", "Disney California Adventure", "購入済み", "Oogie Boogie Bash参加（チケット購入済み）", ""],
    ["10/11", "夜", "宿", "Clarion Hotel Anaheim Resort（徒歩圏）", "アナハイム", "★要記入", "", ""],

    ["10/12", "朝", "移動", "ディズニーへ", "アナハイム", "", "", ""],
    ["10/12", "日中", "観光", "ディズニーランド（ランド側）", "Disneyland", "購入済み", "1day Tier券＋Lightning Lane Multi Pass／★お土産の注意", ""],
    ["10/12", "夜", "宿", "Clarion Hotel Anaheim Resort（連泊）", "アナハイム", "", "", ""],

    ["10/13", "起床後", "移動", "アナハイム→ラスベガスへ", "→ラスベガス", "", "★移動手段未定（luxxpressバス候補ほか代替も検討）", "https://booking.luxxpress.com/"],
    ["10/13", "お昼ごろ", "観光", "ラスベガス到着・観光", "ラスベガス", "", "★この日しか観光できないかも", ""],
    ["10/13", "", "観光", "カジノ", "ラスベガス", "", "★カジノしたい／★荷物どうする", ""],
    ["10/13", "夜", "宿", "Excalibur Hotel & Casino", "ラスベガス", "★要記入", "", ""],

    ["10/14", "起床", "移動", "グランドキャニオンへ", "→グランドキャニオン", "", "★チケットにより夜中出発かも／★移動手段未定", ""],
    ["10/14", "日中", "観光", "グランドキャニオン", "グランドキャニオン", "★未定", "★どこを見るか検討中（Claudeは決めない）", ""],
    ["10/14", "夜", "宿", "Excalibur Hotel & Casino", "ラスベガス", "", "★翌朝早便→滞在時間を要検討（寝ずにカジノ→機内で寝る案も）", ""],

    ["10/15", "6:00頃", "移動", "飛行機搭乗（ハリーリード国際空港・ユナイテッド航空）", "ラスベガス(LAS)", "★便要確認", "★何時に空港着くべきか整理したい", ""],
    ["10/15", "", "移動", "ロサンゼルス国際空港(LAX)で乗継", "LAX", "", "★乗継の注意", ""],
    ["10/16", "16:00頃", "手続き", "成田空港 着", "成田", "", "★帰国時の注意", ""],
]
make_sheet("日程", nittei_headers, nittei_rows,
           widths=[18, 10, 8, 34, 24, 12, 40, 26],
           wrap_cols={"内容", "メモ", "場所"})

# ---------- シート3: 未決事項 ----------
miketsu_headers = ["項目", "状態", "担当", "決定内容", "期限", "メモ"]
miketsu_rows = [
    ["LAX到着〜空港を出るまでの段取り", "相談中", "", "提案: 入国→荷物受取→税関→LAX-itからUber（混雑時1〜2h）", "", "★段取りのたたき台に詳細"],
    ["LA初日・空港周辺で何をするか", "未着手", "", "", "", "観光は後日3人で決める／候補:ランディーズ・イン&アウト"],
    ["Wayfarerに何時に入るか・荷物預け", "未着手", "", "", "", "早着ならベルデスクに荷物預け（ガイド: ホテルの作法）"],
    ["10/9・10/10 フリーの過ごし方", "未着手", "", "", "", "観光は後日3人で決めてからClaudeが精査"],
    ["時差ボケ対策", "相談中", "", "到着初日は日光を浴び夜まで起きる（早寝しない）", "", "→ガイドに回答あり"],
    ["アナハイム移動日(10/13)の荷物一時預け", "相談中", "", "提案: Clarionのベルデスク預かりが第一候補", "", ""],
    ["ディズニーのチケット（OBB＋ランド）", "決定", "", "購入済み（11=Oogie Boogie Bash／12=1day Tier券+Lightning Lane）", "", "各自MyDisneyに紐付け確認"],
    ["お土産購入時の注意", "相談中", "", "アプリMobile Checkoutでその日に持ち帰り（ホテル配送は対象外）", "", ""],
    ["アナハイム→ラスベガスの移動手段", "相談中", "", "提案: FlixBus/Greyhound直行が本命（約6h・3人で約2万円・QR乗車・荷物床下無料）", "", "★段取りのたたき台で4案比較"],
    ["ラスベガスのカジノ・観光・荷物", "相談中", "", "カジノは21歳+パスポート現物必須。Excaliburは$5BJ/$3機械式あり", "", "撮影は自撮りのみ等マナー要確認"],
    ["グランドキャニオンの行き方", "相談中", "", "提案: ウエストリムの日帰りバスツアー（近い・送迎・楽）。サウスは飛行機ツアー", "", "チケット/見る場所は本人たちで"],
    ["グランドキャニオン日(10/14)の出発時刻", "相談中", "", "ツアーなら朝5:00-5:30ホテル送迎・総所要約11h", "", "前夜は早寝"],
    ["最終日(10/15)ホテル滞在時間（早便加味）", "相談中", "", "LAS早朝便→空港は2.5〜3h前着。10/13・14夜は早寝推奨", "", ""],
    ["帰国便の確認・空港到着時刻", "未着手", "", "", "", "便名を確認。LASチェックイン開始時刻も前日確認"],
    ["クレカ: VisaかMastercardを1枚追加", "未着手", "岡崎", "", "出発前", "Amexのみはリスク（受け入れ・予備・タッチ）。発行に2〜3週間"],
    ["日程の日付（10/13重複）を確定", "決定", "", "Day7=10/14・Day8=10/15発→10/16 16時 成田着", "", "7泊9日と整合。確定済み"],
    ["航空券＝ユナイテッド航空（往復）", "決定", "全員", "成田⇔LAX、復路LAS→LAX乗継", "", "荷物規格はUnited基準（ガイド参照）"],
    ["ESTA（電子渡航認証）の申請", "未着手", "全員", "", "出発前", "アメリカ入国に全員必須・早めに申請"],
    ["パスポート残存期間の確認", "未着手", "全員", "", "出発前", "カジノでも現物必須。残存期間を確認"],
]
make_sheet("未決事項", miketsu_headers, miketsu_rows,
           widths=[34, 10, 8, 28, 12, 34],
           wrap_cols={"項目", "決定内容", "メモ"})

out = "旅行データ_テンプレート.xlsx"
wb.save(out)
print("saved:", out, "/ sheets:", wb.sheetnames)
