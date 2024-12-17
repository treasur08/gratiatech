import nest_asyncio
import asyncio
nest_asyncio.apply()

import random
import os
from dotenv import load_dotenv
import string
from withdraw import handle_task_withdrawal_request, handle_numeric_input, finalize_withdrawal
from telegram.constants import ParseMode
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler, CallbackContext
from database import Database
from datetime import datetime
import http.server
import socketserver
import re
import threading

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# State definitions
AWAITING_BET_AMOUNT = range(1)
AWAITING_DASH_ODD = range(2)

# Initialize database
db = Database('gratia.db')
tokens = db.get_unused_tokens()
if not tokens:
    tokens = ['GRAT' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) for _ in range(30000)]
    db.save_tokens(tokens)
    with open("tokens.txt", "w") as file:
        for token in tokens:
            file.write(token + "\n")
    
    print(f"Tokens Generated, Bot Started")
    async def send_tokens_to_admin():
        try:
            application = Application.builder().token(BOT_TOKEN).build()
            await application.bot.send_document(
                chat_id=ADMIN_ID,
                document=open("tokens.txt", "rb"),
                caption="Here is the latest tokens.txt file containing generated tokens.",
                parse_mode=ParseMode.HTML
            )
            print("Tokens file sent to admin successfully!")
        except Exception as e:
            print(f"Failed to send tokens file to admin: {e}")

    asyncio.run(send_tokens_to_admin())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id

    if db.is_user_registered(chat_id):
        await show_main_menu(update, context, user.first_name)
    else:
        if context.args:
            referrer_id = context.args[0]
            context.user_data['referrer_id'] = referrer_id
        keyboard = generate_start_keyboard()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Hi {user.first_name}, Welcome to GRATIA TECHNOLOGY👏〽\nPlease enter your 10 digits GRATIA TECHNOLOGY Token/Coupon Code to gain access and earn an instant 500 NGN Registration Bonus 🎁.\n\nIf you don't have a GRATIA TECHNOLOGY Coupon code, Please use the \"Buy Code\" button to get one!\n\nAs soon as you login, kindly set your GRATIA TECHNOLOGY Withdrawal PIN 🔢 on the Security 🔐 page\n\nWith this PIN🔢, your GRATIA TECHNOLOGY earnings are secure so don't hesitate to add your PIN.\n\nJoin our Whatsapp/Telegram channel so that you can be up to date about latest\ninfos on your GRATIA TECHNOLOGY earning platform\n\nOnce again, Welcome {user.first_name} ❤!",
            reply_markup=keyboard
        )

