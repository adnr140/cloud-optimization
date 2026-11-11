# TD3 — Exécution distribuée sur Compute Engine

Chaque partie indique le critère de la grille /20 qu'elle sert (`[G: …]`, voir `docs/GRILLE.md`). Choix détaillés : `docs/DECISIONS.md` D23–D30.
Les valeurs marquées _à relever_ viennent de l'exécution réelle sur les VMs (dossiers `results/td3/*/`).

## Architecture `[G: Architecture clarity]`

```mermaid
flowchart LR
  A[data/allocation_manual.csv<br/>task_id, workload, size, vm] --> R[run_all.sh<br/>1 valide le CSV<br/>2 lance chaque tâche avec &amp;<br/>3 un seul wait<br/>4 check_results.sh]
  R -->|run_task.sh T1 &| V1[cloudopt-vm1<br/>e2-standard-2]
  R -->|run_task.sh T2 &| V2[cloudopt-vm2<br/>e2-medium]
  R -->|run_task.sh T3 &| V3[cloudopt-vm3<br/>e2-medium]
  V1 & V2 & V3 -->|stdout / stderr par SSH| O[results/td3/&lt;run&gt;/<br/>Ti.out Ti.err Ti.meta<br/>launch.log check.txt]
```

| Rôle | Fichier | Change quand on change le placement ? |
|---|---|---|
| Décision (où va chaque tâche) | `data/allocation_*.csv` | oui, c'est le seul |
| Validation + lancement + attente | `scripts/run_all.sh` | non |
| Une tâche sur une VM | `scripts/run_task.sh` | non |
| Contrôle des résultats | `scripts/check_results.sh` | non |
| Déploiement des binaires | `scripts/deploy_all.sh` | non |
| Preuve de concurrence (`ps` sur chaque VM) | `scripts/ps_all.sh` (appelé par `run_all.sh` 8 s après le lancement) | non |

## Part 1 — Les VMs `[G: Deployment on GCP VMs]`
Projet `arctic-kiln-510814-c8`, zone **`europe-west1-b`** (les 3 VMs dans la même zone), Debian 13 sur les trois.

| VM | Type | vCPU / RAM | Remarque |
|---|---|---|---|
| `cloudopt-vm1` | e2-standard-2 | 2 / 8 Go | cœur dédié (redimensionnée au TD2, D21) |
| `cloudopt-vm2` | e2-medium | 2 / 4 Go | cœur partagé, burst |
| `cloudopt-vm3` | e2-medium | 2 / 4 Go | cœur partagé, burst |

On réutilise les VMs existantes (D13) : aucune nouvelle ressource. Le parc est **hétérogène**, ce qui sera utile en TD4–TD5. Relevé (`scripts/gcp.sh start-all`, 2026-11-11) :

```
NAME          ZONE            MACHINE_TYPE   STATUS   NETWORK_IP  NAT_IP
cloudopt-vm1  europe-west1-b  e2-standard-2  RUNNING  10.132.0.2  35.205.6.138
cloudopt-vm2  europe-west1-b  e2-medium      RUNNING  10.132.0.3  35.195.94.16
cloudopt-vm3  europe-west1-b  e2-medium      RUNNING  10.132.0.4  35.241.216.47
```
Les 3 VMs démarrent en une seule commande ; `RUNNING` n'est pas « prêt » : le script attend que `sshd` réponde (vm1 a demandé ~20 s).

## Part 2 — Déploiement `[G: Deployment on GCP VMs]`
`scripts/deploy_all.sh` (D28) : compilation unique et statique, `scp` vers `~/cloud-optimization/bin/`, md5 identiques au local sur les 3 VMs, test de fumée des 4 workloads. Résultat (2026-11-11) :
- md5 des 4 binaires **identiques** sur le contrôleur et les 3 VMs (`cpu_task 322ad78f…`, `matrix_task f61efa41…`, `memory_task 031c11cd…`, `sort_task b1144a8e…`) ;
- chaque VM affiche son `hostname`, puis une ligne JSON par workload ;
- les **checksums des résultats sont identiques** sur les 3 VMs (ex. `cpu_task` 100000 → `primes_found 9592` ; `sort_task` → `1502330362` ; `memory_task` → `16167664967934279680`) : même binaire, même calcul, même résultat, quelle que soit la machine. Seule la durée varie.
- aucune installation sur vm2 et vm3 : un binaire Go statique n'a besoin d'aucune bibliothèque.

