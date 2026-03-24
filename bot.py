import json
import os
import asyncio
from flask import Flask, request
from telegram import *
from telegram.ext import *

BOT_TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216
BOT_USERNAME = "CRYPWIN_BOT"

QR_TARGET = None

# ===== DATA =====
def load():
    try:
        return json.load(open("users.json"))
    except:
        return {}

def save(data):
    json.dump(data, open("users.json","w"), indent=4)

# ===== MENU =====
def menu(uid):
    kb = [
        ["🎮 Play Game","📊 Balance"],
        ["💰 Deposit","💸 Withdraw"],
        ["🔗 Refer","🏆 Leaderboard"],
        ["🏠 Menu"]
    ]
    if int(uid) == ADMIN_ID:
        kb.append(["👨‍💻 Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()

    ref = context.args[0] if context.args else None

    if uid not in data:
        data[uid] = {"balance":20,"deposit_total":0}

        if ref and ref != uid and ref in data:
            data[ref]["balance"] += 30
            await context.bot.send_message(ref,"🎉 ₹30 referral bonus!")

        save(data)
        await update.message.reply_text("🎁 ₹20 bonus credited!")

    await update.message.reply_text("🏠 Menu", reply_markup=menu(uid))

# ===== MAIN =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QR_TARGET

    uid = str(update.effective_user.id)
    data = load()
    text = update.message.text if update.message.text else ""

    if uid not in data:
        data[uid] = {"balance":0,"deposit_total":0}

    # RESET FLOW
    if text in ["🎮 Play Game","📊 Balance","💰 Deposit","💸 Withdraw","🔗 Refer","🏆 Leaderboard","🏠 Menu","👨‍💻 Admin Panel"]:
        context.user_data.clear()

    # BALANCE
    if text == "📊 Balance":
        await update.message.reply_text(f"💰 ₹{data[uid]['balance']}")

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
            await context.bot.send_message(ADMIN_ID, f"User {uid} wants deposit ₹{amt}\nUse /sendqr {uid}")
            await update.message.reply_text("⏳ Waiting for QR")
            context.user_data["action"] = "wait_qr"
        except:
            await update.message.reply_text("Enter valid number")

    # ADMIN SEND QR
    elif update.message.photo and update.effective_user.id == ADMIN_ID:
        if QR_TARGET:
            await context.bot.send_photo(QR_TARGET, update.message.photo[-1].file_id, caption="Scan & Pay then send screenshot")
            await update.message.reply_text("✅ QR Sent")
            QR_TARGET = None

    # USER SEND SCREENSHOT
    elif update.message.photo and context.user_data.get("deposit_amt"):
        amt = context.user_data["deposit_amt"]

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}_{amt}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")]
        ])

        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id,
                                    caption=f"Deposit Proof\nUser:{uid}\n₹{amt}",
                                    reply_markup=kb)

        await update.message.reply_text("✅ Sent for approval")
        context.user_data.clear()

    # ===== WITHDRAW =====
    elif text == "💸 Withdraw":
        if data[uid]["deposit_total"] < 101:
            await update.message.reply_text("❌ Deposit ₹101 first")
            return

        await update.message.reply_text("Enter amount:")
        context.user_data["action"] = "withdraw_amt"

    elif context.user_data.get("action") == "withdraw_amt":
        try:
            amt = int(text)

            if amt > data[uid]["balance"]:
                await update.message.reply_text("❌ Insufficient balance")
                return

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"wapprove_{uid}_{amt}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"wreject_{uid}")]
            ])

            await context.bot.send_message(ADMIN_ID, f"Withdraw Request\nUser:{uid}\n₹{amt}", reply_markup=kb)
            await update.message.reply_text("⏳ Waiting admin approval")
            context.user_data.clear()

        except:
            await update.message.reply_text("Enter valid number")

    # ===== REFER =====
    elif text == "🔗 Refer":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await update.message.reply_text(f"Invite & earn ₹30\n{link}")

    # ===== LEADERBOARD =====
    elif text == "🏆 Leaderboard":
        sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
        msg = "🏆 Top Players\n\n"
        for i,(u,v) in enumerate(sorted_users[:10]):
            msg += f"{i+1}. {u} → ₹{v['balance']}\n"
        await update.message.reply_text(msg)

    # ===== ADMIN PANEL =====
    elif text == "👨‍💻 Admin Panel" and int(uid) == ADMIN_ID:
        await update.message.reply_text("Admin:\n📊 Stats\n📋 Users\n➕ Add\n➖ Deduct")

    elif text == "📊 Stats" and int(uid) == ADMIN_ID:
        total = sum(u["balance"] for u in data.values())
        await update.message.reply_text(f"Users:{len(data)}\nTotal ₹{total}")

    elif text == "📋 Users" and int(uid) == ADMIN_ID:
        msg = "\n".join([f"{u} → ₹{data[u]['balance']}" for u in data])
        await update.message.reply_text(msg[:4000])

    elif text == "➕ Add" and int(uid) == ADMIN_ID:
        await update.message.reply_text("User ID:")
        context.user_data["action"] = "add_user"

    elif context.user_data.get("action") == "add_user":
        context.user_data["target"] = text
        await update.message.reply_text("Amount:")
        context.user_data["action"] = "add_amt"

    elif context.user_data.get("action") == "add_amt":
        uid2 = context.user_data["target"]
        amt = int(text)
        data[uid2]["balance"] += amt
        save(data)
        await context.bot.send_message(uid2, f"₹{amt} added")
        await update.message.reply_text("Done")
        context.user_data.clear()

    elif text == "➖ Deduct" and int(uid) == ADMIN_ID:
        await update.message.reply_text("User ID:")
        context.user_data["action"] = "ded_user"

    elif context.user_data.get("action") == "ded_user":
        context.user_data["target"] = text
        await update.message.reply_text("Amount:")
        context.user_data["action"] = "ded_amt"

    elif context.user_data.get("action") == "ded_amt":
        uid2 = context.user_data["target"]
        amt = int(text)
        data[uid2]["balance"] -= amt
        save(data)
        await context.bot.send_message(uid2, f"₹{amt} deducted")
        await update.message.reply_text("Done")
        context.user_data.clear()

# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load()
    d = query.data.split("_")

    if d[0] == "approve":
        uid, amt = d[1], int(d[2])
        data[uid]["balance"] += amt
        data[uid]["deposit_total"] += amt
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
        await update.message.reply_text("Send QR image now")

# ===== BOT =====
bot = ApplicationBuilder().token(BOT_TOKEN).build()
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("sendqr", sendqr))
bot.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle))
bot.add_handler(CallbackQueryHandler(button))

# ===== FLASK =====
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot.bot)
    asyncio.run(bot.process_update(update))
    return "ok"

@app.route("/")
def home():
    return "Bot running"

# ===== START =====
if __name__ == "__main__":
    asyncio.run(bot.initialize())
    asyncio.run(bot.start())
    app.run(host="0.0.0.0", port=10000)
