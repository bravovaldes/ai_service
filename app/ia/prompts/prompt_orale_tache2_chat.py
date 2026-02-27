from typing import List, Dict


def prompt_tache2_chat(
    scenario: str,
    role_examinateur: str,
    consigne: str,
    historique: List[Dict[str, str]],
    message_candidat: str,
) -> list:
    """
    Construit le tableau de messages OpenAI pour simuler l'examinateur TCF en mode interaction.
    L'IA joue le rôle de l'examinateur et répond naturellement au candidat.
    """

    system_prompt = f"""Tu es un examinateur officiel du TCF Canada. Tu joues le rôle suivant :
**{role_examinateur}**

Contexte / scénario :
{scenario}

Consigne donnée au candidat :
{consigne}

RÈGLES STRICTES :
1. Tu DOIS rester dans ton rôle de "{role_examinateur}" pendant toute la conversation.
2. Réponds de manière naturelle et réaliste, comme un vrai interlocuteur dans cette situation.
3. Tes réponses doivent être COURTES (1 à 3 phrases maximum), comme dans une vraie conversation orale.
4. Tu peux poser des questions de suivi pour relancer la conversation si le candidat est vague.
5. Tu peux demander des précisions, proposer des alternatives, mentionner des contraintes réalistes.
6. Adapte ton registre de langue à la situation (formel si c'est un contexte professionnel, semi-formel sinon).
7. NE CORRIGE JAMAIS le français du candidat. Tu es un interlocuteur, pas un professeur.
8. NE SORS JAMAIS du rôle. Si le candidat dit quelque chose hors-sujet, ramène la conversation au scénario.
9. Réponds UNIQUEMENT avec le texte de ta réplique. Pas de guillemets, pas de préfixe comme "Examinateur:", pas de JSON.
10. Si le candidat pose une question, réponds-y puis relance avec une question ou une information complémentaire."""

    messages = [{"role": "system", "content": system_prompt}]

    # Historique : examinateur → assistant, candidat → user
    for msg in historique:
        if msg["role"] == "examinateur":
            messages.append({"role": "assistant", "content": msg["content"]})
        else:
            messages.append({"role": "user", "content": msg["content"]})

    # Dernier message du candidat
    messages.append({"role": "user", "content": message_candidat})

    return messages
