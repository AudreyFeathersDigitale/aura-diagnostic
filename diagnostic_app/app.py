from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "aura_leads.db"

LINKEDIN_URL = "https://www.linkedin.com/in/audrey-mouton-80b902217/?skipRedirect=true"

# =========================
# 1) SEGMENTATION EN AMONT
# =========================

PROFILE_QUESTIONS = [
    (
        "business_type",
        "Avant de commencer, je personnalise ton diagnostic en 3 questions rapides.<br><br><b>Ton activité principale aujourd’hui ?</b>",
        {
            "freelance": "Freelance / Coach / Consultant",
            "agency": "Agence",
            "info": "Formation / Infoprenariat",
            "saas": "SaaS / Produit digital",
            "ecommerce": "E-commerce",
        },
    ),
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
        "dependance",
        "Si tu arrêtes de travailler pendant <b>1 semaine</b>, ton business continue vraiment… ou certaines choses commencent à bloquer ?",
        {
            "A": "Tout continue sans moi, même les opérations importantes.",
            "B": "Globalement ça tourne, mais quelques tâches s’accumulent.",
            "C": "Certaines choses commencent à bloquer ou ralentir.",
            "D": "Tout dépend de moi, ça s’arrête presque complètement.",
        },
    ),
    (
        "leads",
        "Aujourd’hui, tes prospects arrivent… mais es-tu sûr(e) de pouvoir tous les suivre sans en perdre ou en oublier ?",
        {
            "A": "Oui, tout est centralisé et suivi automatiquement.",
            "B": "J’ai un système, mais je vérifie encore manuellement.",
            "C": "Ils arrivent à plusieurs endroits, je dois jongler.",
            "D": "Je n’ai pas vraiment de système clair.",
        },
    ),
    (
        "onboarding",
        "Quand un client signe, est-ce que tout est fluide… ou dois-tu encore intervenir à chaque étape ?",
        {
            "A": "Tout est automatisé et fluide.",
            "B": "Partiellement automatisé, mais pas partout.",
            "C": "Je dois intervenir régulièrement.",
            "D": "C’est souvent manuel ou improvisé.",
        },
    ),
    (
        "outils",
        "Tu utilises plusieurs outils… mais est-ce qu’ils travaillent vraiment ensemble ou tu fais encore beaucoup de choses à la main ?",
        {
            "A": "Tout est connecté et fonctionne ensemble.",
            "B": "Une partie des outils est connectée.",
            "C": "Peu de connexions, beaucoup de manipulations.",
            "D": "Rien n’est connecté, je gère tout à la main.",
        },
    ),
    (
        "repetitif",
        "Combien de fois par semaine refais-tu les mêmes actions (copier-coller, relances, organisation…) sans automatisation ?",
        {
            "A": "Très rarement.",
            "B": "Quelques fois par semaine.",
            "C": "Très régulièrement.",
            "D": "Tous les jours ou presque.",
        },
    ),
    (
        "process",
        "Si quelqu’un devait reprendre ton business demain, pourrait-il suivre tes process… ou tout est encore dans ta tête ?",
        {
            "A": "Tout est documenté et structuré.",
            "B": "Une partie est documentée.",
            "C": "Très peu de choses sont structurées.",
            "D": "Tout est dans ma tête.",
        },
    ),
    (
        "frein",
        "Aujourd’hui, ton business tourne grâce à un système… ou surtout parce que tu es là pour tout gérer ?",
        {
            "A": "Le système gère la majorité.",
            "B": "Mix entre système et moi.",
            "C": "Principalement moi.",
            "D": "Uniquement moi.",
        },
    ),
    (
        "temps_perdu",
        "Chaque semaine, combien d’heures passes-tu sur des tâches que tu pourrais éviter avec un meilleur système ?",
        {
            "A": "Moins de 2 heures.",
            "B": "2 à 5 heures.",
            "C": "6 à 10 heures.",
            "D": "Plus de 10 heures.",
        },
    ),
    (
        "charge",
        "As-tu parfois l’impression que si tu ralentis un peu, tout peut partir en vrille ?",
        {
            "A": "Non, tout est sous contrôle.",
            "B": "Parfois.",
            "C": "Souvent.",
            "D": "Oui clairement.",
        },
    ),
    (
        "goulot",
        "Si ton business était vraiment bien structuré, qu’est-ce qui ferait le plus de différence pour toi aujourd’hui ?",
        {
            "A": "Pas grand-chose, ça fonctionne déjà bien.",
            "B": "Gagner du temps.",
            "C": "Réduire les tâches manuelles.",
            "D": "Avoir un système qui tourne sans moi.",
        },
    ),
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
    "dependance": {"main": "STR", "secondary": ("DEL", 0.5), "weight": 1.5},
    "leads": {"main": "ACQ", "secondary": ("STR", 0.3), "weight": 1.0},
    "onboarding": {"main": "ONB", "secondary": ("DEL", 0.4), "weight": 1.0},
    "outils": {"main": "DEL", "secondary": ("STR", 0.5), "weight": 1.0},
    "repetitif": {"main": "DEL", "secondary": ("STR", 0.3), "weight": 1.0},
    "process": {"main": "STR", "secondary": ("DEL", 0.4), "weight": 1.5},
    "frein": {"main": "STR", "secondary": ("DEL", 0.5), "weight": 1.5},
    "temps_perdu": {"main": "DEL", "secondary": None, "weight": 1.2},
    "charge": {"main": "STR", "secondary": ("DEL", 0.3), "weight": 1.2},
    "goulot": {"main": "STR", "secondary": None, "weight": 0.4},  # très léger : question de projection
}

