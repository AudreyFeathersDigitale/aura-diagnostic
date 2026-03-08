from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

LINKEDIN_URL = "https://www.linkedin.com/in/audrey-mouton-80b902217/?skipRedirect=true"

WEIGHTS = {"A": 0, "B": 1, "C": 2, "D": 3}

QUESTIONS = [
    ("dependance", "Si vous arrêtez de travailler 3 jours, que se passe-t-il ?", {
        "A": "Tout continue normalement.",
        "B": "Quelques tâches s'accumulent, mais ça va.",
        "C": "Certaines tâches bloquent / retards clients.",
        "D": "Tout s'arrête.",
    }),
    ("leads", "Où arrivent vos nouveaux prospects aujourd'hui ?", {
        "A": "Automatiquement dans un CRM.",
        "B": "Dans un tableur / outil central + un peu de manuel.",
        "C": "Dans la messagerie / DM / notes éparses.",
        "D": "Je n'ai pas de système clair.",
    }),
    ("onboarding", "Quand un client signe, l'onboarding se passe comment ?", {
        "A": "Automatisé (contrat/paiement/accès/infos).",
        "B": "Semi-automatisé.",
        "C": "Plutôt manuel (copier-coller, checklists).",
        "D": "Souvent le chaos / ça dépend.",
    }),
    ("outils", "Combien d'outils utilisez-vous pour gérer votre activité ?", {
        "A": "1 à 3",
        "B": "4 à 6",
        "C": "7 à 10",
        "D": "10+",
    }),
    ("repetitif", "Combien de tâches répétitives faites-vous manuellement chaque semaine ?", {
        "A": "0 à 2",
        "B": "3 à 5",
        "C": "6 à 10",
        "D": "10+",
    }),
    ("process", "Vos process sont-ils documentés et structurés ?", {
        "A": "Oui, clairement.",
        "B": "Partiellement.",
        "C": "Non.",
        "D": "C'est dans ma tête.",
    }),
    ("frein", "Votre frein principal aujourd'hui ?", {
        "A": "Manque de leads / visibilité.",
        "B": "Manque de temps.",
        "C": "Trop d'opérationnel / trop de tâches.",
        "D": "Organisation floue / trop d'outils / pas de système.",
    }),
]


def score_answers(answers: dict) -> int:
    total = 0
    for key, _, _ in QUESTIONS:
        v = answers.get(key)
        if v in WEIGHTS:
            total += WEIGHTS[v]
    return total


def level_from_score(score: int):
    if score <= 7:
        return ("Niveau 1", "Business très dépendant de vous")
    if score <= 14:
        return ("Niveau 2", "Automatisations partielles (base existante)")
    return ("Niveau 3", "Bonne base (optimisation & scaling)")


