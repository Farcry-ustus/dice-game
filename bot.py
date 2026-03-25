import json
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216

app = Flask(__name__)

DATA_FILE = "data.json"

# ---------------- DATABASE ----------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "deposits": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()

    if str(user.id) not in data["users"]:
        ref = context.args[0] if context.args else None
        data["users"][str(user.id)] = {
            "balance": 0,
            "deposit": 0,
            "ref": ref
        }

        # referral bonus
        if ref and ref in data["users"]:
            data["users"][ref]["balance"] += 30

    save_data(data)

    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🔗 Referral", callback_data="ref")],
        [InlineKeyboardButton("📊 Leaderboard", callback_data="leader")],
    ]

    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👨‍💻 Admin Panel", callback_data="admin")])

    await update.message.reply_text("🏠 Main Menu", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BUTTON HANDLER ----------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    user_id = str(query.from_user.id)

    if query.data == "deposit":
        await query.message.reply_text("📸 Send deposit screenshot")

    elif query.data == "withdraw":
        if data["users"][user_id]["deposit"] < 101:
            await query.message.reply_text("❌ Deposit ₹101 first")
            return
        await query.message.reply_text("💸 Send withdraw amount")

    elif query.data == "ref":
        link = f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"
        await query.message.reply_text(f"🔗 Your referral link:\n{link}")

    elif query.data == "leader":
        users = sorted(data["users"].items(), key=lambda x: x[1]["balance"], reverse=True)
        text = "🏆 Leaderboard:\n"
        for i, u in enumerate(users[:5]):
            text += f"{i+1}. {u[0]} - ₹{u[1]['balance']}\n"
        await query.message.reply_text(text)

    elif query.data == "admin":
        if query.from_user.id != ADMIN_ID:
            return
        keyboard = [
            [InlineKeyboardButton("View Users", callback_data="view_users")],
            [InlineKeyboardButton("Stats", callback_data="stats")]
        ]
        await query.message.reply_text("👨‍💻 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "view_users":
        text = ""
        for uid, u in data["users"].items():
            text += f"{uid} → ₹{u['balance']}\n"
        await query.message.reply_text(text or "No users")

    elif query.data == "stats":
        total = sum(u["balance"] for u in data["users"].values())
        await query.message.reply_text(f"📊 Total Balance: ₹{total}")

    elif query.data.startswith("approve_"):
        dep_id = int(query.data.split("_")[1])
        dep = data["deposits"][dep_id]

        uid = dep["user"]
        amount = dep["amount"]

        data["users"][uid]["balance"] += amount
        data["users"][uid]["deposit"] += amount

        await context.bot.send_message(uid, f"✅ Deposit Approved ₹{amount}")

        data["deposits"].pop(dep_id)
        save_data(data)

        await query.message.reply_text("Approved ✅")

# ---------------- HANDLE SCREENSHOT ----------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    user_id = str(update.effective_user.id)

    dep_id = len(data["deposits"])
    data["deposits"].append({
        "user": user_id,
        "amount": 100  # you can later make dynamic
    })

    save_data(data)

    keyboard = [[InlineKeyboardButton("Approve", callback_data=f"approve_{dep_id}")]]
    await context.bot.send_photo(
        ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"Deposit request from {user_id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("✅ Sent to admin for approval")

# ---------------- FLASK WEBHOOK ----------------
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button))
telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    telegram_app.initialize()
    telegram_app.start()
    app.run(host="0.0.0.0", port=10000)
