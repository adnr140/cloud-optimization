# TD1 — Réponses aux questions

Mesures : `data/benchmark_local.csv`, synthèse `results/summary_local.md`.

## Part 1 — Caractériser la machine
1. **Cœur vs CPU logique.** Un cœur est une unité d'exécution physique. Avec le SMT (hyperthreading), chaque cœur expose 2 CPU logiques qui partagent ses unités de calcul et ses caches L1/L2. Notre Ryzen 7 7840HS a **8 cœurs et 2 threads par cœur, soit 16 CPU logiques** (`nproc` = 16). Deux tâches CPU-intensives placées sur les 2 threads d'un même cœur vont moins vite que sur 2 cœurs distincts. Sur GCP, une vCPU = un thread : une VM à 2 vCPU = 1 seul cœur physique.
2. **RAM disponible.** WSL2 voit **7,4 Gio** au total, dont **6,7 Gio disponibles** au repos, plus 2 Gio de swap. C'est la limite de la VM WSL, pas la RAM physique du portable. C'est largement suffisant pour `memory_task` (512 Mo max).
3. **Pourquoi noter l'environnement.** Un temps d'exécution dépend autant de la machine que du programme : modèle et fréquence du CPU, nombre de cœurs, caches, RAM, virtualisation, charge. Ici, on mesure dans une VM (WSL2 sur Hyper-V) dont les ressources sont plafonnées et partagées avec Windows. Sans ces informations, un résultat n'est ni comparable à celui d'une autre machine ni reproductible. En TD2, on comparera justement plusieurs types de VM GCP par rapport à cette référence.

