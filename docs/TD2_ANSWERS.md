# TD2 — Réponses aux questions (Google Compute Engine)

Chaque partie indique le critère de la grille /20 qu'elle sert (`[G: …]`, voir `docs/GRILLE.md`).
Toutes les valeurs viennent des sorties de `scripts/gcp.sh` et des fichiers de `data/` (campagnes du 2026-11-10).

Configuration utilisée (source unique : `config/gcp.env`) :

| Élément | Valeur |
|---|---|
| Project ID | `arctic-kiln-510814-c8` (nom « Cloud Optimization », projet commun du groupe) |
| Zone | `europe-west1-b` (Belgique), zone des 3 VMs existantes de l’équipe |
| VM | `cloudopt-vm1` |
| Type de machine | `e2-medium` (VMs existantes de l’équipe, cœur partagé) |
| Image | **Debian 13** (`debian-13-trixie-v20260921`) sur les VMs existantes. L'image du TD (`ubuntu-2404-lts-amd64` → `ubuntu-2404-noble-amd64-v20261105`) n'est utilisée que par `create` |
| Disque de démarrage | `cloudopt-vm1`, 10 Go `pd-balanced`, `autoDelete: true` |
| Labels | `course=cloud-optimization,td=td2` |

## Part 0 — Modèle de ressources Compute Engine `[G: Workload and resource model]`
1. **Projet, région, zone.** Le **projet** est une frontière administrative : il regroupe ressources, droits IAM, quotas, API activées et facturation. Une **région** est une zone géographique (ex. `europe-west9`, Paris). Une **zone** est un lieu de déploiement isolé à l'intérieur d'une région (ex. `europe-west9-a`), avec sa propre infrastructure : une panne d'une zone n'arrête pas les autres.
2. **Un VM est une ressource zonale** : à la création, il appartient à une zone précise ; son disque de démarrage aussi.
3. **Type de machine vs image.** Le **type** (`e2-medium`) fixe le matériel virtuel : vCPU et mémoire. L'**image** (`ubuntu-2404-lts-amd64`) fixe le logiciel : le système d'exploitation installé sur le disque. On peut combiner n'importe quelle image compatible avec n'importe quel type.
4. **Image vs disque de démarrage.** L'image est un **modèle** en lecture seule, partagé. Le disque de démarrage est une **copie persistante** créée à partir de l'image, propre au VM : il contient l'OS et nos fichiers, et il existe (et coûte) tant qu'on ne le supprime pas, même VM arrêté.
5. **Disponibilité par zone.** Chaque zone a son propre parc de serveurs physiques : certaines générations de CPU n'y sont pas installées, ou la capacité est momentanément épuisée (`ZONE_RESOURCE_POOL_EXHAUSTED`). Les quotas sont aussi par région. C'est une **contrainte de faisabilité** au sens du CM6 : une machine non disponible est filtrée avant toute optimisation.

## Part 1 — CLI gcloud `[G: Technical quality and reproducibility]`
1. **Compte actif** : le compte école d'Adonis (`gcloud auth list`).
2. **Project ID** : `arctic-kiln-510814-c8`. À ne pas confondre avec le **nom** « Cloud Optimization » : les commandes utilisent l'ID unique.
3. **Pourquoi le bon projet ?** Le projet décide qui paie, quelles règles et quotas s'appliquent, et qui peut voir la ressource. Un VM créé dans un projet personnel est facturé sur la mauvaise carte et invisible pour l'équipe. C'est pourquoi nos scripts passent `--project` explicitement à chaque commande et refusent de tourner sans `PROJECT_ID` (D12).
4. **API Compute Engine** : c'est le service qui reçoit et exécute les requêtes de création, lecture et suppression de VMs, disques, réseaux. `gcloud` n'est qu'un client de cette API ; sans elle activée dans le projet, aucune ressource Compute Engine ne peut être créée.

## Part 2 — Choix de la zone `[G: Design choices (trade-offs)]`
Zone retenue : `europe-west1-b`, celle des VMs existantes du groupe (D13). Critères (encadré du TD, D13) : disponibilité du type E2 dans la zone (vérifiée par `explore`), localisation des données en Europe, prix de la région. La latence ne compte pas pour un calcul batch : la proximité seule n'est pas un argument.

