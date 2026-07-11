const {
  PRE_QUESTIONS,
  PROFILE_QUESTIONS,
  QUESTIONS,
  LINKEDIN_URL
} = window.AURA_CONFIG;

const chat = document.getElementById("chat");
const choices = document.getElementById("choices");
const restartBtn = document.getElementById("restart");
const bar = document.getElementById("bar");

const DEFAULT_PRE_QUESTIONS = [
  {
    id: "name",
    label: "Commençons simplement : comment t’appelles-tu ? 😊",
    type: "text"
  },
  {
    id: "email",
    label: "À quelle adresse email souhaites-tu recevoir ton analyse complète ?",
    type: "email"
  },
  {
    id: "main_time_pain",
    label: "Dernière question avant de commencer : quelle tâche te prend le plus de temps dans ton business aujourd’hui ?",
    type: "textarea"
  }
];

const sourcePreQuestions = Array.isArray(PRE_QUESTIONS) && PRE_QUESTIONS.length
  ? PRE_QUESTIONS
  : DEFAULT_PRE_QUESTIONS;

// On force ici les formulations voulues, même si index.html contient encore l’ancien texte.
const preQuestions = sourcePreQuestions.map((question) => {
  if(question.id === "name"){
    return {
      ...question,
      label: "Commençons simplement : comment t’appelles-tu ? 😊",
      type: "text"
    };
  }

  if(question.id === "email"){
    return {
      ...question,
      label: "À quelle adresse email souhaites-tu recevoir ton analyse complète ?",
      type: "email"
    };
  }

  if(question.id === "main_time_pain"){
    return {
      ...question,
      label: "Dernière question avant de commencer : quelle tâche te prend le plus de temps dans ton business aujourd’hui ?",
      type: "textarea"
    };
  }

  return question;
});

let phase = "pre";
let preStep = 0;
let profileStep = 0;
let step = 0;

let preAnswers = {};
let profileAnswers = {};
let answers = {};

let locked = false;
let finalData = null;
let introShown = false;

function sleep(ms){
  return new Promise(r => setTimeout(r, ms));
}

function updateBar(){
  const total = preQuestions.length + PROFILE_QUESTIONS.length + QUESTIONS.length;
  const done = preStep + profileStep + step;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  bar.style.width = `${pct}%`;
}

