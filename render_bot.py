"""
Telegram Channel Guard Bot - Render Deployment Version (Webhooks)
"""

import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ChatMemberHandler, CallbackQueryHandler
from bot_handler import BotHandler
from channel_monitor import ChannelMonitor

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PORT = int(os.getenv("PORT", 8000))

bot_handler = BotHandler()
channel_monitor = ChannelMonitor()
application = None

def setup_bot():
    """Initialize bot application"""
    global application
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return None
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot_handler.start_command))
    application.add_handler(CommandHandler("help", bot_handler.help_command))
    application.add_handler(CommandHandler("status", bot_handler.status_command))
    application.add_handler(CommandHandler("logs", bot_handler.logs_command))
    application.add_handler(CommandHandler("config", bot_handler.config_command))
    application.add_handler(CommandHandler("add_admin", bot_handler.add_admin_command))
    application.add_handler(CommandHandler("remove_admin", bot_handler.remove_admin_command))
    application.add_handler(CommandHandler("list_admins", bot_handler.list_admins_command))
    application.add_handler(CommandHandler("add_channel", bot_handler.add_channel_command))
    application.add_handler(ChatMemberHandler(channel_monitor.handle_chat_member_update))
    application.add_handler(CallbackQueryHandler(bot_handler.button_callback))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    
    webhook_url = f"{WEBHOOK_URL}/webhook"
    loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
    logger.info(f"✅ Webhook set to: {webhook_url}")
    logger.info(f"✅ Bot initialized and ready!")
    
    return application

@app.route('/')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "service": "telegram-channel-guard-bot",
        "message": "Bot is running on Render"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates via webhook"""
    if not application:
        return jsonify({"status": "error", "message": "Bot not initialized"}), 500
    
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    logger.info(f"Starting bot on port {PORT}...")
    setup_bot()
    app.run(host='0.0.0.0', port=PORT, debug=False)
