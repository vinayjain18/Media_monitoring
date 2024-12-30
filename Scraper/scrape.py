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
from LLM.gpt import gpt_chat
from Script.preprocess_text import remove_urls_and_whitespace,extract_text_from_pdf
import datetime
from Scraper.database_connection import *
from dotenv import load_dotenv
import logging
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
# from Script.summary import summary_generator

load_dotenv()
# Create a logger instance
logger = logging.getLogger(__name__)


def is_pdf(url):
    response = requests.head(url, timeout=10)
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
                text = extract_text_from_pdf(filepath)
                return text
            else:
                print(f'Uh oh! Could not download {pdf_file_name}, HTTP response status code: {response.status}')
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def setup_chrome_options():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--proxy-server='direct://'")
    options.add_argument("--proxy-bypass-list=*")
    options.add_argument("--start-maximized")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    # Add user agent to avoid detection
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return options

def setup_chrome_service():
    try:
        # For Ubuntu, we need to specify the chrome binary path
        chrome_binary_path = "/usr/bin/chromedriver"
        service = webdriver.ChromeService(chrome_binary_path)
        return service
    except Exception as e:
        logger.error(f"Failed to setup Chrome service: {str(e)}")
        return None


def scrape_yahoo_news(company_name, keyword, page_limit=1):
    links = []
    try:
        # Get the current directory where the script is running
        current_dir = os.path.dirname(os.path.realpath(__file__))
        # Define the path to ChromeDriver in the current directory
        # driver_path = os.path.join(current_dir, 'chromedriver.exe')
        # print(driver_path)
        options = setup_chrome_options()
        service = setup_chrome_service()
        driver = webdriver.Chrome(options=options, service=service)
        driver.get("https://search.yahoo.com/")
        # driver.get("https://www.google.com/")
        search_input = driver.find_element(By.XPATH, '//*[@id="yschsp"]')
        # search_input = driver.find_element(By.XPATH, '//*[@id="APjFqb"]')
        search_input.send_keys(company_name + " " + keyword + " news")
        search_input.send_keys(Keys.RETURN)
        # driver.implicitly_wait(15)
        # Wait for the search results to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'algo-sr'))
            # WebDriverWait(driver, 15).until(
            #     EC.presence_of_element_located((By.CLASS_NAME, 'yuRUbf'))
            )
        except TimeoutException:
            print("Search results did not load in time.")
            return links
        # page_count = 0
        # while page_count < page_limit:
        #     page_count += 1
        #     page_source = driver.page_source
        #     soup = BeautifulSoup(page_source, 'html.parser')
        #     search_results = soup.find_all('div', class_='algo-sr')
        #     if not search_results:
        #         print("No search results found. Exiting.")
        #         break
        #     for result in search_results:
        #         link = result.find('a').get('href')
        #         links.append(link)            
        #     try:
        #         next_button = driver.find_element(By.XPATH, '//a[@class="next"]')
        #         next_button.click()
        #         driver.implicitly_wait(5)
        #     except Exception as e:
        #         print(f"Error occurred while clicking next button: {str(e)}")
        #         continue

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        search_results = soup.find_all('div', class_='algo-sr')
        print(search_results)
        if not search_results:
            print("No search results found. Exiting.")
        for result in search_results:
            link = result.find('a').get('href')
            links.append(link)            
        return links
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return links


def fetch_page_source_with_httpx(link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    try:
        with httpx.Client(headers=headers, timeout=10.0) as client:
            response = client.get(link)
            response.raise_for_status()  # Raise an error for bad responses
            logger.info(f"Successfully fetched page source for {link}")
            return response.text
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred for {link}: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"An error occurred for {link}: {str(e)}")
    return None


