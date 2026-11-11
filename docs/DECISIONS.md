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
- **Pourquoi** : le TD interdit d'optimiser les workloads (« their purpose is to create measurable computational behaviour »). Mêmes binaires partout ⇒ seules les machines varient, donc on compare des machines et pas du code. Un binaire Go est autonome (statique, vérifié avec `file`). En TD2, le sujet impose toutefois de **recompiler sur la VM** (voir D15). `[G: Deployment on GCP VMs]`
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
- **Choix** : `data/machine_local.txt` (OS, CPU, cœurs/threads, RAM, disque, virtualisation, governor CPU, versions Go et GNU time) + `data/campaign_meta_local.txt` (heure, charge système avant/après, ordre, nombre de runs).
- **Pourquoi** : « Do not compare results obtained on different student computers without recording the machine specifications ». En TD2 on comparera des VMs hétérogènes : chaque mesure doit pouvoir être rattachée à sa machine. `[G: Workload and resource model]`

### D9. Analyse : moyenne, écart-type, CV, min–max et exposant de croissance
- **Choix** : `analyze.sh` (awk, sans dépendance) produit `results/summary_local.md` et `data/workload_profile_local.csv`. Pour chaque passage d'une taille à la suivante, on calcule l'exposant empirique `k = log(t2/t1) / log(s2/s1)` (k≈1 linéaire, k≈3 cubique). Le graphe `results/size_vs_runtime_rss_local.png` est optionnel (matplotlib).
- **Pourquoi** : répond directement à « doubler la taille double-t-il le temps ? » avec un chiffre. Le fichier profil est la **première estimation des durées et besoins mémoire des tâches** : c'est l'entrée du scheduler. Les heuristiques LPT/SPT ont besoin de durées estimées (CM3), l'ILP a besoin des p_ij (CM4), et Max-Min se calcule sur ces mêmes estimations.
- **Oral** : « nos décisions d'allocation reposent sur des durées mesurées, pas supposées. » `[G: Metrics quality]`, `[G: Problem formulation]`

### D10. Machine de mesure
- **Choix** : portable d'Adonis `OMEN-AdonisR`, Ubuntu 26.04.1 sous **WSL2**, Ryzen 7 7840HS (8 cœurs / 16 threads), 7,4 Gio RAM visibles, Go 1.26.8 (voir `ENVIRONMENT.md`).
- **Conséquence** : WSL2 est une VM Hyper-V. On l'assume et on le documente : c'est la même situation qu'une VM cloud (hyperviseur, ressources plafonnées, voisins invisibles). Précautions pendant la campagne : portable sur secteur, mode performances Windows, navigateur et IDE fermés côté Windows. La RAM visible (7,4 Gio) n'empêche pas `memory_task` à 512 Mo.
- **Pourquoi** : la baseline locale doit venir d'une machine stable et décrite ; éviter les machines partagées ou chargées pendant la campagne (fermer navigateur/IDE lourds, brancher le portable sur secteur).

### D11. Outils des scripts : Bash + awk, Python seulement pour le graphe
- **Choix** : runner et campagne en Bash, stats en awk, graphe en Python/matplotlib optionnel.
- **Pourquoi** : le sujet autorise le shell pour les scripts d'automatisation, et le cœur du projet (scheduler, orchestrateur) sera en langage compilé. Bash + awk tournent sur n'importe quelle VM Ubuntu sans installation.

---

## TD2 — Déploiement sur Google Compute Engine

