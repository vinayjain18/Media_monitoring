import re
from pypdf import PdfReader
# from tiktoken import Tokenizer

def remove_urls_and_whitespace(text):
    text_no_urls = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text_no_whitespace = re.sub(r'\s+', ' ', text_no_urls).strip()
    return text_no_whitespace

def extract_text_from_pdf(filepath):
    reader = PdfReader(filepath)
    number_of_pages = len(reader.pages)
    result = ""
    for i in range(number_of_pages):
        page = reader.pages[i]
        text = page.extract_text()
        result = result + text
    return result

# def calculate_token_length(text):
#     tokenizer = Tokenizer()
#     tokens = tokenizer.tokenize(text)
#     token_lengths = [len(token) for token in tokens]
#     return token_lengths