function scrollBottom(){
  requestAnimationFrame(() => {
    chat.scrollTop = chat.scrollHeight;
  });
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

  const template = document.createElement("template");
  template.innerHTML = html.trim();

  bubble.innerHTML = "";

  async function typeNode(node, parent){
    if(node.nodeType === Node.TEXT_NODE){
      const textNode = document.createTextNode("");
      parent.appendChild(textNode);

      const text = node.textContent || "";

      for(let i = 0; i < text.length; i++){
        textNode.textContent += text[i];

        if(i % 3 === 0){
          scrollBottom();
        }

        await sleep(speed);
      }

      return;
    }

    if(node.nodeType === Node.ELEMENT_NODE){
      const el = document.createElement(node.tagName.toLowerCase());

      for(const attr of node.attributes){
        el.setAttribute(attr.name, attr.value);
      }

      parent.appendChild(el);

      for(const child of node.childNodes){
        await typeNode(child, el);
      }
    }
  }

  for(const node of template.content.childNodes){
    await typeNode(node, bubble);
  }

  scrollBottom();
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

function renderTextInput(question){
  const isTextarea = question.type === "textarea" || question.id === "main_time_pain";

  choices.innerHTML = `
    <div class="leadForm">
      ${
        isTextarea
          ? `
            <textarea
              id="textInput"
              class="leadTextarea"
              placeholder="Ta réponse..."
            ></textarea>
          `
          : `
            <input
              id="textInput"
              class="leadInput"
              type="${question.type === "email" || question.id === "email" ? "email" : "text"}"
              placeholder="Ta réponse..."
            >
          `
      }

      <button
        id="textSubmitBtn"
        class="dmBtn"
        type="button"
      >
        Continuer
      </button>
    </div>
  `;

  const input = document.getElementById("textInput");

  if(input){
    input.focus();

    input.addEventListener("keydown", function(e){
      if(e.key === "Enter" && !e.shiftKey && !isTextarea){
        e.preventDefault();
        submitTextAnswer();
      }
    });
  }
}

function getTotal(){
  return preQuestions.length + PROFILE_QUESTIONS.length + QUESTIONS.length;
}

function getCurrent(){
  if(phase === "pre"){
    return preStep + 1;
  }

  if(phase === "profile"){
    return preQuestions.length + profileStep + 1;
  }

  return preQuestions.length + PROFILE_QUESTIONS.length + step + 1;
}

async function botAsk(){
  updateBar();

  const total = getTotal();
  const current = getCurrent();

  if(phase === "pre"){
    if(preStep === 0 && !introShown){
      introShown = true;

      await addBotMsgTyped(
        `
        <div class="questionText">
          Avant de commencer, j’ai besoin de quelques informations.
          <br><br>
          Elles vont me permettre de personnaliser ton diagnostic
          et de t’envoyer ton analyse complète à la fin.
          <br><br>
          Ça ne prendra pas plus de 20 secondes. 😊
        </div>
        `,
        "bubbleQuestion"
      );

      await sleep(500);
    }

    if(preStep >= preQuestions.length){
      phase = "profile";

      const firstName = preAnswers.name || preAnswers.nom || "";

      await addBotMsgTyped(
        `
        <div class="resultCard">
          <div class="leftTitle">
            Merci ${firstName ? firstName : ""} 🙌
          </div>

          <div style="margin-top:12px;line-height:1.6;">
            J’ai tout ce qu’il me faut pour personnaliser ta synthèse.
            <br><br>
            Maintenant, on peut commencer le diagnostic pour identifier où ton business dépend encore trop de toi.
          </div>
        </div>
        `
      );

      await sleep(700);
      return botAsk();
    }

    const question = preQuestions[preStep];

    await addBotMsgTyped(
      `
      <div class="questionPill">
        ${current} / ${total}
      </div>

      <div class="questionText">
        ${question.label}
      </div>
      `,
      "bubbleQuestion"
    );

    renderTextInput(question);
    return;
  }

  if(phase === "profile"){
    if(profileStep >= PROFILE_QUESTIONS.length){
      phase = "questions";
      return botAsk();
    }

    const [key, question, options] = PROFILE_QUESTIONS[profileStep];

    await addBotMsgTyped(
      `
      <div class="questionPill">
        ${current} / ${total}
      </div>

      <div class="questionText">
        ${question}
      </div>
      `,
      "bubbleQuestion"
    );

    renderChoices(options);
    return;
  }

  if(step >= QUESTIONS.length){
    return finishDiagnostic();
  }

  const [key, question, options] = QUESTIONS[step];

  await addBotMsgTyped(
    `
    <div class="questionPill">
      ${current} / ${total}
    </div>

    <div class="questionText">
      ${question}
    </div>
    `,
    "bubbleQuestion"
  );

  renderChoices(options);
}

async function submitTextAnswer(){
  if(locked) return;

  const input = document.getElementById("textInput");
  const value = input ? input.value.trim() : "";

  if(!value){
    alert("Merci de compléter ce champ.");
    return;
  }

  const question = preQuestions[preStep];

  if(question.id === "email" || question.type === "email"){
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if(!emailRegex.test(value)){
      alert("Merci d’indiquer une adresse email valide.");
      return;
    }
  }

  locked = true;

  preAnswers[question.id] = value;
  preStep++;

  choices.innerHTML = "";

  if(question.id === "name"){
    await addBotMsgTyped(
      `
      <div class="questionText">
        Ravi de faire ta connaissance, <b>${value}</b> 😊
      </div>
      `
    );

    await sleep(400);
  }

  await sleep(250);

  locked = false;
  botAsk();
}

async function selectChoice(value){
  if(locked) return;

  locked = true;

  if(phase === "profile"){
    const [key] = PROFILE_QUESTIONS[profileStep];
    profileAnswers[key] = value;
    profileStep++;
  } else {
    const [key] = QUESTIONS[step];
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

  Object.entries(scores || {}).forEach(([k, v]) => {
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
          ${labels[k] || k}
        </div>

        <div class="dimensionValue ${cls}">
          ${v}%
        </div>

        <div class="dimensionHint">
          ${hints[k] || ""}
        </div>
      </div>
    `;
  });

  html += `</div>`;

  return html;
}

async function finishDiagnostic(){
  choices.innerHTML = "";

  await addBotMsgTyped(
    `⏳ Préparation de ta mini-synthèse...`
  );

  await sleep(1200);

  const response = await fetch("/calculate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      answers,
      profile: profileAnswers,
      lead: preAnswers
    })
  });

  const data = await response.json();
  finalData = data;

  try{
    await fetch("/save-lead", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name: preAnswers.name || preAnswers.nom || "",
        email: preAnswers.email || "",
        repetitive_tasks: preAnswers.main_time_pain || preAnswers.tasks || "",
        answers,
        profile: profileAnswers,
        lead: preAnswers,
        result: finalData
      })
    });
  }catch(error){
    console.log("Erreur save-lead :", error);
  }

  await showMiniSummary();
}

async function showMiniSummary(){
  chat.innerHTML = "";
  choices.innerHTML = "";

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
        ${preAnswers.name ? `${preAnswers.name}, voici ta mini-synthèse :` : "Voici ta mini-synthèse :"}
      </div>

      <div style="margin-top:14px;font-weight:900;">
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

      <div style="margin-top:16px;color:var(--muted);font-weight:800;">
        📩 Ta synthèse complète est envoyée à :
        <br>
        <b>${preAnswers.email || "ton email"}</b>
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
    1) ${finalData.top3[0]}<br>
    2) ${finalData.top3[1]}<br>
    3) ${finalData.top3[2]}
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    <div class="resultCard">
      <div class="leftTitle">
        👉 Ce que ça veut dire concrètement
      </div>

      <div style="margin-top:12px;line-height:1.6;">
        Si rien ne change :
        <br><br>
        • tu resteras le point de passage obligé<br>
        • ta charge continuera d’augmenter<br>
        • ta croissance restera liée à ton temps
      </div>

      <div style="margin-top:18px;font-weight:900;">
        Objectif : réduire les tâches qui reviennent vers toi et libérer de la capacité sans augmenter ta charge.
      </div>
    </div>
    `
  );

  choices.innerHTML = `
    <a
      href="${LINKEDIN_URL}"
      target="_blank"
      class="dmBtn"
      style="text-decoration:none;display:inline-flex;justify-content:center;align-items:center;"
    >
      👉 M’envoyer “diagnostic” sur LinkedIn
    </a>
  `;

  locked = false;
}

document.addEventListener("click", function(e){
  const btn = e.target.closest("#textSubmitBtn");

  if(!btn) return;

  e.preventDefault();
  submitTextAnswer();
});

function reset(){
  phase = "pre";
  preStep = 0;
  profileStep = 0;
  step = 0;

  preAnswers = {};
  profileAnswers = {};
  answers = {};

  locked = false;
  finalData = null;
  introShown = false;

  chat.innerHTML = "";
  choices.innerHTML = "";

  updateBar();
  botAsk();
}

restartBtn.onclick = reset;

reset();