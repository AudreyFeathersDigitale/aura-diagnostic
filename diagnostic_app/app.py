from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

LINKEDIN_URL = "https://www.linkedin.com/in/audrey-mouton-80b902217/?skipRedirect=true"

# Scoring inversé
# A = très bien / sain
# D = critique / douloureux
WEIGHTS = {"A": 3, "B": 2, "C": 1, "D": 0}

QUESTIONS = [
    (
        "dependance",
        "Si vous arrêtez de travailler pendant <b>1 semaine</b>, votre business continue vraiment… ou certaines choses commencent à bloquer ?",
        {
            "A": "Tout continue sans moi, même les opérations importantes.",
            "B": "Globalement ça tourne, mais quelques tâches s’accumulent.",
            "C": "Certaines choses commencent à bloquer ou ralentir.",
            "D": "Tout dépend de moi, ça s’arrête presque complètement.",
        },
    ),
    (
        "leads",
        "Aujourd’hui, vos prospects arrivent… mais êtes-vous sûr de pouvoir tous les suivre sans en perdre ou en oublier ?",
        {
            "A": "Oui, tout est centralisé et suivi automatiquement.",
            "B": "J’ai un système, mais je vérifie encore manuellement.",
            "C": "Ils arrivent à plusieurs endroits, je dois jongler.",
            "D": "Je n’ai pas vraiment de système clair.",
        },
    ),
    (
        "onboarding",
        "Quand un client signe, est-ce que tout est fluide… ou devez-vous encore intervenir à chaque étape ?",
        {
            "A": "Tout est automatisé et fluide.",
            "B": "Partiellement automatisé, mais pas partout.",
            "C": "Je dois intervenir régulièrement.",
            "D": "C’est souvent manuel ou improvisé.",
        },
    ),
    (
        "outils",
        "Vous utilisez plusieurs outils… mais est-ce qu’ils travaillent vraiment ensemble ou vous faites encore beaucoup de choses à la main ?",
        {
            "A": "Tout est connecté et fonctionne ensemble.",
            "B": "Une partie des outils est connectée.",
            "C": "Peu de connexions, beaucoup de manipulations.",
            "D": "Rien n’est connecté, je gère tout à la main.",
        },
    ),
    (
        "repetitif",
        "Combien de fois par semaine refaites-vous les mêmes actions (copier-coller, relances, organisation…) sans automatisation ?",
        {
            "A": "Très rarement.",
            "B": "Quelques fois par semaine.",
            "C": "Très régulièrement.",
            "D": "Tous les jours ou presque.",
        },
    ),
    (
        "process",
        "Si quelqu’un devait reprendre votre business demain, pourrait-il suivre vos process… ou tout est encore dans votre tête ?",
        {
            "A": "Tout est documenté et structuré.",
            "B": "Une partie est documentée.",
            "C": "Très peu de choses sont structurées.",
            "D": "Tout est dans ma tête.",
        },
    ),
    (
        "frein",
        "Aujourd’hui, votre business tourne grâce à un système… ou surtout parce que vous êtes là pour tout gérer ?",
        {
            "A": "Le système gère la majorité.",
            "B": "Mix entre système et moi.",
            "C": "Principalement moi.",
            "D": "Uniquement moi.",
        },
    ),
    (
        "temps_perdu",
        "Chaque semaine, combien d’heures passez-vous sur des tâches que vous pourriez éviter avec un meilleur système ?",
        {
            "A": "Moins de 2 heures.",
            "B": "2 à 5 heures.",
            "C": "6 à 10 heures.",
            "D": "Plus de 10 heures.",
        },
    ),
    (
        "charge",
        "Avez-vous parfois l’impression que si vous ralentissez un peu, tout peut partir en vrille ?",
        {
            "A": "Non, tout est sous contrôle.",
            "B": "Parfois.",
            "C": "Souvent.",
            "D": "Oui clairement.",
        },
    ),
    (
        "goulot",
        "Si votre business était vraiment bien structuré, qu’est-ce qui ferait le plus de différence pour vous aujourd’hui ?",
        {
            "A": "Pas grand-chose, ça fonctionne déjà bien.",
            "B": "Gagner du temps.",
            "C": "Réduire les tâches manuelles.",
            "D": "Avoir un système qui tourne sans moi.",
        },
    ),
]


def score_answers(answers: dict) -> int:
    total = 0
    for key, _, _ in QUESTIONS:
        v = answers.get(key)
        if v in WEIGHTS:
            total += WEIGHTS[v]
    return total


