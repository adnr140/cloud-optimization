# Cloud Optimization — projet semestriel (ESILV A5 CCC)

Ordonnancement de tâches sur des VMs GCP. Ce dépôt suit les TD : **TD1 (workloads locaux et benchmarking) est terminé**.

Équipe : _3 noms_ · Distribution Linux : Ubuntu 26.04.1 LTS (WSL2) · Machine : voir `data/machine_local.txt`

## Installation (référence Ubuntu)
```bash
sudo apt update
sudo apt install -y git make build-essential time golang-go
# optionnel : graphe
sudo apt install -y python3-matplotlib
make check            # vérifie git, make, gcc, go, GNU time
```
Autre distribution : installer les mêmes outils (git, make, gcc, Go, GNU time) avec son gestionnaire de paquets.

## Arborescence
```
workloads/   sources Go fournies (cpu_task, memory_task, matrix_task, sort_task) — non modifiées
bin/         binaires natifs (make build)
config/      campaign.conf : tailles small/medium/large par workload
scripts/     benchmark.sh (1 workload, 1 taille, N runs), campaign.sh, calibrate.sh, machine_info.sh, analyze.sh, plot.py
data/        machine_local.txt, benchmark_local.csv (brut), campaign_meta.txt, workload_profile_local.csv, raw/*.log
results/     summary.md, size_vs_runtime_rss.png
docs/        DECISIONS.md (journal des choix), ENVIRONMENT.md, WORKLOADS.md, TD1_ANSWERS.md
```

## Reproduire toute l'expérience
```bash
make machine          # -> data/machine_local.txt
make build            # go build -> bin/
make calibrate        # 1 run par taille, signale les runs < 1 s ou > 30 s ; ajuster config/campaign.conf
make bench            # 3 runs entrelacés + 1 warm-up -> data/benchmark_local.csv
make analyze          # -> results/summary.md, data/workload_profile_local.csv, graphe
# ou tout d'un coup : make all
```
Pendant `make bench` : portable sur secteur, applications lourdes fermées.

## Lancer un benchmark à la main
```bash
scripts/benchmark.sh -w cpu_task -s 500000 -r 3          # ajoute 3 lignes à data/benchmark_local.csv
scripts/benchmark.sh -w matrix_task -s 400 -r 5 -o /tmp/test.csv
scripts/benchmark.sh -h
```
Erreurs détectées : binaire absent ou non exécutable, taille non entière, GNU time absent, en-tête CSV différent, exécution en échec (aucune ligne écrite dans ce cas).

## Format du CSV
`workload,size,run,runtime_s,max_rss_kb` — une ligne par exécution. `runtime_s` = temps mur (GNU time `%e`), `max_rss_kb` = RSS max (GNU time `%M`).

## Résultats TD1 (Ryzen 7 7840HS, WSL2, 36 runs, CV 0,5–3,6 %)
| workload | tailles | temps moyen (s) | RSS max | croissance mesurée |
|---|---|---|---|---|
| cpu_task | 5M / 10M / 20M | 0,97 / 2,58 / 6,83 | ~2,5 Mo | N^1,41 |
| memory_task | 512 / 1024 / 2048 Mo | 0,90 / 1,48 / 2,73 | = taille | sous-linéaire (à expliquer) |
| matrix_task | 1000 / 1500 / 2000 | 1,08 / 3,85 / 9,37 | 26–94 Mo | N^3,1 |
| sort_task | 10M / 20M / 40M | 1,43 / 3,07 / 6,25 | 79–308 Mo | ≈ n log n |

Détail : [results/summary.md](results/summary.md), [graphe](results/size_vs_runtime_rss.png).
Choix techniques et justifications : [docs/DECISIONS.md](docs/DECISIONS.md). Réponses aux questions : [docs/TD1_ANSWERS.md](docs/TD1_ANSWERS.md). Workloads : [docs/WORKLOADS.md](docs/WORKLOADS.md). Environnement : [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md).
