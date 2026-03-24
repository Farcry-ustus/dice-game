import os
import json
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = "8190804216"
RENDER_URL = "https://dice-game-16.onrender.com"

DATA_FILE = "users.json"

# ---------- DATABASE ----------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

users = load_data()

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "balance": 0,
            "ref": None,
            "deposited": 0
        }
    return users[uid]

# ---------- BOT ----------
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    args = context.args
    if args:
        ref_id = args[0]
        if ref_id != uid:
            get_user(uid)["ref"] = ref_id
            if ref_id in users:
                users[ref_id]["balance"] += 30

    save_data(users)

    keyboard = [
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("📊 Balance", callback_data="balance")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leader")],
        [InlineKeyboardButton("🔗 Refer", callback_data="refer")]
    ]

    await update.message.reply_text(
        "🎮 Welcome to Dice Game Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- BUTTON HANDLER ----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = str(query.from_user.id)
    user = get_user(uid)

    if query.data == "balance":
        await query.message.reply_text(f"💰 Balance: ₹{user['balance']}")

    elif query.data == "deposit":
        await query.message.reply_text("📥 Send screenshot after payment.")
        await context.bot.send_message(ADMIN_ID, f"User {uid} wants to deposit.")

    elif query.data == "withdraw":
        if user["deposited"] < 101:
            await query.message.reply_text("❌ Deposit ₹101 minimum first")
        else:
            await context.bot.send_message(ADMIN_ID, f"Withdraw request from {uid}")
            await query.message.reply_text("⏳ Withdrawal request sent")

    elif query.data == "refer":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await query.message.reply_text(f"🔗 Your link:\n{link}")

    elif query.data == "leader":
        top = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:5]
        text = "🏆 Leaderboard:\n"
        for i, (u, d) in enumerate(top):
            text += f"{i+1}. {u} - ₹{d['balance']}\n"
        await query.message.reply_text(text)

# ---------- ADMIN COMMANDS ----------
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    uid = context.args[0]
    amount = int(context.args[1])

    get_user(uid)["balance"] += amount
    get_user(uid)["deposited"] += amount

    save_data(users)

    await context.bot.send_message(uid, f"✅ ₹{amount} added")
    await update.message.reply_text("Done")

async def deduct_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    uid = context.args[0]
    amount = int(context.args[1])

    get_user(uid)["balance"] -= amount

    save_data(users)

    await context.bot.send_message(uid, f"❌ ₹{amount} deducted")
    await update.message.reply_text("Done")

# ---------- REGISTER ----------
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CallbackQueryHandler(button))
app_bot.add_handler(CommandHandler("add", add_balance))
app_bot.add_handler(CommandHandler("deduct", deduct_balance))

# ---------- FLASK ----------
flask_app = Flask(__name__)

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, app_bot.bot)
    await app_bot.process_update(update)
    return "ok"

@flask_app.route("/")
def home():
    return "Bot Running"

# ---------- START ----------
if __name__ == "__main__":
    import asyncio

    async def main():
        await app_bot.initialize()
        await app_bot.bot.set_webhook(f"{RENDER_URL}/{BOT_TOKEN}")

    asyncio.run(main())

    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
