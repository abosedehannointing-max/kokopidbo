import os
import re
import random
import logging
from datetime import datetime, timedelta
import requests

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ============ CONFIGURATION ============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not set")
    exit(1)

print("Bot token loaded successfully")

# ============ STORAGE ============
active_campaigns = {}

# ============ FOOTBALL NEWS FUNCTIONS ============
def get_football_news():
    """Get football news from free API"""
    try:
        response = requests.get("https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4328", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("events"):
                events = data["events"][:5]
                news = []
                for event in events:
                    item = f"⚽ **{event.get('strEvent', 'Match')}**\n"
                    item += f"📅 {event.get('dateEvent', 'Date TBD')}\n"
                    item += f"🏆 {event.get('strLeague', 'League')}\n"
                    news.append(item)
                return "\n\n".join(news)
    except:
        pass
    
    # Fallback news
    football_news = [
        "⚽ **Real Madrid vs Barcelona**\n📅 This weekend\n🏆 El Clasico promises excitement!",
        "⚽ **Messi leads Argentina**\n📅 World Cup Qualifiers\n🏆 The team prepares for the next match",
        "⚽ **Champions League**\n📅 Semi-finals\n🏆 Europe's best teams compete",
        "⚽ **Transfer Window**\n📅 Summer transfers\n🏆 Big moves across Europe",
    ]
    return random.choice(football_news)

def generate_football_news_ai():
    """Generate football news using AI or template"""
    if OPENAI_API_KEY:
        try:
            prompt = "Write a short football news update, including results or transfers. Max 200 characters."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
                timeout=10
            )
            if response.status_code == 200:
                text = response.json()["choices"][0]["message"]["content"].strip()
                return f"⚽ **FOOTBALL NEWS**\n\n{text}\n\n#Football #News"
        except:
            pass
    
    # Template news
    templates = [
        "⚽ **BREAKING NEWS**\n\nReal Madrid wins with a last-minute goal.\n\n#LaLiga",
        "⚽ **TRANSFER NEWS**\n\nClub looking to strengthen squad for next season.\n\n#Transfers",
        "⚽ **INJURY UPDATE**\n\nStar player will miss the next match.\n\n#Injury",
        "⚽ **MANAGER COMMENTS**\n\nCoach confident about winning the title.\n\n#Interview",
    ]
    return random.choice(templates)

# ============ CONTENT GENERATION ============
def generate_content(topic, day, post_num, total_posts):
    if OPENAI_API_KEY:
        try:
            prompt = f"Write a short post about '{topic}'. Post {post_num} of {total_posts} for Day {day}. Include hashtags."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
                timeout=10
            )
            if response.status_code == 200:
                text = response.json()["choices"][0]["message"]["content"].strip()
                return f"{text}\n\n📅 Day {day} • {post_num}/{total_posts}"
        except:
            pass
    
    templates = [
        f"🤖 **{topic.upper()}** - Daily insights!",
        f"💡 **{topic.upper()} TIP** - Stay consistent!",
        f"📢 **{topic.upper()} UPDATE** - Don't miss out!",
        f"🔥 **{topic.upper()}** - Take action today!",
    ]
    post = random.choice(templates)
    post += f"\n\n📅 Day {day} • {post_num}/{total_posts}\n#{topic.replace(' ', '')}"
    return post

