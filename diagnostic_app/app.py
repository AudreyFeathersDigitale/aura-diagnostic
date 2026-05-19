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
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

LINKEDIN_URL = "https://www.linkedin.com/in/audrey-mouton-80b902217/?skipRedirect=true"
FACEBOOK_URL = "https://www.facebook.com/profile.php?id=61578569620081"
INSTAGRAM_URL = "https://www.instagram.com/business.auto.feathersdigital/"

# =========================
# 1) SEGMENTATION EN AMONT
# =========================

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

# =========================
# 2) QUIZ PRINCIPAL
# =========================

QUESTIONS = [
(
"absence",
"Si tu levais complètement le pied pendant <b>7 jours</b>, qu’est-ce qui se passerait réellement ?",
{
"A":"Le business continuerait normalement.",
"B":"Quelques choses s’accumuleraient.",
"C":"Plusieurs choses ralentiraient.",
"D":"Une grosse partie dépendrait de mon retour."
}
),

(
"dependance",
"Aujourd’hui, quand il y a une décision à prendre, une question client ou quelque chose à débloquer, ça finit généralement comment ?",
{
"A":"Ça avance sans moi.",
"B":"Je donne parfois un avis.",
"C":"Je dois souvent intervenir.",
"D":"Ça finit presque toujours par revenir vers moi."
}
),

(
"leads",
"Quand des prospects arrivent aujourd’hui, leur suivi ressemble plutôt à :",
{
"A":"Tout est clair et fluide.",
"B":"Je garde un œil dessus.",
"C":"Je jongle entre plusieurs tâches ou outils.",
"D":"J’ai peur que certains passent entre les mailles."
}
),

(
"relances",
"Quand un prospect ne répond pas, les relances sont :",
{
"A":"Automatiques ou bien structurées.",
"B":"Semi-organisées.",
"C":"Souvent faites à la main.",
"D":"Très irrégulières."
}
),

(
"onboarding",
"Quand un nouveau client rejoint ton accompagnement :",
{
"A":"Tout démarre naturellement.",
"B":"Je vérifie quelques éléments.",
"C":"Je dois intervenir plusieurs fois.",
"D":"Sans moi, ça ne démarre pas vraiment."
}
),

(
"interruptions",
"Dans une semaine classique, combien de fois tu te retrouves à refaire des choses qui reviennent sans arrêt ?",
{
"A":"Très rarement.",
"B":"Quelques fois.",
"C":"Souvent.",
"D":"J’ai l’impression que ça arrive toute la journée."
}
),

(
"outils",
"Aujourd’hui, certaines informations importantes sont-elles dispersées ?",
{
"A":"Tout est centralisé.",
"B":"Quelques éléments seulement.",
"C":"Je cherche souvent des infos.",
"D":"J’ai parfois l’impression que tout est partout."
}
),

(
"execution",
"Une grande partie des tâches répétitives aujourd’hui est :",
{
"A":"Déjà structurée.",
"B":"Partiellement organisée.",
"C":"Encore très manuelle.",
"D":"Principalement gérée par moi."
}
),

(
"blocages",
"Quand quelque chose ralentit dans ton business :",
{
"A":"Ça se résout sans moi.",
"B":"Je regarde rapidement.",
"C":"Plusieurs choses remontent vers moi.",
"D":"J’ai l’impression que tout revient vers moi."
}
),

(
"temps",
"Quand tu regardes ta semaine, combien de temps est absorbé par des tâches qui n’apportent pas directement de valeur ?",
{
"A":"Moins de 2h",
"B":"2 à 5h",
"C":"6 à 10h",
"D":"Plus de 10h"
}
),

(
"croissance",
"Quand tu veux prendre plus de clients ou lancer quelque chose de nouveau :",
{
"A":"Je peux le faire sereinement.",
"B":"Je dois réorganiser quelques choses.",
"C":"Je sens rapidement une surcharge.",
"D":"J’ai l’impression que tout devient plus compliqué."
}
),

(
"projection",
"Si ton business continuait d’avancer même quand tu lèves le pied, qu’est-ce qui aurait le plus d’impact pour toi ?",
{
"A":"Je récupérerais du temps.",
"B":"J’aurais moins de charge mentale.",
"C":"Je pourrais accueillir plus de clients sereinement.",
"D":"J’aurais enfin l’impression de respirer davantage."
}
)
]

ANSWER_SCORES = {
    "A": 0,
    "B": 1,
    "C": 2,
    "D": 3,
}

# =========================
# 3) MOTEUR DE SCORING
# =========================

QUESTION_DIMENSIONS = {

"absence":{"main":"STR","secondary":("DEL",0.5),"weight":1.8},

"dependance":{"main":"STR","secondary":("DEL",0.5),"weight":1.7},

"leads":{"main":"ACQ","secondary":("STR",0.3),"weight":1.0},

"relances":{"main":"ACQ","secondary":("DEL",0.4),"weight":1.2},

"onboarding":{"main":"ONB","secondary":("DEL",0.5),"weight":1.2},

"interruptions":{"main":"DEL","secondary":("STR",0.4),"weight":1.0},

"outils":{"main":"DEL","secondary":("STR",0.3),"weight":0.8},

"execution":{"main":"DEL","secondary":("STR",0.5),"weight":1.5},

"blocages":{"main":"STR","secondary":("DEL",0.4),"weight":1.4},

"temps":{"main":"DEL","secondary":("STR",0.3),"weight":1.0},

"croissance":{"main":"STR","secondary":("ACQ",0.2),"weight":1.5},

"projection":{"main":"STR","secondary":None,"weight":0}

}

PROFILE_WEIGHTS = {
    "freelance": {"ACQ": 1.1, "ONB": 1.2, "DEL": 1.0, "STR": 1.1},
}

