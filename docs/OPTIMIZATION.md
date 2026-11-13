# Optimisation — répartir les tâches mieux que Round-Robin

Chaque partie indique le critère de la grille /20 qu'elle sert (`[G: …]`, voir `docs/GRILLE.md`). Choix détaillés : `docs/DECISIONS.md` D37–D43.

**En une phrase** : `bin/optimizer` (Go, bibliothèque standard seulement) choisit la VM de chaque tâche pour minimiser le makespan prédit, sous la contrainte de RAM de chaque VM. Il enchaîne les trois familles de méthodes du cours : il **construit** un plan avec les heuristiques du CM3, l'**améliore** par recherche locale (CM5), puis l'**encadre** avec une borne inférieure et, si l'instance est petite, le **prouve** optimal par branch and bound (CM4). Il écrit le même CSV que Round-Robin ; `run_all.sh` (TD3) l'exécute sans modification.

## Lien avec les TD précédents

| TD | Ce qu'il a produit | Ce que l'optimiseur en fait |
|---|---|---|
| TD1–TD2 | durées `p_ij` (`data/p_matrix.csv`), RSS `m_i` (identique sur toutes les VMs, D22) | données du modèle |
| TD3 | `run_all.sh` : tout en parallèle, ~3 s de SSH par tâche, ralentissement quand une VM a plus de tâches que de cœurs | coût SSH et partage du CPU dans le modèle ; orchestrateur **inchangé** |
| TD4 | Round-Robin (baseline), `check_allocation.sh`, `makespan.sh`, 4 runs réels | baseline de comparaison, même vérificateur, **points de calibration** du modèle |

## 1. Le problème `[G: Problem definition]` `[G: Problem formulation]`

**Entrées** (données, mesurées) : les tâches `i` (`data/tasks.csv`), les VMs `j` (`data/vms.csv` : type, RAM, colonne de `p_ij`, cœurs effectifs `c_j`), `p_ij` = durée de la tâche `i` seule sur le type de `j` (TD2), `m_i` = RSS max de `i` (TD2), SSH = 3 s (TD3).