def level_from_score(score: int):
    if score <= 10:
        return ("Niveau 1", "Business très manuel / forte dépendance")
    if score <= 18:
        return ("Niveau 2", "Base existante, mais trop de tâches restent manuelles")
    if score <= 25:
        return ("Niveau 3", "Bonne structure avec optimisation possible")
    return ("Niveau 4", "Système déjà solide, prêt à scaler")


def human_level_label(level: str) -> str:
    if level == "Niveau 1":
        return "encore très dépendant(e) de moi dans mon business"
    if level == "Niveau 2":
        return "encore trop au centre de mon business"
    if level == "Niveau 3":
        return "déjà assez structuré(e), mais avec encore des optimisations à faire"
    if level == "Niveau 4":
        return "déjà bien structuré(e), avec encore un peu d’optimisation possible"
    return "encore trop au centre de mon business"


def estimate_time_gain(answers: dict):
    repetitif_map = {"A": 1, "B": 3, "C": 6, "D": 10}
    temps_map = {"A": 1, "B": 4, "C": 8, "D": 12}

    repetitif = answers.get("repetitif", "B")
    temps_perdu = answers.get("temps_perdu", "B")
    charge = answers.get("charge", "B")
    onboarding = answers.get("onboarding", "B")
    leads = answers.get("leads", "B")
    process = answers.get("process", "B")
    goulot = answers.get("goulot", "B")

    base = max(repetitif_map.get(repetitif, 3), temps_map.get(temps_perdu, 4))

    bonus = 0
    if charge == "C":
        bonus += 1
    elif charge == "D":
        bonus += 3

    if onboarding == "C":
        bonus += 1
    elif onboarding == "D":
        bonus += 2

    if leads == "C":
        bonus += 1
    elif leads == "D":
        bonus += 2

    if process == "C":
        bonus += 1
    elif process == "D":
        bonus += 2

    if goulot == "C":
        bonus += 1
    elif goulot == "D":
        bonus += 2

    estimate_min = max(2, round(base * 0.7 + bonus * 0.5))
    estimate_max = min(20, estimate_min + 3 + min(bonus, 4))

    if estimate_max < estimate_min:
        estimate_max = estimate_min + 2

    return estimate_min, estimate_max


def rule_based_priorities(answers: dict):
    recos = []

    if answers.get("leads") in ("C", "D"):
        recos.append("Gestion des leads")
    else:
        recos.append("Optimisation du système de leads")

    if answers.get("onboarding") in ("C", "D"):
        recos.append("Onboarding client")
    else:
        recos.append("Fluidité de l’onboarding")

    if (
        answers.get("repetitif") in ("C", "D")
        or answers.get("process") in ("C", "D")
        or answers.get("temps_perdu") in ("C", "D")
        or answers.get("charge") in ("C", "D")
        or answers.get("goulot") in ("C", "D")
    ):
        recos.append("Suivi des opérations")
    else:
        recos.append("Organisation des opérations")

    return recos[:3]


