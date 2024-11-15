# utils/gii_utils.py
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def setup_gii_driver():
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        return driver

def scrape_gii_reports():
    url = "https://www.giiresearch.com/publisher/sky/"
    driver = setup_gii_driver()
    driver.get(url)
    
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "reports-list")))
    all_data = []
    previous_page_number = None

    while True:
        try:
            page_data = extract_reports_from_page(driver.page_source)
            all_data.extend(page_data)
            current_page_number = get_current_page_number(driver)
            if current_page_number == previous_page_number:
                break
            previous_page_number = current_page_number
            if not click_next_page(driver):
                break
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "reports-list")))
        except Exception as e:
            print(f"Error during page navigation: {e}")
            break

    driver.quit()
    
    df = pd.DataFrame(all_data).drop_duplicates()
    df.to_excel("scraped_reports.xlsx", index=False)
    print("Selenium scraping complete data to 'scraped_reports.xlsx'.")
    return len(all_data)
    

def extract_reports_from_page(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    reports = soup.find_all("div", class_="one-list-item")
    page_data = []

    for report in reports:
        title = report.find("div", class_="one-list-top").find("a").get_text(strip=True)
        link = report.find("div", class_="one-list-top").find("a")["href"]
        price = report.find("span", class_="price_usd").get_text(strip=True)
        published_date, pages, publisher = None, None, None

        stats = report.find_all("div", class_="one-list-bottom-stat")
        for stat in stats:
            label = stat.find("b").get_text(strip=True)
            value = stat.get_text(strip=True).replace(label, "").strip()
            if label == "PUBLISHED:":
                published_date = value
            elif label == "PAGES:":
                pages = value
            elif label == "PUBLISHER:":
                publisher = value

        page_data.append({
            "Title": title,
            "Link": link,
            "Price": price,
            "Published Date": published_date,
            "Pages": pages,
            "Publisher": publisher,
            "Product Code": None,  
        })
    return page_data

def get_current_page_number(driver):
    return driver.find_element(By.XPATH, "//*[@id='the-pagination']/a[@class='pagination current-page']").text

def click_next_page(driver):
    try:
        pagination_elements = driver.find_elements(By.XPATH, "//*[@id='the-pagination']/a")
        next_button_xpath = f"//*[@id='the-pagination']/a[{len(pagination_elements)}]"
        next_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, next_button_xpath)))
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(1)
        print("Next page clicked")
        return True
    except Exception as e:
        print(f"Error clicking 'Next' button: {e}")
        return False
