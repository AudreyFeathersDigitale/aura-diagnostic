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
    label: "Aujourd'hui, quelle tâche te prend le plus de temps dans ton business ?",
    type: "textarea"
  },
  {
    id: "why_gain_time",
    label: "Si tu récupérais 3 heures par semaine... qu’est-ce qui changerait le plus pour toi ?",
    type: "choice",
    options: {
      family: "Passer plus de temps avec ma famille et mes proches",
      freedom: "Pouvoir enfin décrocher quand ma journée est terminée",
      growth: "Développer davantage mon activité",
      serenity: "Retrouver plus de sérénité au quotidien"
    }
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
      label: "Aujourd'hui, quelle tâche te prend le plus de temps dans ton business ?",
      type: "textarea"
    };
  }

  if(question.id === "why_gain_time"){
    return {
      ...question,
      label: "Si tu récupérais 3 heures par semaine... qu’est-ce qui changerait le plus pour toi ?",
      type: "choice",
      options: {
        family: "Passer plus de temps avec ma famille et mes proches",
        freedom: "Pouvoir enfin décrocher quand ma journée est terminée",
        growth: "Développer davantage mon activité",
        serenity: "Retrouver plus de sérénité au quotidien"
      }
    };
  }

  return question;
});

if(!preQuestions.some((question) => question.id === "why_gain_time")){
  preQuestions.push({
    id: "why_gain_time",
    label: "Si tu récupérais 3 heures par semaine... qu’est-ce qui changerait le plus pour toi ?",
    type: "choice",
    options: {
      family: "Passer plus de temps avec ma famille et mes proches",
      freedom: "Pouvoir enfin décrocher quand ma journée est terminée",
      growth: "Développer davantage mon activité",
      serenity: "Retrouver plus de sérénité au quotidien"
    }
  });
}

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

    if(question.type === "choice"){
      renderChoices(question.options || {});
    } else {
      renderTextInput(question);
    }

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

  if(phase === "pre"){
    const question = preQuestions[preStep];

    if(!question || question.type !== "choice"){
      locked = false;
      return;
    }

    preAnswers[question.id] = value;
    preStep++;

    choices.innerHTML = "";

    await sleep(250);

    locked = false;
    botAsk();
    return;
  }

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

  try{
    const calculateResponse = await fetch("/calculate", {
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

    if(!calculateResponse.ok){
      throw new Error(
        `Erreur de calcul (${calculateResponse.status})`
      );
    }

    finalData = await calculateResponse.json();
  }catch(error){
    console.error("Erreur /calculate :", error);

    await addBotMsgTyped(
      `
      <div class="resultCard">
        <div class="leftTitle">
          Une erreur est survenue pendant le calcul.
        </div>

        <div style="margin-top:12px;line-height:1.6;">
          Merci de recommencer le diagnostic.
        </div>
      </div>
      `
    );

    locked = false;
    return;
  }

  finalData.email_sent = false;
  finalData.email_error = "";

  try{
    const saveResponse = await fetch("/save-lead", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name: preAnswers.name || preAnswers.nom || "",
        email: preAnswers.email || "",
        repetitive_tasks: preAnswers.main_time_pain || preAnswers.tasks || "",
        why_gain_time: preAnswers.why_gain_time || "",
        answers,
        profile: profileAnswers,
        lead: preAnswers,
        result: finalData
      })
    });

    let saveData = {};

    try{
      saveData = await saveResponse.json();
    }catch(parseError){
      console.error("Réponse /save-lead non JSON :", parseError);
    }

    finalData.email_sent =
      saveResponse.ok &&
      saveData.ok === true &&
      saveData.email_sent === true;

    if(!finalData.email_sent){
      finalData.email_error =
        saveData.error ||
        saveData.webhook?.error ||
        "L’envoi du mail n’a pas pu être confirmé.";

      console.error("Erreur /save-lead :", {
        status: saveResponse.status,
        data: saveData
      });
    }
  }catch(error){
    finalData.email_sent = false;
    finalData.email_error = error.message;
    console.error("Erreur réseau /save-lead :", error);
  }

  await showMiniSummary();
}