def rule_based_priorities(answers: dict):
    recos = []
    if answers.get("leads") in ("C", "D"):
        recos.append("Système Leads : capture → tagging → CRM → réponse auto + pipeline clair.")
    else:
        recos.append("Système Leads : standardiser pipeline (stades/tags/relances) + qualification automatique.")

    if answers.get("onboarding") in ("C", "D"):
        recos.append("Système Onboarding : contrat + paiement + email de bienvenue + accès + checklist automatique.")
    else:
        recos.append("Système Onboarding : consolider (templates, centralisation infos, automatisations).")

    if answers.get("repetitif") in ("C", "D") or answers.get("process") in ("C", "D"):
        recos.append("Système Suivi/Opérations : rappels, relances, tâches récurrentes + SOP (documentation).")
    else:
        recos.append("Système Suivi/Opérations : améliorer reporting, relances et standardisation SOP.")
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
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
  .dmBtn,
  .copyBtn{
    border:none;
    cursor:pointer;
    font-weight:950;
    border-radius:16px;
    padding:12px 18px;
    text-decoration:none;
    display:inline-flex;
    align-items:center;
    justify-content:center;
  }

  .restart,
  .dmBtn{
    color:white;
    background: linear-gradient(180deg, var(--blue), var(--blue2));
    box-shadow: 0 18px 26px rgba(47,107,255,.18);
  }

  .restart:hover,
  .dmBtn:hover{
    filter:brightness(1.05);
  }

  .copyBtn{
    color:var(--text);
    background:#ffffff;
    border:1px solid var(--line);
    box-shadow: 0 8px 16px rgba(15,23,42,.06);
  }

  .copyBtn:hover{
    border-color: rgba(47,107,255,.28);
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

  .leadForm{
    display:grid;
    gap:12px;
    margin-top:14px;
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

  .micro{
    font-size:13px;
    color:var(--muted);
    margin-top:8px;
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
          <div class="tag">Je pose 8 questions, une par une.</div>

          <div class="progress"><div id="bar" class="bar"></div></div>

          <hr class="hr">
          <div class="leftTitle">À la fin, tu obtiens :</div>
          <ul class="bullets">
            <li>Ton score & niveau</li>
            <li>3 automatisations prioritaires</li>
            <li>Un texte copiable pour DM</li>
          </ul>
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
              <div class="chatHeaderSub">Prête ? On fait ce diagnostic en 8 questions.</div>
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

function addBotMsg(html, typing=false){
  const row = document.createElement("div");
  row.className = "row";

  const mini = document.createElement("div");
  mini.className = "mini";
  mini.innerHTML = `<img src="${AURA_HEAD}" alt="AURA">`;
  row.appendChild(mini);

  if(typing){
    mini.classList.add("miniThinking");
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";

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

function buildDmText(baseData){
  const activity = (document.getElementById("activityInput")?.value || "").trim() || "[à compléter]";
  const tools = (document.getElementById("toolsInput")?.value || "").trim() || "[à compléter]";

  return `Bonjour Audrey,

Je viens de faire ton diagnostic AURA.

Mon résultat : ${baseData.score}/21 — ${baseData.level} (${baseData.subtitle})
Résumé : ${baseData.summary}

Mes 3 priorités :
1) ${baseData.top3[0]}
2) ${baseData.top3[1]}
3) ${baseData.top3[2]}

Mon activité : ${activity}
Mes outils actuels : ${tools}

Peux-tu me dire quelles 5 automatisations tu me recommandes en premier ?`;
}

function updateCopyBox(){
  if(!finalData) return;
  copyBox.style.display = "block";
  copyBox.textContent = buildDmText(finalData);
}

function renderFinalCTA(baseData){
  const card = document.createElement("div");
  card.className = "resultCard";
  card.innerHTML = `
    <div style="font-weight:900;font-size:18px;">👇 Recevoir mon plan d’automatisation</div>
    <div class="micro">Ajoute ton activité et tes outils, puis envoie-moi le message préparé sur LinkedIn.</div>

    <div class="leadForm">
      <div>
        <label for="activityInput">Mon activité</label>
        <input id="activityInput" class="leadInput" type="text" placeholder="Ex : Coach business, freelance, e-commerce...">
      </div>
      <div>
        <label for="toolsInput">Mes outils actuels</label>
        <textarea id="toolsInput" class="leadTextarea" placeholder="Ex : Notion, Calendly, Stripe, Gmail, Make, Airtable..."></textarea>
      <div class="micro">En général, je réponds avec 2 ou 3 recommandations concrètes adaptées à votre activité.</div></div>
    </div>

    <div class="resultActions">
      <a class="dmBtn" id="linkedinBtn" href="${LINKEDIN_URL}" target="_blank" rel="noopener noreferrer">M’envoyer un DM sur LinkedIn</a>
      <button class="copyBtn" id="copyDmBtn" type="button">Copier le message</button>
    </div>
  `;
  chat.appendChild(card);
  chat.scrollTop = chat.scrollHeight;

  const activityInput = document.getElementById("activityInput");
  const toolsInput = document.getElementById("toolsInput");
  const copyBtn = document.getElementById("copyDmBtn");
  const linkedinBtn = document.getElementById("linkedinBtn");

  const sync = () => {
    updateCopyBox();
    copyBtn.textContent = "Copier le message";
  };

  activityInput.addEventListener("input", sync);
  toolsInput.addEventListener("input", sync);

  copyBtn.onclick = async () => {
    const dmText = buildDmText(baseData);
    try{
      await navigator.clipboard.writeText(dmText);
      copyBtn.textContent = "Message copié";
      copyBox.style.display = "block";
      copyBox.textContent = dmText;
    }catch(e){
      copyBox.style.display = "block";
      copyBox.textContent = dmText;
      copyBtn.textContent = "Copie ci-dessous";
    }
  };

  linkedinBtn.onclick = () => {
    const dmText = buildDmText(baseData);
    copyBox.style.display = "block";
    copyBox.textContent = dmText;
  };

  updateCopyBox();
}

async function finish(){
  locked = true;
  choices.innerHTML = "";
  setProgress();

  if (currentQuestionRow) {
    currentQuestionRow.remove();
    currentQuestionRow = null;
  }

  const msg = addBotMsg("", true);
  setTimeout(() => {
    msg.bubble.innerHTML = "Merci ! Je calcule ton résultat…";
  }, 600);

  const res = await fetch("/result", {
    method:"POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({answers})
  });
  const data = await res.json();
  finalData = data;

  addBotMsg(`<b>Résultat : ${data.score}/21 — ${data.level} (${data.subtitle})</b><br><br>${data.summary}`);
  addBotMsg(`<b>Top 3 automatisations prioritaires :</b><br>1) ${data.top3[0]}<br>2) ${data.top3[1]}<br>3) ${data.top3[2]}`);
  addBotMsg(`Bonne nouvelle : votre business a déjà une base solide.

Mais certaines automatisations clés semblent manquer et pourraient vous faire gagner plusieurs heures chaque semaine.<br> Si tu veux que je te dise <b>quelles 5 automatisations</b> déployer en premier, j’ai préparé ton message.
<br>⏱ Je réponds généralement en moins de 24h.`);
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

    if level == "Niveau 1":
        summary = ("Votre business dépend encore fortement de vous : si vous ralentissez, les opérations ralentissent (ou s’arrêtent). "
                   "Priorité : structurer le flux leads → onboarding → suivi, puis automatiser les répétitions.")
    elif level == "Niveau 2":
        summary = ("Vous avez une base, mais certains points restent manuels et créent des goulots d’étranglement. "
                   "Priorité : automatiser les étapes répétitives et standardiser vos process.")
    else:
        summary = ("Votre base est saine : vous pouvez optimiser pour la fiabilité et la scalabilité. "
                   "Priorité : renforcer les automatisations critiques et simplifier votre stack outils.")

    dm_copy = (
        f"Bonjour Audrey,\n\n"
        f"Je viens de faire ton diagnostic AURA.\n\n"
        f"Mon résultat : {score}/21 — {level} ({subtitle})\n"
        f"Résumé : {summary}\n\n"
        f"Mes 3 priorités :\n"
        f"1) {top3[0]}\n"
        f"2) {top3[1]}\n"
        f"3) {top3[2]}\n\n"
        f"Mon activité : [à compléter]\n"
        f"Mes outils actuels : [à compléter]\n\n"
        f"Peux-tu me dire quelles 5 automatisations tu me recommandes en premier ?"
    )

    return JSONResponse({
        "score": score,
        "level": level,
        "subtitle": subtitle,
        "summary": summary,
        "top3": top3,
        "dm_copy": dm_copy
    })

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)