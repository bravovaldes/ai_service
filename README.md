TCF‑IA Services

Microservice IA pour l’application de préparation au TCF : compréhension écrite, compréhension orale, expression écrite (GPT‑4), expression orale.

---

Installation :

git clone https://github.com/TCF‑Canada/tcf_ai_services.git
cd tcf_ai_services

.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

uvicorn app.main:app --reload

---

Fonctionnalités & structure :

- app/api/ : routes FastAPI (feedback, tts, etc.)
- app/core/ : logique métier (GPT‑4, Azure TTS)
- app/models/ : schémas Pydantic
- static/ : fichiers statiques (ex. audio générés)
- tests/ : tests automatisés (pytest)
- examples/ : requêtes/réponses JSON

Fichiers clés pour le dev & CI :
- .env.example
- Dockerfile, docker-compose.yml, start.sh
- .github/workflows/python-ci.yml

---

Documentation & tests rapides :

Swagger UI : http://127.0.0.1:8000/docs

Endpoint racine :
GET / → { "message": "💡 Microservice IA opérationnel!" }

Exemple d’appel POST Feedback :
curl -X POST http://127.0.0.1:8000/feedback/ecriture \
  -H "Content-Type: application/json" \
  -d '{"texte":"Bonjour","niveau":"A2"}'

Lancer les tests :
pytest -q

---

Workflow Git & branches :

Branche commune : develop
Branches par fonctionnalité :
- feature/feedback-implementation → GPT‑4 feedback
- feature/tts-implementation → Azure TTS
- feature/devops-setup → Docker, CI, scripts
- feature/qa-tests → tests d’intégration & QA

À chaque début de tâche :
git checkout develop
git pull
git checkout -b feature/<votre-tâche>

Pour coder & push :
git add .
git commit -m "description courte"
git push -u origin feature/<votre-tâche>

Ensuite, ouvrez une Pull Request vers develop.

---

Variables d’environnement attendues :

copy .env.example .env

Puis remplir :
OPENAI_API_KEY=...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...

---

Docker & CI (en cours) :

- Dockerfile : containerisation
- docker-compose.yml : exécution locale
- start.sh : script de lancement
- CI : tests automatisés via GitHub Actions

---

Contribuer :

Soumettez les modifications via PR vers develop. Après validation CI et revue, on merge.
