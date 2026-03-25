import json
import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GAME_URL = "https://jovial-beignet-2537d3.netlify.app/"

bot = Bot(TOKEN)
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

DATA_FILE = "users.json"

# ---------------- DATABASE ----------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "deposits": [], "withdraws": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- START ----------------
def start(update, context):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()

    if uid not in data["users"]:
        ref = context.args[0] if context.args else None
        data["users"][uid] = {"balance": 0, "deposit": 0}

        if ref and ref in data["users"]:
            data["users"][ref]["balance"] += 30
            bot.send_message(ref, f"🎉 You invited {user.first_name} and got ₹30!")

    save_data(data)

    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🔗 Referral", callback_data="ref")],
        [InlineKeyboardButton("🎮 Play Game", url=GAME_URL)],
        [InlineKeyboardButton("📊 Leaderboard", callback_data="leader")],
    ]

    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👨‍💻 Admin Panel", callback_data="admin")])

    update.message.reply_text("🏠 Main Menu", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BUTTON ----------------
def button(update, context):
    query = update.callback_query
    query.answer()
    uid = str(query.from_user.id)
    data = load_data()

    if query.data == "deposit":
        context.user_data["state"] = "deposit_amount"
        query.message.reply_text("Enter deposit amount (min ₹101)")

    elif query.data == "withdraw":
        if data["users"][uid]["deposit"] < 101:
            query.message.reply_text("❌ Deposit ₹101 first")
            return
        context.user_data["state"] = "withdraw_amount"
        query.message.reply_text("Enter withdraw amount (>100)")

    elif query.data == "ref":
        link = f"https://t.me/YOUR_BOT_USERNAME?start={uid}"
        query.message.reply_text(f"🔗 Referral:\n{link}")

    elif query.data == "leader":
        query.message.reply_text(
            "🏆 Leaderboard:\n"
            "1. Laksmin Raja ₹4313\n"
            "2. Harshit ₹3409\n"
            "3. Taruni ₹3300\n"
            "4. Yusufi ₹3090\n"
            "5. Dhruv ₹2908"
        )

    elif query.data == "admin" and query.from_user.id == ADMIN_ID:
        query.message.reply_text(
            "👨‍💻 Admin Panel:\n"
            "/users\n/add user_id amount\n/deduct user_id amount\n/msg user_id message"
        )

    elif query.data.startswith("approve_dep_"):
        i = int(query.data.split("_")[-1])
        dep = data["deposits"][i]
        uid2 = dep["user"]
        amt = dep["amount"]

        data["users"][uid2]["balance"] += amt
        data["users"][uid2]["deposit"] += amt
        save_data(data)

        bot.send_message(uid2, f"✅ Deposit ₹{amt} approved")

    elif query.data.startswith("approve_wd_"):
        i = int(query.data.split("_")[-1])
        wd = data["withdraws"][i]
        uid2 = wd["user"]
        amt = wd["amount"]

        data["users"][uid2]["balance"] -= amt
        save_data(data)

        bot.send_message(uid2, "✅ Withdrawal completed")

# ---------------- TEXT ----------------
def text(update, context):
    uid = str(update.effective_user.id)
    text = update.message.text
    data = load_data()
    state = context.user_data.get("state")

    if state == "deposit_amount":
        amt = int(text)
        if amt < 101:
            update.message.reply_text("Minimum ₹101")
            return

        context.user_data["amount"] = amt
        context.user_data["user"] = uid

        bot.send_message(ADMIN_ID, f"User {uid} wants to deposit ₹{amt}\nSend QR")
        update.message.reply_text("Waiting for QR...")

    elif state == "withdraw_amount":
        amt = int(text)
        if amt <= 100 or data["users"][uid]["balance"] < amt:
            update.message.reply_text("Invalid amount")
            return

        context.user_data["amount"] = amt
        context.user_data["state"] = "bank"
        update.message.reply_text("Send account number + IFSC")

    elif state == "bank":
        amt = context.user_data["amount"]

        data["withdraws"].append({
            "user": uid,
            "amount": amt,
            "details": text
        })
        save_data(data)

        wid = len(data["withdraws"]) - 1
        keyboard = [[InlineKeyboardButton("Approve", callback_data=f"approve_wd_{wid}")]]

        bot.send_message(
            ADMIN_ID,
            f"Withdraw:\nUser {uid}\n₹{amt}\n{text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        update.message.reply_text("Request sent")

# ---------------- PHOTO ----------------
def photo(update, context):
    uid = str(update.effective_user.id)
    data = load_data()

    dep_id = len(data["deposits"])
    amt = context.user_data.get("amount", 100)

    data["deposits"].append({"user": uid, "amount": amt})
    save_data(data)

    keyboard = [[InlineKeyboardButton("Approve", callback_data=f"approve_dep_{dep_id}")]]

    bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"Deposit proof {uid}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    update.message.reply_text("Sent for approval")

# ---------------- ADMIN COMMANDS ----------------
def users(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    data = load_data()
    text = "\n".join([f"{u} : ₹{d['balance']}" for u, d in data["users"].items()])
    update.message.reply_text(text or "No users")

def add(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    uid, amt = context.args
    data = load_data()
    data["users"][uid]["balance"] += int(amt)
    save_data(data)
    update.message.reply_text("Added")

def deduct(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    uid, amt = context.args
    data = load_data()
    data["users"][uid]["balance"] -= int(amt)
    save_data(data)
    update.message.reply_text("Deducted")

def msg(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    message = " ".join(context.args[1:])
    bot.send_message(uid, message)

# ---------------- HANDLERS ----------------
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("users", users))
dp.add_handler(CommandHandler("add", add))
dp.add_handler(CommandHandler("deduct", deduct))
dp.add_handler(CommandHandler("msg", msg))
dp.add_handler(CallbackQueryHandler(button))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text))
dp.add_handler(MessageHandler(Filters.photo, photo))

# ---------------- WEBHOOK ----------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot running"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok"

# ---------------- START ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
