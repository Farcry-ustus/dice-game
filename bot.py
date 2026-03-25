import json
import os
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw")
ADMIN_ID = int(os.getenv("8190804216"))
GAME_URL = "https://jovial-beignet-2537d3.netlify.app/"  # 🔥 PUT YOUR LINK

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

# ---------------- BOT ----------------
telegram_app = ApplicationBuilder().token(TOKEN).build()

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    uid = str(user.id)

    if uid not in data["users"]:
        ref = context.args[0] if context.args else None
        data["users"][uid] = {"balance": 0, "deposit": 0}

        if ref and ref in data["users"]:
            data["users"][ref]["balance"] += 30
            await context.bot.send_message(
                ref,
                f"🎉 You invited {user.first_name} and earned ₹30!"
            )

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

    await update.message.reply_text("🏠 Main Menu", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BUTTON ----------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    data = load_data()

    if q.data == "deposit":
        context.user_data["state"] = "enter_amount"
        await q.message.reply_text("💰 Enter deposit amount (min ₹101)")

    elif q.data == "withdraw":
        if data["users"][uid]["deposit"] < 101:
            await q.message.reply_text("❌ You must deposit ₹101 first")
            return

        context.user_data["state"] = "withdraw_amount"
        await q.message.reply_text("💸 Enter withdraw amount (>100)")

    elif q.data == "ref":
        link = f"https://t.me/YOUR_BOT_USERNAME?start={uid}"
        await q.message.reply_text(f"🔗 Your link:\n{link}")

    elif q.data == "leader":
        await q.message.reply_text(
            "🏆 Leaderboard:\n"
            "1. Laksmin Raja ₹4313\n"
            "2. Harshit ₹3409\n"
            "3. Taruni ₹3300\n"
            "4. Yusufi ₹3090\n"
            "5. Dhruv ₹2908"
        )

    elif q.data == "admin":
        if q.from_user.id != ADMIN_ID:
            return
        keyboard = [
            [InlineKeyboardButton("👥 Users", callback_data="users")],
            [InlineKeyboardButton("➕ Add Balance", callback_data="add")],
            [InlineKeyboardButton("➖ Deduct Balance", callback_data="deduct")],
            [InlineKeyboardButton("💬 Message User", callback_data="msg")]
        ]
        await q.message.reply_text("👨‍💻 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- TEXT HANDLER ----------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)
    data = load_data()

    state = context.user_data.get("state")

    # -------- DEPOSIT FLOW --------
    if state == "enter_amount":
        amount = int(text)
        if amount < 101:
            await update.message.reply_text("❌ Minimum ₹101")
            return

        context.user_data["amount"] = amount
        context.user_data["state"] = "wait_qr"

        await context.bot.send_message(
            ADMIN_ID,
            f"💳 User {uid} wants to deposit ₹{amount}\nSend QR image now"
        )

        await update.message.reply_text("⏳ Waiting for admin QR...")

    # -------- WITHDRAW FLOW --------
    elif state == "withdraw_amount":
        amount = int(text)
        if amount <= 100:
            await update.message.reply_text("❌ Must be >100")
            return

        if data["users"][uid]["balance"] < amount:
            await update.message.reply_text("❌ Insufficient balance")
            return

        context.user_data["amount"] = amount
        context.user_data["state"] = "bank_details"

        await update.message.reply_text("🏦 Send Account Number & IFSC")

    elif state == "bank_details":
        details = text
        amount = context.user_data["amount"]

        data["withdraws"].append({
            "user": uid,
            "amount": amount,
            "details": details
        })
        save_data(data)

        wid = len(data["withdraws"]) - 1

        keyboard = [[InlineKeyboardButton("Approve Withdraw", callback_data=f"w_{wid}")]]

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\nUser: {uid}\nAmount: ₹{amount}\nDetails:\n{details}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("⏳ Withdrawal sent to admin")

# ---------------- PHOTO HANDLER ----------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()

    if context.user_data.get("state") == "wait_qr":
        # ADMIN sending QR
        if update.effective_user.id == ADMIN_ID:
            user_id = context.user_data.get("target_user")
            await context.bot.send_photo(user_id, update.message.photo[-1].file_id)
            return

    # USER sending payment proof
    dep_id = len(data["deposits"])
    data["deposits"].append({
        "user": uid,
        "amount": context.user_data.get("amount", 100)
    })
    save_data(data)

    keyboard = [[InlineKeyboardButton("Approve", callback_data=f"d_{dep_id}")]]
    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"Deposit proof from {uid}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("✅ Sent for approval")

# ---------------- APPROVAL ----------------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = load_data()

    if q.data.startswith("d_"):
        i = int(q.data.split("_")[1])
        dep = data["deposits"][i]

        uid = dep["user"]
        amt = dep["amount"]

        data["users"][uid]["balance"] += amt
        data["users"][uid]["deposit"] += amt
        save_data(data)

        await context.bot.send_message(uid, f"✅ Deposit ₹{amt} approved")

    if q.data.startswith("w_"):
        i = int(q.data.split("_")[1])
        wd = data["withdraws"][i]

        uid = wd["user"]
        amt = wd["amount"]

        data["users"][uid]["balance"] -= amt
        save_data(data)

        await context.bot.send_message(uid, "✅ Withdrawal successful")

# ---------------- HANDLERS ----------------
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button))
telegram_app.add_handler(CallbackQueryHandler(approve))
telegram_app.add_handler(MessageHandler(filters.TEXT, text_handler))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

# ---------------- WEBHOOK ----------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot running"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "ok"

# ---------------- START ----------------
async def init():
    await telegram_app.initialize()
    await telegram_app.start()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