def scrape_links(df,company_id,search_query):
    try:
        l = []
        if len(df)==0:
            print("DataFrame is empty.")
            return False
        if(len(df)>=10):
            df = df[:9]
        for link in df:
            print("Link:", link)
            try:
                if is_pdf_or_website(link):
                    pass
                else:
                    options = Options()
                    options.add_argument("window-size=1920,1080")
                    options = setup_chrome_options()
                    service = setup_chrome_service()
                    driver = webdriver.Chrome(options=options, service=service)
                    driver.set_window_size(1920, 1080)
                    print("Driver loaded")
                    driver.get(link)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                    page_source = driver.page_source
                    
                    # retry_count = 3
                    # while retry_count > 0:
                    #     try:
                    #         driver.get(link)
                    #         WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                    #         page_source = driver.page_source
                    #         break
                    #     except TimeoutException:
                    #         print("Timeout occurred, retrying...")
                    #         retry_count -= 1
                    #         time.sleep(5)  # Adjust the sleep duration as needed
                    # else:
                    #     print("Max retries reached, skipping link:", link)
                    #     driver.quit()
                    #     continue
                    # page_source = fetch_page_source_with_httpx(link)
                    if page_source:               
                        soup = BeautifulSoup(page_source, 'html.parser')
                        text = soup.text
                        text = remove_urls_and_whitespace(text)
                        # text = summary_generator(text)
                        output = gpt_chat(text)
                        data = json.loads(output)
                        print(data)
                        if(data.get('categories','') != ''):
                            l.append({
                            'company_id':company_id,
                            'data_provider':'News',
                            'Sentiment':data.get('sentiment',''),
                            'Summary':data.get('summary',''),
                            'Category':json.dumps(data.get('categories','')),
                            'Incident':json.dumps(data.get('incidents','')),
                            'Published_dt':data.get('date',''),
                            'link':link,
                            'Keywords_phrases':search_query,
                            'Themes':json.dumps(data.get('themes','')),
                            'country':data.get('country',''),
                            'proc_ts':datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    driver.quit()
                print("Sleep 1 Sec..")
                time.sleep(1)
            except Exception as inner_e:
                print(f"An error occurred for link {link}: {str(inner_e)}")
                continue    
        if l:
            # df = pd.DataFrame(l)
            # df.to_csv('Updated.csv')
            db_connection = connect()
            print("*"*15)
            print("Saving Record ...")
            cursor = db_connection.cursor()

            for record in l:
                # Check if the country exists
                country_name = record['country']
                cursor.execute("SELECT id FROM d_countries WHERE LOWER(country) = %s", (country_name,))
                country_id = cursor.fetchone()

                if not country_id:
                    # Insert the country if it doesn't exist
                    formatted_country_name = country_name.title()  # Capitalize each word
                    cursor.execute("INSERT INTO d_countries (country) VALUES (%s)", (formatted_country_name,))
                    db_connection.commit()
                    country_id = cursor.lastrowid
                else:
                    country_id = country_id[0]

                insert_query = """
                INSERT INTO greenfi_datamart.d_media_monitor_details(company_id, data_provider, Sentiment, Summary, Category, Incident, Published_dt, link, Keywords_phrases, Themes, country, proc_ts)
                VALUES (%(company_id)s, %(data_provider)s, %(Sentiment)s, %(Summary)s, %(Category)s, %(Incident)s, %(Published_dt)s, %(link)s, %(Keywords_phrases)s, %(Themes)s, %(country)s, %(proc_ts)s)
                """
                cursor.execute(insert_query, record)
                db_connection.commit()

                # Fetch the last inserted ID for this record
                last_id = cursor.lastrowid

                # Insert into d_incidents_themes
                categories = json.loads(record['Category'])
                category = categories.strip('"').strip("'")  # Remove double quotes
                category_id = {'Environmental': 1, 'Social': 2, 'Governance': 3}.get(category, None)
                if category_id:
                    incident_theme_insert_query = """
                    INSERT INTO d_incidents_themes (incident_id, theme_id)
                    VALUES (%s, %s)
                    """
                    cursor.execute(incident_theme_insert_query, (last_id, category_id))

                # Insert into d_incidents_countries
                incident_country_insert_query = """
                INSERT INTO d_incidents_countries (incident_id, country_id)
                VALUES (%s, %s)
                """
                cursor.execute(incident_country_insert_query, (last_id, country_id))

            db_connection.commit()
            cursor.close()
            disconnect(db_connection)
            return True
        else:
            print("No data to write to file.")
            return False
    
    except Exception as outer_e:
        print(f"An error occurred: {str(outer_e)}")
        db_connection = connect()
        print("*"*15)
        print("Saving Record ...")
        cursor = db_connection.cursor()

        for record in l:
            # Check if the country exists
            country_name = record['country']
            cursor.execute("SELECT id FROM d_countries WHERE LOWER(country) = %s", (country_name,))
            country_id = cursor.fetchone()

            if not country_id:
                # Insert the country if it doesn't exist
                formatted_country_name = country_name.title()  # Capitalize each word
                cursor.execute("INSERT INTO d_countries (country) VALUES (%s)", (formatted_country_name,))
                db_connection.commit()
                country_id = cursor.lastrowid
            else:
                country_id = country_id[0]

            insert_query = """
            INSERT INTO greenfi_datamart.d_media_monitor_details(company_id, data_provider, Sentiment, Summary, Category, Incident, Published_dt, link, Keywords_phrases, Themes, country, proc_ts)
            VALUES (%(company_id)s, %(data_provider)s, %(Sentiment)s, %(Summary)s, %(Category)s, %(Incident)s, %(Published_dt)s, %(link)s, %(Keywords_phrases)s, %(Themes)s, %(country)s, %(proc_ts)s)
            """
            cursor.execute(insert_query, record)
            db_connection.commit()

            # Fetch the last inserted ID for this record
            last_id = cursor.lastrowid

            # Insert into d_incidents_themes
            categories = json.loads(record['Category'])
            print("Categories:", categories)
            for category in categories:
                category = category.strip('"')  # Remove double quotes
                category_id = {'Environmental': 1, 'Social': 2, 'Governance': 3}.get(category, None)
                if category_id:
                    incident_theme_insert_query = """
                    INSERT INTO d_incidents_themes (incident_id, theme_id)
                    VALUES (%s, %s)
                    """
                    cursor.execute(incident_theme_insert_query, (last_id, category_id))

            # Insert into d_incidents_countries
            incident_country_insert_query = """
            INSERT INTO d_incidents_countries (incident_id, country_id)
            VALUES (%s, %s)
            """
            cursor.execute(incident_country_insert_query, (last_id, country_id))

        db_connection.commit()
        cursor.close()
        disconnect(db_connection)
        return True


NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def fetch_news_api(company_name, keyword, page_limit=3):
    try:
        url = f'https://newsapi.org/v2/everything?q={keyword} {company_name}&apiKey={NEWS_API_KEY}&pageSize=100'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'ok' and data['totalResults'] > 0:
                articles = data['articles']
                news_list = [
                    {
                        'source': article['source']['name'],
                        'author': article.get('author', ''),
                        'title': article['title'],
                        'description': article['description'],
                        'url': article['url'],
                        'publishedAt': article['publishedAt']
                    } 
                    for article in articles
                ]
                df = pd.DataFrame(news_list)
                return df
            else:
                print("No news articles found.")
                return pd.DataFrame()
        else:
            print(f"Failed to fetch news. Status code: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return pd.DataFrame()

def process_news_links(df, company_id, search_query):
    try:
        l = []
        if df.empty:
            print("DataFrame is empty.")
            return False

        for index, row in df.iterrows():
            link = row['url']
            print(f"Processing Link: {link}")

            # Assuming 'title' and 'description' are extracted from the API
            title = row['title']
            description = row['description']
            text = f"{title}\n{description}"

            try:
                output = gpt_chat(text)
                data = json.loads(output)
                print(data)

                if data.get('categories', ''):
                    l.append({
                        'company_id': company_id,
                        'data_provider': 'NewsAPI',
                        'Sentiment': data.get('sentiment', ''),
                        'Summary': data.get('summary', ''),
                        'Category': json.dumps(data.get('categories', '')),
                        'Incident': json.dumps(data.get('incidents', '')),
                        'Published_dt': row['publishedAt'],
                        'link': link,
                        'Keywords_phrases': search_query,
                        'Themes': json.dumps(data.get('themes', '')),
                        'country': data.get('country', ''),
                        'proc_ts': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
            except Exception as inner_e:
                print(f"Error processing link {link}: {str(inner_e)}")
                continue
        
        print(l)
        if l:
            df = pd.DataFrame(l)
            df.to_csv('Updated.csv')
            db_connection = connect()
            print("*" * 15)
            print("Saving Record ...")
            cursor = db_connection.cursor()
            insert_query = """
            INSERT INTO greenfi_datamart.d_media_monitor_details(
                company_id, data_provider, Sentiment, Summary, Category, Incident, Published_dt,
                link, Keywords_phrases, Themes, country, proc_ts
            ) VALUES (
                %(company_id)s, %(data_provider)s, %(Sentiment)s, %(Summary)s, %(Category)s,
                %(Incident)s, %(Published_dt)s, %(link)s, %(Keywords_phrases)s, %(Themes)s,
                %(country)s, %(proc_ts)s
            )
            """
            cursor.executemany(insert_query, l)
            db_connection.commit()
            cursor.close()
            disconnect(db_connection)
            return True
        else:
            print("No data to write to file.")
            return False

    except Exception as outer_e:
        print(f"An error occurred: {str(outer_e)}")
        return False
