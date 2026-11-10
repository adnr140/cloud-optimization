# Suivi de la grille /20 (TD6, soutenance)

Règle d'équipe : **chaque choix et chaque réponse doit pouvoir être relié à une ligne de ce tableau.**
Statut : ✅ preuve disponible · 🟡 partiel · ⬜ à venir. Mettre à jour à la fin de chaque TD.

| # | Critère (1 pt chacun) | Preuve dans le dépôt | Statut | TD |
|---|---|---|---|---|
| 1 | Problem definition | README (question centrale), à formaliser | ⬜ | 4 |
| 2 | Workload and resource model | `docs/WORKLOADS.md`, `data/workload_profile_local.csv` (durée, RSS, croissance), `data/machine_local.txt` | 🟡 workloads OK, VMs à venir | 1–2 |
| 3 | Architecture clarity | schéma workloads / scheduler / orchestrateur / VMs | ⬜ | 3 |
| 4 | Design choices (trade-offs) | `docs/DECISIONS.md` (D1–D11, alternatives écartées) | 🟡 à poursuivre | tous |
| 5 | Deployment on GCP VMs | binaires statiques prêts (D2) | ⬜ | 2 |
| 6 | Distributed execution, parallel | — | ⬜ | 3 |
| 7 | Orchestration and result collection | `scripts/benchmark.sh` réutilisable à distance, CSV à schéma fixe (D4, D7) | 🟡 | 3 |
| 8 | Technical quality and reproducibility | `Makefile` (`make all`), README, md5 des sources (D2-bis), tailles dans `config/` | ✅ local | tous |
| 9 | Problem formulation (inputs, variables) | p_ij et m_i issus des mesures (D9) | ⬜ | 4 |
| 10 | Constraints | RSS max = besoin mémoire → capacité VM (D3) | ⬜ | 4 |
| 11 | Objective(s) | makespan / coût | ⬜ | 4–5 |
| 12 | Method justification (lien CM) | — | ⬜ | 4–5 |
| 13 | Integration and validity (allocation exécutable) | — | ⬜ | 5 |
| 14 | Baseline | Round-Robin / manuel | ⬜ | 4 |
| 15 | Metrics quality (conditions cohérentes) | runs entrelacés, warm-up, CV 0,5–3,6 % (D6), environnement noté (D8) | 🟡 local | 1–5 |
| 16 | Baseline vs optimized comparison | — | ⬜ | 5 |
| 17 | Interpretation and limitations | `docs/DECISIONS.md` § Limites ; anomalie memory_task sous-linéaire (`docs/TD1_ANSWERS.md`) | 🟡 | tous |
| 18 | Clarity and structure (oral) | — | ⬜ | 6 |
| 19 | Demonstration and visual evidence | `results/size_vs_runtime_rss.png`, `results/summary.md` | 🟡 | 2–6 |
| 20 | Q&A and team mastery | `docs/*` sert de support de révision aux 3 membres | 🟡 | 6 |

Rappel de la grille : « A sophisticated optimization method does not compensate for a non-functional distributed system… Results must be supported by actual measurements. »