## Part 3 — Tâches et allocation manuelle `[G: Integration and validity]`
9 tâches indépendantes, les 4 workloads, tailles déjà validées en TD1/TD2 (D29).

| task | workload | size | allocation 1 (`allocation_manual.csv`) | allocation 2 (`allocation_manual_packed.csv`) |
|---|---|---:|---|---|
| T1 | cpu_task | 10 000 000 | vm1 | vm1 |
| T2 | cpu_task | 5 000 000 | vm2 | vm1 |
| T3 | matrix_task | 1500 | vm3 | vm1 |
| T4 | matrix_task | 1000 | vm1 | vm1 |
| T5 | memory_task | 1024 | vm2 | vm1 |
| T6 | memory_task | 512 | vm3 | vm1 |
| T7 | sort_task | 20 000 000 | vm1 | vm1 |
| T8 | sort_task | 10 000 000 | vm2 | vm2 |
| T9 | cpu_task | 5 000 000 | vm3 | vm3 |

Règles de validité vérifiées **automatiquement** par `run_all.sh` avant tout lancement (D25) : en-tête exact, 4 champs non vides, `task_id` unique, workload connu, taille entière, VM existante et `RUNNING`. Contrôle en plus : caractères autorisés (pas d'injection de commande dans le SSH). Contrôle fait à la main : la somme des RSS par VM tient dans sa RAM (pire cas 1,8 Go sur 8 Go).

## Part 4 — Une tâche sur une VM
```bash
gcloud compute ssh cloudopt-vm1 --zone=europe-west1-b --command="cd ~/cloud-optimization && ./bin/cpu_task --size 500000"
```
Le processus local `gcloud compute ssh` reste actif **jusqu'à la fin** de la commande distante. Enchaîner ces commandes les exécute donc l'une après l'autre : c'est le comportement à éviter.

**Observé** (2026-11-11, deux `cpu_task --size 5000000`, vm1 puis vm2, lancées l'une après l'autre) :

| | début | fin | durée vue par le contrôleur | `runtime_s` du programme |
|---|---|---|---:|---:|
| vm1 | 10:00:20 | 10:00:27 | ~7 s | 4,52 s |
| vm2 | 10:00:27 | 10:00:34 | ~7 s | 4,07 s |

1. **Séquentiel** : la tâche sur vm2 ne démarre qu'à la fin de celle sur vm1 (10:00:27), alors que les deux VMs sont indépendantes. Total ≈ 14 s ≈ somme des deux.
2. **Coût du SSH** : ~2,5 s par tâche (7 s vues par le contrôleur contre 4,5 s de calcul) pour l'authentification et l'ouverture de session. C'est pour ça qu'on garde des tâches de plusieurs secondes, et c'est un coût fixe à intégrer au modèle en TD4 (les temps `p_ij` du TD2 ne le contiennent pas).
3. Même résultat sur les deux VMs (`primes_found 348513`). (L'e2-medium vm2 n'est pas plus lente que vm1 ici : elle sort d'une longue inactivité et a ses crédits de burst, voir D21. Pas d'analyse de performance en TD3.)

## Part 5 — `run_task.sh` `[G: Orchestration and result collection]`
Interface : `scripts/run_task.sh TASK_ID WORKLOAD SIZE VM ZONE [OUTDIR]`. Vérifie les paramètres, exécute `hostname; cd ~/cloud-optimization && exec ./bin/WORKLOAD --size SIZE` sur la VM, redirige stdout vers `TASK_ID.out` et stderr vers `TASK_ID.err` **sur le contrôleur**, écrit `TASK_ID.meta` (VM, hostname distant, code de sortie, heures), et sort avec le code de la commande distante. Test sur une tâche (`scripts/run_task.sh T0 cpu_task 5000000 cloudopt-vm1 europe-west1-b results/td3/single`) :
- code de sortie **0**, 3 fichiers créés **sur le contrôleur** : `T0.out`, `T0.err`, `T0.meta` ;
- `T0.out` = la ligne JSON pure du workload (`{"task":"cpu_task","size":5000000,…,"primes_found":348513}`) ; la ligne `hostname` a bien été retirée ;
- `T0.meta` : `vm=cloudopt-vm1`, **`remote_host=cloudopt-vm1`** (placement prouvé), `exit_code=0` ;
- `T0.err` vide : pas d'erreur, et pas d'avertissement `gcloud` une fois les clés d'hôte connues.

## Part 6 — `&` et `wait`
`&` lance la commande en arrière-plan et rend la main tout de suite : les 9 processus `gcloud` partent en moins d'une seconde. `wait` bloque jusqu'à ce que **tous** les processus lancés par ce shell soient terminés. Donc : `&` = « lance et continue », `wait` = « tout est lancé, attends la fin de tout ».

**Observé** (3 `run_task.sh … &` à la main, A1 et A3 sur vm1, A2 sur vm2, `cpu_task 5000000`) :
```
10:04:46            <- avant les 3 lancements
[1] 2760 [2] 2763 [3] 2768   <- 3 processus en arrière-plan, PID différents
10:04:46            <- après les 3 lancements : même seconde, & n'attend pas
[10:04:54] done A2 on cloudopt-vm2
[10:04:55] done A3 on cloudopt-vm1
[10:04:55] done A1 on cloudopt-vm1
10:04:55            <- wait rend la main quand le DERNIER est fini
```
3 tâches de ~7 s chacune (étape 2) finies en **9 s** au lieu de ~21 s en séquentiel. A1 et A3 partagent vm1 et finissent ensemble : le noyau de la VM a réparti ses 2 vCPU entre les deux processus.

Piège rencontré dans la conception (D24) : `gcloud compute ssh` lit l'entrée standard. Dans une boucle `while read`, il consommerait le reste du CSV. On lit le fichier avant de lancer, et chaque tâche reçoit `</dev/null`.

## Part 7 — Plusieurs tâches sur la même VM `[G: Distributed execution, parallel]`
Chaque tâche a sa propre session SSH, donc son propre processus sur la VM. Aucune file par VM : si 3 tâches vont sur vm1, les 3 tournent ensemble et le noyau Linux de la VM partage ses 2 vCPU entre elles. Nos workloads sont mono-thread (WORKLOADS.md) : avec 3 tâches sur 2 vCPU, chacune reçoit en moyenne ~2/3 d'un vCPU.

## Part 8 — `run_all.sh`
Saute l'en-tête, lit chaque ligne, extrait les 4 champs, appelle `run_task.sh … &`, passe à la ligne suivante, puis **un seul `wait` après la boucle**, puis `All tasks completed`, puis `check_results.sh`. Usage : `scripts/run_all.sh [ALLOCATION_CSV] [OUTDIR]`.

## Part 9 — Exécution distribuée `[G: Distributed execution, parallel]`
Run du 2026-11-11, `scripts/run_all.sh` (allocation 1, 3 tâches par VM) :
- validation OK, puis **9 lancements dans la même seconde** (10:05:19) ;
- fins échelonnées de 10:05:23 (T6) à 10:05:34 (T1), dans un ordre qui n'a rien à voir avec l'ordre du CSV : chaque tâche vit sa vie ;
- `All tasks completed` affiché **après** la dernière fin (T1) : le `wait` unique a bien attendu tout le monde ;
- tableau final `CHECK OK: 9/9`, 3 tâches simultanées sur chaque VM.

| task | vm | fin (s après le lancement) |
|---|---|---:|
| T6 memory 512 | vm3 | 4,1 |
| T9 cpu 5M | vm3 | 5,1 |
| T5 memory 1024 | vm2 | 5,3 |
| T8 sort 10M | vm2 | 6,2 |
| T4 matrix 1000 | vm1 | 6,9 |
| T7 sort 20M | vm1 | 8,6 |
| T2 cpu 5M | vm2 | 8,6 |
| T3 matrix 1500 | vm3 | 10,6 |
| T1 cpu 10M | vm1 | 15,4 |

L'ensemble rend la main en ~15 s, la durée de la tâche la plus longue. Additionnées une à une, ces durées font ~71 s : c'est ce que donnerait une exécution séquentielle. (Ce n'est pas une mesure de performance, seulement le constat que les tâches ont bien tourné en parallèle.)

**Preuve par `ps`** : le premier instantané (pris 8 s après le lancement) n'a vu que T1 sur vm1 et T3 sur vm3, les autres tâches étaient **déjà finies**. Avec ~2,5 s de connexion SSH, 8 s c'était trop tard pour des tâches de 4 à 15 s. Corrections : (1) instantané pris 1 s après le lancement ; (2) **preuve plus rigoureuse** : chaque tâche note maintenant l'heure de son démarrage **sur la VM** (`remote_start_epoch`, horloge de la VM) et la durée annoncée par le workload (`runtime_s`). `check_results.sh` calcule le nombre maximal de processus qui tournaient en même temps sur chaque VM à partir de ces intervalles, et non plus à partir des heures du contrôleur, qui incluent le SSH.

**Run 2, avec la preuve corrigée** (10:15:30, même allocation) : `CHECK OK 9/9`, et cette fois les deux preuves concordent.

```
# ps snapshot 2026-11-11T10:15:32+01:00
== cloudopt-vm1 : 2 workload process(es)
   2139   0 62.5   4080 ./bin/cpu_task --size 10000000
   2140   0 87.5  22844 ./bin/matrix_task --size 1000
== cloudopt-vm2 : 3 workload process(es)
   2022   0 65.5  82192 ./bin/sort_task --size 10000000
   2031   0 73.3   4072 ./bin/cpu_task --size 5000000
   2037   0 50.0 314708 ./bin/memory_task --size 1024
== cloudopt-vm3 : 3 workload process(es)
   1986   0 86.2 531196 ./bin/memory_task --size 512
   2001   0 93.9  39432 ./bin/matrix_task --size 1500
   2016   0 36.3   4072 ./bin/cpu_task --size 5000000
```
- **3 processus workload vivants en même temps** sur vm2 et vm3, 2 sur vm1 (T7 n'avait pas encore fini d'ouvrir sa session SSH) : plusieurs tâches partagent bien la même VM (Part 7).
- Calcul sur l'horloge des VMs (`check_results.sh`) : **3 tâches simultanées au maximum sur chaque VM**.
- `T1.meta` : lancé par le contrôleur à `…530,98`, démarré sur vm1 à `…534,02` → **3 s** d'ouverture SSH avant que le programme ne démarre.
- Observation pour TD4 (pas une mesure TD3) : seul sur l'e2-standard-2, `cpu_task 10M` dure 9,6 s (TD2) ; ici, à 3 tâches sur 2 vCPU, son `runtime_s` vaut 14,6 s. Une durée dépend de ce qui tourne à côté (CM6) : les `p_ij` mesurés seuls ne suffiront pas si on empile plus de tâches que de vCPU.

## Part 10 — Validation `[G: Orchestration and result collection]`
`check_results.sh` contrôle les 6 points du TD pour chaque tâche :

| Point du TD | Comment on le prouve |
|---|---|
| 1. lancée exactement une fois | une seule ligne par tâche dans `launch.log` |
| 2. sur la VM prévue | `remote_host` (hostname vu par la VM) = colonne `vm` |
| 3. une sortie locale par tâche | `Ti.out` contient la ligne JSON du bon workload et de la bonne taille ; aucune sortie en trop |
| 4. erreurs visibles | `Ti.err` conservé pour chaque tâche |
| 5. échecs non ignorés | `exit_code` dans `Ti.meta`, `run_all.sh` sort en 1 si une tâche échoue (test : `allocation_failtest.csv`) |
| 6. `run_all.sh` rend la main après la fin de tout | `wait` unique ; chaque `.meta` a une heure de fin antérieure au message final |

Résultat allocation 1 : `CHECK OK: 9/9 tasks launched once, on the right VM, exit 0, output collected` (`results/td3/allocation_manual/check.txt`).

**Test d'échec** (`scripts/run_all.sh data/allocation_failtest.csv`) : F1 = `cpu_task 1000000` sur vm2, F2 = `cpu_task 1` sur vm3, que le programme refuse.
```
[10:15:53] FAILED F2 on cloudopt-vm3 (exit 1, see …/F2.err)
[10:15:53] done   F1 on cloudopt-vm2
F1 … rc 0  OK
F2 … rc 1  FAIL: exit 1, see F2.err;no cpu_task size 1 JSON line in F2.out
CHECK FAILED: 1 problem(s) out of 2 tasks
exit=1
F2.err : error: --size must be >= 2
```
- l'échec de F2 **n'empêche pas** F1 de finir : les tâches sont indépendantes ;
- le message d'erreur du programme est conservé tel quel dans `F2.err`, le code de sortie dans `F2.meta` (`exit_code=1`) ;
- `run_all.sh` sort en **1** : un script ou un opérateur qui l'appelle voit l'échec. Rien n'est ignoré silencieusement.

## Part 11 — Autre allocation, même mécanisme `[G: Integration and validity]`
Seule la colonne `vm` change (`diff <(cut -d, -f1-3 data/allocation_manual.csv) <(cut -d, -f1-3 data/allocation_manual_packed.csv)` ne renvoie rien). Commande : `scripts/run_all.sh data/allocation_manual_packed.csv`. Aucun script modifié. Vérifié le 2026-11-11 : `diff` vide (« mêmes tâches, seule la colonne vm change »), `git status --short scripts/` vide (aucun script modifié).

Run `scripts/run_all.sh data/allocation_manual_packed.csv` (10:25:57) : **`CHECK OK 9/9`**, 7 tâches simultanées sur vm1 (horloge VM), 1 sur vm2, 1 sur vm3.

```
# ps snapshot 2026-11-11T10:25:59+01:00
== cloudopt-vm1 : 7 workload process(es)   [PID ELAPSED_S %CPU RSS_KB COMMAND]
   2484   0 26.4 226044 ./bin/memory_task --size 512
   2485   0 28.3  41304 ./bin/matrix_task --size 1500
   2486   0 30.1   4072 ./bin/cpu_task --size 10000000
   2487   0 26.4 220500 ./bin/memory_task --size 1024
   2488   0 28.3  47460 ./bin/sort_task --size 20000000
   2525   0 21.8   6128 ./bin/cpu_task --size 5000000
   2539   0 25.0  20828 ./bin/matrix_task --size 1000
== cloudopt-vm2 : 1 workload process(es)
   2367   0  100  84252 ./bin/sort_task --size 10000000
== cloudopt-vm3 : 1 workload process(es)
  13055   0 96.9   4084 ./bin/cpu_task --size 5000000
```
- **7 processus vivants en même temps sur vm1**, chacun à **~22–30 % de CPU** : 2 vCPU partagés entre 7 processus mono-thread donnent 200 % / 7 ≈ **29 %** chacun. C'est l'ordonnanceur du noyau de la VM qui fait ce partage, nous n'avons rien codé (Part 7).
- Sur vm2 et vm3, une tâche seule prend **~100 %** d'un vCPU.
- Les tâches ont tourné sur les VMs nouvellement choisies (`remote_host` = nouvelle colonne `vm`), y compris à 7 sur la même VM, sans erreur ni manque de mémoire (pire cas prévu : 1,8 Go sur 8 Go, D29).
- 7 sessions SSH simultanées vers vm1 : sous la limite `MaxStartups 10` de sshd (D24).

Comme le demande le TD, on **ne compare pas** les deux allocations en performance : ce sera l'objet du TD4–TD5.

## Nettoyage `[G: Design choices (trade-offs)]`
`scripts/gcp.sh stop-all` puis `scripts/gcp.sh inventory` (2026-11-11, 10:27) : les 3 VMs en **`TERMINATED`**, 0 IP statique, 0 image, 3 disques de 10 Go et **42 snapshots** (inchangé depuis le TD2 : la planification quotidienne `default-schedule-1` est toujours attachée, D19, à traiter en équipe). Les VMs restent arrêtées pour TD4–TD5 et seront supprimées à la fin du projet (D19, D30).

## Résultats bruts versionnés
`results/td3/allocation_manual/`, `results/td3/allocation_manual_packed/`, `results/td3/allocation_failtest/` : allocation utilisée, `Ti.out/.err/.meta`, `launch.log`, `ps_snapshot.txt`, `check.txt`.
