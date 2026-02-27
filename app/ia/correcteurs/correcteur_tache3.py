from fastapi.responses import StreamingResponse
from openai import OpenAI
import os
from dotenv import load_dotenv
from app.ia.prompts.prompt_tache3 import prompt_tache3

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def corriger_tache3(texte: str, document1: str, document2: str, consigne: str):
    prompt = prompt_tache3(texte, document1, document2, consigne)

    def stream():
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingResponse(stream(), media_type="text/plain")
