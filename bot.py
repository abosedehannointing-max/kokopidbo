import os
import re
import random
import logging
from datetime import datetime, timedelta
from typing import Dict
import requests

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not TELEGRAM_TOKEN:
    print("❌ CRITICAL ERROR: TELEGRAM_BOT_TOKEN environment variable not set.")
    exit(1)

print(f"✅ Bot token loaded successfully.")
print(f"✅ OpenAI API: {'Configured and ready.' if OPENAI_API_KEY else 'Not configured. Will use template posts.'}")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- In-Memory Storage ---
# WARNING: Data is lost on bot restart. This is fine for this use case.
active_campaigns: Dict[int, Dict] = {}

# --- Core Logic ---
def generate_post_content(topic: str, day: int, post_num: int, total_posts: int) -> str:
    """Generates post text using OpenAI or a random template."""
    if OPENAI_API_KEY:
        try:
            prompt = f"Write a short, engaging, and unique Telegram post about '{topic}'. This is post #{post_num} of {total_posts} for Day {day}. Keep it under 300 characters. Do not mention the post number or day in the text. Be creative and use emojis."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.9
                },
                timeout=15
            )
            if response.status_code == 200:
                post_text = response.json()["choices"][0]["message"]["content"].strip()
                # Add day and post counter
                final_post = f"{post_text}\n\n📅 Day {day} • Post {post_num}/{total_posts}"
                return final_post
            else:
                logger.error(f"OpenAI API Error: {response.status_code}")
        except Exception as e:
            logger.error(f"OpenAI exception: {e}")

    # Fallback Templates (used if OpenAI fails or is not configured)
    templates = [
        f"🤖 **{topic.upper()}** - Daily insights delivered!\nStay tuned for more valuable content.",
        f"💡 **{topic.upper()} TIP**\nWant to master {topic}? Consistency is key. Keep learning every day!",
        f"📢 **{topic.upper()} UPDATE**\nThe world of {topic} moves fast. Don't get left behind!",
        f"🔥 **{topic.upper()}**\nSuccess in {topic} comes to those who take action. Start today!",
        f"✨ **{topic.upper()} INSIGHT**\nHere's something valuable about {topic} you might not have known."
    ]
    post = random.choice(templates)
    post += f"\n\n📅 Day {day} • Post {post_num}/{total_posts}\n"
    post += f"#{topic.replace(' ', '')} #{topic.replace(' ', '')}Daily"
    return post