## Part 3 — Types de machines `[G: Workload and resource model]`
1. **e2-medium** : 2 vCPU, 4096 Mo, `isSharedCpu: true`. Description Google : « 2 vCPU (1/2 shared physical core) » : les 2 vCPU correspondent en garantie à **la moitié d'un cœur physique**, avec du burst au-delà. Plateforme obtenue : **Intel Broadwell** (2014), contre un Ryzen Zen 4 (2023) en local.
2. **vCPU** : un **thread matériel** (hyperthread) d'un cœur physique de l'hôte, attribué au VM par l'hyperviseur. 2 vCPU = 1 cœur physique et ses 2 hyperthreads. Ce n'est pas un cœur complet : deux tâches CPU sur les 2 vCPU se partagent les unités de calcul du même cœur.
3. **Même nombre de vCPU, performances différentes** : génération et fréquence du CPU (E2 peut tomber sur Intel ou AMD de générations différentes, N2 = Intel Cascade/Ice Lake, C3 = Sapphire Rapids), taille des caches, bande passante mémoire, cœur partagé ou dédié (e2-micro/small/medium partagent un cœur par intermittence), voisins sur le même hôte.
4. **Noter le type exact** : « une VM Google Cloud » ne décrit aucune performance. Le type, la zone et la plateforme CPU sont nécessaires pour reproduire la mesure et pour construire la matrice des durées p_ij (tâche i sur machine j) du scheduler.

## Part 4 — Image
Image résolue par la famille du TD : `ubuntu-2404-noble-amd64-v20261105`, créée le 2026-11-06, `X86_64`. Nos VMs existantes ont été créées avec `debian-13-trixie-v20260921` : même architecture x86-64, donc mêmes sources Go, recompilées sur place. Une famille donne la dernière image non dépréciée : pratique, mais deux VMs créés à des dates différentes peuvent avoir un OS différent. Pour figer l'environnement, on note le nom exact de l'image (`data/gcp_explore_cloud_vm1.txt`, `gce_image` dans `machine_cloud_vm1.txt`).

## Part 5 — Création du VM `[G: Deployment on GCP VMs]`
1. **Statut** : `RUNNING`.
2. **Type attaché** : `e2-medium`, plateforme `Intel Broadwell`.
3. **Disque de démarrage** : `cloudopt-vm1`, 10 Go, `pd-balanced`, `autoDelete: true` (supprimé avec la VM).
4. **Réseau et sous-réseau** : `default` / `default`.
5. **IP externe** : oui, `34.156.123.109`, type `ONE_TO_ONE_NAT` (éphémère : elle change à chaque stop/start).

## Part 6 — Réseau `[G: Design choices (trade-offs)]`
1. **IP interne** : `10.132.0.2` (vm2 : .3, vm3 : .4, même sous-réseau `default` de `europe-west1`).
2. **IP externe** : `34.156.123.109`, éphémère (aucune IP statique réservée, D18).

Pare-feu relevé : `default-allow-ssh` (tcp:22 depuis 0.0.0.0/0) rend le SSH possible ; `default-allow-internal` autorise tout le trafic entre nos VMs (utile en TD3) ; `default-allow-rdp` (tcp:3389, bureau à distance Windows) est **inutile** pour des VMs Linux : à supprimer selon le principe du moindre privilège (D18).
3. **Pourquoi pas d'IP externe en production** : un VM sans IP publique n'est pas joignable depuis Internet, ce qui réduit la surface d'attaque. On l'administre alors par IAP ou un bastion, et il sort sur Internet via Cloud NAT si besoin. Pour nos futurs workers (TD3), seul le contrôleur aurait besoin d'un accès.
4. **IP externe insuffisante pour le SSH** : l'adresse dit *où* est l'interface, pas *quel trafic* passe. Il faut une règle de pare-feu VPC autorisant TCP 22 (ex. `default-allow-ssh`), aucune politique d'organisation qui l'interdit, un démon SSH actif dans le VM, la clé publique acceptée (métadonnées ou OS Login) et le droit IAM correspondant.

