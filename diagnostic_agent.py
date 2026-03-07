#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diagnostic Automatisation (Agent IA - version Python)
- 7 questions (A/B/C/D)
- Score 0..21
- Sortie : niveau + synthèse + 3 priorités + next step
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass(frozen=True)
class Question:
    key: str
    prompt: str
    options: Dict[str, str]  # "A".."D" -> label
    weights: Dict[str, int]  # "A".."D" -> points


DEFAULT_WEIGHTS = {"A": 0, "B": 1, "C": 2, "D": 3}


QUESTIONS: List[Question] = [
    Question(
        key="dependance",
        prompt="1) Si vous arrêtez de travailler pendant 3 jours, que se passe-t-il ?",
        options={
            "A": "Rien ne se passe (ça tourne).",
            "B": "Quelques tâches s'accumulent, mais ça va.",
            "C": "Certaines tâches bloquent / retards clients.",
            "D": "Tout s'arrête.",
        },
        weights=DEFAULT_WEIGHTS,
    ),
    Question(
        key="leads",
        prompt="2) Où arrivent vos nouveaux prospects aujourd'hui ?",
        options={
            "A": "Automatiquement dans un CRM.",
            "B": "Dans un tableur (ou outil central) + un peu de manuel.",
            "C": "Dans la messagerie / DM / notes éparses.",
            "D": "Je n'ai pas de système clair.",
        },
        weights=DEFAULT_WEIGHTS,
    ),
    Question(
        key="onboarding",
        prompt="3) Quand un client signe, l'onboarding se passe comment ?",
        options={
            "A": "Automatisé (contrat/paiement/accès/infos).",
            "B": "Semi-automatisé (une partie reste manuelle).",
            "C": "Plutôt manuel (checklists, copier-coller, etc.).",
            "D": "C'est souvent le chaos / ça dépend.",
        },
        weights=DEFAULT_WEIGHTS,
    ),
    Question(
        key="outils",
        prompt="4) Combien d'outils utilisez-vous pour gérer votre activité ?",
        options={
            "A": "1 à 3",
            "B": "4 à 6",
            "C": "7 à 10",
            "D": "10+",
        },
        weights=DEFAULT_WEIGHTS,
    ),
    Question(
        key="repetitif",
        prompt="5) Combien de tâches répétitives faites-vous manuellement chaque semaine ?",
        options={
            "A": "0 à 2",
            "B": "3 à 5",
            "C": "6 à 10",
            "D": "10+",
        },
        weights=DEFAULT_WEIGHTS,
    ),
    Question(
        key="process",
        prompt="6) Vos process sont-ils documentés et structurés ?",
        options={
            "A": "Oui, clairement.",
            "B": "Partiellement.",
            "C": "Non.",
            "D": "C'est dans ma tête.",
        },
        weights=DEFAULT_WEIGHTS,
    ),
    Question(
        key="frein",
        prompt="7) Votre frein principal aujourd'hui ?",
        options={
            "A": "Manque de leads / visibilité.",
            "B": "Manque de temps.",
            "C": "Trop d'opérationnel / trop de tâches.",
            "D": "Organisation floue / trop d'outils / pas de système.",
        },
        weights=DEFAULT_WEIGHTS,
    ),
]


def ask_mcq(q: Question) -> str:
    print("\n" + q.prompt)
    for k in ["A", "B", "C", "D"]:
        print(f"  {k}) {q.options[k]}")
    while True:
        ans = input("Votre réponse (A/B/C/D) : ").strip().upper()
        if ans in q.options:
            return ans
        print("Réponse invalide. Tapez A, B, C ou D.")


def score_answers(answers: Dict[str, str]) -> int:
    total = 0
    for q in QUESTIONS:
        total += q.weights[answers[q.key]]
    return total


def level_from_score(score: int) -> Tuple[str, str]:
    # 0..21
    if score <= 7:
        return ("Niveau 1", "Business très dépendant de vous")
    if score <= 14:
        return ("Niveau 2", "Automatisations partielles (base existante)")
    return ("Niveau 3", "Bonne base (optimisation & scaling)")


def top_priorities(answers: Dict[str, str], score: int) -> List[str]:
    """
    Reco rule-based simple (sans IA externe).
    On priorise : leads -> onboarding -> suivi.
    """
    recos = []

    # Leads
    if answers["leads"] in ("C", "D"):
        recos.append("Système Leads : formulaire/DM → capture → tagging → CRM → email de réponse automatique.")
    else:
        recos.append("Système Leads : standardiser pipeline (stades, tags, relances) + automatiser la qualification.")

    # Onboarding
    if answers["onboarding"] in ("C", "D"):
        recos.append("Système Onboarding : contrat + paiement + email de bienvenue + accès + checklist automatique.")
    else:
        recos.append("Système Onboarding : consolider (templates, automatisations, centralisation infos client).")

    # Opérations / suivi
    if answers["repetitif"] in ("C", "D") or answers["process"] in ("C", "D"):
        recos.append("Système Suivi/Opérations : rappels, relances, tâches récurrentes, documentation (SOP) + automatisations.")
    else:
        recos.append("Système Suivi/Opérations : améliorer reporting, rappels, relances et standardisation des SOP.")

    # Si trop d'outils, on ajoute une note
    if answers["outils"] in ("C", "D"):
        recos.append("Rationalisation outils : réduire la stack, choisir 1 hub (CRM/Notion) + connexions propres via API/no-code.")
    return recos[:3]


def short_diagnosis(answers: Dict[str, str], score: int) -> str:
    level, subtitle = level_from_score(score)

    # 2 phrases max
    if level == "Niveau 1":
        return (
            "Votre activité repose encore beaucoup sur vous : si vous ralentissez, le système ralentit (ou s'arrête). "
            "Priorité : construire un flux simple et robuste (leads → onboarding → suivi) avant d'ajouter plus d'outils."
        )
    if level == "Niveau 2":
        return (
            "Vous avez déjà une base, mais certains points restent manuels et créent des goulots d'étranglement. "
            "Priorité : automatiser les étapes répétitives et standardiser vos process pour gagner du temps et scaler sereinement."
        )
    return (
        "Votre base est saine : vous pouvez maintenant optimiser pour la fiabilité, la qualité et la scalabilité. "
        "Priorité : renforcer les automatisations critiques (leads/onboarding/suivi) et réduire la complexité outil."
    )


def next_step_cta(score: int) -> str:
    # Soft CTA, pas agressif
    return (
        "Prochaine étape (optionnelle) : si vous voulez, répondez avec votre activité + vos outils actuels "
        "(ex : Notion/Calendly/Stripe/HubSpot/Make) et je vous indique les 5 automatisations les plus rentables à déployer."
    )


def run_interactive():
    print("=== Diagnostic Automatisation (2 minutes) ===")
    print("Répondez A/B/C/D. À la fin : score + recommandations.\n")

    answers: Dict[str, str] = {}
    for q in QUESTIONS:
        answers[q.key] = ask_mcq(q)

    total = score_answers(answers)
    level, subtitle = level_from_score(total)

    print("\n" + "=" * 52)
    print(f"Résultat : {total}/21 — {level} ({subtitle})")
    print("-" * 52)
    print(short_diagnosis(answers, total))
    print("\nTop 3 priorités :")
    for i, r in enumerate(top_priorities(answers, total), start=1):
        print(f"{i}. {r}")

    print("\n" + next_step_cta(total))
    print("=" * 52)
    print("\nMot-clé LinkedIn : DM \"diagnostic\" pour tester.\n")


if __name__ == "__main__":
    run_interactive()