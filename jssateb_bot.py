import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
import requests
from bs4 import BeautifulSoup

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
USER_TYPE, USERNAME, PASSWORD = range(3)

# Replace with your actual bot token
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
    await update.message.reply_text(f'You selected: {user_type}. Now, please enter your username:', reply_markup=ReplyKeyboardRemove())
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('Now, please enter your password:')
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['username']
    password = update.message.text
    user_type = context.user_data['user_type']
    
    # Delete the message containing the password for security
    await update.message.delete()
    
    attendance = fetch_attendance(user_type, username, password)
    await update.message.reply_text(f'Your attendance:\n{attendance}')
    return ConversationHandler.END

def fetch_attendance(user_type, username, password):
    login_url = 'https://jssateb.azurewebsites.net/Apps/Login.aspx'
    attendance_url = 'https://jssateb.azurewebsites.net/Apps/TimeTable/StudentAttendance.aspx'
    
    session = requests.Session()
    
    # Fetch the login page to get CSRF token and other hidden fields
    login_page = session.get(login_url)
    login_soup = BeautifulSoup(login_page.content, 'html.parser')
    
    # Extract hidden fields
    hidden_inputs = login_soup.find_all("input", type="hidden")
    form_data = {input.get('name'): input.get('value', '') for input in hidden_inputs}
    
    # Add user-provided data
    form_data.update({
        'ctl00$ContentPlaceHolder1$ddlLoginAs': user_type,
        'ctl00$ContentPlaceHolder1$txtUserName': username,
        'ctl00$ContentPlaceHolder1$txtPassword': password,
        'ctl00$ContentPlaceHolder1$btnLogin': 'Login'
    })
    
    # Perform login
    response = session.post(login_url, data=form_data)
    
    if response.ok:
        # Check if login was successful (you may need to adjust this based on your website's behavior)
        if "Login failed" in response.text:
            return "Login failed. Please check your credentials."
        
        # Fetch attendance page
        attendance_page = session.get(attendance_url)
        soup = BeautifulSoup(attendance_page.content, 'html.parser')
        
        # Extract attendance information
        # You'll need to adjust this based on the actual structure of your attendance page
        attendance_table = soup.find('table', id='ctl00_ContentPlaceHolder1_gvAttendance')
        if attendance_table:
            # Extract and format attendance data
            rows = attendance_table.find_all('tr')
            attendance_data = []
            for row in rows[1:]:  # Skip header row
                cols = row.find_all('td')
                if cols:
                    subject = cols[0].text.strip()
                    total = cols[1].text.strip()
                    present = cols[2].text.strip()
                    percentage = cols[3].text.strip()
                    attendance_data.append(f"{subject}: {present}/{total} ({percentage})")
            return "\n".join(attendance_data)
        else:
            return "Attendance information not found. Please check if you're logged in correctly."
    else:
        return "Failed to connect to the website. Please try again later."

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