async function showMiniSummary(){
  chat.innerHTML = "";
  choices.innerHTML = "";

  const firstName = preAnswers.name || preAnswers.nom || "";
  const email = preAnswers.email || "ton adresse email";

  const scoreClass =
    finalData.dependency_pct >= 70
      ? "danger"
      : finalData.dependency_pct >= 45
      ? "warning"
      : "good";

  const lostMin = finalData.lost_clients_min ?? 0;
  const lostMax = finalData.lost_clients_max ?? 0;

  await addBotMsgTyped(
    `
    <div class="scoreHero">
      <div style="font-size:20px;font-weight:900;">
        ${firstName ? `${firstName}...` : "Ton diagnostic..."}
      </div>

      <div style="margin-top:10px;font-size:18px;font-weight:900;">
        Ton diagnostic est sans appel.
      </div>

      <div class="scorePercent ${scoreClass}">
        ${finalData.dependency_pct}% — ${finalData.level}
      </div>

      <div style="margin-top:16px;line-height:1.65;">
        Aujourd’hui, ton entreprise repose encore beaucoup trop sur toi.
        <br><br>
        Au fond... tu le savais probablement déjà.
        <br><br>
        <b>Sans toi, ton business ralentit.</b>
        <br><br>
        Tu n’es pas seulement à la tête de ton entreprise.
        <b>Aujourd’hui, c’est encore toi qui la fais avancer.</b>
      </div>
    </div>
    `
  );

  await sleep(500);

  await addBotMsgTyped(
    `
    <div class="resultCard">
      <div class="leftTitle">
        ⚠️ Le vrai coût n’est pas celui que tu imagines.
      </div>

      <div style="margin-top:14px;line-height:1.7;">
        Ce ne sont pas seulement des heures de travail.
        <br><br>
        ❤️ <b>Ce sont des moments avec tes proches où tu es là... sans vraiment être là.</b>
        <br><br>
        ❤️ <b>Des soirées où ton ordinateur est fermé... mais ton business continue de tourner dans ta tête.</b>
        <br><br>
        📈 <b>Et pendant que ton temps est absorbé par le quotidien, entre ${lostMin} et ${lostMax} opportunités de développement passent probablement à côté de toi.</b>
      </div>
    </div>
    `
  );

  await sleep(500);

  await addBotMsgTyped(
    `
    <div class="resultCard">
      <div class="leftTitle">
        ${
          finalData.email_sent
            ? "📩 Je viens de t’envoyer ton analyse complète par email."
            : "📩 Ton analyse complète est prête."
        }
      </div>

      <div style="margin-top:14px;line-height:1.7;">
        Tu y découvriras :
        <br><br>
        ✅ <b>Pourquoi ton business dépend encore autant de toi.</b>
        <br><br>
        ✅ <b>Les habitudes qui entretiennent cette dépendance au quotidien.</b>
        <br><br>
        ✅ <b>Les 3 premiers leviers pour retrouver du temps, sans freiner la croissance de ton activité.</b>
      </div>

      <div style="margin-top:20px;padding-top:18px;border-top:1px solid rgba(0,0,0,.08);line-height:1.7;font-weight:900;">
        Tu as réussi à construire un business qui te fait vivre.
        <br><br>
        Maintenant, il est temps de construire un business qui puisse aussi te laisser vivre.
      </div>

      <div style="margin-top:18px;color:var(--muted);font-weight:800;">
        ${
          finalData.email_sent
            ? `Analyse envoyée à : <b>${email}</b>`
            : `
              L’envoi automatique n’a pas pu être confirmé.
              Vérifie ton adresse ou réessaie dans quelques instants.
            `
        }
      </div>
    </div>
    `
  );

  choices.innerHTML = `
    <a
      href="${LINKEDIN_URL}"
      target="_blank"
      rel="noopener noreferrer"
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