def generate_start_keyboard():
    keyboard = [
        ["Buy Code", "About 🤔"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def send_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if str(chat_id) == ADMIN_ID:
        try:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=open("tokens.txt", "rb"),
                caption="Here is the tokens.txt file containing generated tokens.",
                parse_mode=ParseMode.HTML
            )
            await update.message.reply_text("Tokens file has been sent to your chat.")
        except Exception as e:
            print(f"Error sending tokens file: {e}")
            await update.message.reply_text("Failed to send the tokens file.")
    else:
        await update.message.reply_text("This command is restricted to the admin.")


async def handle_buy_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    keyboard = [[InlineKeyboardButton("AY TECH", url="https://wa.link/8ev6zh"), InlineKeyboardButton("YUNGKASLY MEDIA", url="https://wa.link/vld916")],
                 [InlineKeyboardButton("𝐖𝐄𝐁 𝐃𝐄𝐕𝐄𝐋𝐎𝐏𝐄𝐑", url="https://wa.link/9hz3ec"), InlineKeyboardButton("SUCCESS MEDIA", url="https://wa.link/cfh3tc")],
                 [InlineKeyboardButton("SUNDAY OBINNA", url="https://wa.link/ee4x69"), InlineKeyboardButton("COUCH MEDIA", url="https://wa.link/46cv7j")],
                 [InlineKeyboardButton("Yunus'G Media", url="https://wa.link/1imgib"), InlineKeyboardButton("JOSHUAMEDIA", url="https://wa.link/8yjzve")]
                ]    
    markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="To purchase an GRATIA TECHNOLOGY token code, please contact one of our vendors", reply_markup=markup)

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id,text=f"*BREAK DOWN OF HOW GRATIA WORKS* 🧡💙\n\n\n*REGISTRATION FEE*= N2,500\n\n*WELCOME BONUS* = 500\n\n*REFERRAL COMMISSION*, 👉🏽  N1,000\n\n*EVERY DAY EARNING TASKS*⬇️\n\n*TASK BONUS* 👉🏽 N100 per task\n\n*GAME BONUS* 👉🏽 *N200*\n\n*MINIMUM THRESHOLD FOR REFERRAL AND TASK EARNING* ⬇️\n\n*REFERRAL EARNINGS*,⬇️\n\n*MINIMUM SUM OF N2,000*\n\n*DAYS*\n\nANYTIME\n\n*TASK EARNINGS* ⬇️\n\n*MINIMUM SUM OF N6,000* $GRAT\n\n*DAYS*\n\nWEEKENDS [ONCE YOU REACH THE THRESHOLD]\n\n*NOTE*\n\nALL EARNINGS WILL BE PAID DIRECTLY TO YOUR DESIRED BANK ACCOUNT OF YOUR CHOICE.\n\nNO PROBLEM IF YOU CANT REFER,  GRATIA IS HERE FOR YOU🧡💙\n\nBUY CODE NOW TO GET STARTED", parse_mode='Markdown')
            

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = update.message.chat_id
    text = update.message.text

    if str(chat_id) == ADMIN_ID:
        if 'awaiting_task_image' in context.user_data and update.message.photo:
            context.user_data['task_image'] = update.message.photo[-1].file_id
            await update.message.reply_text("Image received. Now send the task instructions:")
            context.user_data['awaiting_task_image'] = False
            context.user_data['awaiting_task_instructions'] = True
            
        elif 'awaiting_task_instructions' in context.user_data and update.message.text:
            image_id = context.user_data.get('task_image')
            if image_id:
                db.save_current_task(image_id, update.message.text)
                await update.message.reply_text("Task posted successfully!")
                del context.user_data['task_image']
                del context.user_data['awaiting_task_instructions']
                
                # Broadcast task to all users
                all_users = db.get_all_users()
                for user_id in all_users:
                    try:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=image_id,
                            caption=update.message.text,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Failed to send task to user {user_id}: {str(e)}")

    elif 'awaiting_pin' in context.user_data and context.user_data['awaiting_pin']:
        await pin_handler(update, context)
    elif 'awaiting_pin_set' in context.user_data and context.user_data['awaiting_pin_set']:
        if text.isdigit() and len(text) == 4:
            db.save_pin(chat_id, text)
            keyboard = [[KeyboardButton("Enable PIN 🔑")], [KeyboardButton("Back")]]
            reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await context.bot.send_message(chat_id=chat_id, text="PIN set successfully 🔑! You can now use it to secure your transactions.\nDo not forget this PIN!\nKeep it somewhere safe\n\nUse the Enable PIN 🔑 button so that you can start using your PIN ",reply_markup=reply)
            del context.user_data['awaiting_pin_set']
        else:
            await context.bot.send_message(chat_id=chat_id, text="Invalid PIN format. Please enter a 4-digit PIN 🔢.")
    elif 'awaiting_pin_change' in context.user_data and context.user_data['awaiting_pin_change']:
        current_pin = db.get_pin(chat_id)
        if text == current_pin:
            await context.bot.send_message(chat_id=chat_id, text="Please enter your new 4-digit PIN 🔢🔑.")
            context.user_data['awaiting_pin_change'] = False
            context.user_data['awaiting_new_pin'] = True
        else:
            inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
            markup = InlineKeyboardMarkup(inline_keyboard)
            await context.bot.send_message(chat_id=chat_id, text="Incorrect PIN ❌. Please enter your current PIN to proceed with changing it.", reply_markup=markup)
    elif 'awaiting_new_pin' in context.user_data and context.user_data['awaiting_new_pin']:
        if text.isdigit() and len(text) == 4:
            db.update_pin(chat_id, text)
            keyboard = [[KeyboardButton("Back")]]
            reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await context.bot.send_message(chat_id=chat_id, text="PIN changed successfully!", reply_markup=reply)
            del context.user_data['awaiting_new_pin']
        else:
            await context.bot.send_message(chat_id=chat_id, text="Invalid PIN format. Please enter a new 4-digit PIN.(PIN must be 4 Digits)")
    else:
            if 'awaiting_account_details' in context.user_data and context.user_data['awaiting_account_details']:
                await handle_account_details(update, context, text)

            elif 'awaiting_broadcast' in context.user_data and context.user_data['awaiting_broadcast']:
                await broadcast_message(update, context, text)
                del context.user_data['awaiting_broadcast']

            elif 'awaiting_withdrawal_amount' in context.user_data and context.user_data['awaiting_withdrawal_amount']:
                await handle_withdrawal_amount(update, context, text)
            elif db.is_user_registered(chat_id):
                if text == "Referral Link 🎁":
                    referral_link = f"https://t.me/gratiatechnologybot?start={chat_id}"
                    share_button = InlineKeyboardButton("Share 📤", switch_inline_query=referral_link)
                    share_markup = InlineKeyboardMarkup([[share_button]])
                    await context.bot.send_message(chat_id=chat_id, text=f"Share this link with your friends,\nEarn 1,000 NGN for every successful Referrals: {referral_link} \n And earn 1,000 NGN for each successful referral", reply_markup=share_markup)

                elif text == "Ref Count":
                    await handle_ref_count(update, context)

                elif text == "Balance 💰":
                    balances = db.get_user_balances(chat_id)
                    await show_balance(update, context, balances)
                elif text == "Affiliate Withdrawal 💸":
                    await ask_account_details(update, context)
                elif text == "Task Withdrawal 💸":
                    await handle_task_withdrawal_request(update, context)
                elif text == "Profile 👤":
                    await show_profile(update, context)
                elif text == "Buy code 🛒":
                    await handle_buy_code(update, context)
                elif text == "Channel 📣":
                    await handle_channel(update, context)
                elif text == "Help 🆘":
                    await handle_info(update, context)
                elif text == "Games ♣":
                    keyboard = [
                        [KeyboardButton("Head or Tail 🪙")],
                        [KeyboardButton("Back")]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text("What game 🎮 do you want to play?", reply_markup=reply_markup)
                
                elif text == "Security 🔐":
                    keyboard = [
                        [KeyboardButton("Set PIN 🔒"), KeyboardButton("Change PIN 🔄")],
                        [KeyboardButton("Forgot PIN 🤔❓"), KeyboardButton("Back")]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(f"*Welcome, {user.first_name} to GRATIA TECHNOLOGY's security Page*\n\nDo well to set your *PIN* before beginning any operations on GRATIA TECHNOLOGY to ensure security of your funds.\n\nAfter setting your PIN don't forget to enable it so that can be regognized.", reply_markup=reply_markup, parse_mode="Markdown")
                elif text == "Head or Tail 🪙":
                    games_today = db.get_games_played_today(chat_id)
                    if games_today >= 2:
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text="You've reached your daily limit of 2 games. Come back tomorrow! 🎮",
                            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True)
                        )
                    else:
                        keyboard = [[KeyboardButton("Head"), KeyboardButton("Tail")], [KeyboardButton("Back")]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text=f"Choose Head or Tail! (Games played today: {games_today}/2)", 
                            reply_markup=reply_markup
                        )
                elif text == "Play Again 🎲":
                    games_today = db.get_games_played_today(chat_id)
                    if games_today >= 2:
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text="You've reached your daily limit of 2 games. Come back tomorrow! 🎮",
                            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True)
                        )
                    else:
                        keyboard = [[KeyboardButton("Head"), KeyboardButton("Tail")], [KeyboardButton("Back")]]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        await context.bot.send_message(
                            chat_id=chat_id, 
                            text=f"Choose Head or Tail! (Games played today: {games_today}/2)", 
                            reply_markup=reply_markup
                        )

                elif text == "Place withdrawal":
                    await handle_place_withdrawal(update, context)
                elif text == "Edit account details":
                    await ask_account_details(update, context)
                elif text == 'Add Account':
                    await ask_account_details(update, context)
                elif text in ["Head", "Tail"]:
                    await process_bet(update, context, text)
                elif text == "Back":
                    await show_main_menu(update, context, user.first_name)
                elif text == "Task 📋":
                    await handle_task(update, context)
                elif text == 'Done Task ✅':
                    await handle_done_task(update, context)
                elif text == "Set PIN 🔒":
                    await handle_set_pin(update, context)
                elif text == "Change PIN 🔄":
                    await handle_change_pin(update, context)
                elif text == "Enable PIN 🔑":
                    await context.bot.send_message(chat_id=chat_id, text="Your PIN 🔢 Has Been Successfully Enabled, you can make use of it\n\nThe Enable Pin button should be used if your PIN is not accepted")
                    context.user_data['awaiting_account_details'] = False
                    context.user_data['awaiting_bet_amount'] = False
                    context.user_data['awaiting_withdrawal_amount'] = False
                    context.user_data['awaiting_pin'] = False
                    context.user_data['awaiting_pin_change'] = False
                    context.user_data['awaiting_pin_set'] = False


                elif text == "Share 📤": 
                    referral_link = f"https://t.me/gratiatechnologybot?start={chat_id}"
                    await context.bot.send_message(chat_id=chat_id, text=f"Share this link with your friends, \n Receive 1,000 NGN for every successsful referral: {referral_link}")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="Invalid option. Please choose from the main menu.")
            else:
                if text in tokens:
                    if db.is_token_used(text):
                        await context.bot.send_message(chat_id=chat_id, text="This token has been used. Enter an unused token.")
                    else:
                        db.register_user(chat_id, user.first_name, text)
                        db.mark_token_as_used(text)
                        referrer_id = context.user_data.get('referrer_id')
                        if referrer_id:
                            db.record_referral(referrer_id, chat_id)
                            db.update_affiliate_balance(referrer_id, 1000)
                            await context.bot.send_message(chat_id=referrer_id, text=f"You have referred {user.first_name} and earned 1000 NGN Referral Bonus! 😁💲")
                        await context.bot.send_message(chat_id=chat_id, text="You have been registered and earned a 500 NGN bonus!")
                        await show_main_menu(update, context, user.first_name)
                else:
                    await context.bot.send_message(chat_id=chat_id, text="Invalid token. Please enter a valid 8 digits GRATIA TECHNOLOGY token.")