### D12. Toute la configuration cloud dans un seul fichier, `--project` et `--zone` explicites partout
- **Choix** : `config/gcp.env` contient le Project ID, la zone, le type de machine, l'image, le disque et les labels. `scripts/gcp.sh` fait toutes les actions (`preflight`, `explore`, `create`, `describe`, `deploy`, `setup`, `bench`, `fetch`, `stop`, `start`, `delete`, `inventory`). Chaque commande `gcloud` reçoit `--project` et `--zone` en argument.
- **Pourquoi** : on ne dépend pas de la configuration par défaut de `gcloud`, qui peut pointer vers un autre projet (le TD insiste : « use only the project authorized for the course »). Le script refuse de tourner tant que `PROJECT_ID` vaut `CHANGE_ME`. Changer de VM = changer une variable, ce qui servira en TD3 pour plusieurs VMs hétérogènes. `[G: Technical quality and reproducibility]`, `[G: Deployment on GCP VMs]`
- **Écarté** : taper les commandes du TD à la main à chaque séance (oublis de zone, ressources créées dans le mauvais projet, rien de rejouable par un autre membre du groupe).
- **Oral** : « notre infrastructure est décrite en texte, versionnée avec le code ; une VM se recrée avec une commande. »

### D13. Réutiliser les 3 VMs de l'équipe : `europe-west1-b`, `e2-medium`
- **Constat** (`gcloud compute instances list`, 2026-11-10) : projet commun `arctic-kiln-510814-c8` (« Cloud Optimization »), `cloudopt-vm1`, `-vm2`, `-vm3` en `europe-west1-b`, toutes **`e2-medium`**, arrêtées (`TERMINATED`), disques de 10 Go `pd-balanced`.
- **Choix** : on ne crée rien. `cloudopt-vm1` sert au TD2 ; vm2 et vm3 serviront à l'exécution distribuée du TD3. `scripts/gcp.sh create` ne fait rien si la VM existe déjà.
- **Pourquoi** :
  - **coût et sobriété** : réutiliser plutôt qu'empiler des ressources ;
  - **zone** : un VM est une ressource **zonale** (CM2). `europe-west1` (Belgique) est européenne (localisation des données) ; la latence ne compte pas pour un calcul batch, donc la proximité n'est pas un critère suffisant (encadré du TD) ;
  - **capacité** : `e2-medium` = 2 vCPU, 4 Go. Notre plus grosse tâche (memory_task 2048, RSS ≈ 2,05 Go) tient : la contrainte de capacité mémoire est respectée (CM4/CM6). On garde donc les mêmes tailles qu'en local.
- **Point clé pour l'analyse** : `e2-medium` est un type **à cœur partagé** (`isSharedCpu: true`) : il garantit une fraction du CPU et peut monter en **burst** au-delà pendant un temps limité. Un benchmark long ou répété peut donc ralentir quand le burst s'épuise. On le surveille avec le CV et l'ordre des passes (D6), et c'est un argument direct pour « cloud n'est pas une spécification de performance ». La série E2 ne garantit pas non plus la plateforme CPU : on enregistre `cpuPlatform` et `lscpu`. **Relevé : `Intel Broadwell`** (2014) pour vm1, face à un Zen 4 (2023) en local. Google décrit e2-medium comme « 1/2 shared physical core ».
- **Écart avec le TD** : les VMs ont été créées avec **Debian 13** (`debian-13-trixie`) et non Ubuntu 24.04. Même architecture x86-64, mêmes sources recompilées sur place : sans effet sur la validité de la comparaison, mais à noter. Le label `goog-ops-agent-policy` indique un agent de supervision Google qui tourne en fond : une source de bruit de plus sur un cœur partagé.
- **Fait (TD Part 15, voir D21)** : vm1 passée en `e2-standard-2` (cœur non partagé, 8 Go) pour une expérience témoin. Parc actuel : **vm1 = e2-standard-2, vm2 et vm3 = e2-medium**, donc déjà des VMs **hétérogènes** pour le TD3.
- **Écarté** : créer de nouvelles VMs `e2-standard-2` (doublons facturables) ; un type plus gros « pour aller plus vite ».

### D14. Labels sur chaque ressource et inventaire en fin de séance
- **Choix** : `--labels=course=cloud-optimization,td=td2`. `scripts/gcp.sh inventory` liste instances, disques, IP statiques, snapshots et images personnelles du projet.
- **Pourquoi** : un VM arrêté n'est pas un VM supprimé : son disque reste facturé (CM2 « measured service », TD Part 14). Les labels permettent de retrouver et de filtrer nos ressources (et de répartir les coûts). `[G: Design choices (trade-offs)]` (coût vs disponibilité)
- **Oral** : « on finit chaque séance par `inventory`. »

