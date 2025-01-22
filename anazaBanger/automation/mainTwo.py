from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Replace these with your credentials
USERNAME = "grantononyango@gmail.com"
PASSWORD = "0724600680@Gt"

# Initialize the WebDriver (use the appropriate driver for your browser)
driver = webdriver.Chrome()  # Replace with `webdriver.Firefox()` for Firefox

try:
    # Navigate to the target website
    driver.get("https://pocketoption.com/en/cabinet")  # Replace with the actual login URL

    # Wait for the login page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "email"))  # Adjust the locator if needed
    )

    # Enter the username
    username_field = driver.find_element(By.NAME, "email")  # Adjust the locator if needed
    username_field.send_keys(USERNAME)

    # Enter the password
    password_field = driver.find_element(By.NAME, "password")  # Adjust the locator if needed
    password_field.send_keys(PASSWORD)

    # Wait for the Sign In button to appear
    sign_in_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "btn-green-light"))  # Using class name
    )

    # Click the Sign In button
    sign_in_button.click()
    print("Sign In button clicked.")

    # Wait for the post-login page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "payouttext-lh"))
    )

    # Click the "Buy" button
    buy_button = driver.find_element(By.CLASS_NAME, "payouttext-lh")
    ActionChains(driver).move_to_element(buy_button).click().perform()
    print("Buy button clicked.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the browser
    driver.quit()
