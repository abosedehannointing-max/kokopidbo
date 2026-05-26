import os
import sys

# Print ALL environment variables at startup
print("=" * 60)
print("ALL ENVIRONMENT VARIABLES:")
print("=" * 60)
for key, value in os.environ.items():
    # Mask sensitive values partially
    if "TOKEN" in key or "KEY" in key:
        print(f"{key} = {value[:10]}...{value[-5:] if len(value) > 15 else '***'}")
    else:
        print(f"{key} = {value}")
print("=" * 60)

# Try to get the token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

print(f"\nTELEGRAM_BOT_TOKEN from get: {'FOUND' if TELEGRAM_TOKEN else 'NOT FOUND'}")
print(f"OPENAI_API_KEY from get: {'FOUND' if OPENAI_API_KEY else 'NOT FOUND'}")
print("=" * 60)

if not TELEGRAM_TOKEN:
    print("❌ CRITICAL: TELEGRAM_BOT_TOKEN is empty!")
    print("This means Railway is NOT passing environment variables to the container.")
    print("Please check Railway configuration or recreate the service.")
    sys.exit(1)

# If we get here, proceed with normal bot code
print("✅ Token found! Starting bot...")

# Continue with normal imports
import re
import random
import logging
from datetime import datetime, timedelta
from typing import Dict
import requests

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Rest of your bot code here (same as before)
def generate_post_content(topic: str, day: int, post_num: int, total_posts: int) -> str:
    if OPENAI_API_KEY:
        try:
            prompt = f"Write a short, engaging Telegram post about '{topic}'. Post {post_num} of {total_posts} for Day {day}. Include hashtags."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
                timeout=15
            )
            if response.status_code == 200:
                post = response.json()["choices"][0]["message"]["content"].strip()
                return f"{post}\n\n📅 Day {day} • Post {post_num}/{total_posts}"
        except Exception as e:
            print(f"OpenAI error: {e}")
    
    templates = [
        f"🤖 **{topic.upper()}** - Daily insights!",
        f"💡 **{topic.upper()} TIP** - Stay consistent!",
        f"📢 **{topic.upper()} UPDATE** - Don't miss out!"
    ]
    post = random.choice(templates)
    post += f"\n\n📅 Day {day} • Post {post_num}/{total_posts}\n#{topic.replace(' ', '')}"
    return post

active_campaigns = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        f"🤖 *Auto Content Bot*\n\nSend: `@channel | topic | days`\nExample: `@AIToolsDail | AI Tools | 7 days`",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if '|' not in text:
        start(update, context)
        return
    
    parts = [p.strip() for p in text.split('|')]
    if len(parts) != 3:
        update.message.reply_text("❌ Use: `@channel | topic | days`")
        return
    
    channel, topic, days_part = parts
    days_match = re.search(r'(\d+)', days_part)
    if not days_match:
        update.message.reply_text("❌ Specify days: `7 days`")
        return
    
    days = int(days_match.group(1))
    if not channel.startswith('@'):
        update.message.reply_text("❌ Channel must start with @")
        return
    
    active_campaigns[user_id] = {
        'channel': channel,
        'topic': topic,
        'days': days,
        'start_date': datetime.now(),
        'end_date': datetime.now() + timedelta(days=days),
        'posts_made': 0,
        'current_post': 1
    }
    
    if 'campaign_jobs' not in context.chat_data:
        context.chat_data['campaign_jobs'] = {}
    job = context.job_queue.run_repeating(post_to_channel, interval=5400, first=2, context=user_id)
    context.chat_data['campaign_jobs'][user_id] = job
    
    update.message.reply_text(f"🚀 *Started!*\n📢 {channel}\n📝 {topic}\n📅 {days} days", parse_mode=ParseMode.MARKDOWN)

def post_to_channel(context: CallbackContext):
    job = context.job
    user_id = job.context
    campaign = active_campaigns.get(user_id)
    
    if not campaign or datetime.now() > campaign['end_date']:
        if campaign:
            active_campaigns.pop(user_id, None)
        job.schedule_removal()
        return
    
    campaign['posts_made'] += 1
    day = (datetime.now() - campaign['start_date']).days + 1
    post = generate_post_content(campaign['topic'], day, campaign['current_post'], 16)
    campaign['current_post'] = (campaign['current_post'] % 16) + 1
    
    try:
        context.bot.send_message(chat_id=campaign['channel'], text=post, parse_mode=ParseMode.MARKDOWN)
        print(f"✅ Posted to {campaign['channel']} - #{campaign['posts_made']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        context.bot.send_message(chat_id=user_id, text=f"❌ Error: {e}")
        active_campaigns.pop(user_id, None)
        job.schedule_removal()

def status_command(update: Update, context: CallbackContext):
    campaign = active_campaigns.get(update.effective_user.id)
    if not campaign:
        update.message.reply_text("❌ No active campaign")
        return
    days_left = (campaign['end_date'] - datetime.now()).days
    update.message.reply_text(f"📊 *Status*\nPosts: {campaign['posts_made']}\nDays left: {days_left}", parse_mode=ParseMode.MARKDOWN)

def stop_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in active_campaigns:
        if 'campaign_jobs' in context.chat_data and user_id in context.chat_data['campaign_jobs']:
            context.chat_data['campaign_jobs'][user_id].schedule_removal()
            del context.chat_data['campaign_jobs'][user_id]
        active_campaigns.pop(user_id)
        update.message.reply_text("✅ Stopped")
    else:
        update.message.reply_text("❌ No active campaign")

def main():
    print("=" * 60)
    print("Starting bot with token...")
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("stop", stop_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    updater.start_polling()
    print("✅ Bot is running!")
    updater.idle()

if __name__ == "__main__":
    main()