DIMENSION_LABELS = {
    "ACQ": "Acquisition",
    "ONB": "Onboarding",
    "DEL": "Exécution",
    "STR": "Structuration",
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    existing = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing_cols = {row["name"] for row in existing}
    if column not in existing_cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                score_pct INTEGER NOT NULL,
                score_display_30 INTEGER NOT NULL,
                level TEXT NOT NULL,
                subtitle TEXT NOT NULL,
                profile_title TEXT NOT NULL,
                profile_text TEXT NOT NULL,
                category_scores_json TEXT NOT NULL,
                top3_json TEXT NOT NULL,
                estimated_min INTEGER NOT NULL,
                estimated_max INTEGER NOT NULL,
                activity TEXT,
                repetitive_tasks TEXT,
                tools TEXT,
                linkedin_clicked INTEGER NOT NULL DEFAULT 0,
                dm_text TEXT
            )
            """
        )

        ensure_column(conn, "leads", "profile_json", "TEXT")
        ensure_column(conn, "leads", "business_type", "TEXT")
        ensure_column(conn, "leads", "revenue_band", "TEXT")
        ensure_column(conn, "leads", "team_size", "TEXT")
        ensure_column(conn, "leads", "dependency_pct", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "autonomy_pct", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "dimension_scores_json", "TEXT")
        ensure_column(conn, "leads", "contact_channel", "TEXT")
        ensure_column(conn, "leads", "monthly_loss_min", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "monthly_loss_max", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "lost_clients_min", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "lost_clients_max", "INTEGER DEFAULT 0")


def safe_json_loads(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def questions_as_json() -> str:
    out = []
    for key, prompt, opts in QUESTIONS:
        out.append({"key": key, "prompt": prompt, "options": opts})
    return json.dumps(out, ensure_ascii=False)


def profile_questions_as_json() -> str:
    out = []
    for key, prompt, opts in PROFILE_QUESTIONS:
        out.append({"key": key, "prompt": prompt, "options": opts})
    return json.dumps(out, ensure_ascii=False)


def get_profile_dimension_weights(profile: dict) -> dict:
    return PROFILE_WEIGHTS["freelance"]


def compute_dimension_scores(answers: dict, profile: dict) -> dict:
    raw_scores = {"ACQ": 0.0, "ONB": 0.0, "DEL": 0.0, "STR": 0.0}
    raw_max = {"ACQ": 0.0, "ONB": 0.0, "DEL": 0.0, "STR": 0.0}
    profile_weights = get_profile_dimension_weights(profile)

    for key, _, _ in QUESTIONS:
        answer = answers.get(key)
        if answer is None:
            continue

        score = ANSWER_SCORES.get(answer, 0)
        meta = QUESTION_DIMENSIONS[key]

        main_dim = meta["main"]
        weight = meta["weight"] * profile_weights.get(main_dim, 1.0)
        secondary = meta["secondary"]

        raw_scores[main_dim] += score * weight
        raw_max[main_dim] += 3 * weight

        if secondary:
            sec_dim, sec_ratio = secondary
            sec_weight = meta["weight"] * sec_ratio * profile_weights.get(sec_dim, 1.0)
            raw_scores[sec_dim] += score * sec_weight
            raw_max[sec_dim] += 3 * sec_weight

    final_scores = {}
    for dim in raw_scores:
        final_scores[dim] = 0 if raw_max[dim] <= 0 else round((raw_scores[dim] / raw_max[dim]) * 100)

    return final_scores


def compute_dependency_pct(dimension_scores: dict, profile: dict) -> int:
    revenue_band = profile.get("revenue_band", "lt3")
    team_size = profile.get("team_size", "solo")

    dimension_weights = {
    "ACQ":0.25,
    "ONB":0.15,
    "DEL":0.30,
    "STR":0.30
}

    score = (
        dimension_scores["ACQ"] * dimension_weights["ACQ"] +
        dimension_scores["ONB"] * dimension_weights["ONB"] +
        dimension_scores["DEL"] * dimension_weights["DEL"] +
        dimension_scores["STR"] * dimension_weights["STR"]
    )

    if team_size in ("small", "team") and dimension_scores["STR"] >= 60:
        score += 5

    if revenue_band in ("10to30", "30plus") and dimension_scores["DEL"] >= 60:
        score += 3

    return min(round(score), 100)

def compute_autonomy_pct(dependency_pct: int) -> int:
    return max(0, 100 - dependency_pct)


def level_from_dependency_pct(dependency_pct: int, profile: dict) -> tuple[str, str]:

    if dependency_pct < 25:
        return (
            "Dépendance faible",
            "Ton business commence déjà à fonctionner avec une certaine autonomie."
        )

    if dependency_pct < 50:
        return (
            "Dépendance modérée",
            "Ton activité avance, mais elle te ramène encore régulièrement au centre."
        )

    if dependency_pct < 75:
        return (
            "Dépendance forte",
            "Tu restes encore le point de passage obligé sur plusieurs zones importantes."
        )

    return (
        "Dépendance critique",
        "Aujourd’hui ton business avance encore à ton rythme."
    )

def display_score_30(dependency_pct: int) -> int:
    autonomy = compute_autonomy_pct(dependency_pct)
    return round((autonomy / 100) * 30)


def summary_message(dependency_pct: int, profile: dict) -> str:
    if dependency_pct < 25:
        return (
            "Ton business a déjà une bonne base.<br><br>"
            "Mais certaines zones peuvent encore mieux tourner sans toi."
        )

    if dependency_pct < 50:
        return (
            "Ton business avance.<br><br>"
            "Mais il te ramène encore trop souvent au centre."
        )

    if dependency_pct < 75:
        return (
            "Ton business fonctionne.<br><br>"
            "Mais il fonctionne encore beaucoup parce que tu compenses là où ton système devrait prendre le relais."
        )

    return (
        "Ton business fonctionne.<br><br>"
        "Mais aujourd’hui, il avance encore trop souvent à ton rythme."
    )

def level_messages(dependency_pct: int, profile: dict) -> tuple[str, str]:
    if dependency_pct < 25:
        tension = (
            "Si rien ne change,<br>"
            "tu vas continuer à porter une charge que ton business devrait déjà absorber."
        )
        closing = (
            "Le sujet n’est pas un manque d’effort.<br>"
            "Le sujet, c’est la structure."
        )
    elif dependency_pct < 50:
        tension = (
            "Si rien ne change,<br>"
            "tu vas continuer à compenser chaque semaine ce que ton système devrait déjà gérer."
        )
        closing = (
            "Le problème n’est pas ton organisation.<br>"
            "Le problème, c’est que ton business dépend encore trop de toi."
        )
    elif dependency_pct < 75:
        tension = (
            "Si rien ne change,<br>"
            "tu vas continuer à porter ton business à bout de bras."
        )
        closing = (
            "Et tant que cette structure ne change pas,<br>"
            "tu ne pourras ni lever le pied sereinement, ni scaler proprement."
        )
    else:
        tension = (
            "Si rien ne change,<br>"
            "ton business va rester directement accroché à ton niveau de disponibilité."
        )
        closing = (
            "Autrement dit : aujourd’hui, tu es encore le système."
        )

    return tension, closing


def projection_cta_message(answer: str) -> str:

    messages = {

        "A":"👉 Tu m’as dit vouloir récupérer davantage de temps.",

        "B":"👉 Tu m’as dit vouloir réduire ta charge mentale.",

        "C":"👉 Tu m’as dit vouloir accueillir plus de clients sereinement.",

        "D":"👉 Tu m’as dit vouloir enfin respirer davantage."
    }

    return messages.get(
        answer,
        "👉 Tu veux que ton business repose moins sur toi."
    )


def estimate_time_gain(
    answers: dict,
    dependency_pct: int,
    dimension_scores: dict,
    profile: dict,
) -> tuple[int, int]:
    revenue_band = profile.get("revenue_band", "lt3")
    team_size = profile.get("team_size", "solo")

    if dependency_pct < 25:
        estimate_min, estimate_max = 2, 5
    elif dependency_pct < 50:
        estimate_min, estimate_max = 4, 8
    elif dependency_pct < 75:
        estimate_min, estimate_max = 7, 13
    else:
        estimate_min, estimate_max = 10, 18

    if dimension_scores["DEL"] >= 70:
        estimate_min += 2
        estimate_max += 3
    elif dimension_scores["DEL"] >= 55:
        estimate_min += 1
        estimate_max += 2

    if dimension_scores["STR"] >= 70:
        estimate_min += 1
        estimate_max += 3
    elif dimension_scores["STR"] >= 55:
        estimate_min += 1
        estimate_max += 1

    if dimension_scores["ACQ"] >= 70:
        estimate_min += 1
        estimate_max += 2

    if dimension_scores["ONB"] >= 70:
        estimate_min += 1
        estimate_max += 2

    if team_size == "small":
        estimate_min += 1
        estimate_max += 2
    elif team_size == "team":
        estimate_min += 2
        estimate_max += 4

    if revenue_band == "3to10":
        estimate_max += 1
    elif revenue_band == "10to30":
        estimate_min += 1
        estimate_max += 3
    elif revenue_band == "30plus":
        estimate_min += 2
        estimate_max += 4

    temps_perdu_answer = answers.get("temps")
    if temps_perdu_answer == "A":
        estimate_max = min(estimate_max, max(estimate_min + 1, 4))
    elif temps_perdu_answer == "B":
        estimate_max = min(estimate_max, max(estimate_min + 2, 7))
    elif temps_perdu_answer == "C":
        estimate_min = max(estimate_min, 6)
    elif temps_perdu_answer == "D":
        estimate_min = max(estimate_min, 10)
        estimate_max += 2

    estimate_min = max(1, estimate_min)
    estimate_max = max(estimate_min + 1, estimate_max)
    estimate_max = min(30, estimate_max)

    return estimate_min, estimate_max


def estimate_business_opportunities(
    estimated_min: int,
    estimated_max: int,
    profile: dict
) -> tuple[int, int]:

    revenue_band = profile.get("revenue_band", "lt3")

    opportunity_factor = {
        "lt3": 1,
        "3to10": 2,
        "10to30": 4,
        "30plus": 6,
    }

    factor = opportunity_factor.get(revenue_band,2)

    min_opportunities = max(
        1,
        round((estimated_min/5)*factor)
    )

    max_opportunities = max(
        min_opportunities+1,
        round((estimated_max/4)*factor)
    )

    return min_opportunities, max_opportunities


def estimate_lost_clients(monthly_loss_min: int, monthly_loss_max: int, profile: dict) -> tuple[int, int]:
    revenue_band = profile.get("revenue_band", "lt3")

    avg_client_value = {
        "lt3": 200,
        "3to10": 500,
        "10to30": 1000,
        "30plus": 2000,
    }

    value = avg_client_value.get(revenue_band, 500)

    return int(monthly_loss_min / value), int(monthly_loss_max / value)


def dimension_priority_copy(dim: str, profile: dict) -> str:

    priorities = {
        "STR": "Des process et une organisation qui reposent encore trop sur toi",

        "DEL": "Des tâches répétitives et suivis qui reviennent encore vers toi",

        "ONB": "Un onboarding client qui dépend encore trop de ton intervention",

        "ACQ": "Le suivi des prospects et des relances reste encore trop manuel",
    }

    return priorities.get(
        dim,
        "Certaines zones de ton activité reposent encore trop sur toi"
    )


def priorities_from_dimensions(dimension_scores: dict, profile: dict) -> list[str]:
    ordered = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
    return [dimension_priority_copy(dim, profile) for dim, _ in ordered[:3]]


def dominant_profile(dimension_scores: dict, profile: dict) -> tuple[str, str]:

    ordered = sorted(
        dimension_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top_dim = ordered[0][0] if ordered else "STR"

    profiles = {

        "STR": (
            "Ton principal frein aujourd’hui vient de la structuration",

            "Tes process, ton organisation et certaines décisions reposent encore trop sur toi."
        ),

        "DEL": (
            "Ton principal frein aujourd’hui vient de l’exécution",

            "Trop de tâches répétitives, suivis et actions opérationnelles reviennent encore vers toi."
        ),

        "ONB": (
            "Ton principal frein aujourd’hui vient de l’onboarding",

            "L’arrivée de nouveaux clients dépend encore trop de ton intervention."
        ),

        "ACQ": (
            "Ton principal frein aujourd’hui vient de l’acquisition",

            "Le suivi des prospects, relances et conversions reste encore trop manuel."
        )

    }

    return profiles.get(
        top_dim,
        profiles["STR"]
    )


def create_lead_record(answers: dict, profile: dict, result_data: dict) -> int:
    now = utcnow_iso()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads (
                created_at,
                updated_at,
                answers_json,
                profile_json,
                business_type,
                revenue_band,
                team_size,
                score_pct,
                dependency_pct,
                autonomy_pct,
                score_display_30,
                level,
                subtitle,
                profile_title,
                profile_text,
                category_scores_json,
                dimension_scores_json,
                top3_json,
                estimated_min,
                estimated_max,
                dm_text,
                monthly_loss_min,
                monthly_loss_max,
                lost_clients_min,
                lost_clients_max
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                json.dumps(answers, ensure_ascii=False),
                json.dumps(profile, ensure_ascii=False),
                "coach_infopreneur",
                profile.get("revenue_band"),
                profile.get("team_size"),
                result_data["score_pct"],
                result_data["dependency_pct"],
                result_data["autonomy_pct"],
                result_data["score_display_30"],
                result_data["level"],
                result_data["subtitle"],
                result_data["profile_title"],
                result_data["profile_text"],
                json.dumps(result_data["dimension_scores"], ensure_ascii=False),
                json.dumps(result_data["dimension_scores"], ensure_ascii=False),
                json.dumps(result_data["top3"], ensure_ascii=False),
                result_data["estimated_min"],
                result_data["estimated_max"],
                result_data["dm_copy"],
                result_data["monthly_loss_min"],
                result_data["monthly_loss_max"],
                result_data["lost_clients_min"],
                result_data["lost_clients_max"],
            ),
        )
        return int(cur.lastrowid)


def update_lead_details(
    lead_id: int,
    activity: str | None,
    repetitive_tasks: str | None,
    tools: str | None,
    linkedin_clicked: bool,
    dm_text: str | None,
    contact_channel: str | None = None,
) -> None:
    now = utcnow_iso()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE leads
            SET updated_at = ?,
                activity = ?,
                repetitive_tasks = ?,
                tools = ?,
                linkedin_clicked = ?,
                dm_text = COALESCE(?, dm_text),
                contact_channel = COALESCE(?, contact_channel)
            WHERE id = ?
            """,
            (
                now,
                activity,
                repetitive_tasks,
                tools,
                1 if linkedin_clicked else 0,
                dm_text,
                contact_channel,
                lead_id,
            ),
        )