### D15. Déployer le commit, pas le dossier ; compiler sur la VM
- **Choix** : `deploy` envoie `git archive HEAD` (sources versionnées uniquement) par `gcloud compute scp`, l'extrait et écrit le hash dans `DEPLOYED_COMMIT`. Les empreintes `md5sum` des sources sont affichées pour vérifier qu'elles sont identiques au local (D2-bis). `setup` installe `golang-go`, `time` et `make`, puis lance `make build` **sur la VM**, comme le demande le TD.
- **Pourquoi** :
  - ce qui tourne sur la VM est exactement un commit connu, rejouable ; le hash est aussi noté dans `campaign_meta_cloud_vm1.txt` ;
  - `scp --recurse` du dossier copierait `.git`, nos binaires locaux, `data/raw` et des fichiers non commités ;
  - compiler sur la cible évite les erreurs d'architecture (`Exec format error` si la VM était ARM, ex. Tau T2A).
- **Limite assumée** : le Go d'Ubuntu 24.04 (`apt`, go1.22) n'est pas notre go1.26 local. Le compilateur fait partie de l'environnement mesuré : version notée dans `machine_cloud_vm1.txt`. Alternative si l'écart gêne : compiler une fois un binaire statique `GOOS=linux GOARCH=amd64` et le copier partout (même binaire = seule la machine varie).

