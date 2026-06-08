# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    html_path = BASE_DIR / "static" / "index.html"

    html_content = html_path.read_text(encoding="utf-8")

    html_content = html_content.replace(
        "%PROFILE_QUESTIONS_JSON%",
        json.dumps(PROFILE_QUESTIONS, ensure_ascii=False)
    )

    html_content = html_content.replace(
        "%QUESTIONS_JSON%",
        json.dumps(QUESTIONS, ensure_ascii=False)
    )

    html_content = html_content.replace(
        "%LINKEDIN_URL_JSON%",
        json.dumps(LINKEDIN_URL)
    )

    html_content = html_content.replace(
        "%INSTAGRAM_URL_JSON%",
        json.dumps(INSTAGRAM_URL)
    )

    return HTMLResponse(html_content)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import html
import os

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DB_PATH", "/data/aura_leads.db"))

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

LINKEDIN_URL = "https://www.linkedin.com/in/audrey-mouton-80b902217/?skipRedirect=true"
INSTAGRAM_URL = "https://www.instagram.com/business.auto.feathersdigital/"


# =========================================================
# QUESTIONS PROFIL
# =========================================================

PROFILE_QUESTIONS = [
    (
        "revenue_band",
        "Ton niveau de chiffre d’affaires mensuel actuel ?",
        {
            "lt3": "Moins de 3k€/mois",
            "3to10": "3k à 10k€/mois",
            "10to30": "10k à 30k€/mois",
            "30plus": "30k€+/mois",
        },
    ),
    (
        "team_size",
        "Ton organisation aujourd’hui ?",
        {
            "solo": "Je suis seul(e)",
            "small": "1 à 3 personnes",
            "team": "4 personnes ou plus",
        },
    ),
]


# =========================================================
# QUESTIONS PRINCIPALES
# =========================================================

QUESTIONS = [

    (
        "absence",
        "Si tu levais complètement le pied pendant <b>7 jours</b>, qu’est-ce qui se passerait réellement ?",
        {
            "A": "Le business continuerait normalement.",
            "B": "Quelques choses s’accumuleraient.",
            "C": "Plusieurs choses ralentiraient.",
            "D": "Une grosse partie dépendrait de mon retour.",
        },
    ),

    (
        "dependance",
        "Aujourd’hui, quand il y a une décision à prendre, une question client ou quelque chose à débloquer, ça finit généralement comment ?",
        {
            "A": "Ça avance sans moi.",
            "B": "Je donne parfois un avis.",
            "C": "Je dois souvent intervenir.",
            "D": "Ça finit presque toujours par revenir vers moi.",
        },
    ),

    (
        "leads",
        "Quand des prospects arrivent aujourd’hui, leur suivi ressemble plutôt à :",
        {
            "A": "Tout est clair et fluide.",
            "B": "Je garde un œil dessus.",
            "C": "Je jongle entre plusieurs tâches ou outils.",
            "D": "J’ai peur que certains passent entre les mailles.",
        },
    ),

    (
        "relances",
        "Quand un prospect ne répond pas, les relances sont :",
        {
            "A": "Automatiques ou bien structurées.",
            "B": "Semi-organisées.",
            "C": "Souvent faites à la main.",
            "D": "Très irrégulières.",
        },
    ),

    (
        "onboarding",
        "Quand un nouveau client rejoint ton accompagnement :",
        {
            "A": "Tout démarre naturellement.",
            "B": "Je vérifie quelques éléments.",
            "C": "Je dois intervenir plusieurs fois.",
            "D": "Sans moi, ça ne démarre pas vraiment.",
        },
    ),

    (
        "interruptions",
        "Dans une semaine classique, combien de fois tu te retrouves à refaire des choses qui reviennent sans arrêt ?",
        {
            "A": "Très rarement.",
            "B": "Quelques fois.",
            "C": "Souvent.",
            "D": "J’ai l’impression que ça arrive toute la journée.",
        },
    ),

    (
        "outils",
        "Aujourd’hui, certaines informations importantes sont-elles dispersées ?",
        {
            "A": "Tout est centralisé.",
            "B": "Quelques éléments seulement.",
            "C": "Je cherche souvent des infos.",
            "D": "J’ai parfois l’impression que tout est partout.",
        },
    ),

    (
        "execution",
        "Une grande partie des tâches répétitives aujourd’hui est :",
        {
            "A": "Déjà structurée.",
            "B": "Partiellement organisée.",
            "C": "Encore très manuelle.",
            "D": "Principalement gérée par moi.",
        },
    ),

    (
        "blocages",
        "Quand quelque chose ralentit dans ton business :",
        {
            "A": "Ça se résout sans moi.",
            "B": "Je regarde rapidement.",
            "C": "Plusieurs choses remontent vers moi.",
            "D": "J’ai l’impression que tout revient vers moi.",
        },
    ),

    (
        "temps",
        "Quand tu regardes ta semaine, combien de temps est absorbé par des tâches qui n’apportent pas directement de valeur ?",
        {
            "A": "Moins de 2h",
            "B": "2 à 5h",
            "C": "6 à 10h",
            "D": "Plus de 10h",
        },
    ),

    (
        "croissance",
        "Quand tu veux prendre plus de clients ou lancer quelque chose de nouveau :",
        {
            "A": "Je peux le faire sereinement.",
            "B": "Je dois réorganiser quelques choses.",
            "C": "Je sens rapidement une surcharge.",
            "D": "J’ai l’impression que tout devient plus compliqué.",
        },
    ),

    (
        "projection",
        "Si ton business continuait d’avancer même quand tu lèves le pied, qu’est-ce qui aurait le plus d’impact pour toi ?",
        {
            "A": "Je récupérerais du temps.",
            "B": "J’aurais moins de charge mentale.",
            "C": "Je pourrais accueillir plus de clients sereinement.",
            "D": "J’aurais enfin l’impression de respirer davantage.",
        },
    ),
]