def render_answers_html(answers_json: str | None) -> str:
    data = safe_json_loads(answers_json) or {}
    if not data:
        return "-"

    question_map = {key: {"prompt": prompt, "options": opts} for key, prompt, opts in QUESTIONS}
    items = []

    for key, value in data.items():
        question = question_map.get(key)
        if question:
            prompt = question["prompt"]
            answer_label = question["options"].get(value, value)
        else:
            prompt = key
            answer_label = value

        items.append(
            f"""
            <div style="margin-bottom:12px;">
                <div style="font-weight:800;color:#0f172a;">{prompt}</div>
                <div style="color:#475569;margin-top:4px;">{html.escape(str(answer_label))}</div>
            </div>
            """
        )
    return "".join(items)


def render_profile_html(profile_json: str | None) -> str:
    data = safe_json_loads(profile_json) or {}
    if not data:
        return "-"

    label_maps = {
        "revenue_band": dict(PROFILE_QUESTIONS[0][2]),
        "team_size": dict(PROFILE_QUESTIONS[1][2]),
    }

    items = []
    labels = {
        "revenue_band": "CA mensuel",
        "team_size": "Taille de l’équipe",
    }

    for key in ["revenue_band", "team_size"]:
        raw = data.get(key)
        display = label_maps.get(key, {}).get(raw, raw or "-")
        items.append(
            f"<div style='margin-bottom:6px;'><b>{html.escape(labels[key])} :</b> {html.escape(str(display))}</div>"
        )

    return "".join(items)


def render_dimension_scores_html(dimension_scores_json: str | None) -> str:
    dimensions = safe_json_loads(dimension_scores_json)

    if not dimensions:
        return "-"

    def score_color(value: int) -> str:
        if value >= 70:
            return "#ef4444"
        if value >= 40:
            return "#f59e0b"
        return "#16a34a"

    items = []
    ordered = [
        ("ACQ", "Acquisition", "Génération & suivi des prospects"),
        ("ONB", "Onboarding", "Mise en route des clients"),
        ("DEL", "Exécution", "Production & tâches quotidiennes"),
        ("STR", "Structuration", "Process & organisation interne"),
    ]

    for key, label, hint in ordered:
        value = int(dimensions.get(key, 0))
        color = score_color(value)
        items.append(f"""
        <div style="
            background:#f8fafc;
            border:1px solid #e5e7eb;
            border-radius:14px;
            padding:12px;
        ">
            <div style="font-size:12px;color:#64748b;font-weight:700;">{label}</div>
            <div style="font-size:24px;font-weight:900;color:{color};margin-top:4px;">{value}%</div>
            <div style="font-size:12px;color:#64748b;margin-top:4px;line-height:1.35;">{hint}</div>
        </div>
        """)

    return f"""
    <div style="
        display:grid;
        grid-template-columns:repeat(2,minmax(0,1fr));
        gap:10px;
        margin-top:8px;
    ">
        {''.join(items)}
    </div>
    """


