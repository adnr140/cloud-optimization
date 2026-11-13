# Passage à l'échelle des méthodes (`scripts/scaling.py`)

Instances aléatoires tirées des 12 tâches mesurées (`data/p_matrix.csv`). Parc : 1 e2-standard-2 pour 2 e2-medium,
les e2-medium avec leur propre colonne (crédits épuisés) pour que les machines soient vraiment hétérogènes.

## 1. Qualité : écart à l'optimum prouvé (petites instances)

40 instances (8 à 12 tâches, 3 ou 4 VMs), chacune résolue à l'optimum par la recherche exacte.

| méthode | optimum trouvé | écart moyen à l'optimum | écart max | plan infaisable (RAM) |
|---|---:|---:|---:|---:|
| Round-Robin (baseline) | 0/37 | 55.62 % | 132.33 % | 3 |
| LPT | 19/40 | 1.48 % | 6.30 % | 0 |
| Min-Min | 0/40 | 31.16 % | 56.63 % | 0 |
| Max-Min | 18/40 | 1.56 % | 6.91 % | 0 |
| meilleur des 3 (LPT, Min-Min, Max-Min) | 19/40 | 1.48 % | 6.30 % | 0 |
| + recherche locale (descente) | 25/40 | 0.75 % | 5.63 % | 0 |
| **+ recherche locale itérée** | 39/40 | 0.00 % | 0.03 % | 0 |

## 2. Passage à l'échelle : temps de calcul et écart à la borne inférieure

Environ 5 tâches par VM. Écart = (plan − borne inférieure) / borne : c'est un **majorant** de l'écart à l'optimum
(la borne peut être loin de l'optimum, l'écart réel est souvent plus petit). Méthode `opt` limitée à 10 s :
au-delà elle rend le meilleur plan trouvé (FEASIBLE), comme un solveur. Moyenne de 3 instances par taille.

| tâches | VMs | plans possibles | Round-Robin | meilleur glouton | + descente | + recherche itérée | `opt` | `opt` : statut | `opt` : temps max |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 9 | 3 | 10^4 | 106.6 % | 28.1 % | 26.1 % | 26.1 % | 26.1 % | 3/3 OPTIMAL | 0.01 s |
| 20 | 4 | 10^12 | 108.5 % | 24.1 % | 21.0 % | 17.8 % | 17.8 % | 3/3 OPTIMAL | 0.11 s |
| 50 | 10 | 10^50 | 126.3 % (2 infaisables) | 12.2 % | 11.3 % | 10.0 % | 10.0 % | 0/3 OPTIMAL | 10.00 s |
| 100 | 20 | 10^130 | 137.2 % (1 infaisable) | 13.0 % | 12.6 % | 11.4 % | 11.4 % | 2/3 OPTIMAL | 10.00 s |
| 200 | 40 | 10^320 | infaisable ×3 | 16.6 % | 15.8 % | 13.8 % | 13.8 % | 0/3 OPTIMAL | 10.00 s |
| 500 | 100 | 10^1000 | infaisable ×3 | 0.8 % | 0.7 % | 0.0 % | 0.0 % | 3/3 OPTIMAL | 2.29 s |
| 1000 | 200 | 10^2301 | infaisable ×3 | 2.0 % | 1.6 % | 1.3 % | 1.3 % | 1/3 OPTIMAL | 10.13 s |

Lecture : les plans possibles explosent (M^N), le temps de calcul de `opt` reste borné par la limite.
Un écart à la borne non nul avec le statut OPTIMAL (9 et 20 tâches) veut dire que la borne est loin : le plan est
prouvé optimal par la recherche exacte, pas par la borne. Round-Robin devient infaisable dès 50 tâches (RAM).
La preuve d'optimalité (OPTIMAL) s'obtient quand la recherche exacte termine (petites instances) ou quand le plan
atteint la borne inférieure (grandes instances dominées par les plus grosses tâches).
