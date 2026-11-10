# Workloads de référence : ce que fait chaque programme (lu dans les sources du prof)

| Workload | `--size` = | Algorithme | Complexité attendue | Mémoire attendue | Ce que mesure le `runtime_s` interne |
|---|---|---|---|---|---|
| `cpu_task` | plus grand entier testé N | test de primalité par divisions impaires jusqu'à √n, pour n = 2..N | ≈ O(N^1.5 / log N) (les nombres premiers dominent le coût) → exposant k ≈ 1.3–1.5 | quasi nulle (quelques Mo, runtime Go) | la boucle de test seulement |
| `memory_task` | Mo alloués | alloue un `[]uint64` de size Mo, l'écrit, puis 5 passes lecture+XOR (`--passes`, défaut 5) | O(size × passes) → k ≈ 1 | ≈ size Mo (RSS ≈ taille demandée) | allocation + écriture + passes |
| `matrix_task` | dimension N (matrices N×N) | multiplication naïve, ordre i-k-j, float64 | O(N³) → k ≈ 3 | 3 × N² × 8 o (≈ 8,6 Mo pour N=600) | la multiplication seulement (pas l'initialisation) |
| `sort_task` | nombre d'entiers | génère `size` entiers pseudo-aléatoires (seed 42, `--seed`) puis `sort.Ints` | O(n log n) → k légèrement > 1 | ≈ 8 o × n (80 Mo pour 10 M) | le tri seulement (pas la génération) |

Sortie : une ligne JSON par exécution, par exemple `{"task":"cpu_task","size":500000,"runtime_s":0.241,"primes_found":41538}`.
Un checksum ou un nombre de premiers permet de vérifier que le calcul est déterministe (même résultat sur toutes les VMs).

## Points utiles pour l'oral
- **Le `runtime_s` interne ≠ le temps mur.** Il exclut le démarrage du processus, et pour matrix/sort il exclut aussi l'initialisation des données. On mesure donc le temps mur avec GNU time (D3) : c'est ce qui compte pour le makespan et le coût. Écart attendu : faible pour cpu, plus visible pour sort (génération) et matrix (init).
- **Tous les workloads sont mono-thread** (pas de goroutines). Une tâche occupe donc ~1 vCPU, et une VM à k vCPU peut exécuter jusqu'à ~k tâches en parallèle avant contention CPU. memory_task sature plutôt la bande passante mémoire. C'est une hypothèse clé pour TD3 et le modèle de capacité.
- **matrix_task** : N=600 ne prend que ~9 Mo. C'est un profil CPU + cache, pas un gros consommateur de RAM.
- **memory_task** est la seule tâche dont la RSS dépend fortement de `--size`. C'est elle qui rend la contrainte mémoire des VMs active (petite VM = RAM limitée).
- Le README du prof suggère des tailles de tri 1 M / 5 M / 10 M (le TD dit 1 M en exemple).

Source : `workloads/*.go`, `workloads/README_prof.md`.