### D16. Même runner, mêmes tailles, même schéma CSV : seul le `TAG` change
- **Choix** : `make bench TAG=cloud_vm1` produit `data/benchmark_cloud_vm1.csv` avec les tailles du TD1 (`config/campaign.conf` inchangé), 3 runs entrelacés + 1 warm-up. `make machine TAG=cloud_vm1` produit `data/machine_cloud_vm1.txt` (sur-ensemble du bloc du TD, plus le **serveur de métadonnées** : instance, zone, type, plateforme CPU). `make compare` produit `results/compare_local_vs_cloud_vm1.md` : moyenne, CV, RSS et ratio cloud/local par configuration, avec les caractéristiques des deux machines en en-tête.
- **Pourquoi** : le TD demande de comparer « for at least one identical workload and input size » avec assez de contexte pour éviter « le cloud est plus rapide ». On compare les 12 configurations, pas une seule. Le ratio cloud/local par workload est la première mesure de **l'hétérogénéité des machines** : c'est ce qui rend le problème d'affectation non trivial (CM3, p_ij dépend de i **et** de j). `[G: Metrics quality]`, `[G: Workload and resource model]`
- **Écarté** : réduire les tailles pour la VM (on perdrait la comparaison directe ; le TD l'autorise mais nos durées restent sous 30 s).

### D17. Exécution non interactive par `gcloud compute ssh --command`
- **Choix** : `bench`, `setup` et `run` passent par `--command` (keep-alive SSH de 30 s). Les fichiers reviennent par `fetch` (`gcloud compute scp`).
- **Pourquoi** : c'est le principe du futur orchestrateur (TD3) : piloter des VMs à distance, lancer, collecter, sans intervention humaine. `[G: Orchestration and result collection]`

### D18. Réseau minimal
- **Choix** : réseau `default`, IP externe **éphémère** (nécessaire au SSH direct), **aucune IP statique**, **aucun port ouvert** en plus du SSH.
- **Constat** : le projet a hérité des règles par défaut, dont `default-allow-rdp` (tcp:3389 ouvert à tout Internet) qui ne sert à rien sur des VMs Linux. Proposition : la supprimer (`gcloud compute firewall-rules delete default-allow-rdp`), après accord de l'équipe puisque le projet est partagé.
- **Pourquoi** : surface d'attaque minimale et pas de coût d'IP réservée. Une IP externe ne suffit pas pour se connecter : il faut aussi une règle de pare-feu qui autorise le port 22 (`describe` les liste). En production on retirerait l'IP externe et on passerait par IAP. `[G: Design choices (trade-offs)]` (sécurité vs simplicité)

### D19. Cycle de vie : démarrer pour mesurer, arrêter en fin de séance, supprimer en fin de projet
- **Choix** : `start` juste avant la campagne, `stop` dès les données rapatriées (`fetch`) et commitées. Les 3 VMs de l'équipe restent **arrêtées** entre les TD (on en a besoin en TD3–TD5), et seront supprimées à la fin du projet (`delete` affiche d'abord `autoDelete` des disques, puis `inventory` vérifie qu'il ne reste rien). `inventory` sert aussi à repérer les disques orphelins.
- **Pourquoi** : stop = plus de facturation vCPU/RAM, mais chaque disque de 10 Go reste facturé (quelques centimes par mois) ; delete = plus rien. Garder 3 disques de 10 Go coûte moins, en temps d'équipe, que reconfigurer 3 VMs à chaque TD. Et comme tout est scripté (D12, D15), une VM perdue se recrée en deux commandes. `[G: Design choices (trade-offs)]` (coût vs effort)
- **Constat de l'inventaire (2026-11-10)** : 0 IP statique, 0 image, 3 disques de 10 Go, mais **42 snapshots** : un snapshot **par jour et par disque** depuis le 2026-10-28 (vers 11h30–12h30 UTC), soit 14 par disque. Cause confirmée : la planification **`default-schedule-1`** (europe-west1), créée le 2026-10-06 en même temps que les VMs : la console Google attache par défaut un snapshot quotidien aux nouveaux disques, avec une rétention de 14 jours. Le disque `instance-20261006-152502` est bien celui de `cloudopt-vm3` (pas d'orphelin). Les snapshots sont incrémentaux, donc le coût est faible, mais il **continue pendant que les VMs sont arrêtées**. C'est exactement le piège « stop ≠ delete » du TD.
- **Proposition (à valider en équipe, suppression irréversible)** : nos données sont dans git, et les VMs se reconfigurent en 3 commandes (D12, D15), donc des sauvegardes quotidiennes de disques de VMs **arrêtées** n'apportent rien. On détache la planification des 3 disques et on laisse la rétention purger les anciens snapshots, ou on les supprime. Commande : `gcloud compute disks remove-resource-policies <disque> --zone europe-west1-b --resource-policies default-schedule-1` pour `cloudopt-vm1`, `cloudopt-vm2`, `instance-20261006-152502`. Leçon : vérifier les **options par défaut** de la console, qui créent des ressources facturables sans qu'on les ait demandées.
- **Écarté** : laisser tourner les VMs entre les séances (facturation continue pour rien) ; `reset` pour redémarrer (équivalent d'un arrêt brutal, risque pour les écritures en cours).

### D20. Point ouvert du TD1 : `memory_task` sous-linéaire → résolu par `memprobe`
- **Constat TD1** : 512 → 1024 → 2048 Mo donnait 0,90 → 1,48 → 2,73 s (exposant 0,71 puis 0,89).
- **Test** : `make memprobe` (temps mur, user, sys, défauts de page mineurs, réglage THP) en local et sur la VM, 3 runs × 4 tailles (`data/memprobe_*.csv`).
- **Résultats** :

| | défauts de page / Mo | sys / user à 2048 Mo | THP |
|---|---:|---:|---|
| Portable (Ubuntu 26.04, WSL2) | **257** (= pages de 4 Ko) | 2,20 s / 1,54 s : **le noyau domine** | `madvise` |
| VM (Debian 13) | **0,9** (≈ pages de 2 Mo) | 1,57 s / 2,15 s | `always` |

- **Conclusions** :
  1. memory_task est surtout un test **du noyau** : chaque nouvelle page touchée provoque un défaut de page et sa mise à zéro. Avec des pages de 4 Ko il y en a 256 par Mo, avec des huge pages de 2 Mo presque aucun ;
  2. sur la VM, la croissance est **parfaitement linéaire** (exposant 0,97 et 1,00 sur e2-standard-2) ; en local, memprobe n'est plus sous-linéaire (0,42 → 0,81 → 1,55 → 3,73 s, exposant ≥ 0,94). La sous-linéarité du TD1 **ne se reproduit pas** : c'était un effet de l'état mémoire de WSL2 pendant cette campagne, pas une propriété du programme ;
  3. c'est pourquoi l'e2-standard-2 (CPU 2014) bat le portable (CPU 2023) sur memory_task (×0,62–0,80) : la configuration de l'OS compte autant que le matériel.
- **Oral** : « une mesure surprenante, on a formulé une hypothèse et on l'a testée avec un outil ciblé ; la réponse n'était pas celle attendue, on le dit. » `[G: Interpretation and limitations]`

### D21. Expérience témoin : même VM, seul le type change (e2-medium → e2-standard-2)
- **Choix** : `scripts/gcp.sh resize e2-standard-2` sur vm1 puis la même campagne (`TAG=cloud_vm1_std2`). Une seule variable change, tout le reste est identique (disque, OS, binaires, tailles, runner, zone, plateforme Broadwell).
- **Pourquoi** : sur e2-medium, cpu_task était 2× plus rapide au passage 1 (CV 32–47 %). Hypothèse : crédits de burst du cœur partagé. Une seule campagne ne permet pas de conclure ; un témoin, si.
- **Résultat** : sur e2-standard-2, CV ≤ 3,5 % partout, passages plats (cpu 20M : 25,8 / 25,9 / 26,8 s). Le passage 1 de l'e2-medium (27,9 s) ≈ e2-standard-2 : en burst, l'e2-medium va à pleine vitesse, puis tombe à ~50 %. **Hypothèse confirmée.** Figure : `results/td2_machines.png` (bas).
- **Compromis coût / performance** (prix Google : e2-medium = 1/2 du prix horaire de l'e2-standard-2). Coût par tâche e2-standard-2 / e2-medium = 2 × t_std2 / t_medium : memory 0,7 ; matrix 0,7–0,9 ; sort 0,95 ; cpu 1,1–1,2. Pour une charge **continue**, l'e2-standard-2 coûte autant ou moins par tâche **et** donne des durées prévisibles. L'e2-medium n'est intéressant que pour des charges courtes et intermittentes (le burst couvre tout). `[G: Design choices (trade-offs)]`, `[G: Metrics quality]`
- **Conséquence pour le scheduler** : sur un cœur partagé, p_ij dépend de l'**historique** de la VM. Pour TD4–5, soit on n'utilise que des types à cœur dédié pour l'estimation, soit on estime l'e2-medium avec sa vitesse **hors burst** (passages 2–3), plus prudente.
- **Écarté** : conclure sur le burst sans témoin ; modifier vm2 ou vm3 (on garde 2 VMs e2-medium pour le TD3).

### D22. La matrice p_ij, sortie directe de la mesure
- **Choix** : `make pmatrix` assemble `data/p_matrix.csv` (une ligne par tâche, une colonne par machine, temps moyen). `make figures` produit `results/td2_machines.png`.
- **Pourquoi** : c'est l'entrée du problème d'affectation (CM3 : machines **non reliées**, R‖Cmax ; CM4 : p_ij dans l'ILP). Nos mesures montrent que les ratios entre machines varient d'une tâche à l'autre (e2-standard-2/local : 0,62 pour memory, 3,8 pour cpu) : on n'est **ni** dans le cas « machines identiques », **ni** « uniformes » (une seule vitesse par machine). Un placement naïf (Round-Robin) ignore cette structure : c'est là que l'optimisation peut gagner. `[G: Problem formulation]`, `[G: Workload and resource model]`
- **Oral** : « on ne suppose pas qu'une VM est “2× plus lente” : on a mesuré que ça dépend de la tâche, et c'est ce qui justifie un scheduler. »

---

## TD3 — Exécution distribuée sur 3 VMs

### D23. Architecture : l'allocation est une donnée, l'exécution est un mécanisme
- **Choix** : `data/allocation_manual.csv` (`task_id,workload,size,vm`) décide **où** va chaque tâche ; `scripts/run_all.sh` lit ce fichier et lance ; `scripts/run_task.sh` exécute **une** tâche sur **une** VM. Changer de placement = changer de fichier : `scripts/run_all.sh data/allocation_manual_packed.csv`. Aucun nom de VM n'est écrit dans un script.
- **Pourquoi** : c'est l'interface du futur scheduler. En TD4–TD5, Round-Robin, LPT, Max-Min ou l'ILP n'auront qu'à **écrire un CSV** ; l'exécution et la collecte restent identiques, donc la comparaison baseline / optimisé ne mesure que l'effet du placement. `[G: Architecture clarity]`, `[G: Integration and validity]`
- **Écarté** : un orchestrateur qui choisit lui-même la VM (mélange décision et exécution, impossible de comparer deux méthodes à mécanisme égal).
- **Oral** : « le scheduler produit un fichier, l'orchestrateur l'exécute : on peut brancher n'importe quel algorithme sans toucher au reste. »

### D24. Une tâche = une session SSH, lancée avec `&`, un seul `wait` après la boucle
- **Choix** : `run_all.sh` appelle `run_task.sh … &` pour chaque ligne, sans attendre, puis exécute **un seul** `wait`. Plusieurs tâches sur la même VM = plusieurs sessions SSH en même temps ; c'est l'OS de la VM qui partage les 2 vCPU entre les processus.
- **Pourquoi** : c'est la règle du TD (pas de file séquentielle par VM, pas de threads ni de sémaphores). Un `wait` dans la boucle rendrait tout séquentiel. Le processus `gcloud compute ssh` reste connecté jusqu'à la fin de la tâche distante, donc `wait` sur les processus locaux = attente de toutes les tâches distantes. `[G: Distributed execution, parallel]`
- **Piège évité** : `gcloud compute ssh` lit l'entrée standard. Dans une boucle `while read … done < fichier`, le premier SSH lancé « mange » le reste du CSV et une seule tâche part. On lit donc le CSV **avant** de lancer (`mapfile`) et chaque `run_task.sh` reçoit `</dev/null`.
- **Limite connue** : `sshd` accepte par défaut 10 connexions non encore authentifiées en même temps (`MaxStartups 10:30:100`), au-delà il en refuse une partie. Notre allocation la plus chargée met 7 tâches sur vm1 : sous la limite. Au-delà de ~10 tâches par VM, il faudrait espacer les lancements ou relever `MaxStartups`.

### D25. Valider l'allocation avant de lancer quoi que ce soit
- **Choix** : `run_all.sh` vérifie l'en-tête, 4 champs non vides par ligne, `task_id` unique, workload connu (`workloads/*.go`), taille entière, VM existante **et** `RUNNING` (un seul `gcloud compute instances list`). À la moindre erreur : liste de toutes les lignes fausses, **rien n'est lancé**, code de sortie 2.
- **Pourquoi** : critères de validité du TD (Part 3). Échouer avant de lancer évite une exécution à moitié faite et des résultats partiels mélangés. C'est la même logique que CM6 (filtrer les affectations infaisables avant d'agir) et que D7. `[G: Integration and validity]`
- **Sécurité** : les valeurs du CSV sont insérées dans une commande shell distante. `run_task.sh` n'accepte que `[a-z_]` pour le workload, des chiffres pour la taille, `[a-z0-9-]` pour la VM. Une ligne `T1,"cpu_task; rm -rf ~",…` est refusée au lieu d'être exécutée sur la VM. `[G: Technical quality]`
- **Vérifié** (faux `gcloud` local) : un CSV avec VM inconnue, `task_id` en double, workload `rm_rf`, taille `abc` et ligne incomplète → 5 erreurs signalées, aucun dossier de résultats créé.

