from openai import OpenAI
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import random

load_dotenv()

keywords = {
    "list": "Lists are mutable sequences in Python that can store multiple items.",
    "function": "Functions in Python are blocks of code that perform a specific task.",
    "loop": "Loops in Python allow you to iterate over data structures.",
    "dictionary": "Collection which is ordered, changeable and do not allow duplicates.",
    "tuples": "Tuples are used to store multiple items in a single variable.",
    "set": "Sets are used to store multiple items in a single variable.",
    "class": "A class in Python is a blueprint for creating objects.",
    "object": "An object is an instance of a class",
    "string": "A string is an array of characters.",
    "attribute": "Attributes define a class.",
    "argument": "An argument is a value passed to a function or method when it is called."
}

def find_keywords(input_text):
    for keyword, explanation in keywords.items():
        if keyword in input_text.lower():
            return explanation
    return None

neutral_phrases = ["Cool!", "Tell me more!", "Why do you think so?", "That's interesting!"]

def generate_neutral_response():
    return random.choice(neutral_phrases)

openai = OpenAI(
    api_key=os.getenv('OPENAI_API_SECRET_KEY')
)
app = FastAPI()
templates = Jinja2Templates(directory="templates")

chat_responses = []

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

chat_log = [{'role': 'system',
             'content': 'You are a Python tutor AI, completely dedicated to teach users how to learn Python from scratch.'
                        }]

@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        user_input = await websocket.receive_text()
        chat_log.append({'role': 'user', 'content': user_input})
        chat_responses.append(user_input)

        keyword_response = find_keywords(user_input)
        if keyword_response:
            await websocket.send_text(keyword_response)
            chat_responses.append(keyword_response)
            continue

        try:
            response = openai.chat.completions.create(
                model='gpt-4o',
                messages=chat_log,
                temperature=0.6,
                stream=True
            )
            ai_response = ''
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    ai_response += chunk.choices[0].delta.content
                    await websocket.send_text(chunk.choices[0].delta.content)

            if not ai_response.strip():
                neutral_response = generate_neutral_response()
                await websocket.send_text(neutral_response)
                chat_responses.append(neutral_response)
            else:
                chat_responses.append(ai_response)

        except Exception as e:
            neutral_response = generate_neutral_response()
            await websocket.send_text(neutral_response)
            chat_responses.append(neutral_response)

@app.post("/", response_class=HTMLResponse)
async def chat(request: Request, user_input: Annotated[str, Form()]):
    chat_log.append({'role': 'user', 'content': user_input})
    chat_responses.append(user_input)

    keyword_response = find_keywords(user_input)
    if keyword_response:
        chat_responses.append(keyword_response)
        return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})

    try:
        response = openai.chat.completions.create(
            model='gpt-4o',
            messages=chat_log,
            temperature=0.6
        )

        bot_response = response.choices[0].message.content
        if not bot_response.strip():
            bot_response = generate_neutral_response()

    except Exception:
        bot_response = generate_neutral_response()

    chat_log.append({'role': 'assistant', 'content': bot_response})
    chat_responses.append(bot_response)
    return templates.TemplateResponse("home.html", {"request": request, "chat_responses": chat_responses})