## Part 7 — SSH et inspection depuis l'OS invité `[G: Workload and resource model]`
Comparaison API (`describe`) et OS invité (`machine_cloud_vm1.txt`) : l'API annonce 2 vCPU et 4096 Mo ; l'OS voit `nproc` = 2, **1 cœur × 2 threads** (les 2 vCPU sont les 2 hyperthreads d'un même cœur), `Intel Xeon @ 2.20GHz` (Broadwell) et **3,8 Gio** (le reste est réservé au noyau et au firmware). Après passage en e2-standard-2, l'OS voit 7,8 Gio. Comme WSL2 en TD1, on mesure dans une VM.

## Part 8 — Métadonnées
`machine_info.sh` interroge le serveur de métadonnées (`instance/name`, `zone`, `machine-type`, `cpu-platform`, `image`) : le programme découvre son environnement sans rien coder en dur. On ne lit **que** ces champs : le serveur peut aussi délivrer des jetons du compte de service, à ne jamais afficher ni stocker.

## Part 9–10 — Transfert et compilation `[G: Deployment on GCP VMs]`, `[G: Technical quality and reproducibility]`
On copie le **commit** (`git archive`, D15) plutôt que le dossier, et on compile sur la VM. Vérification : `file bin/cpu_task` → `ELF 64-bit LSB executable, x86-64, statically linked` ; empreintes md5 des 4 sources **identiques** au local (`64b9f230…`, `a4beadd0…`, `8b86799b…`, `d2c4f4c4…`) ; commit déployé `73f665c`. Go sur la VM : **go1.24.4** (paquet Debian), contre go1.26.8 en local : limite notée en D15.

## Part 12 — Local vs cloud `[G: Metrics quality]`, `[G: Interpretation and limitations]`
Trois machines, **mêmes binaires (mêmes sources md5), mêmes 12 configurations, même runner, 3 runs entrelacés + 1 warm-up** :

| | Portable (local) | `cloud_vm1` | `cloud_vm1_std2` |
|---|---|---|---|
| Type | Ryzen 7 7840HS, WSL2 | GCP **e2-medium** (cœur partagé) | même VM passée en **e2-standard-2** (Part 15) |
| CPU | Zen 4 (2023), 8 cœurs / 16 threads | Intel Broadwell (2014) @ 2,2 GHz, 1 cœur / 2 threads | idem |
| RAM vue par l'OS | 7,4 Gio | 3,8 Gio | 7,8 Gio |
| OS / THP | Ubuntu 26.04, THP `madvise` | Debian 13, THP `always` | idem |
| Go | 1.26.8 | 1.24.4 | 1.24.4 |

Ratio temps VM / temps local (moyenne de 3 runs ; > 1 = VM plus lente). Détail : `results/compare_*.md`, matrice complète `data/p_matrix.csv`, figure `results/td2_machines.png`.

| workload | e2-medium / local | e2-standard-2 / local | CV e2-medium | CV e2-standard-2 |
|---|---:|---:|---:|---:|
| cpu_task | 6,3 – 6,8 | 3,7 – 3,8 | 32 – 39 % | 0,3 – 2,0 % |
| matrix_task | 3,0 – 3,9 | 1,35 – 1,40 | 6 – 47 % | 0,2 – 3,5 % |
| memory_task | 1,8 – 2,3 | **0,62 – 0,80** | 6 – 32 % | 0,5 – 1,8 % |
| sort_task | 2,1 – 2,2 | 1,01 – 1,04 | 1 – 3 % | 0,2 – 2,7 % |

1. **La VM est-elle plus rapide partout ?** Non. L'e2-medium est plus lent sur tout (×1,8 à ×6,8). L'e2-standard-2 est plus lent en calcul pur (cpu ×3,8, matrix ×1,4), **à égalité en tri**, et **plus rapide que le portable sur memory_task** (×0,62 à ×0,80). Le classement des machines **dépend de la tâche**.
2. **« Cloud » n'est pas une spécification** : deux VMs du même projet, même zone, même plateforme CPU (Broadwell), même disque, donnent des temps qui varient de ×1,7 à ×2,9 selon le **type** (cœur partagé ou non). Et une VM 2014 bat un portable 2023 sur une tâche mémoire grâce à la configuration de l'OS (huge pages, voir D20). Une performance n'a de sens qu'avec type, plateforme CPU, OS et historique de charge.
3. **Mémoire** : RSS **identique à ±1 %** sur les 3 machines (ex. memory 2048 : 2053 / 2054 / 2054 Mo ; sort 40M : 308 / 309 / 310 Mo). Seul cpu_task varie de 2,5 à 3,7 Mo (runtime Go 1.24 vs 1.26, négligeable). La RSS est une propriété de la **tâche**, pas de la machine : on peut l'utiliser comme besoin mémoire m_i unique dans la contrainte de capacité.
4. **Runs identiques ?** Non, et c'est le résultat le plus important. Sur **e2-medium**, cpu_task 20M donne 27,9 s au passage 1 puis 52,5 s et 52,6 s (CV 32–47 %). C'est le **mécanisme de burst du cœur partagé** : crédits accumulés quand la VM est inactive, consommés au début de la campagne, puis retour à la part garantie. **Expérience témoin** : sur la même VM en e2-standard-2, les 3 passages sont plats (25,8 / 25,9 / 26,8 s, CV ≤ 3,5 %), et le passage 1 de l'e2-medium (27,9 s) est proche du temps e2-standard-2 (26,2 s) : en burst, l'e2-medium tourne à pleine vitesse. Hypothèse **confirmée**.
5. **Pour reproduire** : type de machine, **plateforme CPU** (`cpuPlatform`), zone, **image exacte** et réglage THP, version du compilateur, commit du code, tailles, nombre et ordre des runs, **et l'état de la VM avant la mesure** (temps d'inactivité pour un cœur partagé). Tout est dans `data/vm_*.txt`, `data/machine_*.txt`, `data/campaign_meta_*.txt`.