HTML = r"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AURA — Diagnostic automatisation</title>
<link rel="icon" type="image/png" href="/static/favicon.png">
<style>
  :root{
    --panel:#eef2f7;
    --card:#ffffff;
    --soft:#f1f5f9;
    --soft2:#f8fafc;
    --text:#0f172a;
    --muted:#64748b;
    --blue:#2f6bff;
    --blue2:#1f5cff;
    --line:rgba(15,23,42,.08);
  }

  *{ box-sizing:border-box; }

  body{
    margin:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto;
    min-height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:22px;
    color:var(--text);
    background:
      radial-gradient(900px 540px at 30% 20%, rgba(47,107,255,.10), transparent 60%),
      radial-gradient(900px 620px at 70% 15%, rgba(255,199,128,.10), transparent 62%),
      linear-gradient(180deg, #f7f9fc, #f3f6fb 55%, #f7f9fc);
  }

  .frame{
    width:min(1120px, 96vw);
    padding:14px;
    border-radius:26px;
    background: rgba(255,255,255,.75);
    border:1px solid rgba(15,23,42,.06);
    box-shadow: 0 30px 90px rgba(15,23,42,.10);
    backdrop-filter: blur(8px);
  }

  .grid{
    display:grid;
    grid-template-columns: 380px 1fr;
    gap:14px;
  }

  .left, .right{
    border-radius:22px;
    border:1px solid rgba(15,23,42,.06);
    overflow:hidden;
  }

  .left{
    background: linear-gradient(180deg, #ffffff, #f4f7fb);
    padding:22px;
    position:relative;
  }

  .left:before{
    content:"";
    position:absolute;
    inset:-80px;
    background:
      radial-gradient(circle at 35% 25%, rgba(47,107,255,.12), transparent 55%),
      radial-gradient(circle at 62% 58%, rgba(255,199,128,.12), transparent 60%);
    filter: blur(22px);
    opacity:.9;
    pointer-events:none;
  }

  .leftInner{
    position:relative;
    z-index:1;
  }

  .right{
    background: var(--panel);
    padding:20px;
    min-height:700px;
    display:flex;
    flex-direction:column;
  }

  .auraBig{
    display:flex;
    justify-content:center;
    margin-top:10px;
  }

  .auraImg{
    width:350px;
    height:310px;
    display:flex;
    justify-content:center;
    align-items:center;
    filter: drop-shadow(0 18px 22px rgba(15,23,42,.12));
    transform-origin:50% 70%;
    animation:
      auraTilt 3.2s ease-in-out infinite,
      auraGlow 2.8s ease-in-out infinite;
  }

  .auraImg img{
    width:150%;
    height:auto;
    object-fit:contain;
    display:block;
    user-select:none;
    -webkit-user-drag:none;
    pointer-events:none;
  }

  .name{
    text-align:center;
    font-weight:950;
    font-size:38px;
    margin-top:10px;
    letter-spacing:.4px;
  }

  .subtitle{
    text-align:center;
    color:var(--muted);
    font-weight:700;
    font-size:14px;
    margin-top:4px;
  }

  .tag{
    text-align:center;
    color:var(--muted);
    font-weight:700;
    margin-top:6px;
  }

  .promiseBox{
    margin-top:16px;
    padding:14px 14px 10px;
    border-radius:18px;
    background: rgba(47,107,255,.06);
    border:1px solid rgba(47,107,255,.10);
  }

  .promiseTitle{
    font-weight:900;
    font-size:15px;
    margin-bottom:8px;
  }

  .promiseList{
    margin:0;
    padding-left:18px;
    color:var(--text);
    font-weight:650;
  }

  .promiseList li{
    margin:8px 0;
  }

  .promiseHighlight{
    margin-top:10px;
    font-weight:900;
    color:var(--blue2);
    font-size:14px;
  }

  .progress{
    margin:16px 0 14px;
    height:12px;
    border-radius:999px;
    background: rgba(15,23,42,.08);
    overflow:hidden;
  }

  .bar{
    width:0%;
    height:100%;
    border-radius:999px;
    background: linear-gradient(90deg, var(--blue), #6aa3ff);
    transition: width .25s ease;
  }

  .leftTitle{
    font-weight:900;
    margin:0 0 10px;
    font-size:16px;
  }

  .chatHeader{
    display:flex;
    justify-content:space-between;
    align-items:center;
    background: rgba(255,255,255,.75);
    border:1px solid var(--line);
    border-radius:18px;
    padding:14px 16px;
    margin-bottom:16px;
  }

  .chatHeaderLeft{
    display:flex;
    gap:12px;
    align-items:center;
    flex:1;
    min-width:0;
  }

  .chatHeaderAvatarWrap{
    width:56px;
    height:56px;
    border-radius:14px;
    background:#eef2f7;
    border:1px solid var(--line);
    display:flex;
    align-items:center;
    justify-content:center;
    flex-shrink:0;
    overflow:hidden;
  }

  .chatHeaderAvatar{
    width:100%;
    height:100%;
    object-fit:cover;
    object-position:center;
    display:block;
  }

  .chatHeaderText{
    min-width:0;
  }

  .chatHeaderTitle{
    font-weight:950;
    font-size:14px;
    line-height:1.2;
  }

  .chatHeaderSub{
    color: var(--muted);
    font-size:13px;
    font-weight:650;
    white-space: normal;
    line-height:1.35;
  }

  .chatHeaderRight{
    color: var(--muted);
    font-size:12px;
    font-weight:900;
    white-space:nowrap;
    margin-left:12px;
  }

  .chat{
    flex:1;
    overflow:auto;
    padding-right:4px;
  }

  .row{
    display:flex;
    gap:10px;
    margin:14px 0;
    align-items:flex-start;
  }

  .mini{
    width:68px;
    height:68px;
    border-radius:999px;
    overflow:hidden;
    border:1px solid var(--line);
    background:#fff;
    display:flex;
    align-items:center;
    justify-content:center;
    flex:0 0 auto;
    animation: popIn .18s ease-out 1;
  }

  .mini img{
    width:100%;
    height:100%;
    object-fit:cover;
    object-position:center;
    display:block;
    user-select:none;
    -webkit-user-drag:none;
  }

  .bubble{
    max-width:84%;
    background: var(--card);
    border:1px solid var(--line);
    border-radius:18px;
    padding:14px 16px;
    box-shadow: 0 10px 18px rgba(15,23,42,.06);
    line-height:1.35;
  }

  .bubbleQuestion{
    background: var(--soft);
    border-color: rgba(15,23,42,.06);
  }

  .questionTag{
    display:inline-block;
    background:#e2e8f0;
    color:#1e293b;
    font-weight:800;
    font-size:12px;
    padding:4px 10px;
    border-radius:999px;
    margin-bottom:6px;
  }

  .typing{
    display:inline-flex;
    gap:6px;
    align-items:center;
  }

  .dot{
    width:7px;
    height:7px;
    border-radius:999px;
    background:#94a3b8;
    opacity:.55;
    animation: pop 1.2s infinite;
  }

  .dot:nth-child(2){ animation-delay:.15s; }
  .dot:nth-child(3){ animation-delay:.30s; }

  @keyframes pop{
    0%,100%{ transform: translateY(0); opacity:.45; }
    50%{ transform: translateY(-4px); opacity:.95; }
  }

  .loaderWrap{
    display:flex;
    align-items:center;
    gap:10px;
  }

  .loader{
    width:18px;
    height:18px;
    border:2px solid rgba(47,107,255,.18);
    border-top:2px solid var(--blue);
    border-radius:999px;
    animation: spin 0.8s linear infinite;
    flex:0 0 auto;
  }

  @keyframes spin{
    from{ transform: rotate(0deg); }
    to{ transform: rotate(360deg); }
  }

  .choices{
    display:grid;
    gap:12px;
    margin-top:12px;
  }

  .btn{
    width:100%;
    display:flex;
    align-items:center;
    gap:14px;
    background: var(--soft2);
    border:1px solid var(--line);
    border-radius:16px;
    padding:16px;
    cursor:pointer;
    font-weight:850;
    text-align:left;
    box-shadow: 0 8px 14px rgba(15,23,42,.05);
    transition: transform .06s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
  }

  .btn:hover{
    border-color: rgba(47,107,255,.28);
    box-shadow: 0 16px 26px rgba(47,107,255,.10);
  }

  .btn:active{
    transform: scale(.99);
  }

  .btnSelected{
    border-color: var(--blue);
    background: #eef4ff;
    box-shadow: 0 10px 20px rgba(47,107,255,.15);
    transform: scale(.98);
  }

  .key{
    width:34px;
    height:34px;
    border-radius:12px;
    display:flex;
    align-items:center;
    justify-content:center;
    background: linear-gradient(180deg, var(--blue), var(--blue2));
    color:white;
    font-weight:950;
    flex:0 0 auto;
  }

  .footer{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    padding-top:14px;
    margin-top:14px;
    border-top:1px solid rgba(15,23,42,.10);
  }

  .cta{
    display:flex;
    align-items:center;
    gap:10px;
    border:1px dashed rgba(15,23,42,.18);
    background: rgba(255,255,255,.70);
    padding:10px 12px;
    border-radius:16px;
    font-weight:900;
  }

  .cta code{
    background:#0f172a;
    color:#e2e8f0;
    padding:4px 10px;
    border-radius:12px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
  }

  .restart,
  .dmBtn{
    border:none;
    cursor:pointer;
    font-weight:950;
    border-radius:16px;
    padding:12px 18px;
    text-decoration:none;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    color:white;
    background: linear-gradient(180deg, var(--blue), var(--blue2));
    box-shadow: 0 18px 26px rgba(47,107,255,.18);
  }

  .restart:hover,
  .dmBtn:hover{
    filter:brightness(1.05);
  }

  .copy{
    display:none;
    margin-top:12px;
    padding:12px;
    border-radius:18px;
    background:#0f172a;
    color:#e2e8f0;
    border:1px solid rgba(15,23,42,.10);
    white-space:pre-wrap;
    font-size:12px;
  }

  .copy.success{
    background: #f0fdf4;
    color: #166534;
    border: 1px solid rgba(22,163,74,.2);
  }

  .resultCard{
    margin-top:12px;
    background:#fff;
    border:1px solid var(--line);
    border-radius:18px;
    padding:16px;
    box-shadow: 0 10px 18px rgba(15,23,42,.06);
  }

  .resultActions{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
    margin-top:14px;
  }

  .micro{
    font-size:13px;
    color:var(--muted);
    margin-top:8px;
  }

  .estimateBox{
    background: linear-gradient(180deg, #ffffff, #f8fbff);
    border:1px solid rgba(47,107,255,.14);
  }

  .leadForm{
    display:grid;
    gap:12px;
    margin-top:16px;
  }

  .leadForm label{
    font-size:13px;
    font-weight:800;
    color:var(--text);
    display:block;
    margin-bottom:6px;
  }

  .leadInput,
  .leadTextarea{
    width:100%;
    border:1px solid var(--line);
    border-radius:14px;
    padding:12px 14px;
    font:inherit;
    background:#fff;
    color:var(--text);
    outline:none;
  }

  .leadInput:focus,
  .leadTextarea:focus{
    border-color: rgba(47,107,255,.45);
    box-shadow: 0 0 0 4px rgba(47,107,255,.08);
  }

  .leadTextarea{
    min-height:90px;
    resize:vertical;
  }

  .messageAppear{
    animation: messageAppear .35s ease;
  }

  @keyframes messageAppear{
    0%{
      opacity:0;
      transform:translateY(10px);
    }
    100%{
      opacity:1;
      transform:translateY(0);
    }
  }

  .typeCaret{
    display:inline-block;
    width:2px;
    height:1em;
    background: var(--blue);
    margin-left:2px;
    vertical-align:-2px;
    animation: caretBlink .9s infinite;
  }

  @keyframes caretBlink{
    0%, 49%{ opacity:1; }
    50%, 100%{ opacity:0; }
  }

  .scoreHero{
    background: linear-gradient(180deg, #ffffff, #f8fbff);
    border:1px solid rgba(47,107,255,.14);
    padding:18px 20px;
    border-radius:16px;
  }

  .scoreHero div:first-child{
    margin-bottom:6px;
  }

  .scorePercent{
    font-size:52px;
    font-weight:950;
    line-height:1;
    margin-top:8px;
  }

  .scorePercent.good{
    color:#16a34a !important;
  }

  .scorePercent.warning{
    color:#f59e0b !important;
  }

  .scorePercent.danger{
    color:#ef4444 !important;
  }

  .scoreSecondary{
    color:var(--muted);
    font-size:13px;
    font-weight:700;
    margin-top:8px;
  }

  .dimensionGrid{
    display:grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap:10px;
    margin-top:10px;
  }

  .dimensionItem{
    background:#f8fafc;
    border:1px solid rgba(15,23,42,.06);
    border-radius:14px;
    padding:10px 12px;
  }

  .dimensionLabel{
    font-size:12px;
    color:var(--muted);
    font-weight:800;
  }

  .dimensionValue{
    font-size:22px;
    font-weight:950;
    margin-top:4px;
  }

  .dimensionHint{
    font-size:12px;
    color:#64748b;
    margin-top:4px;
    line-height:1.3;
  }

  .dimensionValue.good{
    color:#16a34a;
  }

  .dimensionValue.warning{
    color:#f59e0b;
  }

  .dimensionValue.danger{
    color:#ef4444;
  }

  .channelOverlay{
    position:fixed;
    inset:0;
    background:rgba(15,23,42,.45);
    display:flex;
    align-items:center;
    justify-content:center;
    padding:20px;
    z-index:9999;
  }

  .channelModal{
    width:min(560px, 96vw);
    background:#fff;
    border:1px solid rgba(15,23,42,.08);
    border-radius:22px;
    padding:22px;
    box-shadow:0 30px 90px rgba(15,23,42,.20);
  }

  .channelTitle{
    font-size:22px;
    font-weight:950;
    margin-bottom:8px;
  }

  .channelText{
    color:#64748b;
    font-size:14px;
    line-height:1.45;
  }

  .channelGrid{
    display:grid;
    gap:12px;
    margin-top:18px;
  }

  .channelBtn{
    width:100%;
    border:1px solid rgba(15,23,42,.08);
    background:#f8fafc;
    border-radius:16px;
    padding:16px;
    cursor:pointer;
    text-align:left;
    transition:.18s ease;
  }

  .channelBtn:hover{
    border-color:rgba(47,107,255,.30);
    box-shadow:0 12px 24px rgba(47,107,255,.10);
    background:#fff;
  }

  .channelBtnTitle{
    font-weight:900;
    font-size:15px;
  }

  .channelBtnSub{
    color:#64748b;
    font-size:13px;
    margin-top:4px;
  }

  .channelClose{
    margin-top:14px;
    width:100%;
    border:none;
    background:#e2e8f0;
    color:#0f172a;
    font-weight:900;
    border-radius:14px;
    padding:12px 14px;
    cursor:pointer;
  }

  @media (max-width: 980px){
    .grid{ grid-template-columns:1fr; }
    .right{ min-height:620px; }
  }

  @keyframes auraTilt {
    0%,100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-8px) rotate(-1.2deg); }
  }

  @keyframes auraGlow {
    0%,100% { filter: drop-shadow(0 0 0 rgba(47,107,255,.00)); }
    50% { filter: drop-shadow(0 0 18px rgba(47,107,255,.18)); }
  }

  @keyframes auraTalk {
    0%{ transform: translateY(0) scale(1); }
    35%{ transform: translateY(-4px) scale(1.02); }
    70%{ transform: translateY(0) scale(1); }
    100%{ transform: translateY(-2px) scale(1.01); }
  }

  @keyframes auraCute {
    0%{ transform: rotate(0deg); }
    25%{ transform: rotate(1.2deg); }
    50%{ transform: rotate(0deg); }
    75%{ transform: rotate(-1.2deg); }
    100%{ transform: rotate(0deg); }
  }

  .auraTalking{
    animation:
      auraTilt 3.2s ease-in-out infinite,
      auraGlow 2.8s ease-in-out infinite,
      auraTalk .55s ease-in-out 1 !important;
  }

  .auraCute{
    animation:
      auraTilt 3.2s ease-in-out infinite,
      auraGlow 2.8s ease-in-out infinite,
      auraCute .35s ease-in-out 1 !important;
  }

  @keyframes popIn {
    0%{ transform: scale(.85); opacity:.0; }
    100%{ transform: scale(1); opacity:1; }
  }

  @keyframes bubblePulse {
    0%,100%{ transform: translateY(0); }
    50%{ transform: translateY(-2px); }
  }

  .bubbleTyping{ animation: bubblePulse .9s ease-in-out infinite; }

  @keyframes thinkBounce {
    0%,100%{ transform: translateY(0); }
    50%{ transform: translateY(-3px); }
  }

  .miniThinking{ animation: thinkBounce .9s ease-in-out infinite !important; }
</style>
</head>

<body>
  <div class="frame">
    <div class="grid">

      <div class="left">
        <div class="leftInner">
          <div class="auraBig">
            <div class="auraImg" id="auraBox">
              <img id="auraBig" src="/static/aura_open.png" alt="AURA">
            </div>
          </div>

          <div class="name">AURA</div>
<div class="subtitle">Agent IA • Diagnostic de dépendance business</div>
<div class="tag">Découvre pourquoi ton business dépend encore trop de toi.</div>

<div class="promiseBox">

  <div class="promiseTitle">
    En 2 minutes, AURA va identifier :
  </div>

  <ul class="promiseList">
    <li>pourquoi tu restes encore le point de passage obligé</li>
    <li>où tu perds du temps sans vraiment le voir au quotidien</li>
    <li>quelles zones te rendent encore indispensable aujourd’hui</li>
    <li>ce qui bloque ta capacité à grandir sans augmenter ta charge</li>
  </ul>

  <div class="promiseHighlight">
    👉 L’objectif : voir si ton business peut continuer à avancer… même quand tu ralentis.
  </div>

</div>

<div class="progress"><div id="bar" class="bar"></div></div>

<div style="margin-top:18px;" class="leftTitle">
  💡 Beaucoup découvrent que leur vrai problème n’est pas le manque de temps… mais le fait que tout finit toujours par revenir vers eux.
</div>
</div>
</div>

      <div class="right">
        <div class="chatHeader">
          <div class="chatHeaderLeft">
            <div class="chatHeaderAvatarWrap">
              <img class="chatHeaderAvatar" src="/static/aura_head.png" alt="AURA">
            </div>
            <div class="chatHeaderText">
              <div class="chatHeaderTitle">Salut 👋 Je suis AURA.</div>
              <div class="chatHeaderSub">Je vais t’aider à voir où ton business dépend encore trop de toi… puis te montrer ce que ça bloque vraiment dans ta croissance.</div>
            </div>
          </div>
          <div class="chatHeaderRight">~2 minutes</div>
        </div>

        <div class="chat" id="chat"></div>
        <div class="choices" id="choices"></div>

        <div class="footer" id="footer">
          <div class="cta">Mot clé LinkedIn : <code>diagnostic</code></div>
          <button class="restart" id="restart">Recommencer</button>
        </div>

        <div class="copy" id="copyBox"></div>
      </div>

    </div>
  </div>

<script>
const PROFILE_QUESTIONS = %PROFILE_QUESTIONS_JSON%;
const QUESTIONS = %QUESTIONS_JSON%;
const LINKEDIN_URL = %LINKEDIN_URL_JSON%;
const FACEBOOK_URL = %FACEBOOK_URL_JSON%;
const INSTAGRAM_URL = %INSTAGRAM_URL_JSON%;

let phase = "profile";
let profileStep = 0;
let step = 0;
let profileAnswers = {};
let answers = {};
let locked = false;
let currentQuestionRow = null;
let finalData = null;
let currentLeadId = null;

const TOTAL_STEPS = PROFILE_QUESTIONS.length + QUESTIONS.length;

const chat = document.getElementById("chat");
const choices = document.getElementById("choices");
const bar = document.getElementById("bar");
const restartBtn = document.getElementById("restart");
const copyBox = document.getElementById("copyBox");

const AURA_OPEN = "/static/aura_open.png";
const AURA_BLINK = "/static/aura_blink.png";
const AURA_HEAD = "/static/aura_head.png";

const auraImg = document.getElementById("auraBig");
const auraBox = document.getElementById("auraBox");

function sleep(ms){
  return new Promise(resolve => setTimeout(resolve, ms));
}

function formatEuro(value){
  try{
    return new Intl.NumberFormat("fr-FR").format(value);
  }catch(e){
    return String(value);
  }
}

function setProgress(){
  const done = profileStep + step;
  const pct = Math.round((done / TOTAL_STEPS) * 100);
  bar.style.width = pct + "%";
}

function blink(){
  const img = new Image();
  img.onload = () => {
    auraImg.src = AURA_BLINK;
    setTimeout(() => { auraImg.src = AURA_OPEN; }, 140);
  };
  img.onerror = () => {};
  img.src = AURA_BLINK;
}
setInterval(() => { if (Math.random() < 0.33) blink(); }, 2200);

function playAuraTalk(){
  auraBox.classList.remove("auraTalking");
  void auraBox.offsetWidth;
  auraBox.classList.add("auraTalking");

  if (Math.random() < 0.18){
    auraBox.classList.remove("auraCute");
    void auraBox.offsetWidth;
    auraBox.classList.add("auraCute");
  }

  if (Math.random() < 0.55) blink();
}

function addBotMsg(html, typing=false, extraClass=""){
  const row = document.createElement("div");
  row.className = "row messageAppear";

  const mini = document.createElement("div");
  mini.className = "mini";
  mini.innerHTML = `<img src="${AURA_HEAD}" alt="AURA">`;
  row.appendChild(mini);

  if(typing){
    mini.classList.add("miniThinking");
  }

  const bubble = document.createElement("div");
  bubble.className = `bubble ${extraClass}`;

  if(typing){
    bubble.classList.add("bubbleTyping");
    bubble.innerHTML =
      `<span class="typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </span>`;
  } else {
    bubble.innerHTML = html;
    playAuraTalk();
  }

  row.appendChild(bubble);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;

  return { row, bubble };
}

function renderChoices(q, isProfile=false){
  choices.innerHTML = "";
  const opts = q.options;
  const keys = Object.keys(opts);

  for(const k of keys){
    const btn = document.createElement("button");
    btn.className = "btn";
    const badge = isProfile ? "•" : k;
    btn.innerHTML = `<div class="key">${badge}</div><div>${opts[k]}</div>`;
    btn.onclick = (e) => choose(q.key, k, e.currentTarget, isProfile);
    choices.appendChild(btn);
  }
}

function currentQuestionIndex(){
  return profileStep + step + 1;
}

function totalQuestions(){
  return TOTAL_STEPS;
}

function botAsk(){
  locked = true;
  setProgress();

  const q = phase === "profile" ? PROFILE_QUESTIONS[profileStep] : QUESTIONS[step];

  const reactions = [
    "Voyons ça ensemble 👀",
    "Intéressant 🤔",
    "Ok, prochaine question",
    "Je comprends 👍",
    "Continuons"
  ];
  const r = reactions[Math.floor(Math.random() * reactions.length)];

  if (currentQuestionRow) {
    currentQuestionRow.remove();
    currentQuestionRow = null;
  }

  const msg = addBotMsg("", true);

  setTimeout(() => {
    playAuraTalk();
    setTimeout(() => playAuraTalk(), 180);

    msg.bubble.classList.remove("bubbleTyping");
    msg.bubble.classList.add("bubbleQuestion");
    msg.bubble.innerHTML = `
      <div class="questionTag">Question ${currentQuestionIndex()} / ${totalQuestions()} • ${Math.round((currentQuestionIndex()/totalQuestions())*100)}%</div>
      <div style="margin-bottom:6px;color:#64748b;font-size:13px;">${r}</div>
      <div>${q.prompt}</div>
    `;

    currentQuestionRow = msg.row;
    renderChoices(q, phase === "profile");
    locked = false;
  }, 650);
}

function choose(key, value, btn, isProfile=false){
  if(locked) return;

  btn.classList.add("btnSelected");
  choices.style.pointerEvents = "none";

  if(isProfile){
    profileAnswers[key] = value;
    profileStep += 1;
  } else {
    answers[key] = value;
    step += 1;
  }

  setTimeout(() => {
    if(currentQuestionRow){
      currentQuestionRow.remove();
      currentQuestionRow = null;
    }

    choices.style.pointerEvents = "auto";

    if(phase === "profile" && profileStep >= PROFILE_QUESTIONS.length){
      phase = "quiz";
      botAsk();
      return;
    }

    if(phase === "quiz" && step >= QUESTIONS.length){
      finish();
      return;
    }

    botAsk();
  }, 180);
}

function buildDmText(baseData){
  const repetitive = (document.getElementById("repetitiveInput")?.value || "").trim();

  let extra = "";
  if(repetitive){
    extra = `\n\nCe qui me fait perdre le plus de temps aujourd’hui : ${repetitive}`;
  }

  return `Hello Audrey,

Je viens de faire le diagnostic AURA.

Résultat : mon business dépend encore de moi à ${baseData.dependency_pct}%.

Ce qui ressort surtout :
- ${baseData.top3[0]}
- ${baseData.top3[1]}
- ${baseData.top3[2]}

Aujourd’hui, je vois que mon business repose encore trop sur moi sur les zones critiques.
Ça me coûte entre ${formatEuro(baseData.monthly_loss_min)}€ et ${formatEuro(baseData.monthly_loss_max)}€ par mois en temps, friction et croissance bloquée.${extra}

👉 Est-ce que c’est exactement le type de blocage que tu aides à restructurer ?`;
}

function showCopyPreview(text, isSuccess=false){
  copyBox.style.display = "block";
  copyBox.classList.toggle("success", isSuccess);
  copyBox.textContent = text;
}

function updateCopyBox(){
  if(!finalData) return;
  showCopyPreview(buildDmText(finalData), false);
}

async function saveLeadDetails(contactChannel=null){
  if(!currentLeadId || !finalData) return;

  const repetitive_tasks = (document.getElementById("repetitiveInput")?.value || "").trim();
  const dm_text = buildDmText(finalData);

  await fetch("/save-lead", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      lead_id: currentLeadId,
      activity: null,
      repetitive_tasks,
      tools: null,
      linkedin_clicked: contactChannel === "linkedin",
      dm_text,
      contact_channel: contactChannel
    })
  });
}

