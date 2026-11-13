# Suivi de la grille /20 (TD6, soutenance)

Règle d'équipe : **chaque choix et chaque réponse doit pouvoir être relié à une ligne de ce tableau.**
Statut : ✅ preuve disponible · 🟡 partiel · ⬜ à venir. Mettre à jour à la fin de chaque TD.

| # | Critère (1 pt chacun) | Preuve dans le dépôt | Statut | TD |
|---|---|---|---|---|
| 1 | Problem definition | scheduler (décide) séparé de l'orchestrateur (exécute) ; entrées `tasks.csv` + `vms.csv`, sortie `allocation_*.csv` ; objectif : makespan sous RAM (D37, `docs/OPTIMIZATION.md` §1) | ✅ | 4–P |
| 2 | Workload and resource model | `docs/WORKLOADS.md`, profils `data/workload_profile_{local,cloud_vm1,cloud_vm1_std2}.csv`, fiches machine `data/machine_*.txt` + `data/vm_cloud_vm1.txt`, **matrice `data/p_matrix.csv`** (D22), RSS identique sur 3 machines → m_i indépendant de la VM | ✅ 3 machines mesurées | 1–2 |
| 3 | Architecture clarity | schéma tasks + machines → scheduler → allocation CSV → run_all → run_task → VMs → results (`docs/TD4_ANSWERS.md`) ; scheduler branché **sans modifier** l'orchestrateur (D23, D34) | ✅ | 3–4 |
| 4 | Design choices (trade-offs) | `docs/DECISIONS.md` D1–D22 : réutiliser les VMs (D13), déploiement par commit (D15), réseau minimal (D18), cycle de vie (D19), **coût/performance e2-medium vs e2-standard-2 chiffré** (D21) | 🟡 à poursuivre | tous |
| 5 | Deployment on GCP VMs | TD2 : `gcp.sh deploy/setup` sur vm1 (72 runs). TD3 : `deploy_all.sh`, mêmes binaires statiques sur les 3 VMs, md5 identiques, test de fumée des 4 workloads OK (D28) | ✅ | 2–3 |
| 6 | Distributed execution, parallel | `run_all.sh` : 1 SSH par tâche, `&`, un seul `wait` (D24). Réel 2026-11-11 : 9 tâches sur 3 VMs, `ps` montre 3 processus simultanés par VM, puis 7 sur vm1 (~29 % CPU chacun = 2 vCPU / 7) ; `results/td3/` | ✅ | 3 |
| 7 | Orchestration and result collection | `run_task.sh` : .out/.err/.meta par tâche sur le contrôleur, `remote_host` prouve le placement ; `check_results.sh` (6 points du TD) : `CHECK OK 9/9` × 2 allocations, test d'échec visible et exit 1 (D26–D27) | ✅ | 2–3 |
| 8 | Technical quality and reproducibility | `Makefile` (`TAG=`, `compare`, `memprobe`, `pmatrix`, `figures`), infra dans `config/gcp.env`, commit tracé dans `campaign_meta_*.txt`, README section TD2 | ✅ | tous |
| 9 | Problem formulation (inputs, variables) | données `p_ij`, `m_i`, `RAM_j`, `c_j`, SSH ; variables `x_ij` ; modèle de durée calibré sur 12 mesures, erreur 0,78 s (D38, `docs/OPTIMIZATION.md` §1) | ✅ | 4–P |
| 10 | Constraints | `Σ_j x_ij = 1`, `Σ m_i x_ij ≤ RAM_j − 512 Mo`, ≤ 10 tâches par VM (sshd) ; vérifiées à chaque placement (D43) ; piège RAM : RR refusé, `opt` faisable (test 4) | ✅ | 4–P |
| 11 | Objective(s) | makespan prédit, égalités départagées par leximax (plan le plus équilibré) ; coût € discuté à part (D21) | ✅ | P |
| 12 | Method justification (lien CM) | `opt` : glouton CM3 → recherche locale CM5 → borne + branch and bound CM4 ; pourquoi pas l'énumération (`M^N`) ni un ILP (modèle non linéaire) (D39, D40) ; qualité mesurée : optimum 39/40, 1000 tâches en 10 s (D41, `results/scaling.md`) | ✅ | P |
| 13 | Integration and validity (allocation exécutable) | 3 niveaux : `check_allocation.sh` → `run_all.sh` (D25) → `check_results.sh` (D27) ; `test_scheduler.sh` 14/14, `test_optimizer.sh` 48/48 (dont optimum = force brute indépendante) ; run réel RR `results/td4/` | ✅ (RR) ; run réel `opt` à faire (`make opt-run`) | 3–P |
| 14 | Baseline | `scheduler/round_robin.go` (Go), `allocation_rr.csv` = allocation manuelle TD3 ; limites chiffrées : ordre 20,6 → 36,4 s de charge goulot, plan RAM infaisable (D32, D35) ; mesuré : 15,8 s (= TD3 17,6 s), 18,7 s si on change l'ordre | ✅ | 4 |
| 15 | Metrics quality (conditions cohérentes) | mêmes binaires, tailles, runner, ordre entrelacé sur 3 machines (D16) ; CV reporté partout ; **expérience témoin** à variable unique (D21) | ✅ | 1–5 |
| 16 | Baseline vs optimized comparison | prédit : A 15,7 → 12,6 s (−20 %), B 20,2 → 15,9 s (−21 %) ; sur 40 instances : RR à 56 % de l'optimum, `opt` à 0 % (D41, D42) | 🟡 mesures réelles à faire (`make opt-run`) | P |
| 17 | Interpretation and limitations | burst du cœur partagé expliqué et confirmé (D21) ; anomalie memory_task testée et résolue (D20, huge pages) ; limites TD2 listées (compilateur, OS, plateforme E2) | ✅ TD2, à prolonger | tous |
| 18 | Clarity and structure (oral) | — | ⬜ | 6 |
| 19 | Demonstration and visual evidence | `results/td2_machines.png` (3 machines + burst), `results/compare_*.md`, `results/summary_*.md` | 🟡 schéma d'archi à venir | 2–6 |
| 20 | Q&A and team mastery | `docs/*` sert de support de révision aux 3 membres | 🟡 | 6 |

Rappel de la grille : « A sophisticated optimization method does not compensate for a non-functional distributed system… Results must be supported by actual measurements. »
