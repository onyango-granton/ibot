from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Path to your Chrome user data directory
chrome_profile_path = r"C:\\Users\\rich\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1"


# Configure Chrome options
options = webdriver.ChromeOptions()
options.add_argument(f"user-data-dir={chrome_profile_path}")

# Initialize the WebDriver with your profile
driver = webdriver.Chrome(options=options)

try:
    # Navigate to the website
    driver.get("https://pocketoption.com/en/cabinet")  # Replace with the URL after login

    # Wait for the "Buy" button to load
    buy_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "payouttext-lh"))
    )

    # Click the "Buy" button
    buy_button.click()
    print("Buy button clicked.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the browser
    driver.quit()
