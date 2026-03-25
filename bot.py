import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import json, os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GAME_URL = "https://jovial-beignet-2537d3.netlify.app/"

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=4)

app = Flask(__name__)

DATA_FILE = "users.json"

# ---------------- DATABASE ----------------
def load():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "deposits": [], "withdraws": [], "pending": {}}
    return json.load(open(DATA_FILE))

def save(data):
    json.dump(data, open(DATA_FILE, "w"), indent=2)

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.chat.id)
    data = load()

    if uid not in data["users"]:
        ref = msg.text.split(" ")[1] if len(msg.text.split()) > 1 else None
        data["users"][uid] = {"balance": 0, "deposit": 0}

        if ref and ref in data["users"]:
            data["users"][ref]["balance"] += 30
            bot.send_message(ref, f"🎉 You invited {msg.from_user.first_name} & earned ₹30!")

    save(data)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Deposit", callback_data="dep"))
    kb.add(InlineKeyboardButton("💸 Withdraw", callback_data="wd"))
    kb.add(InlineKeyboardButton("🔗 Referral", callback_data="ref"))
    kb.add(InlineKeyboardButton("🎮 Play Game", url=GAME_URL))
    kb.add(InlineKeyboardButton("📊 Leaderboard", callback_data="lead"))

    if msg.chat.id == ADMIN_ID:
        kb.add(InlineKeyboardButton("👨‍💻 Admin Panel", callback_data="admin"))

    bot.send_message(msg.chat.id, "🏠 Main Menu", reply_markup=kb)

# ---------------- BUTTON ----------------
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    uid = str(call.message.chat.id)
    data = load()

    if call.data == "dep":
        bot.send_message(uid, "💰 Enter deposit amount (min ₹101)")
        bot.register_next_step_handler(call.message, deposit_amount)

    elif call.data == "wd":
        if data["users"][uid]["deposit"] < 101:
            bot.send_message(uid, "❌ Deposit ₹101 first")
            return
        bot.send_message(uid, "💸 Enter withdraw amount (>100)")
        bot.register_next_step_handler(call.message, withdraw_amount)

    elif call.data == "ref":
        bot.send_message(uid, f"🔗 Referral:\nhttps://t.me/YOUR_BOT_USERNAME?start={uid}")

    elif call.data == "lead":
        bot.send_message(uid,
        "🏆 Leaderboard:\n"
        "1. Laksmin Raja ₹4313\n"
        "2. Harshit ₹3409\n"
        "3. Taruni ₹3300\n"
        "4. Yusufi ₹3090\n"
        "5. Dhruv ₹2908")

    elif call.data == "admin" and call.from_user.id == ADMIN_ID:
        bot.send_message(uid,
        "👨‍💻 Admin Commands:\n"
        "/users\n/add user_id amount\n/deduct user_id amount\n/msg user_id message")

    elif call.data.startswith("dep_"):
        i = int(call.data.split("_")[1])
        dep = data["deposits"][i]
        u = dep["user"]
        amt = dep["amount"]

        data["users"][u]["balance"] += amt
        data["users"][u]["deposit"] += amt
        save(data)

        bot.send_message(u, f"✅ Deposit ₹{amt} approved")

    elif call.data.startswith("wd_"):
        i = int(call.data.split("_")[1])
        wd = data["withdraws"][i]
        u = wd["user"]
        amt = wd["amount"]

        data["users"][u]["balance"] -= amt
        save(data)

        bot.send_message(u, "✅ Withdrawal successful")

# ---------------- DEPOSIT ----------------
def deposit_amount(msg):
    uid = str(msg.chat.id)
    data = load()

    try:
        amt = int(msg.text)
    except:
        bot.send_message(uid, "Enter valid number")
        return

    if amt < 101:
        bot.send_message(uid, "Minimum ₹101")
        return

    data["pending"][uid] = amt
    save(data)

    bot.send_message(ADMIN_ID, f"💳 User {uid} wants to deposit ₹{amt}\nSend QR")
    bot.send_message(uid, "⏳ Waiting for QR...")

# ---------------- WITHDRAW ----------------
def withdraw_amount(msg):
    uid = str(msg.chat.id)
    data = load()

    try:
        amt = int(msg.text)
    except:
        bot.send_message(uid, "Enter valid number")
        return

    if amt <= 100 or data["users"][uid]["balance"] < amt:
        bot.send_message(uid, "❌ Invalid amount")
        return

    bot.send_message(uid, "🏦 Send Account Number + IFSC")
    bot.register_next_step_handler(msg, withdraw_details, amt)

def withdraw_details(msg, amt):
    uid = str(msg.chat.id)
    data = load()

    data["withdraws"].append({
        "user": uid,
        "amount": amt,
        "details": msg.text
    })
    save(data)

    wid = len(data["withdraws"]) - 1

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Approve", callback_data=f"wd_{wid}"))

    bot.send_message(ADMIN_ID, f"💸 Withdraw\nUser: {uid}\n₹{amt}\n{msg.text}", reply_markup=kb)
    bot.send_message(uid, "⏳ Sent to admin")

# ---------------- PHOTO ----------------
@bot.message_handler(content_types=['photo'])
def photo(msg):
    uid = str(msg.chat.id)
    data = load()

    if msg.chat.id == ADMIN_ID and data["pending"]:
        user = list(data["pending"].keys())[0]
        bot.send_photo(user, msg.photo[-1].file_id)
        bot.send_message(user, "📸 Send payment screenshot")
        return

    amt = data["pending"].get(uid, 100)
    dep_id = len(data["deposits"])

    data["deposits"].append({"user": uid, "amount": amt})
    data["pending"].pop(uid, None)
    save(data)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Approve", callback_data=f"dep_{dep_id}"))

    bot.send_photo(ADMIN_ID, msg.photo[-1].file_id,
                   caption=f"Deposit proof {uid}",
                   reply_markup=kb)

    bot.send_message(uid, "✅ Sent for approval")

# ---------------- ADMIN ----------------
@bot.message_handler(commands=['users'])
def users(msg):
    if msg.chat.id != ADMIN_ID:
        return
    data = load()
    text = "\n".join([f"{u} : ₹{d['balance']}" for u, d in data["users"].items()])
    bot.send_message(msg.chat.id, text or "No users")

# ---------------- WEBHOOK ----------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.json)
        bot.process_new_updates([update])
    except Exception as e:
        print("ERROR:", e)

    return "OK", 200

@app.route("/")
def home():
    return "Bot running"

# ---------------- START ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
