import logging
from collections import defaultdict
from datetime import datetime
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
)

# --- CONFIGURATION ---
TOKEN = "8694345982:AAHAbY0WlTs63lsjHPs9pF6MLhR7VXKNfBg"
user_warnings = defaultdict(int)
user_messages = defaultdict(list)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ADMIN CHECK ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ['creator', 'administrator']

# --- COMMAND FUNCTIONS ---
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context) and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"❌ {target.full_name} ကို Ban လိုက်ပါပြီ။")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context) and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"🔒 {target.full_name} ကို Mute လုပ်လိုက်ပါပြီ။")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    user_warnings[target.id] += 1
    if user_warnings[target.id] >= 3:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"❌ {target.full_name} သတိပေးချက် ၃ ကြိမ်ပြည့်၍ Ban လိုက်ပါပြီ။")
    else:
        await update.message.reply_text(f"⚠️ {target.full_name} - သတိပေးချက်: {user_warnings[target.id]}/3")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context) and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"👢 {target.full_name} ကို Kick လိုက်ပါပြီ။")

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context) and update.message.reply_to_message:
        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text("📌 Pin လုပ်လိုက်ပါပြီ။")

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        await update.message.reply_text(f"👤 {user.full_name} ၏ ID မှာ: `{user.id}` ဖြစ်သည်", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Group ID မှာ: `{update.effective_chat.id}` ဖြစ်သည်", parse_mode="Markdown")

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 *Group စည်းကမ်းချက်များ*\n\n၁။ Link မပို့ရ (Auto-Ban)\n၂။ Spam မလုပ်ရ\n၃။ Admin အား လေးစားပါ", parse_mode="Markdown")

# --- SECURITY & TRACKING ---
async def security_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or await is_admin(update, context): return
    user = update.effective_user
    text = update.effective_message.text or update.effective_message.caption or ""
    if any(x in text.lower() for x in ["http://", "https://", "t.me/", "www."]):
        await update.message.delete()
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.send_message(update.effective_chat.id, f"🚫 {user.full_name} - Link ကြောင့် Ban လိုက်ပါပြီ။")
        return
    user_messages[user.id].append(update.message.date)
    recent = [m for m in user_messages[user.id] if (update.message.date - m).seconds < 5]
    user_messages[user.id] = recent
    if len(recent) > 5:
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions=ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"🛑 {user.full_name} - Spam ကြောင့် Mute လိုက်ပါပြီ။")

async def track_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    target = result.new_chat_member.user
    if result.old_chat_member.status in ["left", "kicked"] and result.new_chat_member.status == "member":
        text = f"✨ ကြိုဆိုပါတယ် {target.full_name}!\n⏰ အချိန်: {datetime.now().strftime('%H:%M:%S')}"
        photos = await context.bot.get_user_profile_photos(target.id, limit=1)
        if photos.total_count > 0: await context.bot.send_photo(result.chat.id, photo=photos.photos[0][0].file_id, caption=text)
        else: await context.bot.send_message(result.chat.id, text=text)
    elif result.new_chat_member.status in ["left", "kicked"]:
        await context.bot.send_message(result.chat.id, f"👋 {target.full_name} ထွက်သွားတဲ့အတွက် ဝမ်းနည်းပါတယ်။ နောက်တစ်ခါ လာလည်ပေးပါနော်!")

# --- MAIN ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handlers([
        CommandHandler("ban", ban_user), CommandHandler("mute", mute_user),
        CommandHandler("warn", warn_user), CommandHandler("kick", kick_user),
        CommandHandler("pin", pin_message), CommandHandler("id", get_info),
        CommandHandler("rules", show_rules),
        MessageHandler(filters.TEXT | filters.CAPTION, security_filter),
        ChatMemberHandler(track_members, ChatMemberHandler.CHAT_MEMBER)
    ])
    print("Bot စတင် အလုပ်လုပ်နေပါပြီ...")
    app.run_polling()

if __name__ == "__main__":
    main()
      