## Part 2 — Compiler
Résultat obtenu : 4 binaires de 2,5 à 2,8 Mo dans `bin/`. `file bin/cpu_task` affiche : `ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, Go BuildID=…, with debug_info, not stripped`.
1. **Ce que produit `go build`** : un exécutable natif au format **ELF 64 bits pour x86-64**, **lié statiquement**. Il contient le code machine du programme, le runtime Go (ordonnanceur de goroutines, garbage collector) et les bibliothèques utilisées. C'est pour ça qu'il pèse ~2,5 Mo pour 70 lignes de code. `with debug_info, not stripped` : il garde ses symboles de débogage (on pourrait le réduire avec `-ldflags="-s -w"`, ce qui n'est pas utile ici).
2. **Source vs exécutable** : le `.go` est du texte lisible par un humain et portable, qui a besoin du compilateur Go. L'exécutable contient des instructions machine directement exécutées par le CPU. Il est lié à une architecture et un OS (linux/amd64) et n'a plus besoin de Go.
3. **Avantages du natif** : aucune dépendance à installer sur la machine cible (lien statique, donc pas besoin de Go ni même de libc), démarrage immédiat, pas d'interpréteur qui fausserait les mesures, performances stables. Déployer = copier un fichier (TD2 : `gcloud compute scp` sur la VM), et toutes les VMs exécutent exactement le même binaire.
4. **Sans la source ?** Oui. Le binaire est autonome : on peut supprimer `workloads/` ou copier `bin/cpu_task` ailleurs, il fonctionne, tant que la cible est Linux x86-64. Sur une VM ARM (ex. GCP Tau T2A), il faudrait recompiler avec `GOARCH=arm64 go build`.

## Part 3 — Comprendre les workloads
Premier essai aux tailles du TD (temps interne `runtime_s`) : cpu 200 000 → 0,011 s (17 984 premiers) ; memory 128 Mo → 0,210 s (alloc 128,3 Mo) ; matrix 200 → 0,010 s ; sort 1 M → 0,112 s.
1. **Le plus CPU-intensif** : `cpu_task`. Il ne fait que des divisions entières (test de primalité jusqu'à √n), sans presque aucune mémoire. Tout le temps passe dans les unités de calcul. `matrix_task` est aussi gourmand en CPU (O(N³) multiplications flottantes), mais il dépend en plus du cache et de la mémoire.
2. **Le plus gourmand en mémoire** : `memory_task`. Il alloue exactement `--size` Mo (le JSON confirme `alloc_mb` = 128,3), alors que matrix 200 ne prend que 3 × 200² × 8 o ≈ 1 Mo et sort 1 M ≈ 8 Mo.
3. **Sens de `--size`** : `cpu_task` = plus grand entier testé ; `memory_task` = Mo alloués (avec 5 passes par défaut, `--passes`) ; `matrix_task` = dimension N des matrices N×N ; `sort_task` = nombre d'entiers générés puis triés (graine fixe 42, `--seed`).
4. **Pourquoi un paramètre en ligne de commande** : on fait varier la charge sans recompiler et on automatise les campagnes. On peut aussi **calibrer** la taille selon la machine : ici, les tailles du TD durent 0,01 à 0,2 s sur notre Ryzen, c'est trop court, et on les augmente sans toucher au code. Enfin, une tâche du projet devient simplement le couple (workload, size), qui est l'unité que le scheduler placera.

## Part 4 — Mesurer une exécution (`/usr/bin/time -v`)
| | cpu_task 500 000 | memory_task 256 |
|---|---:|---:|
| Elapsed (wall) | 0,04 s | 0,44 s |
| User | 0,04 s | 0,20 s |
| System | 0,00 s | **0,24 s** |
| % CPU | 100 % | 100 % |
| Max RSS | **2 632 Ko** (2,6 Mo) | **265 236 Ko** (259 Mo) |
| Minor page faults | 328 | **66 135** |

1. **Temps mur vs temps CPU** : le temps mur est la durée réelle vue de l'extérieur, du lancement à la fin. Le temps CPU (user + sys) est le temps où un cœur a réellement travaillé pour le processus : *user* = notre code, *sys* = le noyau qui travaille pour nous. Ici, mur ≈ user + sys et % CPU = 100 % : les programmes sont mono-thread et n'attendent rien (pas d'E/S). Avec du parallélisme on aurait CPU > mur (% > 100), avec de l'attente CPU < mur. Le makespan et la facture cloud se comptent en **temps mur**.
2. **Plus grande RSS max** : `memory_task`, avec 265 236 Ko ≈ 259 Mo pour 256 Mo demandés (+ ~3 Mo de runtime Go), soit **100× plus** que `cpu_task` (2,6 Mo). Observation intéressante : chez memory_task, le temps **système** (0,24 s) dépasse le temps utilisateur (0,20 s). Les 66 135 défauts de page mineurs ≈ 256 Mo / 4 Ko (= 65 536 pages) : le noyau doit fournir et mettre à zéro chaque page au premier accès. Une partie du coût d'un workload mémoire est donc payée par l'OS, et sous WSL2 aussi par l'hyperviseur.
3. **Pourquoi deux exécutions diffèrent** : l'ordonnanceur de l'OS (et ici celui de Windows/Hyper-V sous WSL2), les autres processus, la fréquence CPU variable (boost, température, mode d'alimentation), l'état des caches et du TLB, le placement en mémoire et le garbage collector Go. À 0,04 s, une variation de 10 ms représente déjà 25 % : c'est pour ça qu'on calibre des runs ≥ 1 s (D5).

## Part 5 — Runner automatique
1. **Pourquoi automatiser** : mêmes commandes et même procédure à chaque fois, pas d'erreur de recopie, campagne rejouable sur une autre machine (TD2), et ça passe à l'échelle.
2. **Une ligne = une exécution** : on garde la dispersion (écart-type, min/max, valeurs aberrantes) et on peut recalculer n'importe quelle statistique plus tard.
3. **Applications lourdes en parallèle** : elles prennent du CPU, de la bande passante mémoire et du cache. Les temps augmentent et deviennent instables, et les comparaisons entre tailles sont biaisées. C'est l'effet « voisin bruyant » qu'on retrouvera sur les VMs partagées.
4. **Erreurs à détecter** : binaire absent ou non exécutable, argument invalide, GNU time absent, CSV avec un mauvais en-tête, exécution en échec (code ≠ 0), sortie de time illisible. Voir D7 dans `DECISIONS.md`.

## Part 7 — Analyse (campagne du 2026-11-10, 36 runs, voir `results/summary_local.md` et `results/size_vs_runtime_rss_local.png`)

| workload | tailles | temps moyen (s) | CV max | RSS max | exposant k mesuré | théorie |
|---|---|---|---:|---|---:|---|
| cpu_task | 5M / 10M / 20M | 0,97 / 2,58 / 6,83 | 1,6 % | 2,3–2,5 Mo (constante) | 1,41 | O(N^1.5 / log N) |
| memory_task | 512 / 1024 / 2048 Mo | 0,90 / 1,48 / 2,73 | 3,6 % | 0,5 / 1,0 / 2,0 Go (= size) | 0,71 → 0,89 | O(size) |
| matrix_task | 1000 / 1500 / 2000 | 1,08 / 3,85 / 9,37 | 2,2 % | 26 / 54 / 94 Mo (∝ N²) | 3,13 / 3,09 | O(N³) |
| sort_task | 10M / 20M / 40M | 1,43 / 3,07 / 6,25 | 3,6 % | 79 / 155 / 308 Mo (∝ n) | 1,10 / 1,03 | O(n log n) |

Tailles finales : celles du TD duraient 0,01 à 0,2 s sur notre machine, on les a donc augmentées (D5).

1. **Le plus lent à sa plus grande taille** : `matrix_task` N=2000, avec **9,37 s**, devant cpu 20M (6,83 s) et sort 40M (6,25 s).
2. **Le plus gourmand en mémoire** : `memory_task`, avec **2,05 Go** de RSS à 2048 Mo. La RSS vaut la taille demandée + ~5 Mo de runtime Go. Ensuite viennent sort 40M (308 Mo ≈ 8 o × 40M) et matrix 2000 (94 Mo ≈ 3 × 2000² × 8 o = 96 Mo, la théorie colle). cpu_task reste à ~2,5 Mo quelle que soit la taille.
3. **Doubler la taille double-t-il le temps ?** Seulement pour `sort_task` (×2,14 puis ×2,04, cohérent avec n log n). `cpu_task` fait **×2,65** à chaque doublement (k = 1,41, proche de la théorie N^1,5/log N, puisque chaque nombre premier coûte ~√n divisions). `memory_task` fait **moins** que ×2 (×1,64 puis ×1,85). `matrix_task` est cubique : +50 % de N donne ×3,55 en temps, donc doubler N multiplierait le temps par ~8.
4. **Plus forte croissance** : `matrix_task`, avec k ≈ **3,1**, conforme à O(N³). Le léger excès au-dessus de 3 vient probablement du cache : à N=2000, les matrices (94 Mo) dépassent largement le L3 de 16 Mo.
5. **Les 3 répétitions sont-elles identiques ?** Non, mais elles sont très proches : CV de **0,5 % à 3,6 %**, avec un écart min–max d'au plus 0,3 s. Les plus stables sont les tâches CPU pures (cpu 0,5–1,6 %). Les plus variables sont les tâches qui sollicitent la mémoire (memory 2048 et sort : 3,6 %), sensibles à l'allocation des pages, au cache et à l'activité Windows sous WSL2. 3 runs suffisent ici (CV < 5 %, critère D6).
6. **Mesures utiles pour comparer des VMs** : le temps mur par (workload, taille), qui donne la durée p_ij d'une tâche i sur une machine j. La RSS max, qui donne le besoin mémoire m_i, c'est-à-dire la contrainte de capacité : memory 2048 ne rentrera pas sur une VM à 2 Go. Le CV, pour savoir si un écart entre deux VMs dépasse le bruit. Et la description de la machine, pour expliquer les écarts.

**Observation à discuter (inattendue)** : `memory_task` croît moins vite que linéairement (k = 0,71 puis 0,89), alors que son travail est proportionnel à la taille. Hypothèses : une partie du coût est fixe (démarrage du processus et du runtime Go), et pour les grosses allocations le noyau peut utiliser des *huge pages* (2 Mo au lieu de 4 Ko), ce qui réduit fortement le nombre de défauts de page par Mo. À vérifier en TD2 en comparant le temps système (`%S`) et les défauts de page (`%R`) selon la taille. Ce genre de point « mesuré, expliqué, limité » est exactement ce que demande le critère *Interpretation and limitations*.

## Conclusion
Sur notre machine (Ryzen 7 7840HS, WSL2, 7,4 Gio), les quatre workloads ont des profils nettement différents. Ces profils correspondent à leur algorithme :
- **cpu_task** est purement CPU : mémoire constante (~2,5 Mo), croissance en N^1,4, très stable (CV ≤ 1,6 %).
- **memory_task** est piloté par la mémoire : RSS égale à la taille demandée (jusqu'à 2 Go), temps modéré et quasi linéaire, et une part importante du travail est faite par le noyau (temps sys > user, défauts de page).
- **matrix_task** est le plus explosif : O(N³) (k ≈ 3,1) avec une mémoire en N² modeste (< 100 Mo). C'est le plus long à grande taille.
- **sort_task** est mixte : temps en n log n (quasi linéaire) et mémoire linéaire (8 o par entier).

Conséquences pour la suite du projet : (1) le **temps** d'une tâche dépend fortement de sa taille et de son type, donc on ne peut pas répartir les tâches « au nombre » comme le fait un Round-Robin naïf. Il faut des estimations de durée, ce que fournit `data/workload_profile_local.csv` (CM3 : LPT ; CM4 : p_ij). (2) La **mémoire** n'est contraignante que pour memory_task et les gros tris : c'est elle qui rendra certaines affectations infaisables sur les petites VMs (CM6 : filtrer avant de scorer). (3) Tous les workloads sont mono-thread, donc une VM à k vCPU peut en exécuter ~k en parallèle : à mesurer en TD3, car les tâches mémoire se gêneront entre elles. (4) La variabilité locale est faible (CV < 4 %). Sur les VMs GCP, tout écart nettement supérieur à ça sera dû à la machine et non au bruit.