function openChannelModal(baseData){
  const existing = document.getElementById("channelOverlay");
  if(existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.className = "channelOverlay";
  overlay.id = "channelOverlay";

  overlay.innerHTML = `
    <div class="channelModal">
      <div class="channelTitle">Choisis où m’envoyer ton message 👇</div>
      <div class="channelText">
        Ton message est copié 👇<br>
        Clique sur le réseau où tu veux me l’envoyer.
      </div>

      <div class="channelGrid">
        <button class="channelBtn" data-channel="linkedin">
          <div class="channelBtnTitle">M'écrire sur LinkedIn</div>
        </button>

        <button class="channelBtn" data-channel="facebook">
          <div class="channelBtnTitle">M'écrire sur Facebook</div>
        </button>

        <button class="channelBtn" data-channel="instagram">
          <div class="channelBtnTitle">M'écrire sur Instagram</div>
        </button>
      </div>

      <button class="channelClose" id="channelCloseBtn">Annuler</button>
    </div>
  `;

  document.body.appendChild(overlay);

  document.getElementById("channelCloseBtn").onclick = () => {
    overlay.remove();
  };

  overlay.querySelectorAll(".channelBtn").forEach(btn => {
    btn.onclick = async () => {
      const channel = btn.dataset.channel;
      const dmText = buildDmText(baseData);

      try{
        await navigator.clipboard.writeText(dmText);
        showCopyPreview("✅ Message copié. Colle-le avec Ctrl+V / Cmd+V sur le réseau choisi.", true);
      }catch(e){
        showCopyPreview(dmText, false);
      }

      await saveLeadDetails(channel);

      let url = LINKEDIN_URL;
      if(channel === "facebook") url = FACEBOOK_URL;
      if(channel === "instagram") url = INSTAGRAM_URL;

      window.open(url, "_blank", "noopener,noreferrer");
      overlay.remove();
    };
  });

  overlay.onclick = (e) => {
    if(e.target === overlay){
      overlay.remove();
    }
  };
}

function renderFinalCTA(baseData){
  const card = document.createElement("div");
  card.className = "resultCard messageAppear";
  card.style.border = "1px solid rgba(47,107,255,.25)";
  card.style.background = "linear-gradient(180deg,#ffffff,#f5f9ff)";

  card.innerHTML = `
    <div style="font-weight:900;font-size:20px;">
      👉 Voilà ce qui pourrait changer dans ton business :
    </div>

    <div class="micro" style="margin-top:10px;">
      • moins de tâches qui reviennent vers toi<br>
      • moins de charge mentale<br>
      • plus de capacité sans augmenter ton temps
    </div>

    <div style="margin-top:12px;font-weight:800;">
      👉 Objectif : te libérer du temps ET débloquer ta croissance
    </div>

    <div style="margin-top:12px;font-weight:800;color:#1f5cff;">
      👉 Si rien ne change, certaines opportunités continueront d’arriver… sans pouvoir être réellement exploitées
    </div>

    <div style="margin-top:14px;padding:12px;border-radius:14px;background:#0f172a;color:#e2e8f0;font-size:13px;">
      ⚠️ 💡 Si ton diagnostic montre un vrai levier d’amélioration, je te dirai exactement où agir en priorité.
    </div>

    <div class="leadForm">
      <div>
        <label for="repetitiveInput">
Quelles tâches te donnent le plus l’impression de tourner en boucle aujourd’hui ?
</label>
        <textarea id="repetitiveInput" class="leadTextarea"
          placeholder="Ex : relances, onboarding, suivi client, DM, WhatsApp, contenu, organisation..."
        ></textarea>
      </div>

      <div style="font-size:12px;color:#64748b;">
        💡 Plus tu es précise, plus mon analyse sera pertinente
      </div>
    </div>

    <div class="resultActions">
      <button class="dmBtn" id="openChannelsBtn" type="button">
        👉 Voir comment supprimer mes points de blocage
      </button>
    </div>

    <div class="micro" style="margin-top:10px;">
      ⏱️ Réponse personnalisée (pas automatisée)
    </div>
  `;

  chat.appendChild(card);
  chat.scrollTop = chat.scrollHeight;

  const repetitiveInput = document.getElementById("repetitiveInput");
  const openChannelsBtn = document.getElementById("openChannelsBtn");

  const syncPreview = async () => {
    updateCopyBox();
    await saveLeadDetails(null);
  };

  repetitiveInput.addEventListener("input", syncPreview);

  openChannelsBtn.onclick = async () => {
    const dmText = buildDmText(baseData);

    try{
      await navigator.clipboard.writeText(dmText);
      showCopyPreview("✅ Message copié. Choisis maintenant où me l’envoyer.", true);
    }catch(e){
      showCopyPreview(dmText, false);
    }

    openChannelModal(baseData);
  };

  updateCopyBox();
}

async function typeTextNode(sourceNode, targetParent, speed){
  const text = sourceNode.textContent || "";
  const textNode = document.createTextNode("");
  targetParent.appendChild(textNode);

  for(let i = 0; i < text.length; i++){
    textNode.textContent += text[i];
    if(i % 3 === 0){
      chat.scrollTop = chat.scrollHeight;
    }
    await sleep(speed);
  }
}

async function typeDomNode(sourceNode, targetParent, speed){
  if(sourceNode.nodeType === Node.TEXT_NODE){
    await typeTextNode(sourceNode, targetParent, speed);
    return;
  }

  if(sourceNode.nodeType !== Node.ELEMENT_NODE){
    return;
  }

  const el = document.createElement(sourceNode.tagName.toLowerCase());

  for(const attr of sourceNode.attributes){
    el.setAttribute(attr.name, attr.value);
  }

  targetParent.appendChild(el);

  for(const child of sourceNode.childNodes){
    await typeDomNode(child, el, speed);
  }
}

async function typeHtmlInto(targetElement, html, speed=16){
  targetElement.innerHTML = "";
  const caret = document.createElement("span");
  caret.className = "typeCaret";

  const template = document.createElement("template");
  template.innerHTML = html.trim();

  for(const node of template.content.childNodes){
    await typeDomNode(node, targetElement, speed);
  }

  targetElement.appendChild(caret);
  chat.scrollTop = chat.scrollHeight;
  await sleep(250);
  caret.remove();
}

async function addBotMsgTyped(html, extraClass="", speed=16){
  const msg = addBotMsg("", false, extraClass);
  await typeHtmlInto(msg.bubble, html, speed);
  return msg;
}

function getDimensionClass(value){
  if (value >= 70) return "danger";
  if (value >= 40) return "warning";
  return "good";
}

function getScoreClass(value){
  if (value >= 70) return "danger";
  if (value >= 40) return "warning";
  return "good";
}

function renderDimensions(dimensions){
  return `
    <div class="dimensionGrid">
      <div class="dimensionItem">
        <div class="dimensionLabel">Acquisition</div>
        <div class="dimensionValue ${getDimensionClass(dimensions.ACQ)}">${dimensions.ACQ}%</div>
        <div class="dimensionHint">Génération & suivi des prospects</div>
      </div>
      <div class="dimensionItem">
        <div class="dimensionLabel">Onboarding</div>
        <div class="dimensionValue ${getDimensionClass(dimensions.ONB)}">${dimensions.ONB}%</div>
        <div class="dimensionHint">Mise en route des clients</div>
      </div>
      <div class="dimensionItem">
        <div class="dimensionLabel">Exécution</div>
        <div class="dimensionValue ${getDimensionClass(dimensions.DEL)}">${dimensions.DEL}%</div>
        <div class="dimensionHint">Production & tâches quotidiennes</div>
      </div>
      <div class="dimensionItem">
        <div class="dimensionLabel">Structuration</div>
        <div class="dimensionValue ${getDimensionClass(dimensions.STR)}">${dimensions.STR}%</div>
        <div class="dimensionHint">Process & organisation interne</div>
      </div>
    </div>
  `;
}

async function finish(){
  locked = true;
  choices.innerHTML = "";
  setProgress();

  if (currentQuestionRow) {
    currentQuestionRow.remove();
    currentQuestionRow = null;
  }

  const loadingMsg = addBotMsg(
    `<div class="loaderWrap">
       <div class="loader"></div>
       <div id="loaderText">Analyse de tes réponses…</div>
     </div>`
  );

  await new Promise(resolve => requestAnimationFrame(resolve));

  const loaderText = loadingMsg.bubble.querySelector("#loaderText");

  const steps = [
    "Analyse de tes réponses…",
    "Détection des priorités…",
    "Calcul de l’impact caché…",
    "Préparation de ton résultat…"
  ];

  let stepIndex = 0;

  const loaderInterval = setInterval(() => {
    stepIndex = Math.min(stepIndex + 1, steps.length - 1);
    loaderText.textContent = steps[stepIndex];
  }, 700);

  const res = await fetch("/result", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      answers,
      profile: profileAnswers
    })
  });

  const data = await res.json();
  finalData = data;
  currentLeadId = data.lead_id;

  await sleep(2400);
  clearInterval(loaderInterval);

  await typeHtmlInto(
    loadingMsg.bubble,
    `
    <div class="scoreHero">
  <div style="font-weight:900;font-size:16px;">Ton business est actuellement limité par toi à :</div>
  <div class="scorePercent ${getScoreClass(data.dependency_pct)}">${data.dependency_pct}%</div>
  <div class="scoreSecondary">
    👉 Concrètement : ton système ne prend pas encore le relais là où il devrait.
  </div>
  <div class="micro" style="margin-top:10px;">
    <b>${data.level}</b> — ${data.subtitle}
  </div>
</div>
`,
14
);

