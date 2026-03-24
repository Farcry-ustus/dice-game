import json
import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

BOT_TOKEN = "8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216
BOT_USERNAME = "CRYPWIN_BOT"

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
    uid = str(update.effective_user.id)
    data = load()
    text = update.message.text if update.message.text else ""

    if uid not in data:
        data[uid] = {"balance":0,"deposit_total":0}

    if text in ["🎮 Play Game","📊 Balance","💰 Deposit","💸 Withdraw","🔗 Refer","🏆 Leaderboard","🏠 Menu","👨‍💻 Admin Panel"]:
        context.user_data.clear()

    if text == "📊 Balance":
        await update.message.reply_text(f"💰 ₹{data[uid]['balance']}")

    elif text == "💰 Deposit":
        await update.message.reply_text("Send payment screenshot directly")

    elif update.message.photo:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}_100"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")]
        ])
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id,
                                     caption=f"Deposit proof from {uid}",
                                     reply_markup=kb)
        await update.message.reply_text("⏳ Sent to admin")

    elif text == "💸 Withdraw":
        if data[uid]["deposit_total"] < 101:
            await update.message.reply_text("❌ Deposit ₹101 first")
            return
        await context.bot.send_message(ADMIN_ID, f"Withdraw request from {uid}")
        await update.message.reply_text("⏳ Request sent")

    elif text == "🔗 Refer":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await update.message.reply_text(f"Earn ₹30 per referral:\n{link}")

    elif text == "🏆 Leaderboard":
        sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
        msg = "🏆 Top Players\n\n"
        for i,(u,v) in enumerate(sorted_users[:10]):
            msg += f"{i+1}. {u} → ₹{v['balance']}\n"
        await update.message.reply_text(msg)

# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load()
    d = query.data.split("_")

    if d[0] == "approve":
        uid = d[1]
        amt = int(d[2])
        data[uid]["balance"] += amt
        data[uid]["deposit_total"] += amt
        save(data)
        await context.bot.send_message(uid, f"✅ ₹{amt} added")
        await query.edit_message_caption("Approved")

    elif d[0] == "reject":
        await context.bot.send_message(d[1], "❌ Rejected")
        await query.edit_message_caption("Rejected")

# ===== BOT =====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle))
app.add_handler(CallbackQueryHandler(button))

print("Bot running...")

app.run_polling()
