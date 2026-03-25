import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import json, os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GAME_URL = "https://jovial-beignet-2537d3.netlify.app/"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "users.json"

def load():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "deposits": [], "withdraws": [], "pending": {}}
    return json.load(open(DATA_FILE))

def save(data):
    json.dump(data, open(DATA_FILE, "w"), indent=2)

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.chat.id)
    data = load()

    if uid not in data["users"]:
        data["users"][uid] = {"balance": 0, "deposit": 0}

    save(data)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Deposit", callback_data="dep"))
    kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="wd"))
    kb.add(InlineKeyboardButton("🔗 Referral", callback_data="ref"))
    kb.add(InlineKeyboardButton("🎮 Play Game", url=GAME_URL))
    kb.add(InlineKeyboardButton("📊 Leaderboard", callback_data="lead"))

    if msg.chat.id == ADMIN_ID:
        kb.add(InlineKeyboardButton("👨‍💻 Admin", callback_data="admin"))

    bot.send_message(msg.chat.id, "🏠 Menu", reply_markup=kb)

# ---------- BUTTON ----------
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    uid = str(call.message.chat.id)
    data = load()

    if call.data == "dep":
        bot.send_message(uid, "Enter amount (min 101)")
        bot.register_next_step_handler(call.message, deposit_amount)

    elif call.data == "wd":
        if data["users"][uid]["deposit"] < 101:
            bot.send_message(uid, "Deposit ₹101 first")
            return
        bot.send_message(uid, "Enter withdraw amount (>100)")
        bot.register_next_step_handler(call.message, withdraw_amount)

    elif call.data == "ref":
        bot.send_message(uid, f"Referral link:\nhttps://t.me/YOUR_BOT?start={uid}")

    elif call.data == "lead":
        bot.send_message(uid,
        "🏆 Leaderboard:\n1. Laksmin Raja ₹4313\n2. Harshit ₹3409\n3. Taruni ₹3300\n4. Yusufi ₹3090\n5. Dhruv ₹2908")

# ---------- DEPOSIT ----------
def deposit_amount(msg):
    uid = str(msg.chat.id)
    amt = int(msg.text)
    data = load()

    if amt < 101:
        bot.send_message(uid, "Minimum 101")
        return

    data["pending"][uid] = amt
    save(data)

    bot.send_message(ADMIN_ID, f"User {uid} deposit ₹{amt}\nSend QR")
    bot.send_message(uid, "Waiting for QR...")

# ---------- WITHDRAW ----------
def withdraw_amount(msg):
    uid = str(msg.chat.id)
    amt = int(msg.text)
    data = load()

    if amt <= 100 or data["users"][uid]["balance"] < amt:
        bot.send_message(uid, "Invalid amount")
        return

    bot.send_message(uid, "Send bank + IFSC")
    bot.register_next_step_handler(msg, withdraw_details, amt)

def withdraw_details(msg, amt):
    uid = str(msg.chat.id)
    data = load()

    data["withdraws"].append({"user": uid, "amount": amt, "details": msg.text})
    save(data)

    wid = len(data["withdraws"]) - 1
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Approve", callback_data=f"wd_{wid}"))

    bot.send_message(ADMIN_ID, f"Withdraw {uid} ₹{amt}\n{msg.text}", reply_markup=kb)
    bot.send_message(uid, "Request sent")

# ---------- PHOTO ----------
@bot.message_handler(content_types=['photo'])
def photo(msg):
    uid = str(msg.chat.id)
    data = load()

    # Admin sending QR
    if msg.chat.id == ADMIN_ID and data["pending"]:
        user = list(data["pending"].keys())[0]
        bot.send_photo(user, msg.photo[-1].file_id)
        bot.send_message(user, "Send payment screenshot")
        return

    # User sending proof
    amt = data["pending"].get(uid, 100)
    dep_id = len(data["deposits"])

    data["deposits"].append({"user": uid, "amount": amt})
    data["pending"].pop(uid, None)
    save(data)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Approve", callback_data=f"dep_{dep_id}"))

    bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=f"Proof {uid}", reply_markup=kb)
    bot.send_message(uid, "Sent for approval")

# ---------- APPROVAL ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("dep_") or c.data.startswith("wd_"))
def approve(call):
    data = load()

    if call.data.startswith("dep_"):
        i = int(call.data.split("_")[1])
        dep = data["deposits"][i]
        uid = dep["user"]
        amt = dep["amount"]

        data["users"][uid]["balance"] += amt
        data["users"][uid]["deposit"] += amt

        bot.send_message(uid, f"Deposit ₹{amt} approved")

    if call.data.startswith("wd_"):
        i = int(call.data.split("_")[1])
        wd = data["withdraws"][i]
        uid = wd["user"]
        amt = wd["amount"]

        data["users"][uid]["balance"] -= amt
        bot.send_message(uid, "Withdrawal successful")

    save(data)

# ---------- WEBHOOK ----------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok"

@app.route("/")
def home():
    return "Bot running"

# ---------- START ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