await sleep(600);

await addBotMsgTyped(
  `
  <div class="resultCard messageAppear" style="border:1px solid #fecaca;background:#fff1f2;">
    <div style="font-weight:900;font-size:18px;color:#b91c1c;">
      ⚠️ Ce que cette dépendance te coûte réellement
    </div>

    <div style="margin-top:12px;font-weight:800;">
      ⏱ Tu bloques actuellement entre <b>${data.estimated_min} et ${data.estimated_max} heures par semaine</b>
    </div>

    <div style="margin-top:12px;font-weight:800;">
      📈 Cela peut représenter <b>${data.lost_clients_min} à ${data.lost_clients_max} opportunités supplémentaires par mois</b>
    </div>

    <div class="micro" style="margin-top:6px;">
      prospects, clients potentiels ou demandes que ton système pourrait absorber plus sereinement.
    </div>
  </div>
  `,
  "",
  14
);

await sleep(600);

await addBotMsgTyped(
  `<b>👉 Tes principales zones de dépendance aujourd’hui :</b>${renderDimensions(data.dimension_scores)}<br><br>
   <b>Priorités :</b><br><br>
   1) ${data.top3[0]}<br>
   2) ${data.top3[1]}<br>
   3) ${data.top3[2]}`,
  "",
  14
);

