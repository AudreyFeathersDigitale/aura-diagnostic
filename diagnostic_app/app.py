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
FACEBOOK_URL = "https://www.facebook.com/profile.php?id=61578569620081"
INSTAGRAM_URL = "https://www.instagram.com/business.auto.feathersdigital/"

# =========================
# 1) SEGMENTATION EN AMONT
# =========================

PROFILE_QUESTIONS = [
    (
        "business_type",
        "Avant de commencer, je personnalise ton diagnostic en 3 questions rapides.<br><br><b>Ton activité principale aujourd’hui ?</b>",
        {
            "freelance": "Solopreneur (freelance, coach, consultant)",
            "agency": "Agence",
            "info": "Infopreneur / Formation",
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
    "goulot": {"main": "STR", "secondary": None, "weight": 0.4},
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
        ensure_column(conn, "leads", "profile_json", "TEXT")
        ensure_column(conn, "leads", "business_type", "TEXT")
        ensure_column(conn, "leads", "revenue_band", "TEXT")
        ensure_column(conn, "leads", "team_size", "TEXT")
        ensure_column(conn, "leads", "dependency_pct", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "autonomy_pct", "INTEGER DEFAULT 0")
        ensure_column(conn, "leads", "dimension_scores_json", "TEXT")
        ensure_column(conn, "leads", "contact_channel", "TEXT")


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
        "freelance": "solopreneur",
        "agency": "agence",
        "info": "infopreneur",
        "saas": "business SaaS",
        "ecommerce": "business e-commerce",
    }
    return mapping.get(business_type, "business")


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
        final_scores[dim] = 0 if weighted_max <= 0 else round((weighted_score / weighted_max) * 100)

    return final_scores


def compute_dependency_pct(dimension_scores: dict) -> int:
    return round(sum(dimension_scores.values()) / len(dimension_scores))


def compute_autonomy_pct(dependency_pct: int) -> int:
    return max(0, 100 - dependency_pct)


def level_from_dependency_pct(dependency_pct: int, profile: dict) -> tuple[str, str]:
    business_type = profile.get("business_type", "freelance")

    LEVEL_COPY = {
        "freelance": {
            "low": (
                "Dépendance faible",
                "Ton business est déjà bien structuré, avec une base solide. Mais certaines zones reposent encore sur toi alors qu’elles pourraient déjà tourner sans intervention."
            ),
            "mid": (
                "Dépendance modérée",
                "Ton activité tient, mais plusieurs frictions te ramènent encore régulièrement au centre. Tu as une base, mais tu dois encore intervenir trop souvent pour que tout fonctionne."
            ),
            "high": (
                "Dépendance forte",
                "Ton business repose encore largement sur toi sur plusieurs points clés. Certaines choses fonctionnent, mais dès que tu lèves le pied, des blocages apparaissent."
            ),
            "critical": (
                "Dépendance critique",
                "Ton business fonctionne principalement parce que tu es là. Si tu ralentis, certaines parties ralentissent immédiatement. Et si tu t’arrêtes, une partie de ton activité s’arrête avec toi."
            ),
        },
        "agency": {
            "low": (
                "Dépendance faible",
                "Ton agence a déjà une base saine, mais certaines zones clés remontent encore vers toi alors qu’elles devraient déjà être mieux absorbées par le système ou l’équipe."
            ),
            "mid": (
                "Dépendance modérée",
                "Ton agence tient, mais tu restes encore trop au centre de la coordination, du suivi ou des validations. La structure avance, mais avec encore trop d’aller-retours vers toi."
            ),
            "high": (
                "Dépendance forte",
                "Ton agence repose encore beaucoup sur toi sur des points clés. Dès que la charge monte, une partie de la complexité revient directement sur toi."
            ),
            "critical": (
                "Dépendance critique",
                "Ton agence dépend encore fortement de toi pour tenir la charge, arbitrer et garder la fluidité. Si tu ralentis, une partie du système ralentit immédiatement avec toi."
            ),
        },
        "info": {
            "low": (
                "Dépendance faible",
                "Ton activité de formation est déjà bien posée, mais certaines étapes entre acquisition, vente et delivery dépendent encore trop de toi."
            ),
            "mid": (
                "Dépendance modérée",
                "Ton activité fonctionne, mais plusieurs briques te ramènent encore dans l’opérationnel. Tu as une base, sans encore avoir un système vraiment fluide."
            ),
            "high": (
                "Dépendance forte",
                "Ton business repose encore beaucoup sur toi entre acquisition, vente et exécution. Dès que tu lèves le pied, certaines zones perdent en fluidité."
            ),
            "critical": (
                "Dépendance critique",
                "Ton activité repose encore trop directement sur toi pour fonctionner proprement. Tant que le système n’absorbe pas mieux la charge, tu restes le point de passage obligé."
            ),
        },
        "saas": {
            "low": (
                "Dépendance faible",
                "Ton business SaaS est déjà plutôt robuste, mais certaines frictions opérationnelles continuent encore de dépendre de toi ou d’ajustements manuels."
            ),
            "mid": (
                "Dépendance modérée",
                "Ton système tient, mais plusieurs zones te ramènent encore dans le support, la coordination ou l’exécution. Tu avances, mais avec encore trop de dépendances humaines."
            ),
            "high": (
                "Dépendance forte",
                "Ton business garde encore trop de dépendances opérationnelles sur des zones qui devraient déjà être plus robustes. Dès que tu ralentis, certaines failles deviennent plus visibles."
            ),
            "critical": (
                "Dépendance critique",
                "Ton business dépend encore fortement de ta capacité à compenser les failles du système. Si tu ralentis, plusieurs zones critiques perdent immédiatement en fiabilité."
            ),
        },
        "ecommerce": {
            "low": (
                "Dépendance faible",
                "Ton activité e-commerce est déjà assez saine, mais certaines frictions d’exécution, de suivi ou de coordination reposent encore trop sur toi."
            ),
            "mid": (
                "Dépendance modérée",
                "Les ventes tournent, mais plusieurs opérations te ramènent encore au centre. Tu avances, mais avec une charge évitable qui reste trop présente."
            ),
            "high": (
                "Dépendance forte",
                "Ton e-commerce repose encore beaucoup sur toi sur plusieurs points clés. Certaines choses avancent, mais trop d’actions dépendent encore de ton attention directe."
            ),
            "critical": (
                "Dépendance critique",
                "Ton activité e-commerce reste trop sensible à ta présence dans l’exécution, le suivi et les points de friction quotidiens. Si tu ralentis, plusieurs zones deviennent vite fragiles."
            ),
        },
    }

    copy = LEVEL_COPY.get(business_type, LEVEL_COPY["freelance"])

    if dependency_pct < 25:
        return copy["low"]
    if dependency_pct < 50:
        return copy["mid"]
    if dependency_pct < 75:
        return copy["high"]
    return copy["critical"]


def display_score_30(dependency_pct: int) -> int:
    autonomy = compute_autonomy_pct(dependency_pct)
    return round((autonomy / 100) * 30)


def business_summary_intro(profile: dict) -> str:
    business_type = profile.get("business_type", "freelance")
    mapping = {
        "freelance": "Pour un solopreneur comme toi",
        "agency": "Pour une agence comme la tienne",
        "info": "Pour un business de formation comme le tien",
        "saas": "Pour un business SaaS comme le tien",
        "ecommerce": "Pour un business e-commerce comme le tien",
    }
    return mapping.get(business_type, "Pour ton business")


def summary_message(dependency_pct: int, profile: dict) -> str:
    intro = business_summary_intro(profile)
    business_type = profile.get("business_type", "freelance")

    if business_type == "freelance":
        if dependency_pct < 25:
            return (
                f"{intro}, la base est déjà saine.<br><br>"
                f"👉 Mais ton activité avance encore partiellement grâce à toi, là où ton système devrait déjà prendre le relais."
            )
        if dependency_pct < 50:
            return (
                f"{intro}, ton business fonctionne… mais il repose encore beaucoup sur toi.<br><br>"
                f"👉 Tu compenses encore plusieurs zones à la main, ce qui crée une charge invisible qui revient chaque semaine."
            )
        if dependency_pct < 75:
            return (
                f"{intro}, ton business avance encore principalement grâce à toi.<br><br>"
                f"👉 Tu es la personne qui relance, organise, débloque et fait tourner le système au quotidien."
            )
        return (
            f"{intro}, tu es encore le système principal de ton business.<br><br>"
            f"👉 Sans toi, plusieurs zones critiques ralentissent immédiatement, se bloquent… ou deviennent instables très vite."
        )

    if business_type == "agency":
        if dependency_pct < 25:
            return (
                f"{intro}, la structure est déjà plus saine que la moyenne.<br><br>"
                f"👉 Mais certaines zones clés remontent encore jusqu’à toi alors qu’elles devraient être absorbées par le système ou l’équipe."
            )
        if dependency_pct < 50:
            return (
                f"{intro}, ton activité tient… mais elle repose encore trop sur ta supervision directe.<br><br>"
                f"👉 Validation, arbitrage, suivi, organisation : trop de choses passent encore par toi."
            )
        if dependency_pct < 75:
            return (
                f"{intro}, ta croissance continue de créer de la complexité… et cette complexité revient encore trop souvent sur toi.<br><br>"
                f"👉 Tant que tu restes ce point de passage central, ton agence avance, mais elle ne se fluidifie pas vraiment."
            )
        return (
            f"{intro}, tu restes encore le centre de gravité opérationnel de la structure.<br><br>"
            f"👉 Si tu ralentis, une partie du suivi, des validations et de la fluidité interne ralentit avec toi."
        )

    if business_type == "info":
        if dependency_pct < 25:
            return (
                f"{intro}, les bases existent déjà.<br><br>"
                f"👉 Mais certaines étapes entre acquisition, vente et delivery reposent encore inutilement sur toi."
            )
        if dependency_pct < 50:
            return (
                f"{intro}, ton activité fonctionne, mais plusieurs briques demandent encore ton intervention directe.<br><br>"
                f"👉 Résultat : tu restes encore trop présent(e) dans des étapes qui devraient déjà être fluides."
            )
        if dependency_pct < 75:
            return (
                f"{intro}, ton système n’absorbe pas encore assez la charge entre acquisition, vente et exécution.<br><br>"
                f"👉 Tu continues à porter trop d’étapes manuellement, ce qui limite ton effet de levier."
            )
        return (
            f"{intro}, trop de choses reposent encore directement sur toi pour fonctionner proprement.<br><br>"
            f"👉 Tant que ce système n’est pas plus robuste, tu restes le point de passage obligé sur plusieurs zones."
        )

    if business_type == "saas":
        if dependency_pct < 25:
            return (
                f"{intro}, le système semble déjà plus robuste que la moyenne.<br><br>"
                f"👉 Mais certaines frictions opérationnelles continuent encore de dépendre de toi ou de traitements manuels."
            )
        if dependency_pct < 50:
            return (
                f"{intro}, ton produit existe, mais certaines zones de support, d’exécution ou de coordination restent encore trop humaines.<br><br>"
                f"👉 Ça te fait perdre de l’effet de levier là où le système devrait déjà être plus solide."
            )
        if dependency_pct < 75:
            return (
                f"{intro}, ton business garde encore trop de dépendances opérationnelles sur des points qui devraient déjà être fluides.<br><br>"
                f"👉 Le risque n’est pas seulement la perte de temps : c’est un manque de robustesse qui limite ta scalabilité."
            )
        return (
            f"{intro}, tu restes encore un point de compensation majeur dans le fonctionnement global.<br><br>"
            f"👉 Tant que certaines zones critiques ne sont pas mieux structurées, ton effet de levier reste artificiellement limité."
        )

    # ecommerce
    if dependency_pct < 25:
        return (
            f"{intro}, la machine tourne déjà mieux que la moyenne.<br><br>"
            f"👉 Mais certaines frictions d’exécution et de suivi dépendent encore trop de ton attention."
        )
    if dependency_pct < 50:
        return (
            f"{intro}, les ventes tournent, mais plusieurs opérations restent encore trop manuelles.<br><br>"
            f"👉 Tu compenses encore des zones qui devraient déjà être plus fluides, plus connectées et moins chronophages."
        )
    if dependency_pct < 75:
        return (
            f"{intro}, trop de tâches d’exécution, de suivi ou de coordination reposent encore sur des manipulations évitables.<br><br>"
            f"👉 Tu laisses du temps, de la marge et de la sérénité sur la table."
        )
    return (
        f"{intro}, ton activité absorbe encore trop d’opérations manuelles pour rester sereine sans toi.<br><br>"
        f"👉 Si tu ralentis, plusieurs points de friction remontent immédiatement au lieu d’être absorbés par le système."
    )


def dominant_profile(dimension_scores: dict, profile: dict) -> tuple[str, str]:
    main_dim = max(dimension_scores, key=dimension_scores.get)
    business_type = profile.get("business_type", "freelance")

    COPY = {
        "freelance": {
            "STR": (
                "Ton business repose encore trop sur toi",
                "En tant que solopreneur, le vrai problème n’est pas que ton business ne tourne pas. "
                "C’est qu’il tourne encore trop parce que tu es là pour compenser, organiser, relancer ou débloquer. "
                "Tant que cette dépendance reste forte, tu continues à porter une charge que ton système devrait déjà absorber à ta place."
            ),
            "DEL": (
                "Tu absorbes encore trop d’opérationnel à la main",
                "Ton principal frein aujourd’hui, c’est le volume de tâches répétitives, de suivi et de micro-actions qui reposent encore sur toi. "
                "Ça te fait avancer, mais au prix d’un temps et d’une énergie que tu ne récupères jamais vraiment."
            ),
            "ONB": (
                "Ton onboarding crée encore trop de friction",
                "Dès qu’un client arrive, tu dois encore trop intervenir pour faire avancer les étapes. "
                "Résultat : chaque nouvelle vente recrée une charge au lieu d’alimenter un système déjà fluide."
            ),
            "ACQ": (
                "Ton acquisition te fait perdre des opportunités chaque semaine",
                "Tu perds du temps… et parfois des prospects. "
                "Quand les relances, le tri ou l’organisation ne sont pas assez systématisés, tu perds du temps… et parfois des prospects."
            ),
        },
        "agency": {
            "STR": (
                "Ton agence dépend encore trop de toi pour rester fluide",
                "Trop de choses remontent encore jusqu’à toi : validation, suivi, arbitrage, organisation. "
                "Tant que tu restes ce point de passage central, ta structure peut avancer, mais elle ne peut pas vraiment se fluidifier ni grandir sans te charger davantage."
            ),
            "DEL": (
                "L’exécution crée encore trop de charge dans ton agence",
                "Ton principal frein aujourd’hui, c’est que l’opérationnel n’absorbe pas encore assez la complexité. "
                "Quand trop de suivi, de coordination ou de micro-décisions restent manuels, la charge revient mécaniquement sur toi."
            ),
            "ONB": (
                "Ton onboarding client manque encore de système",
                "Le démarrage client devrait poser du cadre et créer de la fluidité. "
                "Quand ce n’est pas assez structuré, ça génère du flou, des allers-retours et une dépendance inutile à ton intervention."
            ),
            "ACQ": (
                "Ton pipeline commercial manque encore de système",
                "Les opportunités existent, mais leur traitement n’est pas encore assez robuste. "
                "Quand le suivi commercial dépend trop de vérifications humaines, tu crées de la friction là où tu devrais créer de la prévisibilité."
            ),
        },
        "info": {
            "STR": (
                "Ton activité repose encore trop sur toi",
                "Même si certaines briques existent déjà, trop d’étapes entre acquisition, vente et delivery demandent encore ton intervention directe. "
                "Tant que le système n’absorbe pas mieux cette charge, tu restes le moteur là où tu devrais être davantage en surplomb."
            ),
            "DEL": (
                "Tu gères encore trop de delivery à la main",
                "Le vrai problème n’est pas seulement le volume de tâches. "
                "C’est que des étapes répétitives ou prévisibles demandent encore de ton temps alors qu’elles devraient déjà être mieux cadrées ou automatisées."
            ),
            "ONB": (
                "Ton onboarding n’est pas encore assez fluide",
                "Le passage entre vente et mise en route devrait être presque évident. "
                "Quand il dépend encore trop de toi, chaque nouveau client ou membre recrée de la charge au lieu d’entrer dans un système propre."
            ),
            "ACQ": (
                "Ton acquisition manque encore de fluidité",
                "Tes entrées existent, mais le suivi de ces opportunités repose encore trop sur des actions humaines dispersées. "
                "Ça ralentit ton système et t’oblige à rester plus présent(e) que nécessaire."
            ),
        },
        "saas": {
            "STR": (
                "Ton business manque encore de robustesse opérationnelle",
                "Même avec un produit digital, certaines zones critiques reposent encore trop sur toi ou sur des ajustements manuels. "
                "Tant que cette dépendance reste là, ton effet de levier reste inférieur à ce qu’il devrait être."
            ),
            "DEL": (
                "Trop de frictions opérationnelles restent encore manuelles",
                "Support, suivi, exécution, coordination : trop d’éléments ne sont pas encore assez absorbés par le système. "
                "Le risque, ce n’est pas seulement la perte de temps : c’est un manque de robustesse qui freine ta scalabilité."
            ),
            "ONB": (
                "Ton onboarding n’est pas encore assez robuste",
                "L’entrée utilisateur ou client devrait être fluide et fiable. "
                "Quand elle dépend encore trop d’interventions ou de corrections humaines, tu perds de l’effet de levier là où le système devrait déjà être stable."
            ),
            "ACQ": (
                "Ton acquisition manque encore de système",
                "Le traitement des opportunités n’est pas encore assez fluide ou assez structuré. "
                "Quand le suivi repose trop sur de l’humain, tu limites la vitesse et la prévisibilité de ton moteur commercial."
            ),
        },
        "ecommerce": {
            "STR": (
                "Ton activité e-commerce dépend encore trop de toi",
                "Même si les ventes tournent, trop de points de suivi, de coordination ou de contrôle remontent encore jusqu’à toi. "
                "Tant que ça fonctionne comme ça, tu restes plus opérateur que pilote."
            ),
            "DEL": (
                "Tu absorbes encore trop de tâches manuelles dans l’exécution",
                "Ton principal frein aujourd’hui, c’est le volume d’opérations évitables dans l’exécution et le suivi. "
                "Tu laisses du temps, de la marge et de la sérénité sur la table à cause de frictions qui devraient déjà être mieux absorbées."
            ),
            "ONB": (
                "Tes flux de mise en route et de traitement manquent encore de fluidité",
                "Quand les entrées, le traitement ou certaines étapes amont demandent encore trop de vérifications ou d’actions humaines, tu crées une dépendance inutile à ton attention."
            ),
            "ACQ": (
                "Ton acquisition n’est pas encore assez cadrée",
                "Les opportunités existent, mais leur organisation et leur suivi ne sont pas encore assez fiables. "
                "Quand le système n’absorbe pas bien la captation et le suivi, tu perds à la fois du temps et de la visibilité."
            ),
        },
    }

    return COPY.get(business_type, COPY["freelance"]).get(main_dim, COPY["freelance"]["STR"])


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
        if business_type == "saas":
            return "Renforcer la robustesse du système sur les zones encore trop dépendantes de toi"
        return "Formaliser les process clés et réduire la dépendance à toi"

    if dim == "DEL":
        if business_type == "ecommerce":
            return "Réduire les tâches manuelles dans l’exécution et le suivi"
        if business_type == "agency":
            return "Fluidifier l’exécution et limiter les remontées opérationnelles"
        return "Automatiser les tâches répétitives et l’exécution"

    if dim == "ONB":
        return "Fluidifier l’onboarding"

    return "Structurer le suivi des leads et des relances"


def priorities_from_dimensions(dimension_scores: dict, profile: dict) -> list[str]:
    ordered = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
    return [dimension_priority_copy(dim, profile) for dim, _ in ordered[:3]]


def level_messages(dependency_pct: int, profile: dict) -> tuple[str, str]:
    business_type = profile.get("business_type", "freelance")

    COPY = {
        "freelance": {
            "low": (
                "👉 Si rien ne change, ton activité restera stable… mais tu continueras quand même à porter une partie de la charge que ton système pourrait déjà absorber.",
                "La bonne nouvelle, c’est qu’avec quelques optimisations ciblées, tu peux te libérer encore plus sans alourdir ta structure."
            ),
            "mid": (
                "👉 Si rien ne change, tu risques de rester coincé(e) dans une zone intermédiaire : ton business tourne, mais encore trop grâce à ta présence directe.",
                "La bonne nouvelle, c’est que quelques bons ajustements peuvent déjà te faire récupérer un vrai volume de temps."
            ),
            "high": (
                "👉 Si rien ne change, tu vas continuer à absorber chaque semaine des relances, de l’organisation et des micro-décisions qui ne devraient plus dépendre de toi.",
                "La bonne nouvelle, c’est que c’est exactement le type de situation qui peut se débloquer rapidement avec les bons systèmes."
            ),
            "critical": (
                "👉 Si rien ne change, ton business restera directement accroché à ton niveau de disponibilité. Dès que tu ralentis, plusieurs choses commencent à se tendre.",
                "La bonne nouvelle, c’est qu’en traitant les bons points dans le bon ordre, tu peux reprendre le contrôle beaucoup plus vite que tu ne le penses."
            ),
        },
        "agency": {
            "low": (
                "👉 Si rien ne change, la structure continuera à avancer… mais une partie de la complexité reviendra encore inutilement sur toi.",
                "La bonne nouvelle, c’est qu’avec quelques ajustements ciblés, tu peux alléger fortement la charge de supervision."
            ),
            "mid": (
                "👉 Si rien ne change, tu risques de rester l’arbitre permanent de trop de sujets : validation, suivi, coordination, organisation.",
                "La bonne nouvelle, c’est qu’en renforçant les bons points, tu peux créer beaucoup plus de fluidité sans tout reconstruire."
            ),
            "high": (
                "👉 Si rien ne change, chaque palier de croissance continuera à créer plus de complexité… et cette complexité reviendra encore trop souvent sur toi.",
                "La bonne nouvelle, c’est qu’une meilleure structuration peut rapidement casser cette mécanique."
            ),
            "critical": (
                "👉 Si rien ne change, ton agence continuera à dépendre trop fortement de toi pour tenir proprement la charge, les validations et la fluidité interne.",
                "La bonne nouvelle, c’est qu’en traitant les bons goulots maintenant, tu peux éviter que la croissance te coûte encore plus cher en énergie."
            ),
        },
        "info": {
            "low": (
                "👉 Si rien ne change, ton activité restera stable, mais tu continueras quand même à intervenir sur des étapes qui devraient déjà être plus fluides.",
                "La bonne nouvelle, c’est que quelques optimisations peuvent encore renforcer ton effet de levier."
            ),
            "mid": (
                "👉 Si rien ne change, tu vas rester trop présent(e) entre acquisition, vente et delivery, là où ton système devrait déjà mieux relier les briques.",
                "La bonne nouvelle, c’est que les gains ici sont souvent rapides dès qu’on traite les bons points."
            ),
            "high": (
                "👉 Si rien ne change, tu continueras à porter manuellement des étapes qui grignotent ton temps sans réelle valeur ajoutée.",
                "La bonne nouvelle, c’est qu’un meilleur système peut vite transformer cette charge en fluidité."
            ),
            "critical": (
                "👉 Si rien ne change, ton activité restera trop dépendante de toi pour absorber proprement l’acquisition, la vente et l’exécution.",
                "La bonne nouvelle, c’est qu’une fois les bons points corrigés, ton système peut enfin commencer à respirer sans toi."
            ),
        },
        "saas": {
            "low": (
                "👉 Si rien ne change, ton système restera globalement stable, mais tu laisseras encore du levier sur la table sur des zones qui pourraient être plus robustes.",
                "La bonne nouvelle, c’est qu’avec quelques optimisations, tu peux encore renforcer la scalabilité réelle du business."
            ),
            "mid": (
                "👉 Si rien ne change, tu risques de garder des dépendances humaines sur des points qui devraient déjà être plus robustes et plus prévisibles.",
                "La bonne nouvelle, c’est que traiter ces zones améliore vite l’effet de levier global."
            ),
            "high": (
                "👉 Si rien ne change, certaines frictions opérationnelles continueront à limiter ta scalabilité bien plus que ton produit lui-même.",
                "La bonne nouvelle, c’est qu’en renforçant la structure, tu peux récupérer à la fois du temps et de la robustesse."
            ),
            "critical": (
                "👉 Si rien ne change, ton business continuera à dépendre trop fortement de ta capacité à compenser les failles du système.",
                "La bonne nouvelle, c’est qu’une fois ces points corrigés, ton effet de levier peut changer de niveau."
            ),
        },
        "ecommerce": {
            "low": (
                "👉 Si rien ne change, l’activité restera globalement stable, mais certaines frictions de suivi ou d’exécution continueront à te consommer inutilement.",
                "La bonne nouvelle, c’est qu’il y a encore des gains rapides à aller chercher sans tout remettre à plat."
            ),
            "mid": (
                "👉 Si rien ne change, tu vas continuer à compenser des zones d’exécution qui devraient déjà être plus fluides et mieux connectées.",
                "La bonne nouvelle, c’est que les gains ici sont souvent très concrets dès qu’on traite les bons flux."
            ),
            "high": (
                "👉 Si rien ne change, tu continueras à perdre du temps, de la marge et de la sérénité sur des opérations qui ne devraient plus dépendre autant de toi.",
                "La bonne nouvelle, c’est qu’un meilleur système peut rapidement alléger cette pression."
            ),
            "critical": (
                "👉 Si rien ne change, ton activité e-commerce restera trop sensible à ta présence sur l’exécution, le suivi et les points de friction quotidiens.",
                "La bonne nouvelle, c’est qu’en corrigeant les bonnes zones, tu peux vite reprendre de l’air."
            ),
        },
    }

    profile_copy = COPY.get(business_type, COPY["freelance"])

    if dependency_pct < 25:
        return profile_copy["low"]
    if dependency_pct < 50:
        return profile_copy["mid"]
    if dependency_pct < 75:
        return profile_copy["high"]
    return profile_copy["critical"]


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
                result_data["dependency_pct"],
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
    font-size:40px;
    font-weight:950;
    line-height:1;
    margin-top:6px;
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

function buildDmText(baseData){
  const repetitive = (document.getElementById("repetitiveInput")?.value || "").trim();

  let extra = "";

  if(repetitive){
    extra += `\n\nCe qui me fait perdre le plus de temps : ${repetitive}`;
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

async function saveLeadDetails(contactChannel=null){
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
          <div class="channelBtnTitle">M'écrir sur LinkedIn</div>
           </button>

        <button class="channelBtn" data-channel="facebook">
          <div class="channelBtnTitle">M'écrir sur Facebook</div>
        </button>

        <button class="channelBtn" data-channel="instagram">
          <div class="channelBtnTitle">M'écrir sur Instagram</div>
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
  card.innerHTML = `
    <div style="font-weight:900;font-size:18px;">
      👉 Voir exactement quoi automatiser en priorité
    </div>

    <div class="micro" style="margin-top:6px;">
      Je vais analyser ton cas et te donner un plan clair en 5 actions :
    </div>

    <div class="micro">• quoi automatiser en premier</div>
    <div class="micro">• avec quels outils</div>
    <div class="micro">• dans quel ordre le faire</div>

    <div class="micro" style="margin-top:10px;">
      ⏱️ Réponse personnalisée directement sur le réseau de ton choix
    </div>

    <div class="leadForm">
      <div>
        <label for="repetitiveInput">
          Qu’est-ce qui te fait perdre le plus de temps aujourd’hui ?
        </label>
        <textarea id="repetitiveInput" class="leadTextarea"
          placeholder="Ex : relances, onboarding, suivi client, organisation, copier-coller..."
        ></textarea>
      </div>

      <div style="font-size:12px;color:#64748b;">
        (Optionnel — plus tu es précis, plus le plan sera utile)
        <br>⚡ <b>Réponse personnalisée (pas automatique)</b>
      </div>
    </div>

    <div class="resultActions">
      <button class="dmBtn" id="openChannelsBtn" type="button">
        👉 M'envoyer mon plan personnalisé
      </button>
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
    `Voilà ce qui te ralentit aujourd’hui :<br><br>${data.summary}`,
    14
  );

  await sleep(650);

  await addBotMsgTyped(
    `
    <div class="scoreHero">
      <div style="font-weight:900;font-size:16px;">Ton business dépend encore de toi à :</div>
      <div class="scorePercent ${getScoreClass(data.dependency_pct)}">${data.dependency_pct}%</div>
      <div class="scoreSecondary">Autonomie actuelle estimée : ${data.autonomy_pct}%</div>
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
    `Aujourd’hui, tu pourrais récupérer entre <b>${data.estimated_min} et ${data.estimated_max} heures par semaine</b> avec les bons systèmes.`,
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
    `${data.tension}<br><br>${data.closing}<br><br>👉 Concrètement :<br><br>si tu règles ces 3 points,<br>ton business peut commencer à tourner sans toi sur plusieurs zones.<br><br>Et surtout :<br>tu récupères du temps…<br>sans ralentir ta croissance.`,
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
    answers = body.get("answers", {})
    profile = body.get("profile", {})

    dimension_scores = compute_dimension_scores(answers, profile)
    dependency_pct = compute_dependency_pct(dimension_scores)
    autonomy_pct = compute_autonomy_pct(dependency_pct)
    score_30 = display_score_30(dependency_pct)
    level, subtitle = level_from_dependency_pct(dependency_pct, profile)
    profile_title, profile_text = dominant_profile(dimension_scores, profile)
    top3 = priorities_from_dimensions(dimension_scores, profile)
    estimated_min, estimated_max = estimate_time_gain(answers, dependency_pct, dimension_scores)
    summary = summary_message(dependency_pct, profile)
    tension, closing = level_messages(dependency_pct, profile)

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
        contact_channel=body.get("contact_channel"),
    )

    return JSONResponse({"ok": True})


def render_dimension_scores_html(result_json: str | None, dimension_scores_json: str | None) -> str:
    result_data = safe_json_loads(result_json)
    dimensions = result_data.get("dimension_scores") if result_data else None

    if not dimensions and dimension_scores_json:
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

@app.get("/admin/leads", response_class=HTMLResponse)
def admin_leads():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, updated_at, dependency_pct, autonomy_pct, level, subtitle,
                   profile_title, profile_text, estimated_min, estimated_max,
                   business_type, revenue_band, team_size,
                   activity, repetitive_tasks, free_text, tools,
                   linkedin_clicked, top3_json, contact_channel,
                   answers_json, profile_json, result_json, status,
                   contact_opened_at, contact_clicked_at,
                   dimension_scores_json
            FROM leads
            ORDER BY id DESC
            """
        ).fetchall()

    cards = []
    for row in rows:
        top3 = json.loads(row["top3_json"]) if row["top3_json"] else []
        answers_html = render_answers_html(row["answers_json"])
        profile_html = render_profile_html(row["profile_json"])
        dimensions_html = render_dimension_scores_html(
            row["result_json"],
            row["dimension_scores_json"]
        )

        status_color = "#2563eb"
        if row["status"] == "contact_clicked":
            status_color = "#16a34a"
        elif row["status"] == "cta_opened":
            status_color = "#f59e0b"
        elif row["status"] == "completed":
            status_color = "#64748b"

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

                <div style="
                    background:{status_color};
                    color:white;
                    font-weight:800;
                    font-size:13px;
                    padding:8px 12px;
                    border-radius:999px;
                ">
                    {row["status"] or "completed"}
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
                    {"<br>".join([f"{i+1}) {item}" for i, item in enumerate(top3)]) if top3 else "-"}
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
                    <div style="margin-bottom:6px;"><b>Modale ouverte le :</b> {row["contact_opened_at"] or "-"}</div>
                    <div><b>Canal cliqué le :</b> {row["contact_clicked_at"] or "-"}</div>
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
                    ">{row["free_text"] or "-"}</div>
                </div>

                <div>
                    <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Infos additionnelles</div>
                    <div style="margin-bottom:6px;"><b>Activité libre :</b> {row["activity"] or "-"}</div>
                    <div style="margin-bottom:6px;"><b>Tâches répétitives :</b> {row["repetitive_tasks"] or "-"}</div>
                    <div><b>Outils :</b> {row["tools"] or "-"}</div>
                </div>
            </div>

            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e5e7eb;">
                <div style="font-weight:900;font-size:18px;margin-bottom:10px;">Réponses détaillées</div>
                <div style="line-height:1.55;">{answers_html}</div>
            </div>
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
      <div style="max-width:1200px;margin:0 auto;">
        <h1 style="margin-bottom:20px;font-size:34px;">Leads AURA</h1>
        {''.join(cards) if cards else '<p>Aucun lead pour le moment.</p>'}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)