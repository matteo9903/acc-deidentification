import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from fastapi import HTTPException
import torch
from torch.cuda.amp import autocast
from dotenv import load_dotenv
import os
from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
import base64
import fitz  # PyMuPDF
import io

# SYSTEM PROMPT
from prompts import system_prompt


model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"
# number_gpus = 1
# max_model_len = 8192
# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_id)
# 8-bit quantization configuration
quantization_config = BitsAndBytesConfig(load_in_8bit=True)
# Load the model in 8-bit mode
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",  # Automatically use GPU if available
    quantization_config=quantization_config
)


pipeline = transformers.pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device_map='auto'
)

load_dotenv('.env')
LLAMA_TOKEN = os.environ.get("LLAMA_TOKEN")
SERVER_IP = os.environ.get("SERVER_IP")
PORT = int(os.environ.get("PORT"))


app = FastAPI()
print()

class Message(BaseModel):
        text: str
        role: str

def bot_message(text: str):
    return { "role": "assistant", "content": text }

def user_message(text: str):
    return { "role": "user", "content": text }

def system_message(text: str):
    return { "role": "system", "content": text }

#######################
#######  API  #########
#######################

# Home route
@app.get("/")
def read_root():
    return {"message": "LLAMA server is working!", "code": 200 }

@app.post("/answerMessage")
def answer(message: Message):

    messages = [
        system_message(system_prompt)
    ]
    
    # Check if GPU is available
    if torch.cuda.is_available():
        device = "cuda"  # Use the first GPU
    else:
        device = "cpu"   # Fall back to CPU
    print(f"USING {device}\n---------------------\n")

    base64_pdf = message.text

    # 2. Decode the Base64 string to get the PDF bytes
    try:
        pdf_bytes = base64.b64decode(base64_pdf)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Base64 encoded PDF: {e}")
    
    pdf_text = extract_pdf_text(pdf_bytes)

    if pdf_text is None:
        raise HTTPException(status_code=500, detail="Failed to extract text from PDF")
    
    print("PDF TEXT\n------------------------------\n\n-", pdf_text)

    messages.append(user_message(pdf_text))

    try:
        with autocast():
            outputs = pipeline(
            messages,
            do_sample=True,
            top_k=1,
            top_p=0.9,
            temperature=0.3,
            num_return_sequences=1,
            truncation=True,
            max_length=8192,  # Increase max_length for longer outputs
            max_new_tokens=2000
            )
                
        response =  outputs[0]["generated_text"][-1]["content"]
        print("response\n-----------------------\n",response, '\n------------------------')

        return {"answer": response, "code": 200 }
    except Exception as e:
        print(f"Error while generating the response: {e}")
        return {"error": f"Error while generating the response: {str(e)}", "code": 500}
    
#########################################
##############  FUNCTIONS  ##############
#########################################
def extract_pdf_text(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # Open PDF from bytes
        text = ""
        for page in doc:
            text += page.get_text()  # Extract text from each page
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None



# Entry point for running the app
if __name__ == '__main__':
    uvicorn.run(app, host=SERVER_IP, port=PORT)