# ============ MAIN MENU ============
def main_menu():
    """Create the main menu buttons"""
    keyboard = [
        [InlineKeyboardButton("📝 Create Campaign", callback_data="create_campaign")],
        [InlineKeyboardButton("⚽ Football News", callback_data="football_news")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")],
        [InlineKeyboardButton("🛑 Stop Campaign", callback_data="stop")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ BOT HANDLERS ============
def start(update, context):
    """Handle /start command with menu buttons"""
    update.message.reply_text(
        "⚽ *Welcome to the Content Bot!*\n\n"
        "Create automatic content for your channel "
        "or get football news.\n\n"
        "*Select an option:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )

def button_handler(update, context):
    """Handle button clicks"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "create_campaign":
        query.edit_message_text(
            "📝 *Create Campaign*\n\n"
            "Send a message in this format:\n"
            "`@channel | topic | days`\n\n"
            "*Example:*\n"
            "`@AIToolsDail | Football | 7`\n\n"
            "The bot will post every 90 minutes.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="back")
            ]])
        )
    
    elif data == "football_news":
        # Generate football news
        news = generate_football_news_ai()
        query.edit_message_text(
            f"⚽ *FOOTBALL NEWS*\n\n{news}\n\n"
            "Use /football for more news.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="football_news")],
                [InlineKeyboardButton("◀️ Back", callback_data="back")]
            ])
        )
    
    elif data == "my_status":
        campaign = active_campaigns.get(user_id)
        if campaign:
            days_left = (campaign['end_date'] - datetime.now()).days
            text = (
                f"📊 *Your Status*\n\n"
                f"Channel: {campaign['channel']}\n"
                f"Topic: {campaign['topic']}\n"
                f"Posts: {campaign['posts']}\n"
                f"Days left: {days_left}"
            )
        else:
            text = "📊 *No active campaigns*\n\nUse 'Create Campaign' to start."
        
        query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="back")
            ]])
        )
    
    elif data == "stop":
        if user_id in active_campaigns:
            if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
                context.chat_data['jobs'][user_id].schedule_removal()
                del context.chat_data['jobs'][user_id]
            active_campaigns.pop(user_id, None)
            text = "🛑 *Campaign stopped successfully*"
        else:
            text = "🛑 *No active campaigns*"
        
        query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="back")
            ]])
        )
    
    elif data == "help":
        query.edit_message_text(
            "❓ *Help*\n\n"
            "*Commands:*\n"
            "/start - Main menu\n"
            "/football - Football news\n"
            "/status - Check campaign\n"
            "/stop - Stop campaign\n\n"
            "*Campaign format:*\n"
            "`@channel | topic | days`\n\n"
            "*Example:*\n"
            "`@mychannel | Football | 7`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Back", callback_data="back")
            ]])
        )
    
    elif data == "back":
        query.edit_message_text(
            "⚽ *Main Menu*\n\n"
            "Select an option:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )

def football_command(update, context):
    """Command /football - Get football news"""
    news = generate_football_news_ai()
    update.message.reply_text(
        f"⚽ *FOOTBALL NEWS*\n\n{news}\n\n"
        "Use /football for more news.",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_message(update, context):
    """Process message with format: @channel | topic | days"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if '|' not in text:
        start(update, context)
        return
    
    parts = [p.strip() for p in text.split('|')]
    if len(parts) != 3:
        update.message.reply_text("Use: `@channel | topic | days`", parse_mode=ParseMode.MARKDOWN)
        return
    
    channel, topic, days_part = parts
    days_match = re.search(r'(\d+)', days_part)
    if not days_match:
        update.message.reply_text("Please specify a valid number of days")
        return
    
    days = int(days_match.group(1))
    if not channel.startswith('@'):
        update.message.reply_text("Channel must start with @")
        return
    
    # Stop existing campaign
    if user_id in active_campaigns:
        if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
            context.chat_data['jobs'][user_id].schedule_removal()
        active_campaigns.pop(user_id, None)
    
    # Create new campaign
    end_date = datetime.now() + timedelta(days=days)
    active_campaigns[user_id] = {
        'channel': channel,
        'topic': topic,
        'days': days,
        'start_date': datetime.now(),
        'end_date': end_date,
        'posts': 0,
        'post_num': 1
    }
    
    if 'jobs' not in context.chat_data:
        context.chat_data['jobs'] = {}
    job = context.job_queue.run_repeating(post_to_channel, interval=5400, first=2, context=user_id)
    context.chat_data['jobs'][user_id] = job
    
    update.message.reply_text(
        f"🚀 *Campaign Started!*\n\n"
        f"📢 Channel: {channel}\n"
        f"📝 Topic: {topic}\n"
        f"📅 Duration: {days} days\n"
        f"⏱️ Every 90 minutes\n\n"
        f"Use /status to track progress.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Check Status", callback_data="my_status")
        ]])
    )

def post_to_channel(context):
    job = context.job
    user_id = job.context
    campaign = active_campaigns.get(user_id)
    
    if not campaign:
        job.schedule_removal()
        return
    
    if datetime.now() > campaign['end_date']:
        if user_id in active_campaigns:
            active_campaigns.pop(user_id)
        job.schedule_removal()
        return
    
    campaign['posts'] += 1
    day = (datetime.now() - campaign['start_date']).days + 1
    post_num = campaign['post_num']
    
    text = generate_content(campaign['topic'], day, post_num, 16)
    
    campaign['post_num'] += 1
    if campaign['post_num'] > 16:
        campaign['post_num'] = 1
    
    try:
        context.bot.send_message(
            chat_id=campaign['channel'],
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"Posted to {campaign['channel']} - #{campaign['posts']}")
    except Exception as e:
        print(f"Error: {e}")
        context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Error posting to {campaign['channel']}. Make sure I'm admin."
        )
        if user_id in active_campaigns:
            active_campaigns.pop(user_id)
        job.schedule_removal()

def status_command(update, context):
    user_id = update.effective_user.id
    campaign = active_campaigns.get(user_id)
    
    if not campaign:
        update.message.reply_text(
            "📊 *No active campaign*\n\nUse /start to begin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        return
    
    days_left = (campaign['end_date'] - datetime.now()).days
    update.message.reply_text(
        f"📊 *Campaign Status*\n\n"
        f"📢 Channel: `{campaign['channel']}`\n"
        f"📝 Topic: `{campaign['topic']}`\n"
        f"📨 Posts: `{campaign['posts']}`\n"
        f"📅 Days left: `{days_left}`\n\n"
        f"Use /stop to end.",
        parse_mode=ParseMode.MARKDOWN
    )

def stop_command(update, context):
    user_id = update.effective_user.id
    
    if user_id in active_campaigns:
        if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
            context.chat_data['jobs'][user_id].schedule_removal()
            del context.chat_data['jobs'][user_id]
        active_campaigns.pop(user_id)
        update.message.reply_text("✅ *Campaign stopped*", parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text(
            "❌ *No active campaign*\n\nUse /start to begin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )

def help_command(update, context):
    update.message.reply_text(
        "❓ *Help*\n\n"
        "*Commands:*\n"
        "/start - Main menu\n"
        "/football - Football news\n"
        "/status - Check active campaign\n"
        "/stop - Stop campaign\n\n"
        "*Buttons:* Use the menu to access all features.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )

# ============ MAIN FUNCTION ============
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("football", football_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("stop", stop_command))
    dp.add_handler(CommandHandler("help", help_command))
    
    # Message and button handlers
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("Bot starting with menu buttons and football news...")
    updater.start_polling()
    print("Bot is running!")
    updater.idle()

if __name__ == "__main__":
    main()