### D26. Collecte : 3 fichiers par tâche, écrits directement sur le contrôleur
- **Choix** : stdout et stderr du SSH sont redirigés vers `results/td3/<run>/T1.out` et `T1.err` sur le contrôleur (rien n'est écrit puis recopié depuis la VM). `T1.meta` note `vm`, `remote_host` (sortie de `hostname` sur la VM, première ligne retirée de `.out`), `exit_code`, heures de lancement et de fin côté contrôleur. `launch.log` a une ligne par lancement. Le CSV d'allocation est copié dans le dossier du run.
- **Pourquoi** : un dossier de run se suffit à lui-même (quelle allocation, quelle VM, quel résultat). `.out` reste le JSON pur du workload, directement exploitable. `remote_host` **prouve** le placement : on ne se contente pas de croire `gcloud`. `[G: Orchestration and result collection]`
- **Note** : `.err` n'est pas forcément vide quand tout va bien : `gcloud` y écrit ses avertissements (clés d'hôte). Le succès se juge donc sur le **code de sortie**, pas sur la taille de `.err`.

### D27. Les échecs ne sont jamais silencieux
- **Choix** : `run_task.sh` sort avec le code de la commande distante (255 = échec SSH). Comme `wait` sans argument renvoie toujours 0, `run_all.sh` appelle ensuite `scripts/check_results.sh`, qui contrôle chaque tâche : lancée exactement une fois, `.out/.err/.meta` présents, `remote_host` = VM prévue, code 0, ligne JSON du bon workload et de la bonne taille, aucune sortie en trop. Résultat dans `check.txt` ; `run_all.sh` sort en 1 si une seule tâche est en défaut.
- **Pourquoi** : Part 10 du TD (« failed commands are not silently ignored »). Ça garde un seul `wait` (règle du TD) sans perdre l'information d'échec.
- **Test** : `data/allocation_failtest.csv` contient `cpu_task --size 1`, que le programme refuse (`error: --size must be >= 2`, code 1). Attendu : F1 OK, F2 en échec, l'erreur visible dans `F2.err`, `run_all.sh` sort en 1.

