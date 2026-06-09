import os
import csv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

# =========================
# LINE 設定
# =========================

LINE_CHANNEL_SECRET = "a5dd19ca75f3aa7164172a9c4729bed1"
LINE_CHANNEL_ACCESS_TOKEN = "bmFS85/iNWUXXIBoaH1fF4ovfQfuuGv8U282WwOVP0yUUrCjAC0Gr/hLDtKm1zJwTyISbgPwS8rUSdOn7Za7VtCfbW361iceHASe5BkBaqGQ7OLZaSxyxldqUEsqIkb7KuqlOmmPbrd/b90UR6wfrwdB04t89/1O/w1cDnyilFU="
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# =========================
# Gemini
# =========================

client = genai.Client(api_key=GEMINI_API_KEY)

# =========================
# 教學知識庫
# =========================

knowledge_base = """
你是一位高中數學教學助理。

【一元一次方程式】
解題步驟：
1. 移項
2. 合併同類項
3. 求未知數

常見錯誤：
- 移項忘記變號

【因式分解】
解題步驟：
1. 找公因數
2. 十字交乘
3. 驗算答案

常見錯誤：
- 符號判斷錯誤

【二次方程式】
解題步驟：
1. 因式分解
2. 配方法
3. 公式解

常見錯誤：
- 根號計算錯誤

【教學原則】
1. 不直接公布答案
2. 先給提示
3. 引導學生思考
4. 使用鼓勵語氣
5. 如果學生一直答錯才逐步揭露答案
"""

# =========================
# 使用者模式紀錄
# =========================

user_mode = {}

# =========================
# Webhook
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return "OK"


# =========================
# LINE 收訊息
# =========================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    user_msg = event.message.text.strip()
    user_id = event.source.user_id

    # =====================
    # 指令：數學模式
    # =====================

    if user_msg == "/數學":

        user_mode[user_id] = "math"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=(
                    "已切換至【數學教學模式】\n\n"
                    "之後輸入數學題目，我會用提示方式引導你解題。"
                )
            )
        )
        return

    # =====================
    # 指令：一般模式
    # =====================

    if user_msg == "/一般":

        user_mode[user_id] = "normal"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="已切換至【一般聊天模式】"
            )
        )
        return

    # =====================
    # 指令：幫助
    # =====================

    if user_msg == "/幫助":

        help_text = """
可使用指令：

/數學
切換數學教學模式

/一般
切換一般聊天模式

/幫助
查看功能說明

=================

範例：

2x+3=11

x²-5x+6=0

我會一步一步引導你解題，
而不是直接公布答案。
"""

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_text)
        )
        return

    # =====================
    # 取得模式
    # =====================

    mode = user_mode.get(user_id, "normal")

    # =====================
    # 建立 Prompt
    # =====================

    if mode == "math":

        prompt = f"""
你是一位專業數學教學助理。

請依據以下教材進行教學：

{knowledge_base}

教學規則：

1. 不要直接公布答案
2. 先判斷題型
3. 提供第一步提示
4. 引導學生思考
5. 問學生下一步該怎麼做
6. 使用鼓勵語氣
7. 除非學生要求完整解答，否則不要一次給答案

學生問題：

{user_msg}
"""

    else:

        prompt = f"""
你是一位友善的 AI 助理。

請回答以下問題：

{user_msg}
"""

    # =====================
    # 呼叫 Gemini
    # =====================

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        reply = response.text

    except Exception as e:

        print("Gemini Error:", e)

        reply = f"系統錯誤：{str(e)}"

    # =====================
    # 儲存對話紀錄
    # =====================

    try:

        file_exists = os.path.exists("chat_log.csv")

        with open(
            "chat_log.csv",
            "a",
            newline="",
            encoding="utf-8-sig"
        ) as f:

            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "user_id",
                    "mode",
                    "question",
                    "answer"
                ])

            writer.writerow([
                user_id,
                mode,
                user_msg,
                reply
            ])

    except Exception as e:

        print("CSV Error:", e)

    # =====================
    # 回覆 LINE
    # =====================

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


# =========================
# 啟動 Flask
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