await sleep(600);

await addBotMsgTyped(
  `${data.projection_message}<br><br>
   Aujourd’hui ton diagnostic montre une chose :<br><br>
   ton business avance encore davantage grâce à ta présence que grâce à son système.<br><br>
   Si rien ne change :<br><br>
   • tu resteras le point de passage obligé<br>
   • ta charge continuera d’augmenter<br>
   • ta croissance restera liée à ton temps`,
  "",
  14
);

await sleep(400);
renderFinalCTA(data);

locked = false;
}

function reset(){
  phase = "profile";
  profileStep = 0;
  step = 0;
  profileAnswers = {};
  answers = {};
  locked = false;
  currentQuestionRow = null;
  finalData = null;
  currentLeadId = null;
  chat.innerHTML = "";
  choices.innerHTML = "";
  copyBox.style.display = "none";
  copyBox.classList.remove("success");
  copyBox.textContent = "";
  restartBtn.textContent = "Recommencer";

  botAsk();
}

restartBtn.onclick = reset;
reset();
</script>

</body>
</html>
"""


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def home():
    return (
        HTML
        .replace("%PROFILE_QUESTIONS_JSON%", profile_questions_as_json())
        .replace("%QUESTIONS_JSON%", questions_as_json())
        .replace("%LINKEDIN_URL_JSON%", json.dumps(LINKEDIN_URL))
        .replace("%FACEBOOK_URL_JSON%", json.dumps(FACEBOOK_URL))
        .replace("%INSTAGRAM_URL_JSON%", json.dumps(INSTAGRAM_URL))
    )


@app.post("/result")
async def result(request: Request):
    body = await request.json()
    answers = body.get("answers", {}) or {}
    profile = body.get("profile", {}) or {}

    dimension_scores = compute_dimension_scores(answers, profile)
    dependency_pct = compute_dependency_pct(dimension_scores, profile)
    autonomy_pct = compute_autonomy_pct(dependency_pct)
    score_30 = display_score_30(dependency_pct)
    level, subtitle = level_from_dependency_pct(dependency_pct, profile)
    profile_title, profile_text = dominant_profile(dimension_scores, profile)
    top3 = priorities_from_dimensions(dimension_scores, profile)
    estimated_min, estimated_max = estimate_time_gain(answers, dependency_pct, dimension_scores, profile)
    lost_clients_min, lost_clients_max = estimate_business_opportunities(
    estimated_min,
    estimated_max,
    profile)
    
    projection_message = projection_cta_message(
    answers.get("projection")
)
    summary = summary_message(dependency_pct, profile)
    tension, closing = level_messages(dependency_pct, profile)

    dm_copy = (
        f"Hello Audrey,\n\n"
        f"Je viens de faire le diagnostic AURA.\n\n"
        f"Résultat : mon business dépend encore de moi à {dependency_pct}%.\n\n"
        f"Ce qui ressort surtout :\n"
        f"- {top3[0]}\n"
        f"- {top3[1]}\n"
        f"- {top3[2]}\n\n"
        f"Aujourd’hui, je vois que mon business repose encore trop sur moi sur les zones critiques.\n"
        f"Ça me coûte en temps, friction et croissance bloquée.\n\n"
        f"👉 Est-ce que c’est exactement le type de blocage que tu aides à restructurer ?"
    )

    result_data = {
        "dependency_pct": dependency_pct,
        "autonomy_pct": autonomy_pct,
        "score_pct": dependency_pct,
        "score_display_30": score_30,
        "level": level,
        "subtitle": subtitle,
        "profile_title": profile_title,
        "profile_text": profile_text,
        "dimension_scores": dimension_scores,
        "top3": top3,
        "estimated_min": estimated_min,
        "estimated_max": estimated_max,
        "lost_clients_min": lost_clients_min,
        "lost_clients_max": lost_clients_max,
        "summary": summary,
        "tension": tension,
        "closing": closing,
        "dm_copy": dm_copy,
        "projection_message": projection_message,
        "monthly_loss_min": 0,
        "monthly_loss_max": 0,
    }

    lead_id = create_lead_record(answers, profile, result_data)
    result_data["lead_id"] = lead_id

    return JSONResponse(result_data)


@app.post("/save-lead")
async def save_lead(request: Request):
    body = await request.json()

    lead_id = body.get("lead_id")
    if not lead_id:
        return JSONResponse({"ok": False, "error": "lead_id manquant"}, status_code=400)

    update_lead_details(
        lead_id=int(lead_id),
        activity=body.get("activity"),
        repetitive_tasks=body.get("repetitive_tasks"),
        tools=body.get("tools"),
        linkedin_clicked=bool(body.get("linkedin_clicked")),
        dm_text=body.get("dm_text"),
        contact_channel=body.get("contact_channel"),
    )

    return JSONResponse({"ok": True})


@app.post("/admin/delete-lead/{lead_id}")
def delete_lead(lead_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    return JSONResponse({"ok": True})


@app.post("/admin/delete-all-leads")
def delete_all_leads():
    with get_conn() as conn:
        conn.execute("DELETE FROM leads")
    return JSONResponse({"ok": True})


@app.get("/admin/leads", response_class=HTMLResponse)
def admin_leads():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, updated_at, dependency_pct, autonomy_pct, level, subtitle,
                   profile_title, profile_text, estimated_min, estimated_max,
                   business_type, revenue_band, team_size,
                   activity, repetitive_tasks, tools,
                   linkedin_clicked, top3_json, contact_channel,
                   answers_json, profile_json, dimension_scores_json,
                   monthly_loss_min, monthly_loss_max, lost_clients_min, lost_clients_max
            FROM leads
            ORDER BY id DESC
            """
        ).fetchall()

    cards = []
    for row in rows:
        top3 = safe_json_loads(row["top3_json"]) or []
        answers_html = render_answers_html(row["answers_json"])
        profile_html = render_profile_html(row["profile_json"])
        dimensions_html = render_dimension_scores_html(row["dimension_scores_json"])

        cards.append(f"""
        <div style="
            background:white;
            border:1px solid #e5e7eb;
            border-radius:20px;
            padding:20px;
            margin-bottom:18px;
            box-shadow:0 8px 24px rgba(15,23,42,.06);
        ">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-weight:900;font-size:22px;color:#0f172a;">
                        Lead #{row["id"]} — Dépendance {row["dependency_pct"] or 0}%
                    </div>
                    <div style="color:#64748b;margin-top:6px;font-size:14px;">
                        Créé le : {row["created_at"]}
                    </div>
                    <div style="color:#64748b;font-size:14px;">
                        Mis à jour : {row["updated_at"]}
                    </div>
                </div>

                <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                    <div style="
                        background:#2563eb;
                        color:white;
                        font-weight:800;
                        font-size:13px;
                        padding:8px 12px;
                        border-radius:999px;
                    ">
                        completed
                    </div>

                    <button
                        onclick="deleteLead({row['id']})"
                        style="
                            background:#dc2626;
                            color:white;
                            border:none;
                            font-weight:800;
                            font-size:13px;
                            padding:10px 14px;
                            border-radius:12px;
                            cursor:pointer;
                        "
                    >
                        Supprimer
                    </button>
                </div>
            </div>

            <div style="
                display:grid;
                grid-template-columns:repeat(4,minmax(0,1fr));
                gap:10px;
                margin-top:18px;
            ">
                <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:12px;">
                    <div style="font-size:12px;color:#64748b;font-weight:700;">Autonomie</div>
                    <div style="font-size:24px;font-weight:900;margin-top:4px;">{row["autonomy_pct"] or 0}%</div>
                </div>

                <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:12px;">
                    <div style="font-size:12px;color:#64748b;font-weight:700;">Niveau</div>
                    <div style="font-size:18px;font-weight:900;margin-top:4px;">{row["level"] or "-"}</div>
                </div>

                <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:12px;">
                    <div style="font-size:12px;color:#64748b;font-weight:700;">Temps estimé</div>
                    <div style="font-size:20px;font-weight:900;margin-top:4px;">{row["estimated_min"]} à {row["estimated_max"]}h</div>
                </div>

                <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:12px;">
                    <div style="font-size:12px;color:#64748b;font-weight:700;">Canal choisi</div>
                    <div style="font-size:18px;font-weight:900;margin-top:4px;">{row["contact_channel"] or "-"}</div>
                </div>
            </div>

            <div style="
                display:grid;
                grid-template-columns:repeat(2,minmax(0,1fr));
                gap:10px;
                margin-top:12px;
            ">
                <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:14px;padding:12px;">
                    <div style="font-size:12px;color:#9a3412;font-weight:700;">Coût caché mensuel</div>
                    <div style="font-size:24px;font-weight:900;margin-top:4px;color:#c2410c;">
                        {row["monthly_loss_min"] or 0}€ à {row["monthly_loss_max"] or 0}€
                    </div>
                </div>

                <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;padding:12px;">
                    <div style="font-size:12px;color:#1d4ed8;font-weight:700;">Capacité potentielle perdue</div>
                    <div style="font-size:24px;font-weight:900;margin-top:4px;color:#1d4ed8;">
                        {row["lost_clients_min"] or 0} à {row["lost_clients_max"] or 0} clients
                    </div>
                </div>
            </div>

            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e5e7eb;">
                <div style="font-weight:900;font-size:18px;margin-bottom:8px;">Répartition de la dépendance par zone</div>
                {dimensions_html}
            </div>

            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e5e7eb;">
                <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Synthèse diagnostic</div>
                <div style="margin-bottom:6px;"><b>Profil diagnostic :</b> {row["profile_title"] or "-"}</div>
                <div style="margin-bottom:6px;"><b>Sous-titre :</b> {row["subtitle"] or "-"}</div>
                <div style="line-height:1.5;color:#334155;">{row["profile_text"] or "-"}</div>
            </div>

            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e5e7eb;">
                <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Top 3 priorités</div>
                <div style="line-height:1.7;">
                    {"<br>".join([f"{i+1}) {html.escape(str(item))}" for i, item in enumerate(top3)]) if top3 else "-"}
                </div>
            </div>

            <div style="
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:18px;
                margin-top:18px;
                padding-top:18px;
                border-top:1px solid #e5e7eb;
            ">
                <div>
                    <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Profil répondu</div>
                    <div style="line-height:1.5;">{profile_html}</div>
                </div>

                <div>
                    <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Intention de contact</div>
                    <div style="margin-bottom:6px;"><b>LinkedIn cliqué :</b> {"Oui" if row["linkedin_clicked"] else "Non"}</div>
                    <div style="margin-bottom:6px;"><b>Canal choisi :</b> {row["contact_channel"] or "-"}</div>
                </div>
            </div>

            <div style="
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:18px;
                margin-top:18px;
                padding-top:18px;
                border-top:1px solid #e5e7eb;
            ">
                <div>
                    <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Texte libre saisi</div>
                    <div style="
                        background:#f8fafc;
                        border:1px solid #e5e7eb;
                        border-radius:14px;
                        padding:12px;
                        min-height:90px;
                        white-space:pre-wrap;
                        line-height:1.5;
                    ">{html.escape(row["repetitive_tasks"] or "-")}</div>
                </div>

                <div>
                    <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Infos additionnelles</div>
                    <div style="margin-bottom:6px;"><b>Activité libre :</b> {html.escape(row["activity"] or "-")}</div>
                    <div style="margin-bottom:6px;"><b>Tâches répétitives :</b> {html.escape(row["repetitive_tasks"] or "-")}</div>
                    <div><b>Outils :</b> {html.escape(row["tools"] or "-")}</div>
                </div>
            </div>

            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e5e7eb;">
                <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Réponses détaillées</div>
                <div style="line-height:1.55;">{answers_html}</div>
            </div>
        </div>
        """)

    html_out = f"""
    <!doctype html>
    <html lang="fr">
    <head>
      <meta charset="utf-8"/>
      <title>Leads AURA</title>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
    </head>
    <body style="font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto;background:#f3f4f6;padding:24px;color:#0f172a;">
      <div style="max-width:1200px;margin:0 auto;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:20px;">
          <h1 style="margin:0;font-size:34px;">Leads AURA</h1>

          <button
            onclick="deleteAllLeads()"
            style="
              background:#991b1b;
              color:white;
              border:none;
              font-weight:900;
              font-size:14px;
              padding:12px 16px;
              border-radius:14px;
              cursor:pointer;
            "
          >
            Supprimer tous les leads
          </button>
        </div>

        {''.join(cards) if cards else '<p>Aucun lead pour le moment.</p>'}
      </div>

      <script>
        async function deleteLead(leadId) {{
          const ok = confirm("Supprimer ce lead ?");
          if (!ok) return;

          const res = await fetch(`/admin/delete-lead/${{leadId}}`, {{
            method: "POST"
          }});

          const data = await res.json();
          if (data.ok) {{
            window.location.reload();
          }} else {{
            alert("Erreur pendant la suppression.");
          }}
        }}

        async function deleteAllLeads() {{
          const ok = confirm("Supprimer TOUS les leads ? Cette action est irréversible.");
          if (!ok) return;

          const res = await fetch("/admin/delete-all-leads", {{
            method: "POST"
          }});

          const data = await res.json();
          if (data.ok) {{
            window.location.reload();
          }} else {{
            alert("Erreur pendant la suppression.");
          }}
        }}
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html_out)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)