### D28. Mêmes binaires partout : compilés une fois, statiques, vérifiés par md5
- **Choix** : `deploy_all.sh` compile une fois sur le contrôleur (`CGO_ENABLED=0 GOOS=linux GOARCH=amd64`), vérifie que les 4 binaires sont **statiques**, les copie par `gcloud compute scp` dans `~/cloud-optimization/bin/` de chaque VM, compare les md5 distants aux md5 locaux, puis lance chaque workload une fois avec une petite taille (test de fumée du TD, Part 2).
- **Pourquoi** : c'est l'alternative notée en D15. Un binaire Go statique ne dépend d'aucune bibliothèque de la VM, il n'y a donc rien à installer sur vm2 et vm3 (pas de `apt install golang-go`). Toutes les VMs exécutent **exactement** le même fichier : une différence de durée vient de la machine, pas du compilateur. `[G: Deployment on GCP VMs]`
- **Écarté** : compiler sur chaque VM (3 installations de Go, 3 versions possibles) ; copier tout le dossier projet (inutile pour exécuter).

### D29. Tâches et allocations retenues
- **Tâches** : 9 tâches, les 4 workloads, tailles déjà validées en TD1/TD2 (petites et moyennes : T1 cpu 10M, T2 cpu 5M, T3 matrix 1500, T4 matrix 1000, T5 memory 1024, T6 memory 512, T7 sort 20M, T8 sort 10M, T9 cpu 5M). Seules, elles durent ~1 à 17 s sur nos VMs (`data/p_matrix.csv`) : assez longues pour voir les processus avec `ps`, assez courtes pour un coût négligeable.
- **Allocation 1, `allocation_manual.csv`** : 3 tâches par VM, workloads mélangés. **Allocation 2, `allocation_manual_packed.csv`** : 7 tâches sur vm1, 1 sur vm2, 1 sur vm3. **Seule la colonne `vm` change** (`diff <(cut -d, -f1-3 a) <(cut -d, -f1-3 b)` est vide).
- **Mémoire vérifiée à la main** (RSS mesurée en TD2, D22) : pire cas vm1 en allocation 2 = 1,8 Go pour 8 Go ; pire cas e2-medium = 1,1 Go pour 4 Go. Aucune allocation ne risque de tuer une tâche par manque de mémoire. Ce calcul deviendra la **contrainte de capacité** du modèle en TD4.
- **Pas de jugement de performance** : le TD3 interdit de comparer les deux allocations. Les heures de lancement et de fin servent uniquement à prouver que des tâches se chevauchent sur une même VM.

