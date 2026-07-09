const {
  PRE_QUESTIONS,
  PROFILE_QUESTIONS,
  QUESTIONS,
  LINKEDIN_URL,
  } = window.AURA_CONFIG;

const chat = document.getElementById("chat");
const choices = document.getElementById("choices");
const restartBtn = document.getElementById("restart");
const bar = document.getElementById("bar");

let phase = "pre";
let preStep = 0;
let profileStep = 0;
let step = 0;

let preAnswers = {};
let profileAnswers = {};
let answers = {};

let locked = false;
let finalData = null;

function sleep(ms){
  return new Promise(r => setTimeout(r, ms));
}

function updateBar(){
  const total = PRE_QUESTIONS.length + PROFILE_QUESTIONS.length + QUESTIONS.length;
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

function renderTextInput(questionId){
  const isLongText = questionId === "main_time_pain";

  choices.innerHTML = `
    <div class="leadForm">

      ${
        isLongText
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
              type="${questionId === "email" ? "email" : "text"}"
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
      if(e.key === "Enter" && !e.shiftKey && !isLongText){
        e.preventDefault();
        submitTextAnswer();
      }
    });
  }
}

async function botAsk(){
  updateBar();

  const total = PRE_QUESTIONS.length + PROFILE_QUESTIONS.length + QUESTIONS.length;

  if(phase === "pre"){
    if(preStep >= PRE_QUESTIONS.length){
      phase = "profile";
      return botAsk();
    }

    const q = PRE_QUESTIONS[preStep];
    const current = preStep + 1;

    await addBotMsgTyped(
      `
      <div class="questionPill">
        ${current} / ${total}
      </div>

      <div class="questionText">
        ${q.label}
      </div>
      `,
      "bubbleQuestion"
    );

    renderTextInput(q.id);
    return;
  }

  const current =
    phase === "profile"
      ? PRE_QUESTIONS.length + profileStep + 1
      : PRE_QUESTIONS.length + PROFILE_QUESTIONS.length + step + 1;

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

  const q = PRE_QUESTIONS[preStep];

  if(q.id === "email"){
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if(!emailRegex.test(value)){
      alert("Merci d’indiquer une adresse email valide.");
      return;
    }
  }

  locked = true;

  preAnswers[q.id] = value;
  preStep++;

  choices.innerHTML = "";

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

async function finishDiagnostic(){
  choices.innerHTML = "";

  await addBotMsgTyped(
    `⏳ Préparation de ta synthèse...`
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

  await unlockResults();
}

async function unlockResults(){
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
    1) ${finalData.top3[0]}<br>
    2) ${finalData.top3[1]}<br>
    3) ${finalData.top3[2]}
    `
  );

  await sleep(400);

  await addBotMsgTyped(
    `
    👉 Si rien ne change :
    <br><br>
    • tu resteras le point de passage obligé<br>
    • ta charge continuera d’augmenter<br>
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
        • moins de tâches qui reviennent vers toi<br>
        • moins de charge mentale<br>
        • plus de capacité sans augmenter ton temps
      </div>

      <div style="margin-top:18px;font-weight:900;">
        👉 Objectif : te libérer du temps ET débloquer ta croissance
      </div>

      <div style="margin-top:18px;color:#355CFF;font-weight:900;">
        👉 Si rien ne change, certaines opportunités continueront d’arriver…
        sans pouvoir être réellement exploitées
      </div>

      <div style="margin-top:18px;color:var(--muted);font-weight:800;">
        📩 Ta synthèse complète vient de t’être envoyée par mail.
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

  chat.innerHTML = "";
  choices.innerHTML = "";

  updateBar();
  botAsk();
}

restartBtn.onclick = reset;

reset();
