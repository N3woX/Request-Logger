import psutil
from selenium import webdriver
from undetected_chromedriver import Chrome
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time

def get_chrome_pids():
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'chrome.exe':
            pids.append(proc.info['pid'])
    return pids

def initialize_driver():
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')

    existing_chrome_pids = get_chrome_pids()
    
    driver = Chrome(options=options, desired_capabilities=caps)
    
    time.sleep(1)

    try:
        browser_pid = driver.service.process.pid
    except Exception as e:
        print(f"Error retrieving the PID: {e}")
        driver.quit()
        return None, None, existing_chrome_pids

    return driver, browser_pid, existing_chrome_pids
