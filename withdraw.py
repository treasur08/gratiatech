from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from database import Database

# Minimum withdrawal amount
MIN_WITHDRAWAL_AMOUNT = 6000
WITHDRAWAL_DAY = "Sunday"
ADMIN_ID = 5991907369

db = Database('gratia.db')

keyboard = [
    [
        InlineKeyboardButton("1", callback_data="num_1"), 
        InlineKeyboardButton("2", callback_data="num_2"), 
        InlineKeyboardButton("3", callback_data="num_3")
    ],
    [
        InlineKeyboardButton("4", callback_data="num_4"), 
        InlineKeyboardButton("5", callback_data="num_5"), 
        InlineKeyboardButton("6", callback_data="num_6")
    ],
    [
        InlineKeyboardButton("7", callback_data="num_7"), 
        InlineKeyboardButton("8", callback_data="num_8"), 
        InlineKeyboardButton("9", callback_data="num_9")
    ],
    [
        InlineKeyboardButton("⌫", callback_data="num_backspace"),     
        InlineKeyboardButton("0", callback_data="num_0"), 
        InlineKeyboardButton("✅ Confirm", callback_data="num_confirm_withdrawal")
    ]
]

async def handle_task_withdrawal_request(update, context):
    # Determine if the update is a callback query or a message
    query = update.callback_query
    chat_id = query.message.chat_id if query else update.message.chat_id
    
    # Check if today is Sunday
    current_day = datetime.now().strftime("%A")
    if current_day != WITHDRAWAL_DAY:  
        if query:
            await query.answer()
            await query.edit_message_text(
                "Withdrawals are only allowed on Sundays. Please try again on the next withdrawal day.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
            )
        else:
            await update.message.reply_text(
                "Withdrawals are only allowed on Sundays. Please try again on the next withdrawal day."
            )
        return

    # Get account details
    account_details = db.get_account_details(chat_id)
    if not account_details:
        if query:
            await query.answer()
            await query.edit_message_text(
                "Your account details are missing. Please provide your account details to proceed.",
                reply_markup = ReplyKeyboardMarkup([[KeyboardButton("Add Account")]], resize_keyboard=True)

            )
        else:
            await update.message.reply_text(
                "Your account details are missing. Please provide your account details to proceed.",
                reply_markup = ReplyKeyboardMarkup([[KeyboardButton("Add Account")]], resize_keyboard=True)
            )
        return

    # Get task balance
    balances = db.get_user_balances(chat_id)
    task_balance = balances['task_balance']

    if task_balance < 100:  
        if query:
            await query.answer()
            await query.edit_message_text(
                f"Insufficient balance. Minimum withdrawal amount is 6000 NGN. Your current balance is {task_balance} NGN.",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")]])
            )

        else:
            await update.message.reply_text(
                f"Insufficient balance. Minimum withdrawal amount is 6000 NGN. Your current balance is {task_balance} NGN.",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")]])
            )
        return

    # Ask for withdrawal amount with numeric keyboard
    
    
    context.user_data["withdrawal_amount"] = ""
    if query:
        await query.answer()
        await query.edit_message_text(
            f"💰 *Withdrawal Menu*\n\n"
            f"💳 Available Balance: {task_balance:,} NGN\n\n"
            f"📝 Enter Amount to Withdraw:\n"
            f"Amount: `0.00 NGN`\n\n"
            f"ℹ️ Min. Withdrawal: 6,000 NGN",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"💰 *Withdrawal Menu*\n\n"
            f"💳 Available Balance: {task_balance:,} NGN\n\n"
            f"📝 Enter Amount to Withdraw:\n"
            f"Amount:  `0.00 NGN`\n\n"
            f"ℹ️ Min. Withdrawal: 6,000 NGN",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def handle_numeric_input(update, context, db):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    # Retrieve existing withdrawal amount from user_data
    withdrawal_amount = context.user_data.get("withdrawal_amount", "")
    if "withdrawal_amount" not in context.user_data:
        context.user_data["withdrawal_amount"] = ""

    if data.startswith("num_"):
        action = data[4:]  # Remove 'num_' prefix

        if action.isdigit():
            # Append the digit to the withdrawal amount
            withdrawal_amount += action
        elif action == "backspace":
            # Remove the last character
            withdrawal_amount = withdrawal_amount[:-1]
        elif action == "confirm_withdrawal":
            if not withdrawal_amount:
                await query.answer("Please enter an amount before confirming.")
                return

            withdrawal_amount = int(withdrawal_amount)

            # Validate withdrawal amount
            balances = db.get_user_balances(chat_id)
            task_balance = balances['task_balance']

            if withdrawal_amount < MIN_WITHDRAWAL_AMOUNT:
                await query.answer()
                await query.edit_message_text(
                    f"The minimum withdrawal amount is {MIN_WITHDRAWAL_AMOUNT} NGN. Please enter a valid amount.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            if withdrawal_amount > task_balance:
                await query.answer()
                await query.edit_message_text(
                    f"You cannot withdraw more than your task balance ({task_balance} NGN). Please enter a valid amount.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            # Confirm withdrawal request
            account_details = db.get_account_details(chat_id)
            confirmation_message = (
                f"TASK WITHDRAWAL REQUEST\n"
                f"=======================\n"
                f"BANK DETAILS: {account_details}\n"
                f"WITHDRAWAL AMOUNT: {withdrawal_amount} NGN\n\n"
                f"CLICK THE ✅ BUTTON TO CONFIRM"
            )

            await query.answer()
            await query.edit_message_text(
                confirmation_message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Confirm", callback_data="finalize_withdrawal")]
                ])
            )

            context.user_data["withdrawal_amount"] = withdrawal_amount
            return

    balances = db.get_user_balances(chat_id)
    task_balance = balances['task_balance']
    context.user_data["withdrawal_amount"] = withdrawal_amount
    await query.answer()
    await query.edit_message_text(
        f"💰 *Withdrawal Menu*\n\n"
            f"💳 Available Balance: {task_balance:,} NGN\n\n"
            f"📝 Enter Amount to Withdraw:\n"
            f"Amount: `{withdrawal_amount}` NGN\n\n"
            f"ℹ️ Min. Withdrawal: 6,000 NGN",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
    )

async def finalize_withdrawal(update, context, db):
    query = update.callback_query
    chat_id = query.message.chat_id

    withdrawal_amount = context.user_data.get("withdrawal_amount")
    if not withdrawal_amount:
        await query.answer("No withdrawal amount specified.")
        return

    # Deduct balance and store withdrawal request
    withdrawal_amount = int(withdrawal_amount)
    db.update_task_balance(chat_id, -withdrawal_amount)
    db.store_withdrawal_request(chat_id, withdrawal_amount)

    account_details = db.get_account_details(chat_id)

    # Notify admin
    admin_message = (
        f"🔔 NEW WITHDRAWAL REQUEST\n"
        f"═══════════════════════\n"
        f"👤 User ID: {chat_id}\n"
        f"💰 Amount: {withdrawal_amount:,} NGN\n"
        f"🏦 Bank Details:\n{account_details}\n"
        f"═══════════════════════\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

    # Confirm to user
    await query.answer()
    await query.edit_message_text(
        f"Your withdrawal request for {withdrawal_amount} NGN has been submitted. Please wait for approval.",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Back")]])
    )

    context.user_data.pop("withdrawal_amount", None)
