import requests
from selenium import webdriver
import json
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib import request
import os


def scrape_table():
    url = "https://planet-tracker.org/reports/"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table')    
        print(tables)
        for table in tables:
            data = []
            rows = table.find_all('tr')
            for row in rows[1:]:
                row_data = []
                link = []
                cells = row.find_all('td')
                for cell in cells:
                    if cell.find('a'): 
                        link_text = cell.find('a').get('href').strip() 
                        print(link_text)
                        link.append(link_text)
                    else:
                        row_data.append(cell.get_text(strip=True))
                print(row_data)
                new_obj = {
                    'Event Date':row_data[0],
                    'Link_text':link[0],
                    'Location':row_data[1],
                    'Themes':row_data[2],
                    'Sectors':row_data[3],
                    'Regulator Name':row_data[4]
                }
                data.append(new_obj)
            df = pd.DataFrame(data)
            df.reset_index(inplace=True)
            df.to_csv('./Scrape.csv', index=False)
    else:
        print("Failed to fetch webpage. Status code:", response.status_code)


def scrape_content_using_request(url):
    response = requests.get(url)
    if(response.status_code == 200):
        soup = BeautifulSoup(response.text,'html.parser')
        content = soup.find_all('p')
        print(content)
    else:
        print("Failed to fetch webpage. Status code:", response.status_code)

def scrape_content_selenium(url):
    driver = webdriver.Chrome()
    driver.get(url)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    headline_element = soup.find('h1')
    content_elements = soup.find_all('p')
    headline = headline_element.text.strip() if headline_element else None
    content = '\n'.join([content_element.text.strip() for content_element in content_elements])
    driver.quit()
    return headline, content

def scrape_content_selenium(url):
    driver = webdriver.Chrome()
    driver.get(url)
    all_headlines = []
    all_content = []
    def scrape_page_content(driver):
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        headline_elements = soup.find_all('h1')  # You may need to adjust this based on the actual HTML structure
        headlines = [headline.text.strip() for headline in headline_elements]
        content_elements = soup.find_all('p')  # You may need to adjust this based on the actual HTML structure
        contents = ['\n'.join(content_element.stripped_strings) for content_element in content_elements]
        all_headlines.extend(headlines)
        all_content.extend(contents)
        links = driver.find_elements_by_tag_name('a')
        for link in links:
            link.click()
            driver.implicitly_wait(10)  # Adjust the timeout as needed
            scrape_page_content(driver)
    scrape_page_content(driver)
    driver.quit()
    return all_headlines, all_content

def is_pdf(url):
    response = requests.head(url)
    content_type = response.headers.get('Content-Type', '')
    return 'pdf' in content_type.lower()

def is_pdf_or_website(link):
    if link.lower().endswith('.pdf'):
        return True
    return is_pdf(link)

def download_pdf(url: str,pdf_file_name:str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        req = request.Request(url, headers=headers)
        with request.urlopen(req) as response:
            if response.status == 200:
                current_path=f'{os.getcwd()}/PDF/'
                filepath = os.path.join(current_path, pdf_file_name)
                with open(filepath, 'wb') as pdf_object:
                    pdf_object.write(response.read())
                print(f'{pdf_file_name} was successfully saved!')
                return filepath
            else:
                print(f'Uh oh! Could not download {pdf_file_name}, HTTP response status code: {response.status}')
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
def scrape_yahoo_news(company_name, keyword, page_limit=3):
    try:
        driver = webdriver.Chrome()
        driver.get("https://search.yahoo.com/")
        search_input = driver.find_element(By.XPATH, '//*[@id="yschsp"]')
        search_input.send_keys(company_name + " " + keyword)
        search_input.send_keys(Keys.RETURN)
        driver.implicitly_wait(5)
        links = []
        page_count = 0
        while page_count < page_limit:
            page_count += 1
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            search_results = soup.find_all('div', class_='algo-sr')
            if not search_results:
                print("No search results found. Exiting.")
                break
            for result in search_results:
                link = result.find('a').get('href')
                headline = result.find('a').text if result.find('a').text else None
                news_art = {
                    "link": link,
                    "headline": headline
                }
                links.append(news_art)            
            try:
                next_button = driver.find_element(By.XPATH, '//a[@class="next"]')
                next_button.click()
                driver.implicitly_wait(5)
            except Exception as e:
                print(f"Error occurred while clicking next button: {str(e)}")
                break
        df = pd.DataFrame(links)
        df.to_csv(f"{company_name}.csv", index=False)
        return df
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        df = pd.DataFrame(links)
        df.to_csv(f"{company_name}.csv", index=False)


def scrape_links(df):
    try:
        for index, row in df.iterrows():
            link = row['link']
            print(link)
            file_name = str(index)
            print("File Name : ", file_name)
            if is_pdf_or_website(link):
                options = Options()
                mobile_emulation = {
                    "deviceMetrics": {"width": 360, "height": 640, "pixelRatio": 3.0},
                    "userAgent": "Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Mobile Safari/537.36"
                }
                options.add_experimental_option("mobileEmulation", mobile_emulation)
                driver = webdriver.Chrome(options=options)
                driver.get(link)
                pdf_name = f'{file_name}.pdf'
                pdf_source = download_pdf(link, pdf_name)
                df.loc[index, 'source'] = 'pdf'
                df.loc[index, 'source_path'] = pdf_source
            else:
                options = Options()
                options.add_argument("window-size=1920,1080")
                driver = webdriver.Chrome(options=options)
                driver.set_window_size(1920, 1080)
                retry_count = 3
                while retry_count > 0:
                    try:
                        driver.get(link)
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                        page_source = driver.page_source
                        break
                    except TimeoutException:
                        print("Timeout occurred, retrying...")
                        retry_count -= 1
                        time.sleep(10)  # Adjust the sleep duration as needed
                else:
                    print("Max retries reached, skipping link:", link)
                    driver.quit()
                    continue
                
                soup = BeautifulSoup(page_source, 'html.parser')
                text = soup.text
                print(text)
                name = soup.title.string.strip()
                keywords = ' '.join(name.split())
                df.loc[index, 'source'] = 'Web Content'
                df.loc[index, 'Content'] = text
                df.loc[index, 'Keyword'] = keywords
            driver.quit()
            time.sleep(20)  # Add a delay between iterations
        return df
    except Exception as e:
        print(f"An error occurred: {str(e)}")

dataframe = scrape_yahoo_news("Wilmar International News","Child Labor")

print("*"*15)
print("News Scrapping Complete")
print("*"*15)

dataframe = scrape_links(dataframe)

dataframe.to_csv("Updated.csv")




