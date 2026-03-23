import json
import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN ="8749615890:AAHqCJAy7Dr23sXF6Z37YrIjxbCMKZ8Vuxw"
ADMIN_ID = 8190804216
BOT_USERNAME = "CRYPWIN_BOT"
WEB_APP_URL = "https://jovial-beignet-2537d3.netlify.app/"  # 🔥 put your netlify link

# ---------- DATA ----------
def load():
    try:
        with open("users.json","r") as f:
            return json.load(f)
    except:
        return {}

def save(d):
    with open("users.json","w") as f:
        json.dump(d,f,indent=4)

# ---------- MENU ----------
def menu(user_id):
    keyboard = [
        ["🎮 Play Game","📊 Balance"],
        ["💰 Deposit","💸 Withdraw"],
        ["🔗 Refer","🏆 Leaderboard"]
    ]
    if user_id == ADMIN_ID:
        keyboard.append(["👨‍💻 Admin Panel"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()

    ref = context.args[0] if context.args else None

    if uid not in data:
        data[uid] = {
            "balance": 20,
            "deposit_done": False
        }

        # referral bonus
        if ref and ref != uid and ref in data:
            data[ref]["balance"] += 30
            await context.bot.send_message(ref, "🎉 ₹30 referral bonus added!")

        save(data)

        await update.message.reply_text("🎁 You got ₹20 bonus!")

    await update.message.reply_text("🏠 Menu", reply_markup=menu(update.effective_user.id))

# ---------- MAIN ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load()
    text = update.message.text

    # MENU BUTTON
    if text == "🏠 Menu":
        await update.message.reply_text("🏠 Menu", reply_markup=menu(update.effective_user.id))

    # BALANCE
    elif text == "📊 Balance":
        await update.message.reply_text(f"💰 Balance: ₹{data.get(uid,{}).get('balance',0)}")

    # PLAY GAME (MINI APP)
    elif text == "🎮 Play Game":
        url = f"{WEB_APP_URL}?uid={uid}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=url))]
        ])

        await update.message.reply_text("🔥 Open Game:", reply_markup=keyboard)

    # REFER
    elif text == "🔗 Refer":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await update.message.reply_text(f"Invite & earn ₹30 💸\n{link}")

    # LEADERBOARD
    elif text == "🏆 Leaderboard":
        sorted_users = sorted(data.items(), key=lambda x: x[1]["balance"], reverse=True)
        msg = "🏆 Top Players:\n\n"

        for i, (u, d) in enumerate(sorted_users[:10]):
            msg += f"{i+1}. {u} → ₹{d['balance']}\n"

        await update.message.reply_text(msg)

    # DEPOSIT
    elif text == "💰 Deposit":
        await update.message.reply_text("Enter deposit amount (min ₹101):")
        context.user_data["action"] = "deposit"

    elif context.user_data.get("action") == "deposit":
        try:
            amt = int(text)
            if amt < 101:
                await update.message.reply_text("❌ Minimum ₹101")
                return

            context.user_data["amt"] = amt
            await context.bot.send_message(ADMIN_ID, f"User {uid} wants to deposit ₹{amt}")
            await update.message.reply_text("⏳ Waiting for admin approval")
            context.user_data.clear()
        except:
            await update.message.reply_text("❗ Enter valid number")

    # WITHDRAW
    elif text == "💸 Withdraw":
        if not data.get(uid, {}).get("deposit_done"):
            await update.message.reply_text("❌ Deposit first to withdraw")
            return

        await update.message.reply_text("Enter amount (min ₹300):")
        context.user_data["action"] = "withdraw"

    elif context.user_data.get("action") == "withdraw":
        try:
            amt = int(text)
            if amt < 300:
                await update.message.reply_text("❌ Minimum ₹300")
                return

            if amt > data[uid]["balance"]:
                await update.message.reply_text("❌ Insufficient balance")
                return

            data[uid]["balance"] -= amt
            save(data)

            await context.bot.send_message(ADMIN_ID, f"Withdraw request\nUser: {uid}\nAmount: ₹{amt}")
            await update.message.reply_text("✅ Request sent")
            context.user_data.clear()

        except:
            await update.message.reply_text("❗ Enter valid number")

    # ADMIN PANEL
    elif text == "👨‍💻 Admin Panel" and update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Admin Panel",
            reply_markup=ReplyKeyboardMarkup([["➕ Add","➖ Deduct"],["🏠 Menu"]], resize_keyboard=True))

    elif text == "➕ Add" and update.effective_user.id == ADMIN_ID:
        context.user_data["action"] = "add_user"
        await update.message.reply_text("User ID:")

    elif context.user_data.get("action") == "add_user":
        context.user_data["target"] = text
        context.user_data["action"] = "add_amt"
        await update.message.reply_text("Amount:")

    elif context.user_data.get("action") == "add_amt":
        uid2 = context.user_data["target"]
        amt = int(text)

        if uid2 not in data:
            data[uid2] = {"balance":0,"deposit_done":True}

        data[uid2]["balance"] += amt
        save(data)

        await context.bot.send_message(uid2, f"₹{amt} added")
        await update.message.reply_text("Done")
        context.user_data.clear()

    elif text == "➖ Deduct" and update.effective_user.id == ADMIN_ID:
        context.user_data["action"] = "ded_user"
        await update.message.reply_text("User ID:")

    elif context.user_data.get("action") == "ded_user":
        context.user_data["target"] = text
        context.user_data["action"] = "ded_amt"
        await update.message.reply_text("Amount:")

    elif context.user_data.get("action") == "ded_amt":
        uid2 = context.user_data["target"]
        amt = int(text)

        data[uid2]["balance"] -= amt
        save(data)

        await context.bot.send_message(uid2, f"₹{amt} deducted")
        await update.message.reply_text("Done")
        context.user_data.clear()

# ---------- RUN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

print("Bot running...")
app.run_polling()
