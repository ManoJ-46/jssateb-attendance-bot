from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_operation(func, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return func()
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException) as e:
            if attempt == max_attempts - 1:
                raise e
            time.sleep(2)  # Wait for 2 seconds before retrying

def check_login_and_get_attendance(user_type, username, password):
    login_url = 'https://jssateb.azurewebsites.net/Apps/Login.aspx'
    attendance_url = 'https://jssateb.azurewebsites.net/Apps/TimeTable/StudentAttendance.aspx?WAT=230'

    logger.info("Setting up Chrome options")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    logger.info("Initializing Chrome driver")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)

    try:
        logger.info("Navigating to login page")
        driver.get(login_url)

        logger.info("Selecting user type")
        user_type_dict = {"Student": "optLoginAsStudent", "Parent": "optLoginAsParents", "Staff": "optLoginAsStaff"}
        radio = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, user_type_dict[user_type])))
        driver.execute_script("arguments[0].click();", radio)

        logger.info("Entering username and password")
        username_field = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "txtUserID")))
        username_field.send_keys(username)
        password_field = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "txtPassword")))
        password_field.send_keys(password)

        logger.info("Attempting to log in...")
        login_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "myBtn")))
        driver.execute_script("arguments[0].click();", login_button)

        logger.info("Waiting for page to change after login...")
        WebDriverWait(driver, 30).until(EC.url_changes(login_url))

        logger.info("Checking if login was successful")
        if driver.current_url != login_url:
            logger.info("Login successful, navigating to attendance page")
            driver.get(attendance_url)

            logger.info("Waiting for Summary button")
            summary_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Summary')]"))
            )
            
            logger.info("Clicking Summary button")
            driver.execute_script("arguments[0].click();", summary_button)

            logger.info("Waiting for attendance table to be visible")
            table = WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.ID, "gvAttendanceSummary"))
            )

            logger.info("Extracting attendance data")
            attendance_rows = table.find_elements(By.TAG_NAME, "tr")
            
            if len(attendance_rows) <= 1:
                logger.warning("No attendance data found")
                return "No attendance data available. Please check your account or try again later."

            attendance_data = []
            for row in attendance_rows[1:]:  # Skip header row
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 8:  # Ensure we have enough columns
                    subject_code = columns[0].text
                    subject_name = columns[1].text
                    classes_scheduled = columns[2].text
                    classes_attended = columns[5].text
                    attendance_percentage = columns[7].text
                    attendance_data.append(f"{subject_code} - {subject_name}:\nScheduled: {classes_scheduled}\nAttended: {classes_attended}\nPercentage: {attendance_percentage}")

            logger.info("Attendance data extracted successfully")
            return "Login successful!\n\nAttendance Summary:\n\n" + "\n\n".join(attendance_data)
        else:
            logger.warning("Login failed")
            return "Login failed. Please check your credentials."

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return f"An error occurred while fetching attendance data: {str(e)}"
    finally:
        logger.info("Closing Chrome driver")
        driver.quit()