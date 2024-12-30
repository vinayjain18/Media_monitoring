from flask import Flask, request, jsonify
from Scraper.scrape import scrape_yahoo_news, scrape_links,fetch_news_api,process_news_links
from Scraper.database_connection import *
import csv
from io import StringIO
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

file_path = "news_search_keywords.json"
with open(file_path, "r") as json_file:
    keywords = json.load(json_file)

file_path_auto = "automotive_keywords.json"
with open(file_path_auto, "r") as json_file:
    automotive_keywords = json.load(json_file)

file_path_retail = "retail_keywords.json"
with open(file_path_retail, "r") as json_file:
    retail_keywords = json.load(json_file)

file_path_consumer = "consumer_keywords.json"
with open(file_path_consumer, "r") as json_file:
    consumer_keywords = json.load(json_file)

file_path_healthcare = "healthcare_keywords.json"
with open(file_path_healthcare, "r") as json_file:
    healthcare_keywords = json.load(json_file)

file_path_hospitality = "hospitality_keywords.json"
with open(file_path_hospitality, "r") as json_file:
    hospitality_keywords = json.load(json_file)

file_path_real_estate = "real_estate_keywords.json"
with open(file_path_real_estate, "r") as json_file:
    real_estate_keywords = json.load(json_file)

file_path_telecom = "telecom_keywords.json"
with open(file_path_telecom, "r") as json_file:
    telecom_keywords = json.load(json_file)

file_path_transport = "transport_keywords.json"
with open(file_path_transport, "r") as json_file:
    transport_keywords = json.load(json_file)

file_path_metals = "metals_keywords.json"
with open(file_path_metals, "r") as json_file:
    metals_keywords = json.load(json_file)

