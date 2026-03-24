import json
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216
BOT_USERNAME = "CRYPWIN_BOT"
WEB_APP_URL = "https://jovial-beignet-2537d3.netlify.app/"

QR_TARGET = None

# ===== DATA =====
def load():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# ===== MENU =====
def menu(uid):
    kb = [
        ["🎮 Play Game", "📊 Balance"],
        ["💰 Deposit", "💸 Withdraw"],
        ["🔗 Refer", "🏆 Leaderboard"],
        ["🏠 Menu"]
    ]
    if uid == ADMIN_ID:
        kb.append(["👨‍💻 Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()

    ref = context.args[0] if context.args else None

    if uid not in data:
        data[uid] = {"balance": 20, "deposit_done": False}

        if ref and ref != uid and ref in data:
            data[ref]["balance"] += 30
            await context.bot.send_message(ref, "🎉 ₹30 referral bonus!")

        save(data)
        await update.message.reply_text("🎁 ₹20 bonus credited!")

    await update.message.reply_text("🏠 Menu", reply_markup=menu(update.effective_user.id))

# ===== MAIN =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QR_TARGET

    uid = str(update.effective_user.id)
    data = load()
    text = update.message.text if update.message.text else ""

    # RESET FLOW on new action
    if text in ["🎮 Play Game","📊 Balance","💰 Deposit","💸 Withdraw","🔗 Refer","🏆 Leaderboard","🏠 Menu","👨‍💻 Admin Panel"]:
        context.user_data.clear()

    # BALANCE
    if text == "📊 Balance":
        await update.message.reply_text(f"💰 Balance: ₹{data.get(uid,{}).get('balance',0)}")

    # GAME
    elif text == "🎮 Play Game":
        url = f"{WEB_APP_URL}?uid={uid}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=url))]])
        await update.message.reply_text("🔥 Open Game", reply_markup=kb)

    # ===== DEPOSIT =====
    elif text == "💰 Deposit":
        await update.message.reply_text("Enter amount (min ₹101):")
        context.user_data["action"] = "deposit_amount"

    elif context.user_data.get("action") == "deposit_amount":
        try:
            amt = int(text)
            if amt < 101:
                await update.message.reply_text("❌ Minimum ₹101")
                return

            context.user_data["deposit_amt"] = amt
            await context.bot.send_message(ADMIN_ID, f"Deposit Request\nUser: {uid}\nAmount: ₹{amt}\nUse /sendqr {uid}")
            await update.message.reply_text("⏳ Waiting for QR from admin")
            context.user_data["action"] = "waiting_qr"

        except:
            await update.message.reply_text("❗ Enter valid number")

    # ADMIN SEND QR
    elif update.message.photo and update.effective_user.id == ADMIN_ID:
        if QR_TARGET:
            await context.bot.send_photo(QR_TARGET, update.message.photo[-1].file_id, caption="Scan & Pay, then send screenshot")
            await update.message.reply_text("✅ QR sent")
            QR_TARGET = None

    # USER SEND SCREENSHOT
    elif update.message.photo and context.user_data.get("deposit_amt"):
        amt = context.user_data["deposit_amt"]

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}_{amt}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")]
        ])

        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id,
                                     caption=f"Deposit Proof\nUser: {uid}\n₹{amt}",
                                     reply_markup=kb)

        await update.message.reply_text("✅ Sent for admin approval")
        context.user_data.clear()

    # ===== WITHDRAW =====
    elif text == "💸 Withdraw":
        if not data.get(uid,{}).get("deposit_done"):
            await update.message.reply_text("❌ You must deposit first")
            return

        await update.message.reply_text("Enter amount:")
        context.user_data["action"] = "withdraw_amount"

    elif context.user_data.get("action") == "withdraw_amount":
        try:
            amt = int(text)

            if amt > data[uid]["balance"]:
                await update.message.reply_text("❌ Insufficient balance")
                return

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"wapprove_{uid}_{amt}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"wreject_{uid}")]
            ])

            await context.bot.send_message(ADMIN_ID, f"Withdraw Request\nUser: {uid}\n₹{amt}", reply_markup=kb)
            await update.message.reply_text("⏳ Waiting admin approval")
            context.user_data.clear()

        except:
            await update.message.reply_text("❗ Enter valid number")

    # ===== REFER =====
    elif text == "🔗 Refer":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await update.message.reply_text(f"Invite & earn ₹30 💸\n{link}")

    # ===== LEADERBOARD =====
    elif text == "🏆 Leaderboard":
        sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
        msg = "🏆 Top Players:\n\n"
        for i,(u,v) in enumerate(sorted_users[:10]):
            msg += f"{i+1}. {u} → ₹{v['balance']}\n"
        await update.message.reply_text(msg)

    # ===== ADMIN PANEL =====
    elif text == "👨‍💻 Admin Panel" and int(uid) == ADMIN_ID:
        await update.message.reply_text("Admin Panel:\n📊 Stats\n📋 Users\n➕ Add\n➖ Deduct")

    elif text == "📊 Stats" and int(uid) == ADMIN_ID:
        total = sum(u["balance"] for u in data.values())
        await update.message.reply_text(f"Users: {len(data)}\nTotal Balance: ₹{total}")

    elif text == "📋 Users" and int(uid) == ADMIN_ID:
        msg = "\n".join([f"{u} → ₹{data[u]['balance']}" for u in data])
        await update.message.reply_text(msg[:4000])

# ===== BUTTONS =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load()

    d = query.data.split("_")

    if d[0] == "approve":
        uid, amt = d[1], int(d[2])
        data[uid]["balance"] += amt
        data[uid]["deposit_done"] = True
        save(data)
        await context.bot.send_message(uid, f"✅ Deposit ₹{amt} approved")
        await query.edit_message_caption("Approved")

    elif d[0] == "reject":
        await context.bot.send_message(d[1], "❌ Deposit rejected")
        await query.edit_message_caption("Rejected")

    elif d[0] == "wapprove":
        await context.bot.send_message(d[1], "✅ Fund transferred, check account")
        await query.edit_message_text("Withdraw Approved")

    elif d[0] == "wreject":
        await context.bot.send_message(d[1], "❌ Withdraw rejected")
        await query.edit_message_text("Rejected")

# ===== SEND QR =====
async def sendqr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QR_TARGET
    if update.effective_user.id == ADMIN_ID:
        QR_TARGET = context.args[0]
        await update.message.reply_text("Now send QR image")

# ===== INIT BOT =====
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("sendqr", sendqr))
bot_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle))
bot_app.add_handler(CallbackQueryHandler(button))

# ===== FLASK =====
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def home():
    return "Bot running 🚀"

# ===== START =====
if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(bot_app.initialize())
    asyncio.get_event_loop().run_until_complete(bot_app.start())
    app.run(host="0.0.0.0", port=10000)