## Part 13 — Commande à distance `[G: Orchestration and result collection]`
`scripts/gcp.sh bench` lance toute la campagne par `gcloud compute ssh --command`, sans shell interactif, puis `fetch` rapatrie les CSV. C'est le cœur du futur orchestrateur du TD3 : lancer, suivre, collecter.

## Part 14 — Cycle de vie et coûts `[G: Design choices (trade-offs)]`
- **stop** : statut `TERMINATED`, plus de facturation vCPU/RAM, mais le **disque de 10 Go** reste facturé (et une IP statique le serait aussi). Les fichiers sont conservés au redémarrage (`start`).
- **reset** : redémarrage brutal, sans arrêt propre de l'OS ; à éviter pendant une écriture.
- **delete** : supprime le VM ; le disque de démarrage aussi seulement si `autoDelete: true` (vérifié par `scripts/gcp.sh delete` avant confirmation). `inventory` contrôle ensuite qu'il ne reste ni disque, ni IP, ni snapshot.
- **Ce qui peut encore coûter après un stop** : disques persistants, IP statiques réservées, snapshots, images personnalisées, stockage Cloud Storage.
- **Inventaire réel** (`scripts/gcp.sh inventory`, 2026-11-10) : 3 VMs `TERMINATED`, 3 disques de 10 Go, 0 IP statique, 0 image, et **42 snapshots** créés automatiquement chaque jour (14 par disque) par une planification. Ils restent facturés même VMs arrêtées. Voir D19.
- Notre règle (D19) : chaque VM démarrée est arrêtée en fin de séance ; `inventory` vérifie qu'aucun disque orphelin ne reste. Les 3 VMs sont gardées (arrêtées) pour le TD3 et supprimées à la fin du projet.

## Part 15 — Redimensionner une VM arrêtée `[G: Design choices (trade-offs)]`
Fait sur `cloudopt-vm1` : `scripts/gcp.sh resize e2-standard-2` (stop → `set-machine-type` → start → attente du SSH). Le type a bien changé (`describe` et `gce_machine` dans `machine_cloud_vm1_std2.txt`), l'OS voit 7,8 Gio au lieu de 3,8, et les fichiers du disque sont conservés (binaires déjà compilés, pas de `setup` à refaire). Piège rencontré : juste après `start`, la VM est `RUNNING` mais le SSH refuse la connexion pendant ~20 s (l'OS démarre encore). Le script attend maintenant que `sshd` réponde.

**Coût / performance** (D21) : au tarif Google, l'e2-medium coûte la moitié de l'e2-standard-2 par heure. Coût d'une tâche = prix horaire × durée, donc coût e2-standard-2 / coût e2-medium = 2 × (t_std2 / t_medium) : **0,7** pour memory, **0,7–0,9** pour matrix, **0,95** pour sort, **1,1–1,2** pour cpu. En charge continue, la VM « deux fois plus chère » est **aussi chère ou moins chère par tâche**, et beaucoup plus prévisible.

## Part 16 — Fonctions à connaître (lien avec la suite du projet)
| Fonction | Utilité pour notre projet |
|---|---|
| Spot VMs | beaucoup moins chères (Google annonce jusqu’à ~90 % de remise), mais interruptibles : acceptable pour nos tâches courtes et rejouables, à intégrer comme compromis coût / risque (TD5) |
| Instance templates / MIG | créer N workers identiques d'un coup (TD3) |
| Custom machine types | ajuster vCPU/RAM au besoin mesuré (RSS max) au lieu d'un type standard |
| Snapshots / custom images | figer une VM déjà configurée (Go installé) pour ne pas refaire `setup` |
| Service accounts | identité minimale si un worker doit écrire ses résultats dans Cloud Storage |
