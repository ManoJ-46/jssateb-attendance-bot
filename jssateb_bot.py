import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from jss_login_selenium import check_login_and_get_attendance

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
USER_TYPE, USERNAME, PASSWORD = range(3)

# Updated token (replace with your bot token)
TOKEN = '7391510808:AAHOPfdVOMg5d799Pi7Ig50VcSw5K5sRX1k'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [['Student', 'Parent', 'Staff']]
    await update.message.reply_text(
        'Welcome! Please select your user type:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return USER_TYPE

async def get_user_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_type = update.message.text
    context.user_data['user_type'] = user_type
    await update.message.reply_text(f'You selected: {user_type}. Now please enter your User ID:', reply_markup=ReplyKeyboardRemove())
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Now please enter your password:')
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['username']
    password = update.message.text
    user_type = context.user_data['user_type']

    # Delete the message containing the password for security reasons.
    await update.message.delete()
    await update.message.reply_text('Checking login and fetching attendance... Please wait.')

    try:
        logger.info(f"Attempting to fetch attendance for user: {username}")
        login_result = check_login_and_get_attendance(user_type, username, password)
        if len(login_result) > 4096:
            for x in range(0, len(login_result), 4096):
                await update.message.reply_text(login_result[x:x+4096])
        else:
            await update.message.reply_text(login_result)
        logger.info(f"Attendance fetched successfully for user: {username}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        await update.message.reply_text(f"An unexpected error occurred. Please try again later.")

    # Always return to the start state after one attempt.
    await update.message.reply_text('Session ended. Type /start to begin again.')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USER_TYPE: [MessageHandler(filters.Regex('^(Student|Parent|Staff)$'), get_user_type)],
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()