# =========================================================
# SCORING
# =========================================================

ANSWER_SCORES = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
}


QUESTION_DIMENSIONS = {
    "absence": {"main": "STR", "secondary": ("DEL", 0.5), "weight": 1.8},
    "dependance": {"main": "STR", "secondary": ("DEL", 0.5), "weight": 1.7},
    "leads": {"main": "ACQ", "secondary": ("STR", 0.3), "weight": 1.0},
    "relances": {"main": "ACQ", "secondary": ("DEL", 0.4), "weight": 1.2},
    "onboarding": {"main": "ONB", "secondary": ("DEL", 0.5), "weight": 1.2},
    "interruptions": {"main": "DEL", "secondary": ("STR", 0.4), "weight": 1.0},
    "outils": {"main": "DEL", "secondary": ("STR", 0.3), "weight": 0.8},
    "execution": {"main": "DEL", "secondary": ("STR", 0.5), "weight": 1.5},
    "blocages": {"main": "STR", "secondary": ("DEL", 0.4), "weight": 1.4},
    "temps": {"main": "DEL", "secondary": ("STR", 0.3), "weight": 1.0},
    "croissance": {"main": "STR", "secondary": ("ACQ", 0.2), "weight": 1.5},
    "projection": {"main": "STR", "secondary": None, "weight": 0},
}


DIMENSION_LABELS = {
    "ACQ": "Acquisition",
    "ONB": "Onboarding",
    "DEL": "Exécution",
    "STR": "Structuration",
}


# =========================================================
# DATABASE
# =========================================================

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    with get_conn() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                profile_json TEXT,
                revenue_band TEXT,
                team_size TEXT,
                dependency_pct INTEGER,
                autonomy_pct INTEGER,
                level TEXT,
                subtitle TEXT,
                profile_title TEXT,
                profile_text TEXT,
                dimension_scores_json TEXT,
                top3_json TEXT,
                estimated_min INTEGER,
                estimated_max INTEGER,
                email TEXT,
                repetitive_tasks TEXT,
                linkedin_clicked INTEGER DEFAULT 0,
                contact_channel TEXT,
                dm_text TEXT
            )
            """
        )


@app.on_event("startup")
def startup():
    init_db()


# =========================================================
# CALCULS
# =========================================================

def compute_dimension_scores(answers: dict):

    raw_scores = {
        "ACQ": 0,
        "ONB": 0,
        "DEL": 0,
        "STR": 0,
    }

    raw_max = {
        "ACQ": 0,
        "ONB": 0,
        "DEL": 0,
        "STR": 0,
    }

    for key, _, _ in QUESTIONS:

        answer = answers.get(key)

        if answer is None:
            continue

        score = ANSWER_SCORES.get(answer, 0)

        meta = QUESTION_DIMENSIONS[key]

        main_dim = meta["main"]
        weight = meta["weight"]

        raw_scores[main_dim] += score * weight
        raw_max[main_dim] += 3 * weight

        secondary = meta["secondary"]

        if secondary:

            sec_dim, sec_ratio = secondary

            sec_weight = weight * sec_ratio

            raw_scores[sec_dim] += score * sec_weight
            raw_max[sec_dim] += 3 * sec_weight

    final_scores = {}

    for dim in raw_scores:

        if raw_max[dim] <= 0:
            final_scores[dim] = 0
        else:
            final_scores[dim] = round(
                (raw_scores[dim] / raw_max[dim]) * 100
            )

    return final_scores