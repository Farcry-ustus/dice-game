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

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GAME_URL = "https://jovial-beignet-2537d3.netlify.app/"

DATA_FILE = "users.json"

# ---------------- DATABASE ----------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "deposits": [], "withdraws": [], "pending_qr": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- INIT ----------------
telegram_app = ApplicationBuilder().token(TOKEN).build()
app = Flask(__name__)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()

    if uid not in data["users"]:
        ref = context.args[0] if context.args else None
        data["users"][uid] = {"balance": 0, "deposit": 0}

        if ref and ref in data["users"]:
            data["users"][ref]["balance"] += 30
            await context.bot.send_message(
                ref, f"🎉 You invited {user.first_name} and earned ₹30!"
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
        context.user_data["state"] = "deposit_amount"
        await q.message.reply_text("💰 Enter amount (min ₹101)")

    elif q.data == "withdraw":
        if data["users"][uid]["deposit"] < 101:
            await q.message.reply_text("❌ Deposit ₹101 first")
            return
        context.user_data["state"] = "withdraw_amount"
        await q.message.reply_text("💸 Enter withdraw amount (>100)")

    elif q.data == "ref":
        link = f"https://t.me/YOUR_BOT_USERNAME?start={uid}"
        await q.message.reply_text(f"🔗 Referral:\n{link}")

    elif q.data == "leader":
        await q.message.reply_text(
            "🏆 Leaderboard:\n"
            "1. Laksmin Raja ₹4313\n"
            "2. Harshit ₹3409\n"
            "3. Taruni ₹3300\n"
            "4. Yusufi ₹3090\n"
            "5. Dhruv ₹2908"
        )

    elif q.data == "admin" and q.from_user.id == ADMIN_ID:
        await q.message.reply_text(
            "👨‍💻 Admin Commands:\n"
            "/users\n/add user_id amount\n/deduct user_id amount\n/msg user_id message"
        )

    elif q.data.startswith("approve_dep_"):
        i = int(q.data.split("_")[-1])
        dep = data["deposits"][i]
        uid2 = dep["user"]
        amt = dep["amount"]

        data["users"][uid2]["balance"] += amt
        data["users"][uid2]["deposit"] += amt
        save_data(data)

        await context.bot.send_message(uid2, f"✅ Deposit ₹{amt} approved")

    elif q.data.startswith("approve_wd_"):
        i = int(q.data.split("_")[-1])
        wd = data["withdraws"][i]
        uid2 = wd["user"]
        amt = wd["amount"]

        data["users"][uid2]["balance"] -= amt
        save_data(data)

        await context.bot.send_message(uid2, "✅ Withdrawal successful")

# ---------------- TEXT ----------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text
    data = load_data()
    state = context.user_data.get("state")

    # DEPOSIT
    if state == "deposit_amount":
        amt = int(text)
        if amt < 101:
            await update.message.reply_text("❌ Minimum ₹101")
            return

        context.user_data["amount"] = amt
        data["pending_qr"][uid] = amt
        save_data(data)

        await context.bot.send_message(
            ADMIN_ID,
            f"💳 User {uid} wants to deposit ₹{amt}\nSend QR image now"
        )
        await update.message.reply_text("⏳ Waiting for QR...")

    # WITHDRAW
    elif state == "withdraw_amount":
        amt = int(text)
        if amt <= 100 or data["users"][uid]["balance"] < amt:
            await update.message.reply_text("❌ Invalid amount")
            return

        context.user_data["amount"] = amt
        context.user_data["state"] = "bank"
        await update.message.reply_text("🏦 Send Account + IFSC")

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

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw\nUser: {uid}\n₹{amt}\n{text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("⏳ Sent to admin")

# ---------------- PHOTO ----------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()

    # ADMIN sending QR
    if update.effective_user.id == ADMIN_ID:
        if data["pending_qr"]:
            user_id = list(data["pending_qr"].keys())[0]
            await context.bot.send_photo(user_id, update.message.photo[-1].file_id)
            await context.bot.send_message(user_id, "📸 Send payment screenshot after paying")
            return

    # USER sending proof
    dep_id = len(data["deposits"])
    amt = data["pending_qr"].get(uid, 100)

    data["deposits"].append({"user": uid, "amount": amt})
    data["pending_qr"].pop(uid, None)
    save_data(data)

    keyboard = [[InlineKeyboardButton("Approve", callback_data=f"approve_dep_{dep_id}")]]

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"Deposit proof {uid}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("✅ Sent for approval")

# ---------------- ADMIN COMMANDS ----------------
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data = load_data()
    text = "\n".join([f"{u} : ₹{d['balance']}" for u, d in data["users"].items()])
    await update.message.reply_text(text or "No users")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid, amt = context.args
    data = load_data()
    data["users"][uid]["balance"] += int(amt)
    save_data(data)
    await update.message.reply_text("Added")

async def deduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid, amt = context.args
    data = load_data()
    data["users"][uid]["balance"] -= int(amt)
    save_data(data)
    await update.message.reply_text("Deducted")

async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    message = " ".join(context.args[1:])
    await context.bot.send_message(uid, message)

# ---------------- HANDLERS ----------------
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("users", users))
telegram_app.add_handler(CommandHandler("add", add))
telegram_app.add_handler(CommandHandler("deduct", deduct))
telegram_app.add_handler(CommandHandler("msg", msg))
telegram_app.add_handler(CallbackQueryHandler(button))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

# ---------------- WEBHOOK ----------------
@app.route("/", methods=["GET"])
def home():
    return "Bot running"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "ok"

# ---------------- START ----------------
async def main():
    await telegram_app.initialize()
    await telegram_app.start()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