def questions_as_json():
    import json

    out = []
    for key, prompt, opts in QUESTIONS:
        out.append({"key": key, "prompt": prompt, "options": opts})
    return json.dumps(out, ensure_ascii=False)


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

  .hr{
    height:1px;
    background: rgba(15,23,42,.10);
    border:none;
    margin:14px 0;
  }

  .leftTitle{
    font-weight:900;
    margin:0 0 10px;
    font-size:16px;
  }

  .bullets{
    margin:0;
    padding-left:18px;
    color:var(--muted);
    font-weight:650;
  }

  .bullets li{
    margin:8px 0;
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
            <div class="promiseTitle">En 2 minutes, tu vas découvrir :</div>
            <ul class="promiseList">
              <li>où ton business dépend encore trop de toi</li>
              <li>où tu perds du temps chaque semaine</li>
              <li>quoi automatiser en priorité</li>
            </ul>
            <div class="promiseHighlight">+ tu peux recevoir un plan d’automatisation personnalisé à la fin</div>
          </div>

          <div class="progress"><div id="bar" class="bar"></div></div>

          <div class="leftTitle">💡 En moyenne, les entrepreneurs découvrent 5 à 15 heures perdues chaque semaine.</div>
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
const QUESTIONS = %QUESTIONS_JSON%;
const LINKEDIN_URL = %LINKEDIN_URL_JSON%;

let step = 0;
let answers = {};
let locked = false;
let currentQuestionRow = null;
let finalData = null;

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
  const pct = Math.round((step / QUESTIONS.length) * 100);
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

function renderChoices(q){
  choices.innerHTML = "";
  const opts = q.options;

  for(const k of ["A","B","C","D"]){
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.innerHTML = `<div class="key">${k}</div><div>${opts[k]}</div>`;
    btn.onclick = (e) => choose(q.key, k, opts[k], e.currentTarget);
    choices.appendChild(btn);
  }
}

function botAsk(){
  locked = true;
  setProgress();

  const q = QUESTIONS[step];
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
      <div class="questionTag">Question ${step+1} / ${QUESTIONS.length} • ${Math.round(((step+1)/QUESTIONS.length)*100)}%</div>
      <div style="margin-bottom:6px;color:#64748b;font-size:13px;">${r}</div>
      <div>${q.prompt}</div>
    `;

    currentQuestionRow = msg.row;
    renderChoices(q);
    locked = false;
  }, 650);
}

function choose(key, letter, label, btn){
  if(locked) return;

  btn.classList.add("btnSelected");
  choices.style.pointerEvents = "none";

  answers[key] = letter;
  step += 1;

  setTimeout(() => {
    if(currentQuestionRow){
      currentQuestionRow.remove();
      currentQuestionRow = null;
    }

    choices.style.pointerEvents = "auto";

    if(step >= QUESTIONS.length){
      finish();
    } else {
      botAsk();
    }
  }, 180);
}

function averageHours(baseData){
  return Math.round((baseData.estimated_min + baseData.estimated_max) / 2);
}

function humanLevelLabel(level){
  if(level === "Niveau 1") return "encore très dépendant(e) de moi dans mon business";
  if(level === "Niveau 2") return "encore trop au centre de mon business";
  if(level === "Niveau 3") return "déjà assez structuré(e), mais avec encore des optimisations à faire";
  if(level === "Niveau 4") return "déjà bien structuré(e), avec encore un peu d’optimisation possible";
  return "encore trop au centre de mon business";
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
    extra += `\n\nLes tâches qui me prennent du temps aujourd’hui : ${repetitive}`;
  }

  if(tools){
    extra += `\n\nLes outils que j’utilise déjà : ${tools}`;
  }

  return `Hello Audrey,

Je viens de faire ton diagnostic AURA.

Je suis ${humanLevelLabel(baseData.level)}.

Ça a surtout pointé :
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

function renderFinalCTA(baseData){
  const card = document.createElement("div");
  card.className = "resultCard messageAppear";
  card.innerHTML = `
    <div style="font-weight:900;font-size:18px;">👇 Recevoir mon plan personnalisé (5 actions concrètes)</div>
    <div class="micro">Je peux te dire par quoi commencer pour débloquer ça rapidement, avec des recommandations adaptées à ton cas.</div>

    <div class="leadForm">
      <div>
        <label for="activityInput">Ton activité</label>
        <input id="activityInput" class="leadInput" type="text" placeholder="Ex : coach business, freelance, agence, e-commerce...">
      </div>

      <div>
        <label for="repetitiveInput">Quelles sont les tâches que tu fais souvent et qui te prennent du temps ?</label>
        <textarea id="repetitiveInput" class="leadTextarea" placeholder="Ex : relances, onboarding, suivi client, organisation, copier-coller..."></textarea>
      </div>

      <div>
        <label for="toolsInput">Quels outils utilises-tu déjà ?</label>
        <input id="toolsInput" class="leadInput" type="text" placeholder="Ex : Notion, Calendly, Stripe, Gmail, Make, Airtable...">
      </div>
    </div>

    <div class="micro">Je te réponds en général avec 2–3 recommandations adaptées à ton cas.</div>

    <div class="resultActions">
      <a class="dmBtn" id="linkedinBtn" href="${LINKEDIN_URL}" target="_blank" rel="noopener noreferrer">Recevoir mon plan sur LinkedIn</a>
    </div>
  `;
  chat.appendChild(card);
  chat.scrollTop = chat.scrollHeight;

  const activityInput = document.getElementById("activityInput");
  const repetitiveInput = document.getElementById("repetitiveInput");
  const toolsInput = document.getElementById("toolsInput");
  const linkedinBtn = document.getElementById("linkedinBtn");

  const syncPreview = () => {
    updateCopyBox();
  };

  activityInput.addEventListener("input", syncPreview);
  repetitiveInput.addEventListener("input", syncPreview);
  toolsInput.addEventListener("input", syncPreview);

  linkedinBtn.onclick = async (e) => {
    e.preventDefault();

    const dmText = buildDmText(baseData);

    try{
      await navigator.clipboard.writeText(dmText);
      showCopyPreview("✅ Message copié. LinkedIn s’ouvre dans un nouvel onglet. Collez-le avec Ctrl+V / Cmd+V.", true);
    }catch(e){
      showCopyPreview(dmText, false);
    }

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
       <div id="loaderText">Analyse de vos réponses…</div>
     </div>`
  );

  await new Promise(resolve => requestAnimationFrame(resolve));

  const loaderText = loadingMsg.bubble.querySelector("#loaderText");

  const steps = [
    "Analyse de vos réponses…",
    "Détection des priorités…",
    "Préparation de votre résultat…"
  ];

  let stepIndex = 0;

  const loaderInterval = setInterval(() => {
    stepIndex = Math.min(stepIndex + 1, steps.length - 1);
    loaderText.textContent = steps[stepIndex];
  }, 700);

  const res = await fetch("/result", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({answers})
  });

  const data = await res.json();
  finalData = data;

  await sleep(2200);
  clearInterval(loaderInterval);

  await typeHtmlInto(
    loadingMsg.bubble,
    `<b>Aujourd’hui, ton business dépend encore beaucoup de toi.</b><br><br>
     ${data.summary}`,
    14
  );

  await sleep(700);

  await addBotMsgTyped(
    `Si rien ne change, tu continues probablement à perdre entre <b>${data.estimated_min} et ${data.estimated_max} heures par semaine</b> sur des tâches qui pourraient être simplifiées ou automatisées.`,
    "estimateBox",
    14
  );

  await sleep(700);

  await addBotMsgTyped(
    `<b>Les 3 points qui te bloquent probablement le plus aujourd’hui :</b><br>
     1) ${data.top3[0]}<br>
     2) ${data.top3[1]}<br>
     3) ${data.top3[2]}`,
    "",
    14
  );

  await sleep(700);

  await addBotMsgTyped(
    `C’est généralement ce qui empêche de vraiment déléguer, respirer ou faire tourner son business sans être au centre de tout.`,
    "",
    14
  );

  await sleep(700);

  await addBotMsgTyped(
    `Si tu veux, je peux te dire exactement par quoi commencer pour débloquer ça rapidement.<br><br>
     👉 Et te préparer un plan personnalisé avec 5 actions concrètes.`,
    "",
    14
  );

  await sleep(400);
  renderFinalCTA(data);

  locked = false;
}

function reset(){
  step = 0;
  answers = {};
  locked = false;
  currentQuestionRow = null;
  finalData = null;
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


@app.get("/", response_class=HTMLResponse)
def home():
    import json

    return (
        HTML
        .replace("%QUESTIONS_JSON%", questions_as_json())
        .replace("%LINKEDIN_URL_JSON%", json.dumps(LINKEDIN_URL))
    )


@app.post("/result")
async def result(request: Request):
    body = await request.json()
    answers = body.get("answers", {})

    score = score_answers(answers)
    level, subtitle = level_from_score(score)
    top3 = rule_based_priorities(answers)
    estimated_min, estimated_max = estimate_time_gain(answers)

    if level == "Niveau 1":
        summary = (
            "Si vous ralentissez, certaines opérations peuvent ralentir ou s’arrêter. "
            "Vous êtes encore le point de passage de beaucoup trop de choses."
        )
    elif level == "Niveau 2":
        summary = (
            "Vous avez déjà une base, mais trop d’étapes restent encore manuelles ou dépendantes de vous. "
            "Vous avez probablement commencé à structurer, sans encore vraiment fluidifier."
        )
    elif level == "Niveau 3":
        summary = (
            "Votre base est plutôt saine, mais certaines zones continuent probablement à vous faire perdre du temps inutilement. "
            "Vous n’êtes plus dans le chaos, mais pas encore dans la fluidité."
        )
    else:
        summary = (
            "Votre structure est déjà solide. "
            "L’enjeu n’est plus de survivre à l’opérationnel, mais d’optimiser ce qui peut encore vous freiner."
        )

    avg_hours = round((estimated_min + estimated_max) / 2)

    dm_copy = (
        f"Hello Audrey,\n\n"
        f"Je viens de faire ton diagnostic AURA.\n\n"
        f"Je suis {human_level_label(level)}.\n\n"
        f"Ça a surtout pointé :\n"
        f"- {top3[0]}\n"
        f"- {top3[1]}\n"
        f"- {top3[2]}\n\n"
        f"Et visiblement je pourrais récupérer ~{avg_hours}h/semaine là-dessus 😅\n\n"
        f"Tu commencerais par quoi à ma place ?"
    )

    return JSONResponse(
        {
            "score": score,
            "level": level,
            "subtitle": subtitle,
            "summary": summary,
            "top3": top3,
            "estimated_min": estimated_min,
            "estimated_max": estimated_max,
            "dm_copy": dm_copy,
        }
    )


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)