async def handle_channel(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Join Telegram Channel", url="https://t.me/gratia0002")],
        [InlineKeyboardButton("Payment Channel", url="https://t.me/paymentchannel00001")],
        [InlineKeyboardButton("Discussion Group", url="https://t.me/paymentchannel00001")],
        [InlineKeyboardButton("WhatsApp Group", url="https://chat.whatsapp.com/J7CUtUUORrq1sdXiTLgCgb")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Join our Channels and Groups for more updates and new information:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text("Join our Telegram Channel for more updates and new information:", reply_markup=reply_markup)


async def process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE, choice: str):
    chat_id = update.message.chat_id
    
    # Check daily game count
    games_today = db.get_games_played_today(chat_id)
    if games_today >= 2:
        await context.bot.send_message(chat_id=chat_id, text="You've reached your daily limit of 2 games. Come back tomorrow! 🎮")
        return

    animations = ["Spinning |","Spinning /","Spinning -","Spinning |","🗿 ࿓"]
    message = await context.bot.send_message(chat_id=chat_id, text=animations[0])
    for emoji in animations[1:]:
        await asyncio.sleep(0.2)
        await message.edit_text(emoji)

    await asyncio.sleep(0.5)
    result = random.choice(["Head", "Tail"])
    keyboard = [[KeyboardButton("Play Again 🎲")], [KeyboardButton("Back")]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if choice == result:
        db.update_task_balance(chat_id, 100)
        db.increment_games_played_today(chat_id)
        await context.bot.send_message(chat_id=chat_id, text=f"🎉 You won! The coin landed on {result}. You earned 100 NGN!", reply_markup=reply)
    else:
        db.increment_games_played_today(chat_id)
        await context.bot.send_message(chat_id=chat_id, text=f"Better luck next time! The coin landed on {result}.", reply_markup=reply)


async def handle_info(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Join Telegram Channel", url="https://t.me/gratia0002")],
        [InlineKeyboardButton("Payment Channel", url="https://t.me/paymentchannel00001")],
        [InlineKeyboardButton("Discussion Group", url="https://t.me/paymentchannel00001")],
        [InlineKeyboardButton("WhatsApp Group", url="https://chat.whatsapp.com/J7CUtUUORrq1sdXiTLgCgb")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("For help or more info on GRATIA TECHNOLOGY, please visit our website or contact our support:", reply_markup=reply_markup)

async def handle_buy_code(update: Update, context):
    keyboard = [[InlineKeyboardButton("AY TECH", url="https://wa.link/8ev6zh"), InlineKeyboardButton("YUNGKASLY MEDIA", url="https://wa.link/vld916")],
                 [InlineKeyboardButton("𝐖𝐄𝐁 𝐃𝐄𝐕𝐄𝐋𝐎𝐏𝐄𝐑", url="https://wa.link/9hz3ec"), InlineKeyboardButton("SUCCESS MEDIA", url="https://wa.link/cfh3tc")],
                 [InlineKeyboardButton("SUNDAY OBINNA", url="https://wa.link/ee4x69"), InlineKeyboardButton("COUCH MEDIA", url="https://wa.link/46cv7j")],
                 [InlineKeyboardButton("Yunus'G Media", url="https://wa.link/1imgib"),  InlineKeyboardButton("JOSHUAMEDIA", url ='https://wa.link/8yjzve')]
                ] 
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("To buy a code, please contact any active seller listed below", reply_markup=reply_markup)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, first_name: str):
    keyboard = [
        [KeyboardButton("Profile 👤"), KeyboardButton("Security 🔐")],
        [KeyboardButton("Referral Link 🎁"), KeyboardButton("Balance 💰")],
        [KeyboardButton("Affiliate Withdrawal 💸"), KeyboardButton("Task Withdrawal 💸")],
        [KeyboardButton("Channel 📣"), KeyboardButton("Help 🆘")],
        [KeyboardButton("Games ♣"), KeyboardButton("Ref Count")],
        [KeyboardButton("Task 📋"), KeyboardButton("Withdraw History 💱")],
        [KeyboardButton("Buy code 🛒")]

    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"Welcome, {first_name}! to GRATIA TECHNOLOGY", reply_markup=reply_markup)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_info = db.get_user_info(chat_id)  # Custom method to get user info
    if user_info:
        first_name = user_info['first_name']
        last_name = user_info['last_name'] if user_info['last_name'] else ''
        user_id = user_info['chat_id']
        balances = db.get_user_balances(chat_id)
        completed_task = user_info['completed_task']
        task_earnings = completed_task * 100
        referral_link = f"https://t.me/gratiatechnologybot?start={chat_id}"
        referral_count = db.get_referral_count(chat_id)

        profile_text = (f"<b>GRATIA TECHNOLOGY USER PROFILE 👤</b>♨️\n\n"
                        f"<b>♨️Full Name:</b> {first_name} {last_name}\n"
                        f"<b>♨️User ID:</b> <code>{user_id}</code>\n"
                        f"<b>♨️Referral Balance:</b> {balances['affiliate_balance']} NGN\n"
                        f"<b>♨️Task Balance:</b> {balances['task_balance']} NGN\n"
                        f"<b>♨️Task Done:</b> {completed_task}\n"
                        f"<b>♨️Task Earns:</b> {task_earnings} NGN\n"
                        f"<b>♨️Ref Count:</b> {referral_count}\n"
                        f"<b>♨️Ref Link:</b> <code>{referral_link}</code>")

        await context.bot.send_message(chat_id=chat_id, text=profile_text, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text="User profile not found.")

#Im leaving here for the pin
async def handle_set_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    current_pin = db.get_pin(chat_id)
    if current_pin:
        keyboard = [[KeyboardButton("Change PIN 🔄")], [KeyboardButton("Back")]]
        reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await context.bot.send_message(chat_id=chat_id, text="You already have a PIN set. Use 'Change PIN 🔄' option to update it.", reply_markup=reply)
    else:
        inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
        markup = InlineKeyboardMarkup(inline_keyboard)
        await context.bot.send_message(chat_id=chat_id, text="Welcome to GRATIA TECHNOLOGY's Security Page\n\nYou are seeing this page because its probably the first time you are here.\n\nEnsure that you set a 4 Digit PIN 🔢 that you would always remember\nUse this PIN for Withdrawal purposes ONLY\n\nPlease enter a new 4-digit PIN.", reply_markup=markup)
        context.user_data['awaiting_pin_set'] = True

async def handle_change_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    current_pin = db.get_pin(chat_id)
    if not current_pin:
        keyboard = [[KeyboardButton("Back")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await context.bot.send_message(chat_id=chat_id, text="You don't have a PIN set yet. Use 'Set PIN' option to create one.", reply_markup=reply_markup)
    else:
        inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
        markup = InlineKeyboardMarkup(inline_keyboard)
        await context.bot.send_message(chat_id=chat_id, text="Please enter your current PIN to proceed with changing it.", reply_markup=markup)
        context.user_data['awaiting_pin_change'] = True

async def ask_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    context.user_data['awaiting_pin'] = True
    inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')],[InlineKeyboardButton("Enable PIN 🔑", callback_data='enable')]]
    markup = InlineKeyboardMarkup(inline_keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Please enter your 4-digit PIN to proceed 🔢\n\nIf not set, press the Cancel ❌ button and set it on the Security menu:", reply_markup=markup)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    print(f"Callback query received: {data}")

    if data == 'cancel':
        await handle_cancel(update, context)
    if data == "back_to_menu":
        await show_admin_menu(update, context)
    if data == 'reload':
        await handle_reload(update, context)
    if data == 'enable':
        await handle_enable(update, context)
    if data == 'rules':
        await handle_rules(update, context)
    if data == 'show_user_count':
        await show_user_count(update, context)
    if data == 'show_user_proofs':
        await show_user_proofs(update, context)
    if data == "clear_proofs":
        await clear_proofs(update, context)
    if data == 'broadcast_message':
        await query.message.reply_text('Please send the message you want to broadcast:')
        context.user_data['awaiting_broadcast'] = True
    elif data == 'broadcast_photo':
        await query.message.reply_text('Please upload the photo you want to broadcast:')
        context.user_data['awaiting_photo'] = True
    elif data == 'stop':
        context.user_data['awaiting_broadcast'] = False
        await query.message.reply_text('Broadcast message canceled.')

    elif data == 'post_task':
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please send the task image:"
        )
        context.user_data['awaiting_task_image'] = True
        await query.answer()
    elif data.startswith("num_"):
        await handle_numeric_input(update, context, db)
    elif data == 'finalize_withdrawal':
        await finalize_withdrawal(update, context, db)


async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == 'user_count':
        await show_user_count(update, context)
    elif data == 'broadcast':
        await broadcast_message(update, context)


async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    last_completed = db.get_last_task_completed(chat_id)

    if last_completed and not enough_time_has_passed(last_completed):
        await context.bot.send_message(
            chat_id=chat_id, 
            text="You have done the task ✅, have a nice day.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True)
        )
    else:
        current_task = db.get_current_task()
        if current_task:
            await context.bot.send_photo(
                chat_id=chat_id, 
                photo=current_task['image'],
                caption=current_task['instructions'],
                parse_mode="HTML"
            )
            keyboard = [[KeyboardButton("Done Task ✅")], [KeyboardButton("Back")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Please follow the instructions above and click 'Done Task ✅' when you are done.",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="No tasks available at the moment. Check back later!",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True)
            )

async def handle_done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    last_completed = db.get_last_task_completed(chat_id)

    if last_completed and not enough_time_has_passed(last_completed):
        await context.bot.send_message(chat_id=chat_id, text="Sorry you have earlier submitted the task. Please wait for a new task.")
        return

    # Ask user to upload a picture
    await context.bot.send_message(chat_id=chat_id, text="Please upload a screenshot of the completed task.")

    # Set the state to await the picture
    context.user_data['awaiting_task_picture'] = True


    


def enough_time_has_passed(last_completed):
    if isinstance(last_completed, str):
        last_completed = datetime.strptime(last_completed, '%Y-%m-%d %H:%M:%S')
    return (datetime.now() - last_completed).total_seconds() > (30 * 60 * 60)



async def handle_ref_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    referral_count = db.get_referral_count(chat_id)
    await context.bot.send_message(chat_id=chat_id, text=f"You have {referral_count} referrals.",
                                   reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True))


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, balances: int):
    chat_id = update.message.chat_id
    balances = db.get_user_balances(chat_id)
    
    keyboard = [
        [KeyboardButton("Withdraw 💸"), KeyboardButton("Games ♣")],
        [KeyboardButton("Back")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    balance_text = (
        f"💰 Your GRATIA TECHNOLOGY Balances:\n\n"
        f"📊 Task Balance: {balances['task_balance']} NGN\n"
        f"🤝 Affiliate Balance: {balances['affiliate_balance']} NGN\n\n"
        f"Total Balance: {balances['task_balance'] + balances['affiliate_balance']} NGN"
    )
    
    await update.message.reply_text(balance_text, reply_markup=reply_markup)

async def ask_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not context.user_data.get('pin_verified'):
        context.user_data['next_action'] = ask_account_details
        await ask_pin(update, context)
        return
    context.user_data['awaiting_account_details'] = True
    inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
    markup = InlineKeyboardMarkup(inline_keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Please enter your ACCOUNT DETAILS: (Account name, Account number, Bank name):", reply_markup=markup)

async def handle_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user = update.message.from_user
    chat_id = update.message.chat_id

    if 'account_details' not in context.user_data:
        context.user_data['account_details'] = []
    
    context.user_data['account_details'].append(text)
    
    if len(context.user_data['account_details']) == 1:
        await context.bot.send_message(chat_id=chat_id, text="Great! Now enter your account number:")
    elif len(context.user_data['account_details']) == 2:
        await context.bot.send_message(chat_id=chat_id, text="Perfect! Finally enter your bank name:")
    elif len(context.user_data['account_details']) == 3:
        account_name, account_number, bank_name = context.user_data['account_details']
        db.save_account_details(chat_id, account_number, account_name, bank_name)
        balance = db.get_user_balances(chat_id)
        
        await context.bot.send_message(chat_id=chat_id, text=f"Hi {user.first_name}, your balance is {balance['affiliate_balance']} NGN\nMinimum withdrawal is 2,000 NGN")
        await context.bot.send_message(
            chat_id=chat_id, 
            text="Press 'Place withdrawal' to withdraw your Balance\nPress 'Edit Details' to edit your Account Details",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("Place withdrawal")],
                [KeyboardButton('Task Withdrawal 💸')],
                [KeyboardButton("Edit account details")], 
                [KeyboardButton("Back")]
            ], resize_keyboard=True)
        )
        
        del context.user_data['account_details']
        context.user_data['awaiting_account_details'] = False


async def handle_place_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    referral_count = db.get_referral_count(chat_id)
    if referral_count == 0:
        await context.bot.send_message(chat_id=chat_id, text="Please refer someone to GRATIA TECHNOLOGY before placing a withdrawal")
        return
    context.user_data['awaiting_withdrawal_amount'] = True
    inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
    markup = InlineKeyboardMarkup(inline_keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Enter the amount you want to withdraw\nMinimum withdrawal (2,000 NGN):", reply_markup=markup)


# Inside handle_withdrawal_amount function in your Telegram bot script

async def handle_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    chat_id = update.message.chat_id

    if not text.isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Please enter a valid number, eg: '2000'\nNo Signs or Commas")
        return

    withdrawal_amount = int(text)

    if withdrawal_amount < 2000:
        await context.bot.send_message(chat_id=chat_id, text="The minimum withdrawal amount is 2,000 NGN. Please enter a valid amount.")
        return

    balance = db.get_user_balances(chat_id)
    affiliate_balance = balance['affiliate_balance']
    task_bal = balance['task_balance']

    if withdrawal_amount > affiliate_balance:
        await context.bot.send_message(chat_id=chat_id, text="You do not have enough balance to withdraw this amount.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True))
        context.user_data['awaiting_withdrawal_amount'] = False
        return

    # Store withdrawal request
    db.store_withdrawal_request(chat_id, withdrawal_amount)

    # Deduct withdrawal amount from user's balance
    db.update_affiliate_balance(chat_id, -withdrawal_amount)

    # Retrieve account details
    account_details = db.get_account_details(chat_id)

    # Forward details to admin
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"Withdrawal Request:\nChat ID: {chat_id}\nWithdrawal Amount: {withdrawal_amount} NGN\nAccount Details: {account_details}\nUser Referral Balance: {affiliate_balance}\n User Task Balance: {task_bal}")

    # Confirmation message to user
    confirmation_message = f"Your withdrawal request of {withdrawal_amount} NGN has been submitted. You will receive your funds shortly."
    await context.bot.send_message(chat_id=chat_id, text=confirmation_message)

    # Reset awaiting state
    context.user_data['awaiting_withdrawal_amount'] = False

async def passs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.message.chat_id, text="No tasks for now. come back later", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True))





async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    await query.message.reply_text("Operation cancelled.")
    context.user_data.clear()


async def handle_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.reply_text(
        '*Welcome to Head or Tail Game! 🪙*\n\n'
        '*How to Play:*\n'
        '*1. Game Rules*:\n'
        '- You can play twice per day\n'
        '- Guess where the coin lands: Head or Tail\n'
        '- Correct guess earns you 100 NGN\n'
        '- Wrong guess? Try again next time!\n\n'
        '*2. Game Mechanics:*\n'
        '- Select your guess (Head/Tail)\n'
        '- System flips a virtual coin\n'
        '- If your guess matches, you win!\n\n'
        '*Rewards:*\n'
        '- Win 100 NGN per correct guess\n'
        '- Maximum 2 games per day\n'
        '- Maximum potential daily earnings: 200 NGN\n\n'
        'Ready to test your luck? Choose Head or Tail!',
        parse_mode='Markdown'
    )





async def handle_enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.message:
        await query.message.reply_text("PIN 🔑 enabled! Click on the 'Withdraw 💸' button and re-enter PIN")
    else:

        await context.bot.send_message(chat_id=user_id, text="PIN 🔑 enabled! Click on the 'Withdraw 💸' button and re-enter PIN")
    context.user_data['awaiting_account_details'] = False
    context.user_data['awaiting_bet_amount'] = False
    context.user_data['awaiting_withdrawal_amount'] = False
    context.user_data['awaiting_pin'] = False
    context.user_data['awaiting_pin_change'] = False
    context.user_data['awaiting_pin_set'] = False




async def handle_reload(update: Update, context):
    query = update.callback_query
    await query.message.reply_text("Click on the 'Withdraw 💸' button and re-enter PIN")
    context.user_data['awaiting_account_details'] = False
    context.user_data['awaiting_bet_amount'] = False
    context.user_data['awaiting_withdrawal_amount'] = False
    context.user_data['awaiting_pin'] = False
    context.user_data['awaiting_pin_change'] = False
    context.user_data['awaiting_pin_set'] = False


async def show_withdrawal_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_withdrawals = db.get_withdrawal_requests_by_user(chat_id)

    if not user_withdrawals:
        keyboard = [[KeyboardButton("Withdraw 💸")], [KeyboardButton("Back")]]
        reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await context.bot.send_message(chat_id=chat_id, text="You have no withdrawal history.", reply_markup=reply)
        return

    total_earnings = sum(withdrawal['withdrawal_amount'] for withdrawal in user_withdrawals)
    message = f"Total Payouts: {total_earnings}\n\n"

    for withdrawal in user_withdrawals:
        amount = withdrawal['withdrawal_amount']
        status = withdrawal['status']
        date = withdrawal['timestamp']
        account_details = db.get_account_details(chat_id)
        account_number, account_name, bank_name = account_details.split(', ')
        masked_account_number = account_name[:2] + '*' * (len(account_name) - 3) + account_name[-1]

        message += (f"Amount: {amount}\n"
                    f"Status: {status} ✅\n"
                    f"Date: {date}\n"
                    f"Sender: GRATIA TECHNOLOGY NG\n"
                    f"Receiver: {account_number} ({masked_account_number}) {bank_name}\n\n")

    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Back")]], resize_keyboard=True))

async def pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text
    if 'awaiting_pin' in context.user_data and context.user_data['awaiting_pin']:
        if text.isdigit() and len(text) == 4 and db.verify_pin(chat_id, text):
            context.user_data['awaiting_pin'] = False
            if 'awaiting_account_details' in context.user_data:
                await context.bot.send_message(chat_id=chat_id, text="PIN 🔢 Verified 🔑")
                context.user_data['awaiting_account_details'] = True
                inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
                markup = InlineKeyboardMarkup(inline_keyboard)
                await context.bot.send_message(chat_id=chat_id, text="*Please enter your ACCOUNT DETAILS*:\n\nFirstly Enter Your Account Name\n\n`John Mark`", reply_markup=markup, parse_mode='Markdown')
                                           
        else:
            inline_keyboard = [[InlineKeyboardButton("Cancel ❌", callback_data='cancel')]]
            markup = InlineKeyboardMarkup(inline_keyboard)
            await context.bot.send_message(chat_id=chat_id, text="Invalid PIN. Please try again.", reply_markup=markup)

    else:
        inline_keyboard = [[InlineKeyboardButton("Enter Again 🔃", callback_data='reload')]]
        markup = InlineKeyboardMarkup(inline_keyboard)
        await context.bot.send_message(chat_id=chat_id, text="Confirming your pin from DataBase... Enter Again")
        context.user_data['awaiting_account_details'] = False

async def handle_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    top_referrers = db.get_top_referrers()

    if top_referrers:
        leaderboard_text = "🏆 Top Referrers 🏆\n\n"
        for i, (user_id, referral_count) in enumerate(top_referrers, start=1):
            user = await context.bot.get_chat(user_id)
            leaderboard_text += f"{i}. {user.first_name} - {referral_count} referrals\n"
    else:
        leaderboard_text = "No referrals yet 😥. Be the first to refer someone 😁🏆!"

    await context.bot.send_message(chat_id=chat_id, text=leaderboard_text)

async def admin(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if str(chat_id) == ADMIN_ID:  # Assuming ADMIN_ID is defined somewhere
        await show_admin_menu(update, context)
    else:
        await update.message.reply_text("You are not authorized to access the admin menu.")

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Show User Count", callback_data='show_user_count'),
            InlineKeyboardButton("User Proofs", callback_data='show_user_proofs')
        ],
        [
            InlineKeyboardButton("Broadcast Pic", callback_data='broadcast_photo'),
            InlineKeyboardButton("Broadcast Message", callback_data='broadcast_message')
        ],
        [
            InlineKeyboardButton("Post Task", callback_data='post_task')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Admin Menu:', reply_markup=reply_markup)


async def show_user_proofs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proofs = db.get_user_proofs()

    if not proofs:
        await context.bot.send_message(chat_id=ADMIN_ID, text="There are no proofs for now.")
    else:
        # Prepare keyboard markup
        keyboard = [
            [InlineKeyboardButton("Clear 💨", callback_data='clear_proofs'), InlineKeyboardButton("Back", callback_data='back_to_menu')]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        for proof in proofs:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=proof['file_id'], caption=f"User ID: {proof['chat_id']}\n Submitted on: {proof['timestamp']}", reply_markup=markup)


async def approve_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error: No arguments provided.")
        return

    chat_id = context.args[0]
    db.update_user_task_status(chat_id, 'approved')
    await context.bot.send_message(chat_id=chat_id, text="Your task has been approved by GRATIA TECHNOLOGY.")
    await update.message.reply_text('Users task has been approved')


async def reject_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error: No arguments provided.")
        return

    chat_id = context.args[0]
    db.update_user_task_status(chat_id, 'rejected')
    db.update_task_balance(chat_id, -100)
    await context.bot.send_message(chat_id=chat_id, text="Unfortunately, your task was disapproved. Do the task well next time 🤝")
    await update.message.reply_text('Users task has been approved')

# Function to handle broadcasting
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE, broadcast_text=None, broadcast_photo=None, caption=None):
    all_users = db.get_all_users()
    for user_chat_id in all_users:
        try:
            if broadcast_text:
                await context.bot.send_message(user_chat_id, broadcast_text)
            if broadcast_photo:
                await context.bot.send_photo(user_chat_id, photo=broadcast_photo, caption=caption)
        except Exception as e:
            print(f"Failed to send message to user {user_chat_id}: {str(e)}")

    if update.callback_query:
        await update.callback_query.answer('Broadcast sent to all users.')
    elif update.message:
        await update.message.reply_text('Broadcast sent to all users.')


async def show_user_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_count = db.get_user_count()
    if update.message:
        await update.message.reply_text(f"Total users: {user_count}")
    elif update.callback_query:
        await update.callback_query.answer(f"Total users: {user_count}")



async def clear_proofs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.clear_user_proofs()
    if update.message:
        await update.message.reply_text("All proofs cleared from the database")
    elif update.callback_query:
        await update.callback_query.answer("All proofs cleared from the database.")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('admin', admin))
    application.add_handler(CommandHandler('show_user_count', show_user_count))
    application.add_handler(CommandHandler('approve', approve_task))
    application.add_handler(CommandHandler('tokens', send_tokens))
    application.add_handler(CommandHandler('reject', reject_task))
    application.add_handler(CommandHandler('withdraw_history', show_withdrawal_history))
    application.add_handler(CommandHandler("set_pin", handle_set_pin))

    # CallbackQuery Handlers
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(CallbackQueryHandler(handle_task_withdrawal_request, pattern="^task_withdrawal$"))
    application.add_handler(CallbackQueryHandler(pin_handler))

    # Message Handlers for Text Commands
    application.add_handler(MessageHandler(filters.Text("Buy Code"), handle_buy_code))
    application.add_handler(MessageHandler(filters.Text("Withdraw History 💱"), show_withdrawal_history))
    application.add_handler(MessageHandler(filters.Text("Leaderboard 📊"), handle_leaderboard))
    application.add_handler(MessageHandler(filters.Text("About 🤔"), handle_help))

    # General Message Handlers

    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO) & ~filters.COMMAND,handle_message))
  

    application.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, handle_place_withdrawal))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdrawal_amount))


    # Task and Picture Handlers
    
    # Run the bot
    application.run_polling()

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.start()
    main()
