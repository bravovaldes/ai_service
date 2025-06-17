# TCF‑IA Services

Microservice IA pour l’application de préparation au TCF : compréhension écrite, compréhension orale, expression écrite.

---

## 🚀 Installation & Mise en route

1. **Cloner le projet :**
   ```bash
   git clone https://github.com/TCF‑Canada/tcf_ai_services.git
   cd tcf_ai_services
   ```

2. **Activer l’environnement virtuel (PowerShell – Windows) :**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Installer les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

4. **Démarrer l’API FastAPI (local) :**
   ```bash
   uvicorn app.main:app --reload
   ```
   L’API est accessible via [http://127.0.0.1:8000](http://127.0.0.1:8000), et la documentation Swagger à `/docs`.

---

## 🧑‍💻 Développement & Tests


### Pour exécuter les tests :
```bash
pytest -q
```

---

## 📂 Structure du projet

```
app/
 ├── api/                ← Routes FastAPI
 ├── core/               ← Logique métier (GPT‑4, TTS)
 └── models/             ← Schémas Pydantic
static/                   ← Fichiers statiques (audio...)
tests/                    ← Tests automatisés
examples/                 ← JSON exemples
.env.example              ← Variables d’environnement
Dockerfile                ← Containerisation
docker-compose.yml        ← Exécution locale multi‑services
start.sh                  ← Script de lancement
.github/workflows/python‑ci.yml ← CI (tests + validation PR)
```

---

## 🔁 Git Workflow

- Branche principale : `develop`
- Branches fonctionnalité :
  - `feature/feedback-implementation` → GPT‑4 feedback
  - `feature/tts-implementation` → Azure TTS
  - `feature/devops-setup` → Docker, scripts, CI
  - `feature/qa-tests` → Tests & QA

### Pour démarrer :
```bash
git checkout develop
git pull
git checkout -b feature/<votre-tâche>
git add .
git commit -m "Courte description"
git push -u origin feature/<votre-tâche>
```

→ Créez une Pull Request vers `develop`. Les tests s’exécutent automatiquement.

---





## 🛠️ Docker & CI

- `Dockerfile`, `docker-compose.yml`, `start.sh`
- CI via GitHub Actions pour valider chaque PR automatiquement

---

## 📝 Contribution

Travaillez sur une branche *feature/*, soumettez via Pull Request vers `develop`, puis intégrez après validation CI/revue.

---