PROFILE_WEIGHTS = {
    "freelance": {"ACQ": 1.1, "ONB": 1.2, "DEL": 1.0, "STR": 1.1},
    "agency": {"ACQ": 1.0, "ONB": 1.1, "DEL": 1.1, "STR": 1.3},
    "info": {"ACQ": 1.1, "ONB": 1.0, "DEL": 1.0, "STR": 1.1},
    "saas": {"ACQ": 0.9, "ONB": 1.0, "DEL": 1.1, "STR": 1.2},
    "ecommerce": {"ACQ": 0.9, "ONB": 0.8, "DEL": 1.3, "STR": 1.2},
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

        # Colonnes ajoutées sans casser les bases existantes
        ensure_column(conn, "leads", "profile_json", "TEXT")
        ensure_column(conn, "leads", "business_type", "TEXT")
        ensure_column(conn, "leads", "revenue_band", "TEXT")
        ensure_column(conn, "leads", "team_size", "TEXT")
        ensure_column(conn, "leads", "dependency_pct", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "autonomy_pct", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "dimension_scores_json", "TEXT")


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


def profile_label(profile: dict) -> str:
    business_type = profile.get("business_type", "")
    mapping = {
        "freelance": "freelance / coach / consultant",
        "agency": "agence",
        "info": "infopreneur / formateur",
        "saas": "SaaS / produit digital",
        "ecommerce": "e-commerce",
    }
    return mapping.get(business_type, "entrepreneur")


def get_profile_dimension_weights(profile: dict) -> dict:
    business_type = profile.get("business_type", "freelance")
    return PROFILE_WEIGHTS.get(business_type, PROFILE_WEIGHTS["freelance"])


def compute_dimension_scores(answers: dict, profile: dict) -> dict:
    raw_scores = {"ACQ": 0.0, "ONB": 0.0, "DEL": 0.0, "STR": 0.0}
    raw_max = {"ACQ": 0.0, "ONB": 0.0, "DEL": 0.0, "STR": 0.0}

    for key, _, _ in QUESTIONS:
        answer = answers.get(key, "A")
        score = ANSWER_SCORES.get(answer, 0)
        meta = QUESTION_DIMENSIONS[key]

        main_dim = meta["main"]
        weight = meta["weight"]
        secondary = meta["secondary"]

        raw_scores[main_dim] += score * weight
        raw_max[main_dim] += 3 * weight

        if secondary:
            sec_dim, sec_ratio = secondary
            raw_scores[sec_dim] += score * weight * sec_ratio
            raw_max[sec_dim] += 3 * weight * sec_ratio

    profile_weights = get_profile_dimension_weights(profile)

    final_scores = {}
    for dim in raw_scores:
        weighted_score = raw_scores[dim] * profile_weights.get(dim, 1.0)
        weighted_max = raw_max[dim] * profile_weights.get(dim, 1.0)
        if weighted_max <= 0:
            final_scores[dim] = 0
        else:
            final_scores[dim] = round((weighted_score / weighted_max) * 100)

    return final_scores


def compute_dependency_pct(dimension_scores: dict) -> int:
    return round(sum(dimension_scores.values()) / len(dimension_scores))


def compute_autonomy_pct(dependency_pct: int) -> int:
    return max(0, 100 - dependency_pct)


def level_from_dependency_pct(dependency_pct: int) -> tuple[str, str]:
    if dependency_pct < 25:
        return (
            "Dépendance faible",
            "Base déjà saine, mais certaines zones restent encore trop manuelles ou trop dépendantes de toi.",
        )
    if dependency_pct < 50:
        return (
            "Dépendance modérée",
            "Ton activité tient, mais plusieurs frictions t’obligent encore à rester trop au centre.",
        )
    if dependency_pct < 75:
        return (
            "Dépendance forte",
            "Aujourd’hui, ton business dépend clairement de toi sur plusieurs points clés.",
        )
    return (
        "Dépendance critique",
        "Tu es encore le système principal de ton business. Si tu ralentis, plusieurs choses ralentissent aussi.",
    )


def display_score_30(dependency_pct: int) -> int:
    # score secondaire discret, uniquement si tu veux le garder côté admin / compatibilité
    autonomy = compute_autonomy_pct(dependency_pct)
    return round((autonomy / 100) * 30)


def dominant_profile(dimension_scores: dict) -> tuple[str, str]:
    ordered = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
    main_dim = ordered[0][0]
    second_dim = ordered[1][0]

    if main_dim == "STR":
        return (
            "Ton business repose encore trop sur toi",
            "Le principal problème aujourd’hui, c’est que trop de choses dépendent encore directement de toi pour avancer correctement."
        )

    if main_dim == "DEL":
        return (
            "Tu absorbes encore trop d’opérations manuelles",
            "Ton principal frein aujourd’hui, c’est le volume de tâches répétitives, de manipulations et de suivi opérationnel qui reposent encore sur toi."
        )

    if main_dim == "ONB":
        return (
            "Ton onboarding crée encore trop de friction",
            "Le passage prospect → client n’est pas encore assez fluide, ce qui t’oblige à intervenir plus que nécessaire."
        )

    return (
        "Ton acquisition manque encore de système",
        "Tes opportunités existent, mais leur suivi et leur traitement dépendent encore trop d’une gestion humaine ou dispersée."
    )


def estimate_time_gain(answers: dict, dependency_pct: int, dimension_scores: dict) -> tuple[int, int]:
    if dependency_pct < 25:
        estimate_min, estimate_max = 2, 5
    elif dependency_pct < 50:
        estimate_min, estimate_max = 5, 8
    elif dependency_pct < 75:
        estimate_min, estimate_max = 8, 14
    else:
        estimate_min, estimate_max = 12, 20

    if dimension_scores["DEL"] >= 70:
        estimate_min += 1
        estimate_max += 2

    if dimension_scores["STR"] >= 70:
        estimate_min += 1
        estimate_max += 2

    estimate_max = min(20, estimate_max)
    return estimate_min, estimate_max


def dimension_priority_copy(dim: str, profile: dict) -> str:
    business_type = profile.get("business_type", "freelance")

    if dim == "STR":
        if business_type == "agency":
            return "Formaliser les process et réduire la dépendance au fondateur"
        return "Formaliser les process clés et réduire la dépendance à toi"

    if dim == "DEL":
        if business_type == "ecommerce":
            return "Réduire les tâches manuelles dans l’exécution et le suivi"
        return "Automatiser les tâches répétitives et l’exécution"

    if dim == "ONB":
        return "Fluidifier l’onboarding client"

    return "Structurer le suivi des leads et des relances"


def priorities_from_dimensions(dimension_scores: dict, profile: dict) -> list[str]:
    ordered = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
    top_dims = [dim for dim, _ in ordered[:3]]
    return [dimension_priority_copy(dim, profile) for dim in top_dims]


def summary_message(level: str, dependency_pct: int, profile: dict) -> str:
    label = profile_label(profile)

    if dependency_pct < 25:
        return (
            f"Pour un profil {label} comme le tien, la base est déjà plutôt saine.<br><br>"
            f"👉 Mais il reste encore quelques points où ton business dépend directement de toi."
        )
    if dependency_pct < 50:
        return (
            f"Pour un profil {label} comme le tien, ton business tient déjà sur une base correcte.<br><br>"
            f"👉 Mais plusieurs frictions t’obligent encore à intervenir trop souvent."
        )
    if dependency_pct < 75:
        return (
            f"Pour un profil {label} comme le tien, ton business dépend encore fortement de toi.<br><br>"
            f"👉 Plusieurs zones clés ne sont pas encore assez fluides, documentées ou automatisées."
        )
    return (
        f"Pour un profil {label} comme le tien, tu es encore le système principal de ton business.<br><br>"
        f"👉 Si tu ralentis, plusieurs zones critiques ralentissent avec toi."
    )


def level_messages(dependency_pct: int) -> tuple[str, str]:
    if dependency_pct < 25:
        tension = (
            "👉 Si rien ne change, ton activité restera stable, mais tu laisseras encore des gains faciles de temps et de fluidité sur la table."
        )
        closing = (
            "La bonne nouvelle, c’est qu’avec quelques optimisations ciblées, tu peux encore alléger ton quotidien sans tout reconstruire."
        )
        return tension, closing

    if dependency_pct < 50:
        tension = (
            "👉 Si rien ne change, tu risques de rester bloqué dans une zone intermédiaire : ça fonctionne, mais tu restes trop mobilisé(e) pour faire tourner l’ensemble."
        )
        closing = (
            "La bonne nouvelle, c’est que quelques ajustements bien choisis peuvent déjà te faire récupérer un vrai volume de temps."
        )
        return tension, closing

    if dependency_pct < 75:
        tension = (
            "👉 Si rien ne change, tu vas continuer à absorber chaque semaine des tâches évitables, manuelles ou mal transmises."
        )
        closing = (
            "La bonne nouvelle, c’est que c’est exactement le type de situation qui peut se débloquer rapidement avec les bons systèmes."
        )
        return tension, closing

    tension = (
        "👉 Si rien ne change, ton business restera fortement dépendant de toi : moindre baisse de disponibilité, et plusieurs choses commencent à bloquer."
    )
    closing = (
        "La bonne nouvelle, c’est qu’en traitant les bons points dans le bon ordre, tu peux commencer à reprendre le contrôle très vite."
    )
    return tension, closing


def human_level_label(dependency_pct: int) -> str:
    if dependency_pct < 25:
        return "déjà assez structuré(e), mais encore un peu trop présent(e) sur certains points"
    if dependency_pct < 50:
        return "encore trop au centre de certaines zones de mon business"
    if dependency_pct < 75:
        return "encore fortement au centre de mon business"
    return "encore le système principal de mon business"


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
                dm_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                json.dumps(answers, ensure_ascii=False),
                json.dumps(profile, ensure_ascii=False),
                profile.get("business_type"),
                profile.get("revenue_band"),
                profile.get("team_size"),
                result_data["dependency_pct"],  # compat
                result_data["dependency_pct"],
                result_data["autonomy_pct"],
                result_data["score_display_30"],
                result_data["level"],
                result_data["subtitle"],
                result_data["profile_title"],
                result_data["profile_text"],
                json.dumps(result_data["dimension_scores"], ensure_ascii=False),  # compat
                json.dumps(result_data["dimension_scores"], ensure_ascii=False),
                json.dumps(result_data["top3"], ensure_ascii=False),
                result_data["estimated_min"],
                result_data["estimated_max"],
                result_data["dm_copy"],
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
                dm_text = COALESCE(?, dm_text)
            WHERE id = ?
            """,
            (
                now,
                activity,
                repetitive_tasks,
                tools,
                1 if linkedin_clicked else 0,
                dm_text,
                lead_id,
            ),
        )


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
  }

  .scorePercent{
    font-size:40px;
    font-weight:950;
    line-height:1;
    margin-top:6px;
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
          <div class="subtitle">Agent IA • Diagnostic automatisation</div>
          <div class="tag">Découvre pourquoi ton business dépend encore de toi.</div>

          <div class="promiseBox">
            <div class="promiseTitle">En 2 minutes, AURA te montre :</div>
            <ul class="promiseList">
              <li>où ton business dépend encore trop de toi</li>
              <li>où tu perds du temps chaque semaine</li>
              <li>quoi automatiser en priorité</li>
            </ul>
            <div class="promiseHighlight">+ tu peux recevoir un plan d’automatisation personnalisé à la fin</div>
          </div>

          <div class="progress"><div id="bar" class="bar"></div></div>

          <div style="margin-top:18px;" class="leftTitle">
            💡 En moyenne, les entrepreneurs découvrent 5 à 15 heures perdues chaque semaine.
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
              <div class="chatHeaderSub">Je vais t’aider à voir où ton business dépend encore trop de toi… puis te montrer comment commencer à débloquer ça.</div>
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

function averageHours(baseData){
  return Math.round((baseData.estimated_min + baseData.estimated_max) / 2);
}

function humanLevelLabel(dependencyPct){
  if(dependencyPct < 25) return "déjà assez structuré(e), mais encore un peu trop présent(e) sur certains points";
  if(dependencyPct < 50) return "encore trop au centre de certaines zones de mon business";
  if(dependencyPct < 75) return "encore fortement au centre de mon business";
  return "encore le système principal de mon business";
}

function buildDmText(baseData){
  const activity = (document.getElementById("activityInput")?.value || "").trim();
  const repetitive = (document.getElementById("repetitiveInput")?.value || "").trim();
  const tools = (document.getElementById("toolsInput")?.value || "").trim();

  let extra = "";

  if(activity){
    extra += `\n\nMon activité : ${activity}`;
  }

  if(repetitive){
    extra += `\n\nLes tâches qui me prennent le plus de temps aujourd’hui : ${repetitive}`;
  }

  if(tools){
    extra += `\n\nLes outils que j’utilise déjà : ${tools}`;
  }

  return `Hello Audrey,

Je viens de faire ton diagnostic AURA.

Mon business dépend encore de moi à ${baseData.dependency_pct}%.

Les plus grosses zones de friction qui sont ressorties :
- ${baseData.top3[0]}
- ${baseData.top3[1]}
- ${baseData.top3[2]}

Et visiblement je pourrais récupérer ~${averageHours(baseData)}h/semaine là-dessus 😅${extra}

Tu commencerais par quoi à ma place ?`;
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

async function saveLeadDetails(linkedinClicked=false){
  if(!currentLeadId || !finalData) return;

  const activity = (document.getElementById("activityInput")?.value || "").trim();
  const repetitive_tasks = (document.getElementById("repetitiveInput")?.value || "").trim();
  const tools = (document.getElementById("toolsInput")?.value || "").trim();
  const dm_text = buildDmText(finalData);

  await fetch("/save-lead", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      lead_id: currentLeadId,
      activity,
      repetitive_tasks,
      tools,
      linkedin_clicked: linkedinClicked,
      dm_text
    })
  });
}

function renderFinalCTA(baseData){
  const card = document.createElement("div");
  card.className = "resultCard messageAppear";
  card.innerHTML = `
    <div style="font-weight:900;font-size:18px;">👉 Voir quoi automatiser en priorité (plan personnalisé en 5 actions)</div>
    <div class="micro">Je vais analyser ton cas et te montrer exactement :</div>
    <div class="micro">• quoi automatiser en priorité</div>
    <div class="micro">• quels outils utiliser</div>
    <div class="micro">• dans quel ordre le mettre en place</div>
    <div class="micro" style="margin-top:10px;">👉 pour que tu récupères du temps rapidement</div>

    <div class="leadForm">
      <div>
        <label for="activityInput">Ton activité</label>
        <input id="activityInput" class="leadInput" type="text" placeholder="Ex : coach business, freelance, agence, e-commerce...">
      </div>

      <div>
        <label for="repetitiveInput">Quelles tâches te prennent le plus de temps aujourd’hui ?</label>
        <textarea id="repetitiveInput" class="leadTextarea" placeholder="Ex : relances, onboarding, suivi client, organisation, copier-coller..."></textarea>
      </div>

      <div>
        <label for="toolsInput">Quels outils utilises-tu actuellement pour gérer ton business ?</label>
        <input id="toolsInput" class="leadInput" type="text" placeholder="Ex : Notion, Calendly, Stripe, Gmail, Make, Airtable...">
      </div>
    </div>

    <div class="micro">Je t’envoie un plan clair avec 5 actions concrètes adaptées à ton business.</div>

    <div class="resultActions">
      <a class="dmBtn" id="linkedinBtn" href="${LINKEDIN_URL}" target="_blank" rel="noopener noreferrer">Voir mes 5 actions prioritaires</a>
    </div>
  `;
  chat.appendChild(card);
  chat.scrollTop = chat.scrollHeight;

  const activityInput = document.getElementById("activityInput");
  const repetitiveInput = document.getElementById("repetitiveInput");
  const toolsInput = document.getElementById("toolsInput");
  const linkedinBtn = document.getElementById("linkedinBtn");

  const syncPreview = async () => {
    updateCopyBox();
    await saveLeadDetails(false);
  };

  activityInput.addEventListener("input", syncPreview);
  repetitiveInput.addEventListener("input", syncPreview);
  toolsInput.addEventListener("input", syncPreview);

  linkedinBtn.onclick = async (e) => {
    e.preventDefault();

    const dmText = buildDmText(baseData);

    try{
      await navigator.clipboard.writeText(dmText);
      showCopyPreview("✅ Message copié. LinkedIn s’ouvre dans un nouvel onglet. Colle-le avec Ctrl+V / Cmd+V.", true);
    }catch(e){
      showCopyPreview(dmText, false);
    }

    await saveLeadDetails(true);
    window.open(LINKEDIN_URL, "_blank", "noopener,noreferrer");
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

function renderDimensions(dimensions){
  return `
    <div class="dimensionGrid">
      <div class="dimensionItem">
        <div class="dimensionLabel">Acquisition</div>
        <div class="dimensionValue">${dimensions.ACQ}%</div>
      </div>
      <div class="dimensionItem">
        <div class="dimensionLabel">Onboarding</div>
        <div class="dimensionValue">${dimensions.ONB}%</div>
      </div>
      <div class="dimensionItem">
        <div class="dimensionLabel">Exécution</div>
        <div class="dimensionValue">${dimensions.DEL}%</div>
      </div>
      <div class="dimensionItem">
        <div class="dimensionLabel">Structuration</div>
        <div class="dimensionValue">${dimensions.STR}%</div>
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

  await sleep(2200);
  clearInterval(loaderInterval);

  await typeHtmlInto(
    loadingMsg.bubble,
    `Voici ce que ton diagnostic montre aujourd’hui :<br><br>${data.summary}`,
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `
    <div class="scoreHero">
      <div style="font-weight:900;font-size:16px;">Ton business dépend encore de toi à :</div>
      <div class="scorePercent">${data.dependency_pct}%</div>
      <div class="scoreSecondary">Indice secondaire : ${data.dependency_pct}/100 • Autonomie actuelle estimée : ${data.autonomy_pct}%</div>
      <div class="micro" style="margin-top:10px;"><b>${data.level}</b> — ${data.subtitle}</div>
    </div>
    `,
    "",
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `<b>Répartition de la dépendance par zone :</b>${renderDimensions(data.dimension_scores)}`,
    "",
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `<b>Ton principal blocage aujourd’hui :</b><br>${data.profile_title}<br><br>${data.profile_text}`,
    "",
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `Tu pourrais probablement récupérer entre <b>${data.estimated_min} et ${data.estimated_max} heures par semaine</b> avec les bons systèmes.`,
    "estimateBox",
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `<b>Les 3 zones à traiter en priorité :</b><br>
     1) ${data.top3[0]}<br>
     2) ${data.top3[1]}<br>
     3) ${data.top3[2]}`,
    "",
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `${data.tension}<br><br>${data.closing}<br><br>👉 Je peux te dire précisément par quoi commencer et te préparer un plan clair en 5 actions.`,
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
    )


@app.post("/result")
async def result(request: Request):
    body = await request.json()
    answers = body.get("answers", {})
    profile = body.get("profile", {})

    dimension_scores = compute_dimension_scores(answers, profile)
    dependency_pct = compute_dependency_pct(dimension_scores)
    autonomy_pct = compute_autonomy_pct(dependency_pct)
    score_30 = display_score_30(dependency_pct)
    level, subtitle = level_from_dependency_pct(dependency_pct)
    profile_title, profile_text = dominant_profile(dimension_scores)
    top3 = priorities_from_dimensions(dimension_scores, profile)
    estimated_min, estimated_max = estimate_time_gain(answers, dependency_pct, dimension_scores)
    summary = summary_message(level, dependency_pct, profile)
    tension, closing = level_messages(dependency_pct)

    avg_hours = round((estimated_min + estimated_max) / 2)
    dm_copy = (
        f"Hello Audrey,\n\n"
        f"Je viens de faire ton diagnostic AURA.\n\n"
        f"Mon business dépend encore de moi à {dependency_pct}%.\n\n"
        f"Les plus grosses zones de friction qui sont ressorties :\n"
        f"- {top3[0]}\n"
        f"- {top3[1]}\n"
        f"- {top3[2]}\n\n"
        f"Et visiblement je pourrais récupérer ~{avg_hours}h/semaine là-dessus 😅\n\n"
        f"Tu commencerais par quoi à ma place ?"
    )

    result_data = {
        "dependency_pct": dependency_pct,
        "autonomy_pct": autonomy_pct,
        "score_pct": dependency_pct,      # compat
        "score_display_30": score_30,     # compat / admin
        "level": level,
        "subtitle": subtitle,
        "profile_title": profile_title,
        "profile_text": profile_text,
        "dimension_scores": dimension_scores,
        "top3": top3,
        "estimated_min": estimated_min,
        "estimated_max": estimated_max,
        "summary": summary,
        "tension": tension,
        "closing": closing,
        "dm_copy": dm_copy,
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
    )

    return JSONResponse({"ok": True})


@app.get("/admin/leads", response_class=HTMLResponse)
def admin_leads():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, dependency_pct, autonomy_pct, level, profile_title,
                   estimated_min, estimated_max, business_type, revenue_band, team_size,
                   activity, repetitive_tasks, tools, linkedin_clicked, top3_json
            FROM leads
            ORDER BY id DESC
            """
        ).fetchall()

    cards = []
    for row in rows:
        top3 = json.loads(row["top3_json"]) if row["top3_json"] else []
        cards.append(f"""
        <div style="background:white;border:1px solid #e5e7eb;border-radius:16px;padding:16px;margin-bottom:14px;box-shadow:0 4px 16px rgba(15,23,42,.05);">
            <div style="font-weight:900;font-size:18px;">Lead #{row["id"]} — Dépendance {row["dependency_pct"] or 0}%</div>
            <div style="color:#64748b;margin-top:4px;">{row["created_at"]}</div>

            <div style="margin-top:10px;"><b>Niveau :</b> {row["level"]}</div>
            <div><b>Profil diagnostic :</b> {row["profile_title"]}</div>
            <div><b>Autonomie estimée :</b> {row["autonomy_pct"] or 0}%</div>
            <div><b>Temps estimé :</b> {row["estimated_min"]} à {row["estimated_max"]} h/semaine</div>
            <div><b>Type de business :</b> {row["business_type"] or "-"}</div>
            <div><b>CA mensuel :</b> {row["revenue_band"] or "-"}</div>
            <div><b>Structure :</b> {row["team_size"] or "-"}</div>
            <div><b>LinkedIn cliqué :</b> {"Oui" if row["linkedin_clicked"] else "Non"}</div>

            <div style="margin-top:10px;"><b>Top 3 :</b><br>{"<br>".join(top3) if top3 else "-"}</div>

            <div style="margin-top:10px;"><b>Activité libre :</b> {row["activity"] or "-"}</div>
            <div><b>Tâches répétitives :</b> {row["repetitive_tasks"] or "-"}</div>
            <div><b>Outils :</b> {row["tools"] or "-"}</div>
        </div>
        """)

    html = f"""
    <!doctype html>
    <html lang="fr">
    <head>
      <meta charset="utf-8"/>
      <title>Leads AURA</title>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
    </head>
    <body style="font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto;background:#f3f4f6;padding:24px;color:#0f172a;">
      <div style="max-width:980px;margin:0 auto;">
        <h1 style="margin-bottom:20px;">Leads AURA</h1>
        {''.join(cards) if cards else '<p>Aucun lead pour le moment.</p>'}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)