from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

# Initialize the WebDriver (use the appropriate driver for your browser)
driver = webdriver.Chrome()  # Replace with `webdriver.Firefox()` for Firefox

try:
    # Navigate to the target website
    driver.get("https://pocketoption.com/en/cabinet")  # Replace with the actual URL

    # Wait for the element to load
    driver.implicitly_wait(10)  # Wait up to 10 seconds

    # Find the element by its class
    buy_button = driver.find_element(By.CLASS_NAME, "payouttext-lh")

    # Click the button
    ActionChains(driver).move_to_element(buy_button).click().perform()
    print("Buy button clicked.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the browser
    driver.quit()