**Variables** (ce qu'on décide) : `x_ij ∈ {0,1}`, 1 si la tâche `i` va sur la VM `j`. C'est la formalisation 2 du CM3 (une binaire par paire tâche–VM) ; dans le code, `assign[i] = j` (formalisation 1, même décision).

**Contraintes** `[G: Constraints]` :

| contrainte | formule | d'où elle vient |
|---|---|---|
| chaque tâche sur exactement une VM | `Σ_j x_ij = 1` | TD4 (chaque tâche exactement une fois) |
| mémoire | `Σ_i m_i·x_ij ≤ RAM_j − 512 Mo` | toutes les tâches d'une VM tournent **en même temps** (`&` + un `wait`, D24) ; 512 Mo pour l'OS. CM6 : filtrer les VMs infaisables |
| connexions SSH | `Σ_i x_ij ≤ 10` | limite `MaxStartups` de sshd (D24) |

**Objectif** `[G: Objective(s)]` : minimiser le makespan `T = max_j finish_j`, le temps que l'utilisateur attend `run_all.sh`. Égalités départagées par **leximax** : à makespan égal, on préfère le plan dont la 2ᵉ VM la plus lente finit le plus tôt, etc. (le plus équilibré).

### Le modèle de durée d'une VM `[G: Workload and resource model]`

`finish_j = SSH + shared({p_ij : i sur j}, c_j)` : **partage du processeur** (CM6, « a workload's duration may depend on what else is running »). La VM a `c_j` cœurs effectifs ; quand `n` de ses tâches tournent, chacune avance à la vitesse `min(1, c_j/n)` ; une tâche finie libère sa part pour les autres.

Calibré sur les **12 temps de fin mesurés** (4 runs réels × 3 VMs, `scripts/fit_model.py`, `results/model_fit.md`) :

| hypothèse | `c` ajusté | erreur moyenne | erreur relative | validation croisée (run laissé de côté) |
|---|---:|---:|---:|---:|
| H1 : chaque VM avec la colonne `p` de son type | 2,53 | 3,07 s | 28,1 % | 3,54 s |
| **H2 : toutes à la vitesse e2-standard-2** (retenue) | **1,25** | **0,78 s** | **8,5 %** | **0,82 s** |

Lecture physique : une e2 à 2 vCPU = 1 cœur physique + son hyperthread, d'où ~1,25 cœur effectif ; et sur des runs courts l'e2-medium tourne en **burst** à pleine vitesse (TD2, D21). Le modèle prédit les runs réels à moins de 0,5 s près : RR 15,7 prédit / 15,8 mesuré, RR réordonné 18,8 / 18,7, allocation tassée du TD3 23,8 / 23,5.

**Pourquoi ce n'est pas un ILP tel quel** : `shared()` n'est pas linéaire en `x_ij`. Un ILP (CM4) demanderait de l'approcher par `T ≥ SSH + Σ_i p_ij·x_ij / c_j` et `T ≥ SSH + p_ij·x_ij` ; c'est exactement notre « borne de travail » ci-dessous, qui **sous-estime** les mesures (TD4 : 12,6 s estimés, 17,6 s mesurés sur vm1). On garde donc le modèle mesuré et on écrit nous-mêmes la recherche.

## 2. Pourquoi « tout essayer » ne passe pas à l'échelle

Il y a `M^N` plans : 3⁹ = 19 683 pour nos 9 tâches, mais 10¹⁰⁰ pour 100 tâches sur 10 VMs (CM4, diapo 7 : « a solver must navigate the tree without visiting it all »). Même avec élagage, une recherche exacte reste exponentielle au pire. Le CM4 le dit : « Search time can explode with the instance size… Use when the instance is small enough. Consider a heuristic when the decision budget is tight. » D'où une méthode en étages, chacune bornée en temps.

## 3. La méthode `opt` : quatre étages, un par cours `[G: Method justification]`

| étage | ce qu'il fait | cours | coût |
|---|---|---|---|
| 0. filtrer | une VM où la tâche ne tient pas (RAM, 10 tâches) n'est jamais proposée | CM6 « filter before score » | — |
| 1. construire | LPT (plus longue d'abord → VM qui finit le plus tôt), Min-Min, Max-Min ; on garde le meilleur des trois | CM3 (heuristiques constructives, Braun et al. 2001) | O(n²·m), 0,5 s pour 1000 tâches |
| 2. améliorer | **descente** : depuis la VM critique, déplacer une tâche, échanger deux tâches, ou échanger deux tâches contre une ; on applique le meilleur voisin qui améliore, jusqu'à un optimum local | CM5 (recherche locale) | polynomial par pas |
| 3. itérer | **recherche locale itérée** : 200 perturbations (une tâche de la VM critique et une autre tâche envoyées au hasard), nouvelle descente, on garde si c'est mieux. Graine fixe : résultat reproductible | CM5 (métaheuristique) | ~20 ms par perturbation à 1000 tâches |
| 4. encadrer, prouver | borne inférieure `L` ; si le plan atteint `L`, il est **optimal** ; sinon branch and bound (brancher, déduire, borner) sous limite de temps (10 s) : **OPTIMAL** si la recherche termine, **FEASIBLE + écart** sinon | CM4 (« plan, bound, and the status that links them ») | exponentiel au pire, mais coupé à 10 s |

Chaque étage part du plan de l'étage précédent, donc **il ne peut pas l'empirer** (testé : `opt ≤ ils ≤ ls ≤ glouton`).

**Pourquoi un échange 2-contre-1** : sur le scénario B, LPT met deux `sort 20M` sur vm1 avec le `cpu 10M`. Ni un déplacement ni un échange 1-1 n'améliore (optimum local à 17,0 s) ; échanger les deux tris contre une `matrix 1500` de vm3 le fait (16,0 s). La recherche itérée trouve ensuite 15,9 s, que le branch and bound prouve optimal.

**La borne inférieure** (`lowerBound`, commentée dans le code) : aucun plan ne finit avant `T` si l'une de ces conditions nécessaires échoue : (a) chaque tâche tient seule sur une VM avant `T` ; (b) tout le travail tient sur tous les cœurs effectifs (une VM fait au plus `c_j` secondes de travail par seconde) ; (c) les tâches « grosses » partout (deux ne peuvent pas partager une VM avant `T`) ont chacune leur VM (couplage biparti). Le plus petit `T` qui passe est trouvé par dichotomie. Testé : la borne est toujours ≤ l'optimum trouvé par force brute.

**Branch and bound** : tâches dans l'ordre LPT, élagage si `max(fin partielle, SSH + (travail placé + travail restant minimal) / Σc_j)` dépasse le meilleur plan ; **symétrie** : vm2 et vm3 sont identiques, une tâche n'est essayée que sur la première VM vide de chaque groupe identique (CM4 : « prune only with valid deductions or bounds »).

## 4. Résultats sur nos VMs (prédits par le modèle) `[G: Baseline vs optimized comparison]`

| scénario | Round-Robin | LPT (CM3) | `opt` | borne | statut |
|---|---:|---:|---:|---:|---|
| A : les 9 tâches du TD3–TD4 | 15,7 s (mesuré **15,8 s**) | 12,6 s | **12,6 s** (−20 %) | 12,6 s | OPTIMAL (atteint la borne) |
| A réordonné | 18,8 s (mesuré **18,7 s**) | 12,6 s | **12,6 s** (−33 %) | 12,6 s | OPTIMAL ; `opt` ne dépend pas de l'ordre du fichier |
| B : 10 tâches plus lourdes (`data/tasks_b.csv`) | 20,2 s | 17,0 s | **15,9 s** (−21 %) | 15,0 s | OPTIMAL (recherche complète : 908 nœuds sur 59 049 plans) |
| piège RAM (`data/tasks_ram_trap.csv`) | **infaisable** (4,1 Go sur 4 Go) | 8,8 s | **8,8 s** | 8,8 s | OPTIMAL |

Plans :
- **A** : vm1 = T1 seul (`cpu 10M`, 9,6 s, c'est la borne : SSH + la plus longue tâche) ; vm2 = T2 T3 T5 ; vm3 = T4 T6 T7 T8 T9. La plus longue tâche dicte le makespan, on ne peut pas faire mieux que 12,6 s.
- **B** : vm1 = B1 B3 ; vm2 = B6 B9 (un `cpu 10M` + une `matrix 1500` chacune) ; vm3 = les 6 petites. Trois VMs à 15 s de travail chacune.

**Mesures réelles** : à faire (`make opt-run`, voir README). Elles seront ajoutées ici avec l'écart prédit / mesuré.

## 5. Passage à l'échelle (`make scaling`, `results/scaling.md`)

Instances aléatoires construites **uniquement** à partir des 12 tâches mesurées. Parc : 1 e2-standard-2 pour 2 e2-medium ; ici les e2-medium utilisent leur propre colonne (crédits épuisés, runs longs) pour que les machines soient vraiment hétérogènes, le cas difficile du CM3.

**Qualité** (40 petites instances, 8 à 12 tâches, optimum prouvé par la recherche exacte) :

| méthode | optimum trouvé | écart moyen | écart max |
|---|---:|---:|---:|
| Round-Robin | 0/37 (+3 plans infaisables) | 55,6 % | 132 % |
| Min-Min | 0/40 | 31,2 % | 56,6 % |
| LPT | 19/40 | 1,5 % | 6,3 % |
| + descente | 25/40 | 0,7 % | 5,6 % |
| **+ recherche itérée** | **39/40** | **0,0 %** | **< 0,05 %** |

**Taille** (moyenne de 3 instances, ~5 tâches par VM, limite 10 s) : voir le tableau complet dans `results/scaling.md`. À retenir : 1000 tâches sur 200 VMs (10²³⁰¹ plans) sont réparties en ~10 s avec un écart ≤ 1,3 % à la borne inférieure ; Round-Robin y produit des plans **infaisables** (RAM) dès 50 tâches. La recherche exacte prouve l'optimum jusqu'à ~20 tâches ; au-delà, l'optimum est prouvé quand le plan atteint la borne, sinon on rend le plan avec son écart (statut FEASIBLE), comme un solveur à limite de temps.

## 6. Tests (`make test-optimizer`, 48/48, sans VM) `[G: Integration and validity]`

1. Chaque méthode écrit une allocation valide (même `check_allocation.sh` que Round-Robin).
2. Chaque étage n'empire jamais : `opt ≤ ils ≤ ls ≤ glouton`, et `opt ≤ rr`.
3. `opt` = **force brute indépendante** (`scripts/bruteforce_check.py`, Python, aucun code partagé, énumère tous les plans) sur 8 instances ; borne inférieure ≤ optimum.
4. Piège RAM : Round-Robin refusé, `opt`, LPT, Min-Min, Max-Min respectent la RAM.
5. Instance impossible (6 × 2 Go) : erreur « INFEASIBLE, proved » et aucun fichier écrit.
6. Déterministe ; une recherche interrompue rend FEASIBLE, jamais un faux OPTIMAL.
7. Le modèle prédit les 3 runs réels à ±1,5 s.
8. 1000 tâches × 200 VMs : plan valide dans la limite de temps, statut et écart affichés.

## 7. Limites (à assumer à l'oral) `[G: Interpretation and limitations]`

- **L'optimum est celui du modèle.** Il est calibré sur 12 points ; erreur moyenne 0,78 s. Un plan « optimal » à 12,6 s peut mesurer 13 ou 14 s. CM4 : « the proof is about the model: wrong data, wrong plan ».
- **Burst** : H2 suppose que les e2-medium ont des crédits (runs courts). Pour des runs longs, passer leur `p_column` à `cloud_vm1` dans `data/vms.csv` (H1) : l'optimiseur enverra alors le CPU sur l'e2-standard-2.
- **Borne faible sur les tailles moyennes** : à 9–200 tâches hétérogènes, l'écart à la borne (10–26 %) surestime l'écart réel ; à 9–20 tâches la recherche exacte montre que le plan est en fait optimal.
- Pas de coût en € dans l'objectif : à makespan égal toutes nos VMs sont déjà allumées pendant le run ; le coût par tâche est discuté en D21.
- Les durées `p_ij` viennent de 3 runs par configuration (TD2) ; la variabilité du cloud (TD4 : 15,8 s contre 17,6 s au TD3 pour le même plan) est du même ordre que certains gains.

## Reproduire

```bash
make optimizer        # go build -> bin/optimizer
make test-optimizer   # 48 tests, sans VM
make opt              # data/allocation_opt.csv (A) + allocation_b_{rr,lpt,opt}.csv (B), vérifiées
make scaling          # results/scaling.md, ~4 min
make fit-model        # recalibre le modèle sur tous les runs réels -> results/model_fit.md
```

## Questions probables à l'oral

- **« Pourquoi ne pas tester toutes les combinaisons ? »** `M^N` plans : 10¹⁰⁰ pour 100 tâches sur 10 VMs. On ne le fait que pour prouver l'optimum sur les petites instances, et même là le branch and bound n'en visite qu'une fraction (908 nœuds sur 59 049 en B).
- **« Votre heuristique est-elle bonne ? »** On le mesure : sur 40 instances où l'optimum est connu, la recherche itérée le trouve 39 fois (écart max < 0,05 %) ; sur les grandes, on donne l'écart à une borne prouvée.
- **« Pourquoi LPT et pas Min-Min ? »** Mesuré : Min-Min seul est à 31 % de l'optimum en moyenne (il remplit d'abord avec les petites tâches et laisse les grosses pour la fin), LPT à 1,5 %. On calcule les trois et on garde le meilleur, ça ne coûte rien.
- **« Que veut dire OPTIMAL ? »** Optimal pour le modèle : soit la recherche a tout évalué ou élagué, soit le plan atteint une borne inférieure prouvée. Sinon on écrit FEASIBLE et l'écart (CM4).
- **« Pourquoi Go sans solveur ? »** Le projet impose un langage compilé ; notre modèle de durée n'est pas linéaire ; et toute la logique (construction, recherche locale, borne, élagage) tient en un fichier qu'on peut expliquer ligne par ligne.