### D30. Cycle de vie TD3
- **Choix** : `scripts/gcp.sh start-all` (démarre les 3 VMs en une commande et attend leur SSH), `stop-all` en fin de séance, `inventory` pour vérifier. Les VMs restent arrêtées jusqu'au TD4–TD5 et sont supprimées à la fin du projet (D19).
- **Pourquoi** : 3 VMs allumées coûtent 3 fois plus ; on ne les démarre que pour exécuter.

## Limites connues (à assumer à l'oral) `[G: Interpretation and limitations]`
- 3 répétitions donnent une idée de la variabilité, pas un intervalle de confiance solide.
- GNU time `%e` a une résolution de 10 ms, d'où la contrainte de calibration (D5).
- Mesures sous WSL2 : les processus Windows partagent le CPU sans être visibles depuis Linux, et `/proc/loadavg` ne les voit pas.
- Pas d'épinglage CPU (`taskset`) ni de fréquence CPU fixée : sur portable, turbo et throttling font varier les temps. Le CV le montre.
- Les mesures sont faites **une tâche à la fois**. En TD3, plusieurs tâches tourneront en même temps sur une VM et se partageront CPU et bande passante mémoire (CM6 : « a workload's duration may depend on what else is running »). Les durées locales ne seront donc qu'une estimation de départ.
- Les tailles du TD1 sont propres à notre machine : les durées absolues ne se transposent pas telles quelles à une VM. Mesuré en TD2 sur 2 types de VM (D21, D22).
- TD2 : compilateur différent (go1.26.8 local, go1.24.4 VM) et OS différent (THP) : on compare des **environnements** complets, pas seulement des CPU (D15, D20).
- TD2 : la plateforme CPU E2 n'est pas garantie ; une VM recréée pourrait tomber sur un autre CPU que Broadwell. On revérifie `cpuPlatform` à chaque campagne.
- TD2 : sur e2-medium, la durée dépend de l'inactivité qui précède la mesure (burst, D21). 3 runs ne suffisent pas à modéliser ce comportement.
- TD3 : les heures de début et de fin sont prises sur le contrôleur et incluent l'établissement du SSH (~2–5 s). Elles prouvent le chevauchement, ce ne sont pas des durées d'exécution.
- TD3 : pas de reprise automatique d'une tâche échouée ; l'échec est signalé, l'opérateur relance.
- TD3 : au-delà de ~10 tâches simultanées sur une même VM, la limite `MaxStartups` de sshd peut refuser des connexions (D24).

## Ce que le TD1 prépare pour la suite
| Sortie TD1 | Réutilisée en | Rôle |
|---|---|---|
| `bin/*` (binaires natifs) | TD2 | recompilés sur la VM à partir du même commit (D15) |
| `benchmark.sh` | TD2–TD3 | même runner exécuté à distance, même schéma CSV |
| `machine_local.txt` | TD2 | point de comparaison avec les types de VM |
| `workload_profile_local.csv` | TD4–TD5 | estimations p_ij (durée) et m_i (mémoire) pour LPT / Max-Min / ILP |
| CV par configuration | TD5 + soutenance | discussion de l'erreur de prédiction et de la variabilité |
