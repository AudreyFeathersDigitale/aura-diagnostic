from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

LINKEDIN_URL = "https://www.linkedin.com/in/audrey-mouton-80b902217/?skipRedirect=true"

WEIGHTS = {"A": 3, "B": 2, "C": 1, "D": 0}

QUESTIONS = [
    ("dependance","Si vous arrêtez de travailler pendant <b>1 semaine</b>, que se passe-t-il ?",{"A":"Tout continue","B":"Quelques retards","C":"Ça bloque","D":"Tout s’arrête"}),
    ("leads","Où arrivent vos prospects ?",{"A":"CRM","B":"Mix","C":"Partout","D":"Aucun système"}),
    ("onboarding","Onboarding client ?",{"A":"Auto","B":"Partiel","C":"Manuel","D":"Improvisé"}),
    ("outils","Nombre d’outils ?",{"A":"1-3","B":"4-6","C":"7-10","D":"10+"}),
    ("repetitif","Tâches répétitives ?",{"A":"0-2","B":"3-5","C":"6-10","D":"10+"}),
    ("process","Process documentés ?",{"A":"Oui","B":"Partiel","C":"Non","D":"Dans ma tête"}),
    ("frein","Qui gère ?",{"A":"Système","B":"Mix","C":"Moi","D":"Moi uniquement"}),
    ("temps_perdu","Temps perdu ?",{"A":"<2h","B":"2-5h","C":"6-10h","D":"10h+"}),
    ("charge","Charge mentale ?",{"A":"Rare","B":"Parfois","C":"Souvent","D":"Tout le temps"}),
    ("goulot","Objectif ?",{"A":"Rien","B":"Temps","C":"Moins manuel","D":"Système autonome"}),
]

def score_answers(answers):
    return sum(WEIGHTS.get(answers.get(k),0) for k,_,_ in QUESTIONS)

def level_from_score(score):
    if score<=10: return "Niveau 1"
    if score<=18: return "Niveau 2"
    if score<=25: return "Niveau 3"
    return "Niveau 4"

def human_level(level):
    return {
        "Niveau 1":"encore très dépendant(e) de moi",
        "Niveau 2":"encore trop au centre",
        "Niveau 3":"assez structuré(e)",
        "Niveau 4":"déjà bien structuré(e)"
    }[level]

HTML = r"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AURA</title>

<style>
body{font-family:sans-serif;margin:0;padding:20px;background:#f5f7fb;}
.container{display:grid;grid-template-columns:350px 1fr;gap:20px;}
.left{background:#fff;padding:20px;border-radius:20px;}
.right{background:#eef2f7;padding:20px;border-radius:20px;}
.btn{padding:10px;border-radius:10px;margin:5px;cursor:pointer;background:#fff;}
.dm{background:#2f6bff;color:#fff;padding:12px;border:none;border-radius:12px;}
</style>
</head>

<body>
<div class="container">

<div class="left">
<h2>AURA</h2>
<p><b>En 2 minutes :</b></p>
<ul>
<li>où ton business dépend de toi</li>
<li>où tu perds du temps</li>
<li>quoi automatiser</li>
</ul>
<p><b>+ plan personnalisé à la fin</b></p>
</div>

<div class="right">
<div id="app"></div>
</div>

</div>

<script>
const QUESTIONS = %QUESTIONS%;
const LINKEDIN = %LINKEDIN%;

let step=0, answers={};

function render(){
    const app=document.getElementById("app");

    if(step>=QUESTIONS.length){
        fetch("/result",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({answers})})
        .then(r=>r.json()).then(data=>{
            const avg=Math.round((data.min+data.max)/2);

            app.innerHTML=`
            <h3>Ton business dépend encore de toi.</h3>
            <p>Tu perds ~${avg}h/semaine.</p>
            <p><b>Blocages :</b><br>${data.top3.join("<br>")}</p>

            <p>Je peux te dire quoi faire 👇</p>

            <button class="dm" onclick="sendDM('${data.level}','${avg}','${data.top3.join("|")}')">
            Recevoir mon plan
            </button>
            `;
        });
        return;
    }

    const q=QUESTIONS[step];
    app.innerHTML=`<h3>${q.prompt}</h3>`;

    for(let k in q.options){
        const b=document.createElement("button");
        b.className="btn";
        b.innerText=q.options[k];
        b.onclick=()=>{answers[q.key]=k;step++;render();}
        app.appendChild(b);
    }
}

function sendDM(level,avg,top3){
    const msg=`Hello Audrey,

Je viens de faire ton diagnostic.

Je suis ${level}.

Blocages :
${top3.replaceAll("|","\n")}

Je peux récupérer ~${avg}h/semaine.

Tu commencerais par quoi ?`;

    navigator.clipboard.writeText(msg);
    window.open(LINKEDIN,"_blank");
}

render();
</script>
</body>
</html>
"""

@app.get("/",response_class=HTMLResponse)
def home():
    import json
    return HTML.replace("%QUESTIONS%",json.dumps([{"key":k,"prompt":p,"options":o} for k,p,o in QUESTIONS])).replace("%LINKEDIN%",json.dumps(LINKEDIN_URL))

@app.post("/result")
async def result(request:Request):
    body=await request.json()
    answers=body["answers"]

    score=score_answers(answers)
    level=level_from_score(score)

    top3=["Leads","Onboarding","Suivi"]

    return JSONResponse({
        "score":score,
        "level":level,
        "min":5,
        "max":15,
        "top3":top3
    })

if __name__=="__main__":
    uvicorn.run("app:app",reload=True)