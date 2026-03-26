"""
NyayaBot Telegram Bot
Deploy policy chatbot on Telegram
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

sys.path.append(str(Path(__file__).parent.parent))
from rag.engine import NyayaBotRAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== INIT =====
engine = NyayaBotRAGEngine(api_key=os.getenv("ANTHROPIC_API_KEY"))
user_sessions: Dict[int, Dict] = {}  # user_id -> {lang, history}

# ===== LANGUAGE SELECTION KEYBOARD =====
LANG_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
     InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi")],
    [InlineKeyboardButton("தமிழ்", callback_data="lang_ta"),
     InlineKeyboardButton("বাংলা", callback_data="lang_bn")],
    [InlineKeyboardButton("తెలుగు", callback_data="lang_te"),
     InlineKeyboardButton("मराठी", callback_data="lang_mr")],
    [InlineKeyboardButton("ગુજરાતી", callback_data="lang_gu"),
     InlineKeyboardButton("ಕನ್ನಡ", callback_data="lang_kn")]
])

WELCOME_MSG = """🏛 *Welcome to NyayaBot!*

I help Indian citizens understand government schemes and welfare policies.

Ask me about:
• Eligibility for welfare schemes
• Benefits and amounts
• How to apply
• Required documents

Type /language to change language.
Type /schemes to see popular schemes.
Type /help for more commands.

_What would you like to know?_"""

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {"lang": "en", "history": []}
    await update.message.reply_text(
        WELCOME_MSG, parse_mode="Markdown",
        reply_markup=LANG_KEYBOARD
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *NyayaBot Commands*\n\n"
        "/start — Restart the bot\n"
        "/language — Change response language\n"
        "/schemes — Browse popular schemes\n"
        "/clear — Clear conversation history\n"
        "/about — About NyayaBot\n\n"
        "Simply type your question to get started!",
        parse_mode="Markdown"
    )

async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 Choose your preferred language:",
        reply_markup=LANG_KEYBOARD
    )

async def schemes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schemes_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌾 PM-KISAN", callback_data="scheme_PM-KISAN"),
         InlineKeyboardButton("🏠 PM Awas", callback_data="scheme_PM Awas Yojana")],
        [InlineKeyboardButton("🏥 Ayushman", callback_data="scheme_Ayushman Bharat"),
         InlineKeyboardButton("👷 MGNREGA", callback_data="scheme_MGNREGA")],
        [InlineKeyboardButton("🔥 Ujjwala", callback_data="scheme_Ujjwala Yojana"),
         InlineKeyboardButton("🏦 Jan Dhan", callback_data="scheme_Jan Dhan")],
    ])
    await update.message.reply_text(
        "📋 *Popular Government Schemes*\nTap to learn more:",
        parse_mode="Markdown",
        reply_markup=schemes_keyboard
    )

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["history"] = []
    await update.message.reply_text("✅ Conversation cleared! Ask me anything.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("lang_"):
        lang = query.data[5:]
        if user_id not in user_sessions:
            user_sessions[user_id] = {"lang": lang, "history": []}
        else:
            user_sessions[user_id]["lang"] = lang
        lang_names = {"en": "English", "hi": "हिंदी", "ta": "தமிழ்", "bn": "বাংলা",
                      "te": "తెలుగు", "mr": "मराठी", "gu": "ગુજરાતી", "kn": "ಕನ್ನಡ"}
        await query.edit_message_text(f"✅ Language set to {lang_names.get(lang, lang)}!\n\nNow ask me your question.")

    elif query.data.startswith("scheme_"):
        scheme = query.data[7:]
        await query.edit_message_text(f"⏳ Looking up {scheme}...")
        session = user_sessions.get(user_id, {"lang": "en", "history": []})
        response = engine.chat(
            f"Tell me about {scheme} - eligibility, benefits, and how to apply",
            language=session["lang"],
            conversation_history=session["history"]
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📋 *{scheme}*\n\n{response.answer}",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = {"lang": "en", "history": []}

    session = user_sessions[user_id]

    # Show typing
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Add to history
    session["history"].append({"role": "user", "content": user_text})

    # Get response
    response = engine.chat(
        user_message=user_text,
        language=session["lang"],
        conversation_history=session["history"]
    )

    # Add to history
    session["history"].append({"role": "assistant", "content": response.answer})

    # Keep last 10 turns
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    # Format response
    answer = response.answer
    if len(answer) > 4000:
        answer = answer[:3900] + "\n\n_[Response truncated — ask for more details]_"

    # Source tag
    footer = ""
    if response.scheme_names:
        footer = f"\n\n📌 _{', '.join(response.scheme_names[:3])}_"
    if response.retrieval_time_ms:
        footer += f"\n⚡ _{response.total_time_ms:.0f}ms_"

    await update.message.reply_text(
        answer + footer,
        parse_mode="Markdown"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF uploads"""
    doc = update.message.document
    if not doc.file_name.endswith('.pdf'):
        await update.message.reply_text("Please send a PDF file.")
        return

    await update.message.reply_text("📄 Processing your PDF...")
    file = await context.bot.get_file(doc.file_id)
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        await file.download_to_memory(tmp)
        tmp_path = tmp.name

    scheme_name = Path(doc.file_name).stem.replace('_', ' ').title()
    chunks = engine.processor.process_pdf(tmp_path, scheme_name)
    
    if chunks:
        engine.vector_store.add_chunks(chunks, engine.embedder)
        engine.vector_store.save()
        await update.message.reply_text(
            f"✅ Document '{scheme_name}' indexed successfully!\n"
            f"Added {len(chunks)} knowledge chunks.\n\n"
            f"You can now ask questions about this document."
        )
    else:
        await update.message.reply_text("❌ Could not process PDF. Please try a text-based PDF.")
    
    Path(tmp_path).unlink(missing_ok=True)

# ===== MAIN =====
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("language", language_cmd))
    app.add_handler(CommandHandler("schemes", schemes_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("NyayaBot Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
