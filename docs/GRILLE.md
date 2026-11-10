# Suivi de la grille /20 (TD6, soutenance)

Règle d'équipe : **chaque choix et chaque réponse doit pouvoir être relié à une ligne de ce tableau.**
Statut : ✅ preuve disponible · 🟡 partiel · ⬜ à venir. Mettre à jour à la fin de chaque TD.

| # | Critère (1 pt chacun) | Preuve dans le dépôt | Statut | TD |
|---|---|---|---|---|
| 1 | Problem definition | README (question centrale), à formaliser | ⬜ | 4 |
| 2 | Workload and resource model | `docs/WORKLOADS.md`, `data/workload_profile_<tag>.csv` (durée, RSS, croissance), `data/machine_<tag>.txt` + `data/vm_cloud_vm1.txt` (type, plateforme CPU, zone), D13, D16 | 🟡 outillé, mesures VM à faire | 1–2 |
| 3 | Architecture clarity | schéma workloads / scheduler / orchestrateur / VMs | ⬜ | 3 |
| 4 | Design choices (trade-offs) | `docs/DECISIONS.md` (D1–D20 : zone, type E2 vs plateforme fixe, déploiement par commit, réseau minimal, stop vs delete) | 🟡 à poursuivre | tous |
| 5 | Deployment on GCP VMs | `config/gcp.env`, `scripts/gcp.sh create/deploy/setup` (D12, D15) ; preuve d'exécution = `data/benchmark_cloud_vm1.csv` | 🟡 scripts prêts, VM à créer | 2 |
| 6 | Distributed execution, parallel | — | ⬜ | 3 |
| 7 | Orchestration and result collection | `scripts/benchmark.sh`, `scripts/gcp.sh bench/fetch` (exécution distante non interactive + rapatriement, D17), CSV à schéma fixe (D4, D7) | 🟡 1 VM, multi-VM en TD3 | 2–3 |
| 8 | Technical quality and reproducibility | `Makefile` (`make all`, `TAG=`), README, md5 des sources (D2-bis), tailles dans `config/`, infra décrite dans `config/gcp.env`, commit déployé tracé (D15) | ✅ local, 🟡 cloud | tous |
| 9 | Problem formulation (inputs, variables) | p_ij et m_i issus des mesures (D9) | ⬜ | 4 |
| 10 | Constraints | RSS max = besoin mémoire → capacité VM (D3) | ⬜ | 4 |
| 11 | Objective(s) | makespan / coût | ⬜ | 4–5 |
| 12 | Method justification (lien CM) | — | ⬜ | 4–5 |
| 13 | Integration and validity (allocation exécutable) | — | ⬜ | 5 |
| 14 | Baseline | Round-Robin / manuel | ⬜ | 4 |
| 15 | Metrics quality (conditions cohérentes) | runs entrelacés, warm-up, CV 0,5–3,6 % (D6), environnement noté (D8), mêmes tailles et même runner local/cloud (D16), `results/compare_local_vs_cloud_vm1.md` | 🟡 | 1–5 |
| 16 | Baseline vs optimized comparison | — | ⬜ | 5 |
| 17 | Interpretation and limitations | `docs/DECISIONS.md` § Limites ; anomalie memory_task testée par `make memprobe` (D20) ; plateforme E2 non garantie, version de Go différente (D13, D15) ; `docs/TD2_ANSWERS.md` Part 12 | 🟡 | tous |
| 18 | Clarity and structure (oral) | — | ⬜ | 6 |
| 19 | Demonstration and visual evidence | `results/size_vs_runtime_rss_local.png`, `results/summary_local.md` | 🟡 | 2–6 |
| 20 | Q&A and team mastery | `docs/*` sert de support de révision aux 3 membres | 🟡 | 6 |

Rappel de la grille : « A sophisticated optimization method does not compensate for a non-functional distributed system… Results must be supported by actual measurements. »