# --- Bot Command Handlers ---
def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    ai_status = "🧠 AI-Powered Mode (OpenAI)" if OPENAI_API_KEY else "📝 Template Mode"
    update.message.reply_text(
        f"🤖 *Auto Content Bot*\n\n"
        f"*Status:* `{ai_status}`\n\n"
        f"*Quick Setup:*\n"
        f"`@channel_username | topic | number_of_days`\n\n"
        f"*Example:*\n"
        f"`@AIToolsDail | AI Tools | 7 days`\n\n"
        f"*Commands:*\n"
        f"/status - Check your active campaign\n"
        f"/stop - Stop your active campaign",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_new_campaign(update: Update, context: CallbackContext):
    """Parses the 'channel | topic | days' message and starts a campaign."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if '|' not in text:
        start(update, context)
        return

    parts = [p.strip() for p in text.split('|')]
    if len(parts) != 3:
        update.message.reply_text("❌ Invalid format. Please use: `@channel | topic | days`", parse_mode=ParseMode.MARKDOWN)
        return

    channel, topic, days_part = parts
    days_match = re.search(r'(\d+)', days_part)
    if not days_match:
        update.message.reply_text("❌ Please specify a valid number of days (e.g., `7 days`).")
        return

    days = int(days_match.group(1))
    if not 1 <= days <= 30:
        update.message.reply_text("❌ Days must be between 1 and 30.")
        return
    if not channel.startswith('@'):
        update.message.reply_text("❌ Channel must start with `@`. Example: `@AIToolsDail`", parse_mode=ParseMode.MARKDOWN)
        return

    # --- Create and schedule the campaign ---
    end_date = datetime.now() + timedelta(days=days)
    active_campaigns[user_id] = {
        'channel': channel,
        'topic': topic,
        'days': days,
        'start_date': datetime.now(),
        'end_date': end_date,
        'posts_made': 0,
        'current_post_number': 1
    }

    # Schedule the first post immediately (2 seconds later)
    if 'campaign_jobs' not in context.chat_data:
        context.chat_data['campaign_jobs'] = {}
    job = context.job_queue.run_repeating(post_to_channel, interval=5400, first=2, context=user_id) # 5400 seconds = 90 minutes
    context.chat_data['campaign_jobs'][user_id] = job

    ai_note = "🧠 *Each post will be unique and AI-generated!*" if OPENAI_API_KEY else "📝 *Using templates. Add `OPENAI_API_KEY` for AI-generated content.*"

    update.message.reply_text(
        f"🚀 *Campaign Started!*\n\n"
        f"📢 Channel: `{channel}`\n"
        f"📝 Topic: `{topic}`\n"
        f"📅 Duration: `{days} days`\n"
        f"⏱️ Posting interval: `~90 minutes`\n"
        f"{ai_note}\n\n"
        f"First post is on its way!",
        parse_mode=ParseMode.MARKDOWN
    )

def post_to_channel(context: CallbackContext):
    """The function called by the job queue to send a post."""
    job = context.job
    user_id = job.context
    campaign = active_campaigns.get(user_id)

    if not campaign:
        # Campaign was deleted, remove the job
        job.schedule_removal()
        return

    if datetime.now() > campaign['end_date']:
        # Campaign is over
        end_campaign(user_id, context)
        job.schedule_removal()
        return

    campaign['posts_made'] += 1
    day_number = (datetime.now() - campaign['start_date']).days + 1
    current_post_num = campaign['current_post_number']
    total_posts_per_day = 16

    post_text = generate_post_content(campaign['topic'], day_number, current_post_num, total_posts_per_day)

    campaign['current_post_number'] += 1
    if campaign['current_post_number'] > total_posts_per_day:
        campaign['current_post_number'] = 1

    try:
        context.bot.send_message(
            chat_id=campaign['channel'],
            text=post_text,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"✅ Posted to {campaign['channel']} for user {user_id}. Total posts: {campaign['posts_made']}")
    except Exception as e:
        logger.error(f"❌ Failed to post to {campaign['channel']}. Error: {e}")
        context.bot.send_message(
            chat_id=user_id,
            text=f"❌ *Fatal Error:* Could not post to `{campaign['channel']}`.\n\n"
                 f"Please ensure I am an administrator in that channel, and the username is correct. Stopping campaign.",
            parse_mode=ParseMode.MARKDOWN
        )
        end_campaign(user_id, context)
        # Find and remove the job
        if 'campaign_jobs' in context.chat_data and user_id in context.chat_data['campaign_jobs']:
            context.chat_data['campaign_jobs'][user_id].schedule_removal()
            del context.chat_data['campaign_jobs'][user_id]

def status_command(update: Update, context: CallbackContext):
    """Shows the status of the user's active campaign."""
    user_id = update.effective_user.id
    campaign = active_campaigns.get(user_id)

    if not campaign:
        update.message.reply_text("❌ No active campaign. Start one with `@channel | topic | days`", parse_mode=ParseMode.MARKDOWN)
        return

    days_passed = (datetime.now() - campaign['start_date']).days
    days_left = (campaign['end_date'] - datetime.now()).days
    progress_percent = (campaign['posts_made'] / (campaign['days'] * 16)) * 100

    update.message.reply_text(
        f"📊 *Campaign Status*\n\n"
        f"📢 Channel: `{campaign['channel']}`\n"
        f"📝 Topic: `{campaign['topic']}`\n"
        f"📨 Posts made: `{campaign['posts_made']}`\n"
        f"📅 Day `{days_passed + 1}` of `{campaign['days']}`\n"
        f"⏰ Days remaining: `{days_left}`\n"
        f"📈 Progress: `{progress_percent:.1f}%`\n\n"
        f"Use /stop to end this campaign.",
        parse_mode=ParseMode.MARKDOWN
    )

def stop_command(update: Update, context: CallbackContext):
    """Stops the user's active campaign."""
    user_id = update.effective_user.id
    campaign = active_campaigns.pop(user_id, None)

    if not campaign:
        update.message.reply_text("❌ No active campaign to stop.")
        return

    # Stop the scheduled job for this campaign
    if 'campaign_jobs' in context.chat_data and user_id in context.chat_data['campaign_jobs']:
        context.chat_data['campaign_jobs'][user_id].schedule_removal()
        del context.chat_data['campaign_jobs'][user_id]

    update.message.reply_text(
        f"🛑 *Campaign Stopped*\n\n"
        f"📝 Topic: `{campaign['topic']}`\n"
        f"📨 Total posts made: `{campaign['posts_made']}`\n\n"
        f"You can start a new one anytime.",
        parse_mode=ParseMode.MARKDOWN
    )

def end_campaign(user_id: int, context: CallbackContext):
    """Helper function to clean up a finished or failed campaign."""
    campaign = active_campaigns.pop(user_id, None)
    if campaign:
        # Notify user that the campaign is complete
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Campaign Completed!*\n\n"
                     f"📝 Topic: `{campaign['topic']}`\n"
                     f"📨 Total posts: `{campaign['posts_made']}`\n"
                     f"📅 Duration: `{campaign['days']} days`\n\n"
                     f"Thanks for using the bot! Start a new campaign when you're ready.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Could not notify user {user_id} of campaign end: {e}")

    # Job cleanup is handled by the caller (post_to_channel) or by the stop command.

def error_handler(update, context):
    """Log errors caused by updates."""
    logger.warning(f"Update {update} caused error {context.error}")

# --- Main Function ---
def main():
    """Starts the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("stop", stop_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_new_campaign))
    dp.add_error_handler(error_handler)

    # Start the Bot
    print("🚀 Starting bot on Railway...")
    updater.start_polling()
    print("✅ Bot is now running. Awaiting commands.")

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT.
    updater.idle()

if __name__ == '__main__':
    main()
