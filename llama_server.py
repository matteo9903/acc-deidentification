from fastapi import HTTPException
from dotenv import load_dotenv
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import ollama

import pymupdf4llm


# SYSTEM PROMPT
from prompts import system_prompt, prompt_2
from utilities import *

load_dotenv('.env')
LLM_TOKEN = os.environ.get("LLM_TOKEN")
SERVER_IP = os.environ.get("SERVER_IP")
PORT = int(os.environ.get("N_PORT"))

app = FastAPI()

 
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],)

class Message(BaseModel):
        text: str
        role: str
        extension: str

def bot_message(text: str):
    return { "role": "assistant", "content": text }

def user_message(text: str):
    return { "role": "user", "content": text }

def system_message(text: str):
    return { "role": "system", "content": text }

def get_llm_answer(messages):
    model = "llama3.3:70b-instruct-q6_K"
    response = ollama.chat(
        model = model,
        messages = messages,
        options={
            "temperature": 0
        }
    )
    
    return response['message']['content']

#######################
#######  API  #########
#######################

# Home route
@app.get("/")
def read_root():
    return {"message": "LLAMA server is working!", "code": 200 }

@app.post("/answerMessage")
def answer_message(message: Message):

    messages = [
        system_message(system_prompt),
        system_message(prompt_2)
    ]
    
    model_input = None
    
    if message.extension == 'pdf':
        base64_pdf = message.text
        try:
            model_input = convert_pdf_to_text(base64_pdf)
        except Exception as e:
            print(f"Error while converting the PDF to text: {e}")
            return {"error": f"Error while converting the PDF to text: {str(e)}", "code": 500}
    elif message.extension == 'txt':
        model_input = message.text

    # 2. Decode the Base64 string to get the PDF bytes
    
    messages.append(user_message(model_input))

    try:
        print("Getting LLM answer...")
        llm_answer = get_llm_answer(messages)
        print("LLM answer correctly generated")
        return {"response": llm_answer, "code": 200}
    except Exception as e:
        print(f"Error while generating the response: {e}")
        return {"error": f"Error while generating the response: {str(e)}", "code": 500}
    
@app.post("/getPdfRegions")
def get_pdf_regions(message: Message):
    base64_string = message.text
    
    try:
        print("Identifyng PDF regions...")
        new_base64 = find_pdf_regions(base64_string)
    except Exception as e:
        print(f"Error while finding PDF regions: {e}")
        return {"error": f"Error while finding PDF regions: {str(e)}", "code": 500}
    
    print("PDF regions correctly identified")
    return {"response": new_base64, "code": 200}


@app.post("/getTextFromPdf")
def answer_message(message: Message):
    
    if message.extension == 'pdf':
        base64_pdf = message.text
        try:
            print("Converting PDF to text...")
            response = convert_pdf_to_text(base64_pdf)
        except Exception as e:
            print(f"Error while converting PDF to text: {e}")
            return {"error": f"Error while converting PDF to text: {str(e)}", "code": 500}
    
    print("PDF correctly converted to text")
    return {"response": response, "code": 200}
 


# Entry point for running the app
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=3000)