# Suivi de la grille /20 (TD6, soutenance)

Règle d'équipe : **chaque choix et chaque réponse doit pouvoir être relié à une ligne de ce tableau.**
Statut : ✅ preuve disponible · 🟡 partiel · ⬜ à venir. Mettre à jour à la fin de chaque TD.

| # | Critère (1 pt chacun) | Preuve dans le dépôt | Statut | TD |
|---|---|---|---|---|
| 1 | Problem definition | README (question centrale), à formaliser | ⬜ | 4 |
| 2 | Workload and resource model | `docs/WORKLOADS.md`, profils `data/workload_profile_{local,cloud_vm1,cloud_vm1_std2}.csv`, fiches machine `data/machine_*.txt` + `data/vm_cloud_vm1.txt`, **matrice `data/p_matrix.csv`** (D22), RSS identique sur 3 machines → m_i indépendant de la VM | ✅ 3 machines mesurées | 1–2 |
| 3 | Architecture clarity | schéma workloads / scheduler / orchestrateur / VMs | ⬜ | 3 |
| 4 | Design choices (trade-offs) | `docs/DECISIONS.md` D1–D22 : réutiliser les VMs (D13), déploiement par commit (D15), réseau minimal (D18), cycle de vie (D19), **coût/performance e2-medium vs e2-standard-2 chiffré** (D21) | 🟡 à poursuivre | tous |
| 5 | Deployment on GCP VMs | `scripts/gcp.sh deploy/setup` : commit `73f665c` déployé, compilé sur la VM (md5 identiques), 72 runs exécutés sur `cloudopt-vm1` (`data/benchmark_cloud_vm1*.csv`) | ✅ 1 VM, 3 en TD3 | 2 |
| 6 | Distributed execution, parallel | — | ⬜ | 3 |
| 7 | Orchestration and result collection | `scripts/gcp.sh bench/fetch` : campagne lancée à distance sans shell interactif, résultats rapatriés ; attente du SSH après démarrage (D17, D21) | 🟡 1 VM, multi-VM en TD3 | 2–3 |
| 8 | Technical quality and reproducibility | `Makefile` (`TAG=`, `compare`, `memprobe`, `pmatrix`, `figures`), infra dans `config/gcp.env`, commit tracé dans `campaign_meta_*.txt`, README section TD2 | ✅ | tous |
| 9 | Problem formulation (inputs, variables) | p_ij et m_i issus des mesures (D9) | ⬜ | 4 |
| 10 | Constraints | RSS max = besoin mémoire → capacité VM (D3) | ⬜ | 4 |
| 11 | Objective(s) | makespan / coût | ⬜ | 4–5 |
| 12 | Method justification (lien CM) | — | ⬜ | 4–5 |
| 13 | Integration and validity (allocation exécutable) | — | ⬜ | 5 |
| 14 | Baseline | Round-Robin / manuel | ⬜ | 4 |
| 15 | Metrics quality (conditions cohérentes) | mêmes binaires, tailles, runner, ordre entrelacé sur 3 machines (D16) ; CV reporté partout ; **expérience témoin** à variable unique (D21) | ✅ | 1–5 |
| 16 | Baseline vs optimized comparison | — | ⬜ | 5 |
| 17 | Interpretation and limitations | burst du cœur partagé expliqué et confirmé (D21) ; anomalie memory_task testée et résolue (D20, huge pages) ; limites TD2 listées (compilateur, OS, plateforme E2) | ✅ TD2, à prolonger | tous |
| 18 | Clarity and structure (oral) | — | ⬜ | 6 |
| 19 | Demonstration and visual evidence | `results/td2_machines.png` (3 machines + burst), `results/compare_*.md`, `results/summary_*.md` | 🟡 schéma d'archi à venir | 2–6 |
| 20 | Q&A and team mastery | `docs/*` sert de support de révision aux 3 membres | 🟡 | 6 |

Rappel de la grille : « A sophisticated optimization method does not compensate for a non-functional distributed system… Results must be supported by actual measurements. »
