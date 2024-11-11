from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_login_and_get_attendance(user_type, username, password):
    login_url = 'https://jssateb.azurewebsites.net/Apps/Login.aspx'
    attendance_url = 'https://jssateb.azurewebsites.net/Apps/TimeTable/StudentAttendance.aspx?WAT=230'

    logger.info("Setting up Chrome options")
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')
    options.page_load_strategy = 'eager'

    logger.info("Initializing Chrome driver")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        logger.info("Navigating to login page")
        driver.get(login_url)

        logger.info("Selecting user type and logging in")
        user_type_dict = {"Student": "optLoginAsStudent", "Parent": "optLoginAsParents", "Staff": "optLoginAsStaff"}
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, user_type_dict[user_type]))).click()
        driver.find_element(By.ID, "txtUserID").send_keys(username)
        driver.find_element(By.ID, "txtPassword").send_keys(password)
        driver.find_element(By.ID, "myBtn").click()

        logger.info("Waiting for page to change after login...")
        WebDriverWait(driver, 10).until(EC.url_changes(login_url))

        if driver.current_url != login_url:
            logger.info("Login successful, navigating to attendance page")
            driver.get(attendance_url)

            logger.info("Extracting student name")
            student_name = WebDriverWait(driver, 10).until(lambda d: d.execute_script("""
                var nameElement = document.querySelector('.username');
                if (nameElement) {
                    return nameElement.childNodes[0].textContent.trim();
                }
                return '';
            """))

            logger.info("Clicking Summary button")
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Summary')]"))).click()

            logger.info("Extracting attendance data")
            attendance_data = WebDriverWait(driver, 10).until(lambda d: d.execute_script("""
                var rows = document.querySelectorAll("#divSSTB2TBody tr");
                var data = [];
                for (var i = 0; i < rows.length; i++) {
                    var cells = rows[i].querySelectorAll("td");
                    if (cells.length >= 10) {
                        data.push({
                            subject_name: cells[3].textContent.trim(),
                            attendance_percentage: cells[9].textContent.trim()
                        });
                    }
                }
                return data;
            """))

            if not attendance_data:
                logger.warning("No attendance data found")
                return f"Hey {student_name}, no attendance data available. Please check your account or try again later."

            logger.info("Attendance data extracted successfully")

            formatted_data = []
            total_percentage = 0
            subject_count = 0

            for item in attendance_data:
                formatted_item = f"{item['subject_name']}: {item['attendance_percentage']}"
                formatted_data.append(formatted_item)
                percentage = int(item['attendance_percentage'].rstrip('%'))
                total_percentage += percentage
                subject_count += 1

            overall_percentage = total_percentage / subject_count if subject_count > 0 else 0

            result = f"Hey {student_name}!\n\nYour Attendance Summary 👇\n\n" + "\n".join(formatted_data)
            result += f"\n\nOverall Attendance: {overall_percentage:.2f}%"

            logger.info(f"Overall Attendance for {student_name}: {overall_percentage:.2f}%")
            return result
        else:
            logger.warning("Login failed")
            return "Try again later, if the issue persists contact just4jssateb@gmail.com"

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return "Try again later, if the issue persists contact just4jssateb@gmail.com"

    finally:
        logger.info("Closing Chrome driver")
        driver.quit()