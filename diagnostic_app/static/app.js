const {
  PROFILE_QUESTIONS,
  QUESTIONS,
  LINKEDIN_URL,
  INSTAGRAM_URL
} = window.AURA_CONFIG;


const chat = document.getElementById("chat");
const choices = document.getElementById("choices");
const restartBtn = document.getElementById("restart");
const bar = document.getElementById("bar");
const copyBox = document.getElementById("copyBox");


let phase = "profile";

let profileStep = 0;
let step = 0;

let profileAnswers = {};
let answers = {};

let locked = false;

let finalData = null;


function sleep(ms){
  return new Promise(r => setTimeout(r, ms));
}


function updateBar(){

  const total =
    PROFILE_QUESTIONS.length +
    QUESTIONS.length;

  const done =
    profileStep + step;

  const pct =
    Math.round((done / total) * 100);

  bar.style.width = `${pct}%`;
}


function scrollBottom(){

  requestAnimationFrame(() => {
    chat.scrollTop = chat.scrollHeight;
  });
}


function escapeHtml(str){

  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}


function addBotBubble(html, cls=""){

  const row = document.createElement("div");
  row.className = "row";

  row.innerHTML = `
    <div class="mini">
      <img src="/static/aura.png" alt="AURA">
    </div>

    <div class="bubble ${cls}">
      ${html}
    </div>
  `;

  chat.appendChild(row);

  scrollBottom();

  return row;
}


async function addBotMsgTyped(html, cls="", speed=10){

  const row = addBotBubble("", cls);

  const bubble = row.querySelector(".bubble");

  bubble.innerHTML = html;

  scrollBottom();

  await sleep(speed * 10);
}


function renderChoices(options){

  choices.innerHTML = "";

  const keys = Object.keys(options);

  keys.forEach((key, idx) => {

    const btn = document.createElement("button");

    btn.className = "btn";

    btn.innerHTML = `
      <div class="key">
        ${String.fromCharCode(65 + idx)}
      </div>

      <div>
        ${options[key]}
      </div>
    `;

    btn.onclick = () => selectChoice(key);

    choices.appendChild(btn);

  });
}


async function botAsk(){

  updateBar();

  if(phase === "profile"){

    if(profileStep >= PROFILE_QUESTIONS.length){

      phase = "questions";

      return botAsk();
    }

    const [key, question, options] =
      PROFILE_QUESTIONS[profileStep];

    await addBotMsgTyped(
      `<div class="questionTag">Question ${profileStep + 1}</div>${question}`,
      "bubbleQuestion"
    );

    renderChoices(options);

    return;
  }

  if(step >= QUESTIONS.length){

    return finishDiagnostic();
  }

  const [key, question, options] =
    QUESTIONS[step];

  await addBotMsgTyped(
    `<div class="questionTag">Question ${step + 1}</div>${question}`,
    "bubbleQuestion"
  );

  renderChoices(options);
}


async function selectChoice(value){

  if(locked) return;

  locked = true;

  if(phase === "profile"){

    const [key] =
      PROFILE_QUESTIONS[profileStep];

    profileAnswers[key] = value;

    profileStep++;

  } else {

    const [key] =
      QUESTIONS[step];

    answers[key] = value;

    step++;
  }

  choices.innerHTML = "";

  await sleep(250);

  locked = false;

  botAsk();
}


function renderDimensions(scores){

  const labels = {
    ACQ: "Acquisition",
    ONB: "Onboarding",
    DEL: "Exécution",
    STR: "Structuration"
  };

  const hints = {
    ACQ: "Génération & suivi des prospects",
    ONB: "Mise en route des clients",
    DEL: "Production & tâches quotidiennes",
    STR: "Process & organisation interne"
  };

  let html = `<div class="dimensionGrid">`;

  Object.entries(scores).forEach(([k, v]) => {

    let cls = "good";

    if(v >= 70){
      cls = "danger";
    }
    else if(v >= 45){
      cls = "warning";
    }

    html += `
      <div class="dimensionItem">

        <div class="dimensionLabel">
          ${labels[k]}
        </div>

        <div class="dimensionValue ${cls}">
          ${v}%
        </div>

        <div class="dimensionHint">
          ${hints[k]}
        </div>

      </div>
    `;
  });

  html += `</div>`;

  return html;
}