def check_company_id_exists(company_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM d_company_details WHERE company_id = %s", (company_id,))
    result = cursor.fetchone()
    cursor.close()
    disconnect(conn)
    return result is not None

def scrape_with_retries(company_name, search_query, retries=2, delay=5):
    """Helper function to retry scraping multiple times."""
    for attempt in range(retries):
        news_link_list = scrape_yahoo_news(company_name, search_query)
        if len(news_link_list)!=0:
            return news_link_list  # Successful scrape
        elif attempt < retries - 1:
            print("Sleeping for 5 Sec")  # Avoid sleeping after the last attempt
            time.sleep(delay)
    return news_link_list  # Failed after all retries


@app.route('/scrape_single_company', methods=['POST'])
def scrape_company():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        company_name = data.get('company_name')
        search_query = data.get('search_query')
        company_id = data.get('company_id')  # Get company_id from JSON instead of query params

        if not company_name or not search_query or not company_id:
            return jsonify({'error': 'company_name, search_query, and company_id are required'}), 400

        if not check_company_id_exists(company_id):
            return jsonify({'error': 'Company ID not found'}), 404

        news_link_list = scrape_with_retries(company_name, search_query)
        if len(news_link_list)!=0:
            status = scrape_links(news_link_list[:20], company_id, search_query)
            if status:
                return jsonify({'message': 'Company data added successfully'}), 201
            else:
                return jsonify({'error': 'Error occurred during data scraping'}), 500
        else:
            return jsonify({'message': 'No Source found'}), 204

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/scrape_bulk_company', methods=['POST'])
def scrape_bulk_company():
    try:
        companies = []
        # Check if it's a CSV upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                csv_file = file.read().decode('utf-8')
                csv_data = csv.DictReader(StringIO(csv_file))

                for row in csv_data:
                    company_name = row.get('company_name')
                    search_query = row.get('search_query')
                    company_id = row.get('company_id')

                    if not company_name or not search_query or not company_id:
                        return jsonify({'error': 'CSV must contain company_name, search_query, and company_id'}), 400

                    if not check_company_id_exists(company_id):
                        return jsonify({'error': f'Company ID {company_id} not found'}), 404

                    news_link_list = scrape_with_retries(company_name, search_query)
                    if news_link_list is not None and len(news_link_list)!=0:
                        status = scrape_links(news_link_list, company_id, search_query)
                        companies.append({'company_name': company_name, 'status': 'Data added successfully' if status else 'Error occurred'})
                    else:
                        companies.append({'company_name': company_name, 'status': 'No Source found'})

                return jsonify({'message': 'CSV processed', 'results': companies}), 201

        # Handle JSON array
        data = request.get_json()
        if isinstance(data, list):
            for company_data in data:
                company_name = company_data.get('company_name')
                search_query = company_data.get('search_query')
                company_id = company_data.get('company_id')

                if not company_name or not search_query or not company_id:
                    companies.append({'company_name': company_name, 'status': 'company_name, search_query, and company_id are required'})
                    continue

                if not check_company_id_exists(company_id):
                    companies.append({'company_name': company_name, 'status': f'Company ID {company_id} not found'})
                    continue

                news_link_list = scrape_with_retries(company_name, search_query)
                print(news_link_list)
                if len(news_link_list)!=0:
                    status = scrape_links(news_link_list, company_id, search_query)
                    companies.append({'company_name': company_name, 'status': 'Data added successfully' if status else 'Error occurred'})
                else:
                    companies.append({'company_name': company_name, 'status': 'No Source found'})

            return jsonify({'message': 'JSON list processed', 'results': companies}), 201

        return jsonify({'error': 'Invalid request format'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/scrape_bulk_company_keywords', methods=['POST'])
def scrape_bulk_company_keywords():
    def process_company_in(company_name, search_query, company_id):
        if not check_company_id_exists(company_id):
            return {'company_name': company_name, 'status': f'Company ID {company_id} not found'}
        print("Search query:", search_query)
        news_link_list = scrape_with_retries(company_name, search_query)
        if news_link_list and len(news_link_list) != 0:
            status = scrape_links(news_link_list, company_id, search_query)
            return {'company_name': company_name, 'Keyword': search_query, 'status': 'Data added successfully' if status else 'Error occurred'}
        else:
            return {'company_name': company_name, 'Keyword': search_query, 'status': 'No Source found'}

    try:
        companies = []

        # Handle JSON array
        data = request.get_json()
        if isinstance(data, dict):
            company_name = data.get('company_name')
            company_id = data.get('company_id')
            industry = data.get('industry')
            if industry=="Retail":
                keywords = retail_keywords
            elif industry=="Automotive":
                keywords = automotive_keywords
            elif industry=="Consumer Goods":
                keywords = consumer_keywords
            elif industry=="Healthcare":
                keywords = healthcare_keywords
            elif industry=="Hospitality":
                keywords = hospitality_keywords
            elif industry=="Real Estate":
                keywords = real_estate_keywords
            elif industry=="Telecom":
                keywords = telecom_keywords
            elif industry=="Transport":
                keywords = transport_keywords
            elif industry=="Metals":
                keywords = metals_keywords
            else:
                keywords = keywords
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(process_company_in, company_name, search_query, company_id)
                    for search_query in keywords
                ]
                for future in as_completed(futures):
                    companies.append(future.result())

            # for search_query in keywords:
                # company_name = data.get('company_name')
                # search_query = company_data.get('search_query')
                # company_id = data.get('company_id')

                # if not company_name or not search_query or not company_id:
                #     companies.append({'company_name': company_name, 'status': 'company_name, search_query, and company_id are required'})
                #     continue

                # if not check_company_id_exists(company_id):
                #     companies.append({'company_name': company_name, 'status': f'Company ID {company_id} not found'})
                #     continue

                # news_link_list = scrape_with_retries(company_name, search_query)
                # print(news_link_list)
                # if len(news_link_list)!=0:
                #     status = scrape_links(news_link_list, company_id, search_query)
                #     companies.append({'company_name': company_name, 'status': 'Data added successfully' if status else 'Error occurred'})
                # else:
                #     companies.append({'company_name': company_name, 'status': 'No Source found'})

            return jsonify({'message': 'JSON list processed', 'results': companies}), 201

        return jsonify({'error': 'Invalid request format'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/news-api', methods=['POST'])
def scrape_company_with_NewsAPI():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        company_name = data.get('company_name')
        search_query = data.get('search_query')

        if not company_name or not search_query:
            return jsonify({'error': 'company_name and search_query are required'}), 400

        company_id = request.args.get('company_id')
        if not company_id:
            return jsonify({'error': 'Company ID parameter is missing'}), 400

        if not check_company_id_exists(company_id):
            return jsonify({'error': 'Company ID not found'}), 404

        try:
            news_df = fetch_news_api(company_name, search_query)
        except Exception as e:
            return jsonify({'error': f'News API request failed: {str(e)}'}), 500

        if news_df.empty:
            return jsonify({'message': 'No news articles found from the News API'}), 204

        try:
            status = process_news_links(news_df, company_id, search_query)
        except ValueError as ve:
            return jsonify({'error': f'Invalid data processing: {str(ve)}'}), 500
        except Exception as e:
            return jsonify({'error': f'An error occurred during link processing: {str(e)}'}), 500

        if status:
            return jsonify({'message': 'Company data added successfully'}), 201
        else:
            return jsonify({'message': 'No valid data to add after processing'}), 204

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

def process_company(company_id, company_name, search_query):
    if not check_company_id_exists(company_id):
        return {'company_id': company_id, 'error': 'Company ID not found'}
    
    news_df = fetch_news_api(company_name, search_query)
    if news_df.empty:
        return {'company_id': company_id, 'message': 'No news found for the specified search query'}

    status = process_news_links(news_df, company_id, search_query)
    if status:
        return {'company_id': company_id, 'message': 'Company data added successfully'}
    else:
        return {'company_id': company_id, 'message': 'No news passed the ESG check'}



@app.route('/bulk_scrape', methods=['POST'])
def bulk_scrape():
    try:
        companies = []

        # Check if it's a CSV upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                csv_file = file.read().decode('utf-8-sig')
                csv_data = csv.DictReader(StringIO(csv_file))

                for row in csv_data:
                    company_id = row.get('company_id')
                    company_name = row.get('company_name')
                    keyword = row.get('keyword')

                    if not company_id or not company_name or not keyword:
                        return jsonify({'error': 'CSV must contain company_id, company_name, and keyword'}), 400

                    result = process_company(company_id, company_name, keyword)
                    companies.append(result)

                return jsonify({'results': companies}), 200

        # Handle JSON array
        data = request.get_json()
        if isinstance(data, list):
            for company in data:
                if not all(k in company for k in ('company_id', 'company_name', 'keyword')):
                    return jsonify({'error': 'Each dictionary must contain company_id, company_name, and keyword'}), 400

                result = process_company(company['company_id'], company['company_name'], company['keyword'])
                companies.append(result)

            return jsonify({'results': companies}), 200

        return jsonify({'error': 'Invalid request format'}), 400

    except Exception as e:
        import traceback
        print(traceback.format_exc()) 
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return jsonify({"message": "Running Media Monitoring..."}), 200

if __name__ == '__main__':
    app.run('0.0.0.0', port=5002)
