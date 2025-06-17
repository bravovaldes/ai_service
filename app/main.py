from fastapi import FastAPI
from app.api import expression_routes

app = FastAPI(
    title="Service IA - Expression Écrite TCF",
    version="1.0",
    description="API basée sur GPT-4 pour corriger les trois types de tâches d'expression écrite du TCF Canada"
)

app.include_router(expression_routes.router)