function renderLeadForm(){

  return `
    <div class="resultCard">

      <div class="leftTitle">
        👉 Voir où agir en priorité
      </div>

      <div style="margin-top:8px;color:var(--muted);font-weight:600;">
        Reçois ton analyse personnalisée + les priorités à débloquer.
      </div>

      <div class="leadForm">

        <input
  id="emailInput"
  class="leadInput"
  placeholder="Email, Instagram ou LinkedIn"
  type="text"
>

        <textarea
          id="tasksInput"
          class="leadTextarea"
          placeholder="Quelles tâches te prennent le plus de temps aujourd’hui ?"
        ></textarea>

        <button
          class="dmBtn"
          onclick="unlockResults()"
        >
          Voir mon diagnostic complet
        </button>

      </div>

    </div>
  `;
}


async function finishDiagnostic(){

  await addBotMsgTyped(
    `⏳ Préparation de ton résultat...`
  );

  await sleep(1200);

  const response = await fetch("/calculate", {

    method: "POST",

    headers: {
      "Content-Type": "application/json"
    },

    body: JSON.stringify({
      answers,
      profile: profileAnswers
    })
  });

  const data = await response.json();

  finalData = data;

  choices.innerHTML = "";

  await addBotMsgTyped(
    renderLeadForm()
  );
}


async function unlockResults(){

  const email =
    document.getElementById("emailInput").value.trim();

  const tasks =
    document.getElementById("tasksInput").value.trim();

 if(!email){
  alert("Laisse ton meilleur contact");
  return;
}

  const response = await fetch("/save-lead", {

    method: "POST",

    headers: {
      "Content-Type": "application/json"
    },

    body: JSON.stringify({
      email,
      repetitive_tasks: tasks,
      result: finalData
    })
  });

  await response.json();

  chat.innerHTML = "";

  const scoreClass =
    finalData.dependency_pct >= 70
      ? "danger"
      : finalData.dependency_pct >= 45
      ? "warning"
      : "good";

  await addBotMsgTyped(
    `
    <div class="scoreHero">

      <div style="font-size:18px;font-weight:900;">
        Ton business est actuellement limité par toi à :
      </div>

      <div class="scorePercent ${scoreClass}">
        ${finalData.dependency_pct}%
      </div>

      <div style="margin-top:10px;font-weight:800;color:var(--muted);">
        👉 ${finalData.subtitle}
      </div>

      <div style="margin-top:10px;">
        <b>${finalData.level}</b> —
        ${finalData.profile_text}
      </div>

    </div>
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    <div class="resultCard">

      <div class="leftTitle">
        ⚠️ Ce que cette dépendance te coûte réellement
      </div>

      <div style="margin-top:14px;line-height:1.5;">

        ⏱️ Tu bloques actuellement entre
        <b>${finalData.estimated_min} et ${finalData.estimated_max} heures</b>
        par semaine.

        <br><br>

        📈 Cela peut représenter entre
<b>${finalData.lost_clients_min} et ${finalData.lost_clients_max} opportunités</b>
que ton système n’absorbe pas encore sereinement.

      </div>

    </div>
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    <b>Répartition de la dépendance par zone :</b>
    ${renderDimensions(finalData.dimension_scores)}
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    <b>👉 Tes 3 principaux points de dépendance :</b>

    <br><br>

    1) ${finalData.top3[0]}

    <br>

    2) ${finalData.top3[1]}

    <br>

    3) ${finalData.top3[2]}
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    👉 Si rien ne change :

    <br><br>

    • tu resteras le point de passage obligé

    <br>

    • ta charge continuera d’augmenter

    <br>

    • ta croissance restera liée à ton temps
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    <div class="resultCard">

      <div class="leftTitle">
        👉 Voilà ce qui pourrait changer dans ton business :
      </div>

      <div style="margin-top:12px;line-height:1.6;">

        • moins de tâches qui reviennent vers toi

        <br>

        • moins de charge mentale

        <br>

        • plus de capacité sans augmenter ton temps

      </div>

      <div style="margin-top:18px;font-weight:900;">
        👉 Objectif :
        te libérer du temps ET débloquer ta croissance
      </div>

      <div style="margin-top:18px;color:#355CFF;font-weight:900;">
        👉 Si rien ne change,
        certaines opportunités continueront d’arriver…
        sans pouvoir être réellement exploitées
      </div>

    </div>
    `
  );

  choices.innerHTML = `
    <a
      href="${LINKEDIN_URL}"
      target="_blank"
      class="dmBtn"
      style="
        text-decoration:none;
        display:inline-flex;
        justify-content:center;
        align-items:center;
      "
    >
      👉 M’envoyer “diagnostic” sur LinkedIn
    </a>
  `;

  locked = false;
}


function reset(){

  phase = "profile";

  profileStep = 0;
  step = 0;

  profileAnswers = {};
  answers = {};

  locked = false;

  finalData = null;

  chat.innerHTML = "";
  choices.innerHTML = "";

  botAsk();
}


restartBtn.onclick = reset;

reset();