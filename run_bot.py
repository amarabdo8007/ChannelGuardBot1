"""
Telegram Channel Guard Bot - Main Entry Point
Runs Flask HTTP server for health checks and Telegram bot for monitoring
"""

import os
import logging
import threading
from flask import Flask, jsonify
from telegram.ext import Application, CommandHandler, ChatMemberHandler, CallbackQueryHandler
from bot_handler import BotHandler
from channel_monitor import ChannelMonitor

# إعداد اللوجات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# إنشاء تطبيق Flask للـ health checks
app = Flask(__name__)

@app.route('/')
def health_check():
    """Health check endpoint for deployment monitoring"""
    return jsonify({
        "message": "Bot is running",
        "service": "telegram-bot",
        "status": "healthy",
        "bot_initialized": True,
        "timestamp": os.getenv("REPL_ID", "unknown"),
        "port": "5000"
    })

@app.route('/health')
def health():
    """Simple health endpoint"""
    return jsonify({"status": "ok"})

def run_flask_server():
    """Run Flask server in background thread"""
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def main():
    """Main function to start both Flask server and Telegram bot"""
    
    # جلب التوكن من المتغيرات البيئية
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        logger.error("❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # بدء Flask server في thread منفصل
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    logger.info("Flask HTTP server started on port 5000")
    
    # إعداد البوت
    bot_handler = BotHandler()
    channel_monitor = ChannelMonitor()
    
    # إنشاء تطبيق التليجرام
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", bot_handler.start_command))
    application.add_handler(CommandHandler("help", bot_handler.help_command))
    application.add_handler(CommandHandler("status", bot_handler.status_command))
    application.add_handler(CommandHandler("logs", bot_handler.logs_command))
    application.add_handler(CommandHandler("config", bot_handler.config_command))
    application.add_handler(CommandHandler("add_admin", bot_handler.add_admin_command))
    application.add_handler(CommandHandler("remove_admin", bot_handler.remove_admin_command))
    application.add_handler(CommandHandler("list_admins", bot_handler.list_admins_command))
    application.add_handler(CommandHandler("add_channel", bot_handler.add_channel_command))
    
    # إضافة معالج تغييرات العضوية
    application.add_handler(ChatMemberHandler(channel_monitor.handle_chat_member_update))
    
    # إضافة معالج الأزرار
    application.add_handler(CallbackQueryHandler(bot_handler.button_callback))
    
    logger.info("Starting Telegram bot in main thread...")
    logger.info("Bot started and ready!")
    
    # تشغيل البوت
    application.run_polling()

if __name__ == "__main__":
    main()
