# Journal des décisions techniques

Chaque décision suit le même format : **choix**, **pourquoi** (lien cours / grille), **alternative écartée**, **ce qu'on dira à l'oral**.
Les critères de la grille /20 sont notés `[G: critère]`.

---

## TD1 — Workloads locaux et benchmarking

### D1. Un `Makefile` comme point d'entrée unique
- **Choix** : `make check → machine → build → calibrate → bench → analyze` (ou `make all`). Arborescence imposée par le TD (`workloads/ bin/ data/ results/ scripts/`) + `config/`.
- **Pourquoi** : « another person can rebuild and rerun the experiment » (principes d'évaluation). Une seule commande, même chaîne sur notre PC et plus tard sur les VMs. `[G: Technical quality and reproducibility]`
- **Écarté** : lancer les commandes à la main (erreurs, oublis, non reproductible).
- **Oral** : « tout le pipeline se rejoue avec `make all` ; on montre les cibles avec `make help`. »

### D2. Workloads Go de référence, non modifiés, compilés en binaires natifs
- **Choix** : on garde le Go du prof tel quel ; `go build -trimpath` avec Go 1.26.8 ; la version de Go est notée dans `machine_local.txt`.
- **Pourquoi** : le TD interdit d'optimiser les workloads (« their purpose is to create measurable computational behaviour »). Mêmes binaires partout ⇒ seules les machines varient, donc on compare des machines et pas du code. Un binaire Go est autonome (souvent statique, à vérifier avec `file`) : en TD2 on le copie sur une VM sans installer Go. `[G: Deployment]`
- **Écarté** : réécrire en C/Rust (gain nul pour le projet, risque de casser l'interface `--size`).
- **Oral** : « la variable étudiée, c'est la machine ; le code est figé. »

### D2-bis. Vérifier qu'on mesure bien les sources du prof (empreintes md5)
- **Constat (Part 3)** : les `cpu_task`, `memory_task` et `matrix_task` présents sur la machine venaient d'un ancien travail. Leur sortie JSON était différente (`workload`, `host`, `c00` au lieu de `task`, `primes_found`, `checksum`).
- **Choix** : les anciens sont rangés dans `workloads/old/` et on remet les sources de l'archive du prof, avec contrôle par `md5sum` : cpu `64b9f230…`, matrix `a4beadd0…`, memory `8b86799b…`, sort `d2c4f4c4…`.
- **Pourquoi** : comparer des machines n'a de sens qu'avec un code identique partout (D2). L'empreinte prouve que c'est le même code sur le PC et sur chaque VM. `[G: Technical quality and reproducibility]`
- **Oral** : « on vérifie l'empreinte des sources avant chaque campagne ».

### D3. Mesure externe avec GNU time : temps mur (`%e`) et RSS max (`%M`)
- **Choix** : `/usr/bin/time -f "%e %M"` autour de chaque exécution. Le JSON affiché par le programme est conservé dans `data/raw/*.log` mais pas utilisé dans le CSV.
- **Pourquoi** :
  - le **temps mur** est la grandeur qui compose le **makespan** (CM3 : « makespan = quand le dernier job finit ») ; c'est aussi ce qu'on paie au cloud (facturation au temps d'usage, CM2 « measured service ») ;
  - la **RSS max** donne le besoin mémoire réel d'une tâche, donc la **contrainte de capacité** d'une VM (CM6 : filtrer les machines infaisables avant de scorer ; CM4 : contrainte de capacité dans l'ILP) ;
  - un outil externe mesure tous les workloads de la même façon, quel que soit le langage.
- **Écarté** : le temps interne du programme (ne couvre pas le démarrage du processus) ; `time` du shell (pas de RSS).
- **Oral** : « runtime = futur p_ij du modèle, RSS = futur besoin mémoire m_i pour la contrainte de capacité. » `[G: Workload and resource model]`

### D4. CSV brut, une ligne = une exécution, schéma imposé
- **Choix** : `workload,size,run,runtime_s,max_rss_kb`, jamais de moyenne dans le CSV. Les stats sont calculées uniquement par `scripts/analyze.sh`.
- **Pourquoi** : garder la variabilité (écart-type, min/max) pour pouvoir en parler. `[G: Interpretation and limitations : measurement variability]`, `[G: Metrics quality]`
- **Écarté** : stocker seulement la moyenne (on perd l'info de dispersion, on ne peut plus recalculer).

### D5. Calibration des tailles : chaque exécution doit durer entre ~1 s et ~30 s
- **Choix** : `make calibrate` lance une fois chaque taille et signale les runs trop courts ou trop longs ; les tailles finales sont figées dans `config/campaign.conf`.
- **Pourquoi** : GNU time a une résolution de 10 ms, donc un run d'1 s a moins de 1 % d'erreur de quantification. Sous ~0,2 s on mesure surtout le bruit et le démarrage. Au-dessus de 30 s, la campagne ne tient pas dans la séance. Le TD demande d'adapter les tailles et de les documenter.
- **Constat** : aux tailles du TD, nos runs durent 0,01 s (cpu 200k, matrix 200) à 0,2 s (memory 128). C'est trop court sur un Ryzen 7 7840HS.
- **Tailles finales, validées par la campagne** : tous les runs durent entre 0,96 s et 9,43 s. Tailles initialement proposées (extrapolées des complexités O(N^1.5), O(N), O(N³), O(n log n), à confirmer par `calibrate`) : cpu 5M / 10M / 20M ; memory 512 / 1024 / 2048 Mo (RAM WSL 7,4 Gio : OK) ; matrix 1000 / 1500 / 2000 ; sort 10M / 20M / 40M. Ce sont des doublements quand c'est possible, pour répondre directement à « doubler la taille double-t-il le temps ? ».

### D6. 3 répétitions entrelacées + 1 warm-up non enregistré
- **Choix** : passe 1 = toutes les configurations une fois, puis passe 2, puis passe 3 (et non 3 runs d'affilée). Un run de chauffe par configuration, jeté.
- **Pourquoi** : si la machine dérive pendant la campagne (throttling thermique, tâche de fond), la dérive se répartit sur toutes les configurations au lieu de biaiser l'une d'elles. Le warm-up enlève l'effet « premier lancement » (binaire pas encore en cache disque, CPU en basse fréquence).
- **Écarté** : plus de répétitions (le TD en demande 3 ; on mesure le coefficient de variation CV pour vérifier que 3 suffisent, et on en ajoute si CV > 5 %).
- **Oral** : « on a contrôlé la variabilité : CV par configuration dans le tableau. »

### D7. Le runner échoue tôt et n'écrit jamais de ligne fausse
- **Choix** : `benchmark.sh` vérifie avant de lancer : binaire présent et exécutable, taille entière > 0, GNU time présent, en-tête CSV correct. Si une exécution échoue (code ≠ 0), il affiche la sortie du programme, sort en erreur et **n'ajoute aucune ligne**. `campaign.sh` vérifie tous les binaires avant de démarrer et sauvegarde l'ancien CSV (`.bak`) au lieu de l'écraser.
- **Pourquoi** : une ligne fausse dans le CSV fausserait les estimations du scheduler plus tard. C'est la même logique que CM6 : vérifier la faisabilité avant d'agir. `[G: Orchestration and result collection]` (on réutilisera ce runner sur les VMs en TD2/TD3)

### D8. Environnement enregistré avec chaque campagne
- **Choix** : `data/machine_local.txt` (OS, CPU, cœurs/threads, RAM, disque, virtualisation, governor CPU, versions Go et GNU time) + `data/campaign_meta.txt` (heure, charge système avant/après, ordre, nombre de runs).
- **Pourquoi** : « Do not compare results obtained on different student computers without recording the machine specifications ». En TD2 on comparera des VMs hétérogènes : chaque mesure doit pouvoir être rattachée à sa machine. `[G: Workload and resource model]`

### D9. Analyse : moyenne, écart-type, CV, min–max et exposant de croissance
- **Choix** : `analyze.sh` (awk, sans dépendance) produit `results/summary.md` et `data/workload_profile_local.csv`. Pour chaque passage d'une taille à la suivante, on calcule l'exposant empirique `k = log(t2/t1) / log(s2/s1)` (k≈1 linéaire, k≈3 cubique). Le graphe `results/size_vs_runtime_rss.png` est optionnel (matplotlib).
- **Pourquoi** : répond directement à « doubler la taille double-t-il le temps ? » avec un chiffre. Le fichier profil est la **première estimation des durées et besoins mémoire des tâches** : c'est l'entrée du scheduler. Les heuristiques LPT/SPT ont besoin de durées estimées (CM3), l'ILP a besoin des p_ij (CM4), et Max-Min se calcule sur ces mêmes estimations.
- **Oral** : « nos décisions d'allocation reposent sur des durées mesurées, pas supposées. » `[G: Measurement]`, `[G: Problem formulation]`

### D10. Machine de mesure
- **Choix** : portable d'Adonis `OMEN-AdonisR`, Ubuntu 26.04.1 sous **WSL2**, Ryzen 7 7840HS (8 cœurs / 16 threads), 7,4 Gio RAM visibles, Go 1.26.8 (voir `ENVIRONMENT.md`).
- **Conséquence** : WSL2 est une VM Hyper-V. On l'assume et on le documente : c'est la même situation qu'une VM cloud (hyperviseur, ressources plafonnées, voisins invisibles). Précautions pendant la campagne : portable sur secteur, mode performances Windows, navigateur et IDE fermés côté Windows. La RAM visible (7,4 Gio) n'empêche pas `memory_task` à 512 Mo.
- **Pourquoi** : la baseline locale doit venir d'une machine stable et décrite ; éviter les machines partagées ou chargées pendant la campagne (fermer navigateur/IDE lourds, brancher le portable sur secteur).

### D11. Outils des scripts : Bash + awk, Python seulement pour le graphe
- **Choix** : runner et campagne en Bash, stats en awk, graphe en Python/matplotlib optionnel.
- **Pourquoi** : le sujet autorise le shell pour les scripts d'automatisation, et le cœur du projet (scheduler, orchestrateur) sera en langage compilé. Bash + awk tournent sur n'importe quelle VM Ubuntu sans installation.

---

## Limites connues (à assumer à l'oral) `[G: Interpretation and limitations]`
- 3 répétitions donnent une idée de la variabilité, pas un intervalle de confiance solide.
- GNU time `%e` a une résolution de 10 ms, d'où la contrainte de calibration (D5).
- Mesures sous WSL2 : les processus Windows partagent le CPU sans être visibles depuis Linux, et `/proc/loadavg` ne les voit pas.
- Pas d'épinglage CPU (`taskset`) ni de fréquence CPU fixée : sur portable, turbo et throttling font varier les temps. Le CV le montre.
- Les mesures sont faites **une tâche à la fois**. En TD3, plusieurs tâches tourneront en même temps sur une VM et se partageront CPU et bande passante mémoire (CM6 : « a workload's duration may depend on what else is running »). Les durées locales ne seront donc qu'une estimation de départ.
- Les tailles du TD1 sont propres à notre machine : les durées absolues ne se transposent pas telles quelles à une VM. On mesurera à nouveau sur chaque type de VM en TD2.

## Ce que le TD1 prépare pour la suite
| Sortie TD1 | Réutilisée en | Rôle |
|---|---|---|
| `bin/*` (binaires natifs) | TD2 | copiés tels quels sur les VMs GCP |
| `benchmark.sh` | TD2–TD3 | même runner exécuté à distance, même schéma CSV |
| `machine_local.txt` | TD2 | point de comparaison avec les types de VM |
| `workload_profile_local.csv` | TD4–TD5 | estimations p_ij (durée) et m_i (mémoire) pour LPT / Max-Min / ILP |
| CV par configuration | TD5 + soutenance | discussion de l'erreur de prédiction et de la variabilité |
