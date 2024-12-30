from openai import OpenAI
import vertexai
from vertexai.language_models import TextGenerationModel
import os
from dotenv import load_dotenv

load_dotenv()

clients = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./LLM_GCP_Textbson.json"

def gpt_chat(text):
    prompt_file = "./prompt.txt"
    with open(prompt_file, "r") as file:
        system_prompt = file.read()
    response = clients.chat.completions.create(
        model="gpt-4o-mini",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": f"{system_prompt}"},
            {"role": "user", "content": f"{text}"},
        ],
        temperature=0.01,
        presence_penalty=0.5,
        seed=123,
    )
    return response.choices[0].message.content


def GcpGPT(text):
    prompt_file = "./prompt.txt"
    with open(prompt_file, "r") as file:
        system_prompt = file.read()
    vertexai.init(project="llmapplication", location="us-central1")
    parameters = {
        "max_output_tokens": 1024,
        "temperature": 0.9,
        "top_p": 1
    }
    model = TextGenerationModel.from_pretrained("text-bison-32k")
    response = model.predict(system_prompt + text, **parameters)
    return response.text
