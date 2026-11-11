# Suivi de la grille /20 (TD6, soutenance)

Règle d'équipe : **chaque choix et chaque réponse doit pouvoir être relié à une ligne de ce tableau.**
Statut : ✅ preuve disponible · 🟡 partiel · ⬜ à venir. Mettre à jour à la fin de chaque TD.

| # | Critère (1 pt chacun) | Preuve dans le dépôt | Statut | TD |
|---|---|---|---|---|
| 1 | Problem definition | TD4 : scheduler (décide) séparé de l'orchestrateur (exécute) ; entrées `tasks.csv` + `machines.csv`, sortie `allocation_*.csv` (`docs/TD4_ANSWERS.md`) ; objectif proposé D36 | 🟡 à formaliser en TD5 | 4–5 |
| 2 | Workload and resource model | `docs/WORKLOADS.md`, profils `data/workload_profile_{local,cloud_vm1,cloud_vm1_std2}.csv`, fiches machine `data/machine_*.txt` + `data/vm_cloud_vm1.txt`, **matrice `data/p_matrix.csv`** (D22), RSS identique sur 3 machines → m_i indépendant de la VM | ✅ 3 machines mesurées | 1–2 |
| 3 | Architecture clarity | schéma tasks + machines → scheduler → allocation CSV → run_all → run_task → VMs → results (`docs/TD4_ANSWERS.md`) ; scheduler branché **sans modifier** l'orchestrateur (D23, D34) | ✅ | 3–4 |
| 4 | Design choices (trade-offs) | `docs/DECISIONS.md` D1–D22 : réutiliser les VMs (D13), déploiement par commit (D15), réseau minimal (D18), cycle de vie (D19), **coût/performance e2-medium vs e2-standard-2 chiffré** (D21) | 🟡 à poursuivre | tous |
| 5 | Deployment on GCP VMs | TD2 : `gcp.sh deploy/setup` sur vm1 (72 runs). TD3 : `deploy_all.sh`, mêmes binaires statiques sur les 3 VMs, md5 identiques, test de fumée des 4 workloads OK (D28) | ✅ | 2–3 |
| 6 | Distributed execution, parallel | `run_all.sh` : 1 SSH par tâche, `&`, un seul `wait` (D24). Réel 2026-11-11 : 9 tâches sur 3 VMs, `ps` montre 3 processus simultanés par VM, puis 7 sur vm1 (~29 % CPU chacun = 2 vCPU / 7) ; `results/td3/` | ✅ | 3 |
| 7 | Orchestration and result collection | `run_task.sh` : .out/.err/.meta par tâche sur le contrôleur, `remote_host` prouve le placement ; `check_results.sh` (6 points du TD) : `CHECK OK 9/9` × 2 allocations, test d'échec visible et exit 1 (D26–D27) | ✅ | 2–3 |
| 8 | Technical quality and reproducibility | `Makefile` (`TAG=`, `compare`, `memprobe`, `pmatrix`, `figures`), infra dans `config/gcp.env`, commit tracé dans `campaign_meta_*.txt`, README section TD2 | ✅ | tous |
| 9 | Problem formulation (inputs, variables) | entrées séparées `tasks.csv` / `machines.csv` (D31) ; p_ij, m_i, capacités `data/vm_profile.csv` prêts (D35) ; variable x_ij à écrire | 🟡 | 4–5 |
| 10 | Constraints | somme des RSS ≤ RAM de la VM ; `estimate_alloc.sh` détecte un plan RR infaisable (`tasks_ram_trap.csv`, 4,1 Go sur 4 Go, D35) | 🟡 vérifiée, à intégrer au scheduler TD5 | 4–5 |
| 11 | Objective(s) | proposé : makespan sous contrainte de RAM, coût relevé (D36) | 🟡 à valider en équipe | 4–5 |
| 12 | Method justification (lien CM) | — | ⬜ | 4–5 |
| 13 | Integration and validity (allocation exécutable) | 3 niveaux : `check_allocation.sh` (sortie du scheduler, sans VM) → `run_all.sh` (avant lancement, D25) → `check_results.sh` (après, D27) ; `test_scheduler.sh` 14/14 (D33) ; run réel `results/td4/` : 2 allocations générées, `CHECK OK 9/9` chacune | ✅ (RR) ; à refaire avec le scheduler TD5 | 3–5 |
| 14 | Baseline | `scheduler/round_robin.go` (Go), `allocation_rr.csv` = allocation manuelle TD3 ; limites chiffrées : ordre 20,6 → 36,4 s de charge goulot, plan RAM infaisable (D32, D35) ; mesuré : 15,8 s (= TD3 17,6 s), 18,7 s si on change l'ordre | ✅ | 4 |
| 15 | Metrics quality (conditions cohérentes) | mêmes binaires, tailles, runner, ordre entrelacé sur 3 machines (D16) ; CV reporté partout ; **expérience témoin** à variable unique (D21) | ✅ | 1–5 |
| 16 | Baseline vs optimized comparison | — | ⬜ | 5 |
| 17 | Interpretation and limitations | burst du cœur partagé expliqué et confirmé (D21) ; anomalie memory_task testée et résolue (D20, huge pages) ; limites TD2 listées (compilateur, OS, plateforme E2) | ✅ TD2, à prolonger | tous |
| 18 | Clarity and structure (oral) | — | ⬜ | 6 |
| 19 | Demonstration and visual evidence | `results/td2_machines.png` (3 machines + burst), `results/compare_*.md`, `results/summary_*.md` | 🟡 schéma d'archi à venir | 2–6 |
| 20 | Q&A and team mastery | `docs/*` sert de support de révision aux 3 membres | 🟡 | 6 |

Rappel de la grille : « A sophisticated optimization method does not compensate for a non-functional distributed system… Results must be supported by actual measurements. »
