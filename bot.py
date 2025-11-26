import os
import json
import sqlite3
import re
import zipfile
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import asyncio
import tempfile
from flask import Flask
from threading import Thread
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Render web service
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running!", 200

@app.route('/health')
def health():
    return "OK", 200

# Bot Token - Set this as environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Store user sessions temporarily
user_sessions = {}

class TelegramAccountManager:
    def __init__(self, api_id, api_hash, phone, session_path):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_path = session_path
        self.client = None
    
    async def verify_session(self):
        """Check if session is active"""
        try:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                return {
                    'status': 'active',
                    'phone': me.phone,
                    'user_id': me.id,
                    'username': me.username,
                    'first_name': me.first_name or 'Empty',
                    'last_name': me.last_name or 'Empty'
                }
            else:
                return {'status': 'inactive', 'message': 'Session not authorized'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            if self.client:
                await self.client.disconnect()
    
    async def get_otp_code(self):
        """Get latest OTP from Telegram official chat"""
        try:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                messages = []
                async for message in self.client.iter_messages('Telegram', limit=5):
                    if message.text:
                        messages.append({
                            'text': message.text,
                            'date': str(message.date)
                        })
                        
                        # Check if it's a login code
                        if 'Login code' in message.text or 'code:' in message.text.lower():
                            code_match = re.search(r'\b\d{5}\b', message.text)
                            if code_match:
                                return {
                                    'status': 'success',
                                    'code': code_match.group(),
                                    'message': message.text,
                                    'date': str(message.date)
                                }
                
                return {
                    'status': 'no_code',
                    'recent_messages': messages
                }
            else:
                return {'status': 'error', 'message': 'Session not authorized'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            if self.client:
                await self.client.disconnect()
    
    async def get_recent_messages(self, limit=10):
        """Get recent messages from all chats"""
        try:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                dialogs = await self.client.get_dialogs(limit=10)
                all_messages = []
                
                for dialog in dialogs:
                    async for msg in self.client.iter_messages(dialog, limit=2):
                        if msg.text:
                            all_messages.append({
                                'chat': dialog.name,
                                'text': msg.text[:100],
                                'date': str(msg.date)
                            })
                
                return {'status': 'success', 'messages': all_messages}
            else:
                return {'status': 'error', 'message': 'Session not authorized'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            if self.client:
                await self.client.disconnect()

def extract_archive(file_path, extract_to):
    """Extract ZIP/RAR files"""
    try:
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            return True
        # Add RAR support if needed (requires rarfile library)
        return False
    except Exception as e:
        print(f"Extract error: {e}")
        return False

def find_session_files(directory):
    """Find .session and .json files in directory"""
    json_files = []
    session_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            if file.endswith('.json'):
                json_files.append(full_path)
            elif file.endswith('.session'):
                session_files.append(full_path)
    
    return json_files, session_files

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    logger.info(f"Start command received from user {update.effective_user.id}")
    welcome_msg = """
🤖 **Telegram Account Login Bot**

मैं आपकी Telegram account login में मदद करूंगा!

**कैसे इस्तेमाल करें:**

📦 **Option 1: ZIP File भेजो**
   • सारी files एक ZIP में भेज दो
   • मैं automatically सब extract करूंगा!

📁 **Option 2: Individual Files भेजो**
   • `.session` file
   • `.json` file (credentials)

मैं automatically:
✅ Files extract करूंगा
✅ Account verify करूंगा
✅ Details दिखाऊंगा
✅ OTP code निकालूंगा
✅ Recent messages दिखाऊंगा

**Commands:**
/start - शुरू करें
/help - मदद
/status - Account status देखें
/getotp - Latest OTP code पाएं
/messages - Recent messages देखें
/clear - Data clear करें (नया account के लिए)

📁 **अभी ZIP file या individual files upload करो!**
"""
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
📚 **Help Menu**

**File Upload:**

🎁 **ZIP File Method (Recommended):**
• अपनी सारी files एक ZIP में pack करो
• ZIP file मुझे भेज दो
• बस! मैं सब automatically handle करूंगा

📁 **Individual Files Method:**
• पहले `.json` file upload करो
• फिर `.session` file upload करो

**Commands:**
/status - अपने account की status देखो
/getotp - Latest OTP code निकालो
/messages - हाल के messages देखो
/clear - Data clear करके नया account load करो

**Login Process:**
1️⃣ Files upload करो (ZIP या individual)
2️⃣ मैं account verify करूंगा
3️⃣ Telegram X खोलकर phone number डालो
4️⃣ `/getotp` command से code लो
5️⃣ Code + 2FA password डालो
6️⃣ Done! 🎉

**Tips:**
💡 ZIP file में दोनों files (.session + .json) होनी चाहिए
💡 File names match होने चाहिए
💡 ZIP में multiple accounts हो सकते हैं!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user data"""
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        # Clean up temp directory
        if 'temp_dir' in user_sessions[user_id]:
            try:
                shutil.rmtree(user_sessions[user_id]['temp_dir'])
            except:
                pass
        
        del user_sessions[user_id]
        await update.message.reply_text("✅ Data cleared! अब नया account upload कर सकते हो।")
    else:
        await update.message.reply_text("ℹ️ कोई data नहीं है clear करने के लिए।")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded files"""
    user_id = update.effective_user.id
    document = update.message.document
    file_name = document.file_name
    
    # Initialize user session if not exists
    if user_id not in user_sessions:
        user_sessions[user_id] = {'json': None, 'session': None, 'temp_dir': tempfile.mkdtemp()}
    
    temp_dir = user_sessions[user_id]['temp_dir']
    
    # Download file
    await update.message.reply_text(f"📥 Downloading `{file_name}`...", parse_mode='Markdown')
    file = await context.bot.get_file(document.file_id)
    file_path = os.path.join(temp_dir, file_name)
    await file.download_to_drive(file_path)
    
    # Check if it's a ZIP file
    if file_name.endswith('.zip'):
        await update.message.reply_text("📦 ZIP file detected! Extracting...")
        
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        if extract_archive(file_path, extract_dir):
            # Find session and json files
            json_files, session_files = find_session_files(extract_dir)
            
            if json_files and session_files:
                await update.message.reply_text(f"✅ Found {len(json_files)} JSON and {len(session_files)} session files!")
                
                # Use first matching pair
                for json_file in json_files:
                    json_name = os.path.splitext(os.path.basename(json_file))[0]
                    
                    for session_file in session_files:
                        session_name = os.path.splitext(os.path.basename(session_file))[0]
                        
                        if json_name == session_name:
                            # Found matching pair!
                            user_sessions[user_id]['json'] = json_file
                            user_sessions[user_id]['session'] = session_file
                            
                            await update.message.reply_text(f"🎯 Found matching files: `{json_name}`\n\n🔄 Processing...", parse_mode='Markdown')
                            await process_account(update, context, user_id)
                            return
                
                # If no matching pair found, list what we found
                msg = "⚠️ Files found but names don't match:\n\n"
                msg += "📄 JSON files:\n"
                for jf in json_files:
                    msg += f"  • `{os.path.basename(jf)}`\n"
                msg += "\n📁 Session files:\n"
                for sf in session_files:
                    msg += f"  • `{os.path.basename(sf)}`\n"
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ ZIP में .json या .session files नहीं मिली!")
        else:
            await update.message.reply_text("❌ ZIP extract करने में error!")
    
    # Handle individual JSON file
    elif file_name.endswith('.json'):
        user_sessions[user_id]['json'] = file_path
        await update.message.reply_text(f"✅ JSON file received: `{file_name}`\n\n📁 अब `.session` file भेजो!", parse_mode='Markdown')
    
    # Handle individual session file
    elif file_name.endswith('.session'):
        user_sessions[user_id]['session'] = file_path
        await update.message.reply_text(f"✅ Session file received: `{file_name}`\n\n🔄 Processing...", parse_mode='Markdown')
        
        # If both files are uploaded, process them
        if user_sessions[user_id]['json']:
            await process_account(update, context, user_id)
        else:
            await update.message.reply_text("⚠️ अब `.json` file भी भेजो!")
    
    else:
        await update.message.reply_text("❌ Invalid file type! Please send `.zip`, `.json`, or `.session` files only.")

async def process_account(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """Process the uploaded account files"""
    json_path = user_sessions[user_id]['json']
    session_path = user_sessions[user_id]['session']
    
    try:
        # Load JSON credentials
        with open(json_path, 'r', encoding='utf-8') as f:
            creds = json.load(f)
        
        api_id = creds.get('app_id')
        api_hash = creds.get('app_hash')
        phone = creds.get('phone')
        twofa = creds.get('twoFA', 'N/A')
        
        # Extract session name (without extension)
        session_name = os.path.splitext(session_path)[0]
        
        # Store in user session
        user_sessions[user_id]['manager'] = TelegramAccountManager(api_id, api_hash, phone, session_name)
        user_sessions[user_id]['credentials'] = creds
        
        # Verify account
        await update.message.reply_text("🔍 Verifying account...")
        result = await user_sessions[user_id]['manager'].verify_session()
        
        if result['status'] == 'active':
            msg = f"""
✅ **ACCOUNT ACTIVE!**

📱 Phone: `+{result['phone']}`
🆔 User ID: `{result['user_id']}`
👤 Name: {result['first_name']} {result['last_name']}
🔗 Username: @{result['username'] or 'None'}
🔐 2FA: `{twofa}`

━━━━━━━━━━━━━━━━━━━━

**📱 LOGIN STEPS:**

1️⃣ **Telegram X/App खोलो**
2️⃣ **Phone डालो:** `+{result['phone']}`
3️⃣ **"We sent you a code" दिखेगा**
4️⃣ **यहां `/getotp` टाइप करो**
5️⃣ **Code Telegram X में paste करो**
6️⃣ **2FA डालो:** `{twofa}`
7️⃣ **Done! 🎉**

━━━━━━━━━━━━━━━━━━━━

अभी Telegram X में login start करो! 👇
"""
            keyboard = [
                [InlineKeyboardButton("🔢 Get OTP Code", callback_data='get_otp')],
                [InlineKeyboardButton("📬 Recent Messages", callback_data='get_messages')],
                [InlineKeyboardButton("🔄 Check Status", callback_data='check_status')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
        
        elif result['status'] == 'inactive':
            msg = f"""
❌ **SESSION NOT AUTHORIZED**

⚠️ Session Dead/Expired hai!

**Problem:**
{result['message']}

**Solutions:**
1️⃣ Seller se baat karo - ACTIVE session chahiye
2️⃣ Dusra account try karo
3️⃣ Refund mango

💡 Working session LOGGED IN hona chahiye!
"""
            await update.message.reply_text(msg, parse_mode='Markdown')
        
        else:
            await update.message.reply_text(f"❌ **Error**: {result['message']}", parse_mode='Markdown')
    
    except Exception as e:
        await update.message.reply_text(f"❌ **Processing Error**: {str(e)}\n\nJSON file corrupt ho sakti hai ya format galat hai.", parse_mode='Markdown')

async def get_otp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get OTP code command"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or 'manager' not in user_sessions[user_id]:
        await update.message.reply_text("❌ पहले files upload करो! /start से शुरू करो।")
        return
    
    await update.message.reply_text("🔍 Checking for OTP code...")
    
    manager = user_sessions[user_id]['manager']
    result = await manager.get_otp_code()
    
    if result['status'] == 'success':
        msg = f"""
🔥 **OTP CODE FOUND!**

✅ **CODE: `{result['code']}`** ✅

📝 Full Message:
```
{result['message'][:500]}
```

🕐 Time: {result['date']}

━━━━━━━━━━━━━━━━━━━━

📱 **AB YE KARO:**

1️⃣ Code copy karo: `{result['code']}`
2️⃣ Telegram X में paste karo
3️⃣ 2FA password: `{user_sessions[user_id]['credentials'].get('twoFA', 'N/A')}`
4️⃣ Done! 🎉

━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    elif result['status'] == 'no_code':
        msg = "⚠️ **No login code found yet!**\n\n"
        if result.get('recent_messages'):
            msg += "📬 Recent messages from Telegram:\n\n"
            for i, m in enumerate(result['recent_messages'][:3], 1):
                msg += f"{i}. ```\n{m['text'][:150]}\n```\n🕐 {m['date']}\n\n"
        msg += "\n💡 **Steps:**\n"
        msg += "1️⃣ Telegram X में login request bhejo\n"
        msg += "2️⃣ 10 seconds wait karo\n"
        msg += "3️⃣ Phir `/getotp` command bhejo!"
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    else:
        await update.message.reply_text(f"❌ Error: {result['message']}")

async def get_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get recent messages command"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or 'manager' not in user_sessions[user_id]:
        await update.message.reply_text("❌ पहले files upload करो! /start से शुरू करो।")
        return
    
    await update.message.reply_text("📬 Fetching recent messages...")
    
    manager = user_sessions[user_id]['manager']
    result = await manager.get_recent_messages()
    
    if result['status'] == 'success':
        msg = "📬 **Recent Messages:**\n\n"
        for i, m in enumerate(result['messages'][:12], 1):
            msg += f"{i}. 💬 **{m['chat']}**\n{m['text']}\n🕐 {m['date']}\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Error: {result['message']}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'get_otp':
        # Create a fake update object for the command
        await get_otp_command(query, context)
    elif query.data == 'get_messages':
        await get_messages_command(query, context)
    elif query.data == 'check_status':
        await status_command(query, context)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check account status"""
    user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.from_user.id
    
    if user_id not in user_sessions or 'manager' not in user_sessions[user_id]:
        reply_func = update.message.reply_text if hasattr(update, 'message') else update.edit_message_text
        await reply_func("❌ No account loaded! Upload files first with /start")
        return
    
    reply_func = update.message.reply_text if hasattr(update, 'message') else update.edit_message_text
    await reply_func("🔄 Checking status...")
    
    manager = user_sessions[user_id]['manager']
    result = await manager.verify_session()
    
    if result['status'] == 'active':
        msg = f"""
✅ **Account Status: ACTIVE**

📱 Phone: `+{result['phone']}`
🆔 ID: `{result['user_id']}`
👤 Name: {result['first_name']} {result['last_name']}
🔗 Username: @{result['username'] or 'None'}

━━━━━━━━━━━━━━━━━━━━

Account working perfectly! 🎉
Ready to login on Telegram X!
"""
        await reply_func(msg, parse_mode='Markdown')
    else:
        await reply_func(f"❌ Status: {result.get('message', 'Unknown error')}")

async def run_bot_async():
    """Start the bot asynchronously"""
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error("❌ Error: BOT_TOKEN not set!")
        logger.error("Set environment variable: BOT_TOKEN=your_token_here")
        return
    
    logger.info("🤖 Initializing bot...")
    logger.info(f"📱 Bot token: {BOT_TOKEN[:10]}...")
    
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("getotp", get_otp_command))
    application.add_handler(CommandHandler("messages", get_messages_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Initialize and start
    await application.initialize()
    await application.start()
    logger.info("✅ Bot successfully started and polling!")
    
    # Start polling
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Keep running
    while True:
        await asyncio.sleep(1)

def run_bot():
    """Run bot in thread with its own event loop"""
    try:
        logger.info("🔄 Starting bot thread...")
        asyncio.run(run_bot_async())
    except Exception as e:
        logger.error(f"❌ Bot thread error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function - runs both Flask and Bot"""
    logger.info("=" * 50)
    logger.info("🚀 STARTING APPLICATION")
    logger.info("=" * 50)
    
    # Verify BOT_TOKEN
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error("❌ CRITICAL: BOT_TOKEN not set!")
        logger.error("Please set BOT_TOKEN environment variable in Render")
        return
    
    logger.info(f"✅ BOT_TOKEN found: {BOT_TOKEN[:10]}...")
    
    # Start bot in a separate thread
    logger.info("🤖 Starting bot in background thread...")
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot thread started!")
    
    # Start Flask web server
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🌐 Starting Flask server on port {port}...")
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

if __name__ == '__main__':
    main()
