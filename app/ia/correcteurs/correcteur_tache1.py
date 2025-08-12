from fastapi.responses import StreamingResponse
from openai import OpenAI
import os, json
from dotenv import load_dotenv
from app.ia.prompts.prompt_tache1 import prompt_tache1

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def corriger_tache1(texte: str, consigne: str):
    prompt = prompt_tache1(texte, consigne)

    def stream():
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingResponse(stream(), media_type="text/plain")
