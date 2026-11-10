# TD2 — Réponses aux questions (Google Compute Engine)

Chaque partie indique le critère de la grille /20 qu'elle sert (`[G: …]`, voir `docs/GRILLE.md`).
Les valeurs marquées **⟨à relever⟩** viennent des sorties de `scripts/gcp.sh` et sont complétées après exécution.

Configuration utilisée (source unique : `config/gcp.env`) :

| Élément | Valeur |
|---|---|
| Project ID | ⟨à relever⟩ |
| Zone | `europe-west1-b` (Belgique), zone des 3 VMs existantes de l’équipe |
| VM | `cloudopt-vm1` |
| Type de machine | `e2-standard-2` |
| Image | famille `ubuntu-2404-lts-amd64` (projet `ubuntu-os-cloud`), image résolue ⟨à relever⟩ |
| Disque de démarrage | 20 Go `pd-balanced`, autoDelete ⟨à relever⟩ |
| Labels | `course=cloud-optimization,td=td2` |

## Part 0 — Modèle de ressources Compute Engine `[G: Workload and resource model]`
1. **Projet, région, zone.** Le **projet** est une frontière administrative : il regroupe ressources, droits IAM, quotas, API activées et facturation. Une **région** est une zone géographique (ex. `europe-west9`, Paris). Une **zone** est un lieu de déploiement isolé à l'intérieur d'une région (ex. `europe-west9-a`), avec sa propre infrastructure : une panne d'une zone n'arrête pas les autres.
2. **Un VM est une ressource zonale** : à la création, il appartient à une zone précise ; son disque de démarrage aussi.
3. **Type de machine vs image.** Le **type** (`e2-standard-2`) fixe le matériel virtuel : vCPU et mémoire. L'**image** (`ubuntu-2404-lts-amd64`) fixe le logiciel : le système d'exploitation installé sur le disque. On peut combiner n'importe quelle image compatible avec n'importe quel type.
4. **Image vs disque de démarrage.** L'image est un **modèle** en lecture seule, partagé. Le disque de démarrage est une **copie persistante** créée à partir de l'image, propre au VM : il contient l'OS et nos fichiers, et il existe (et coûte) tant qu'on ne le supprime pas, même VM arrêté.
5. **Disponibilité par zone.** Chaque zone a son propre parc de serveurs physiques : certaines générations de CPU n'y sont pas installées, ou la capacité est momentanément épuisée (`ZONE_RESOURCE_POOL_EXHAUSTED`). Les quotas sont aussi par région. C'est une **contrainte de faisabilité** au sens du CM6 : une machine non disponible est filtrée avant toute optimisation.

## Part 1 — CLI gcloud `[G: Technical quality and reproducibility]`
1. **Compte actif** : ⟨à relever⟩ (`scripts/gcp.sh preflight`, ligne « active account »).
2. **Project ID** : ⟨à relever⟩.
3. **Pourquoi le bon projet ?** Le projet décide qui paie, quelles règles et quotas s'appliquent, et qui peut voir la ressource. Un VM créé dans un projet personnel est facturé sur la mauvaise carte et invisible pour l'équipe. C'est pourquoi nos scripts passent `--project` explicitement à chaque commande et refusent de tourner sans `PROJECT_ID` (D12).
4. **API Compute Engine** : c'est le service qui reçoit et exécute les requêtes de création, lecture et suppression de VMs, disques, réseaux. `gcloud` n'est qu'un client de cette API ; sans elle activée dans le projet, aucune ressource Compute Engine ne peut être créée.

## Part 2 — Choix de la zone `[G: Design choices (trade-offs)]`
Zone retenue : ⟨à relever⟩. Critères (encadré du TD, D13) : disponibilité du type E2 dans la zone (vérifiée par `explore`), localisation des données en Europe, prix de la région. La latence ne compte pas pour un calcul batch : la proximité seule n'est pas un argument.

## Part 3 — Types de machines `[G: Workload and resource model]`
1. **e2-standard-2** : ⟨à relever : guestCpus, memoryMb, isSharedCpu⟩ (attendu : 2 vCPU, 8192 Mo, `isSharedCpu: false`).
2. **vCPU** : un **thread matériel** (hyperthread) d'un cœur physique de l'hôte, attribué au VM par l'hyperviseur. 2 vCPU = 1 cœur physique et ses 2 hyperthreads. Ce n'est pas un cœur complet : deux tâches CPU sur les 2 vCPU se partagent les unités de calcul du même cœur.
3. **Même nombre de vCPU, performances différentes** : génération et fréquence du CPU (E2 peut tomber sur Intel ou AMD de générations différentes, N2 = Intel Cascade/Ice Lake, C3 = Sapphire Rapids), taille des caches, bande passante mémoire, cœur partagé ou dédié (e2-micro/small/medium partagent un cœur par intermittence), voisins sur le même hôte.
4. **Noter le type exact** : « une VM Google Cloud » ne décrit aucune performance. Le type, la zone et la plateforme CPU sont nécessaires pour reproduire la mesure et pour construire la matrice des durées p_ij (tâche i sur machine j) du scheduler.

## Part 4 — Image
Image résolue par la famille : ⟨à relever : name, creationTimestamp, architecture X86_64⟩. Une famille donne la dernière image non dépréciée : pratique, mais deux VMs créés à des dates différentes peuvent avoir un OS différent. Pour figer l'environnement, on note le nom exact de l'image (`data/gcp_explore_cloud_vm1.txt`, `gce_image` dans `machine_cloud_vm1.txt`).

## Part 5 — Création du VM `[G: Deployment on GCP VMs]`
1. **Statut** : ⟨à relever⟩ (attendu `RUNNING`).
2. **Type attaché** : ⟨à relever⟩.
3. **Disque de démarrage** : ⟨nom, taille, type⟩ (attendu : `cloudopt-vm1`, 20 Go, `pd-balanced`).
4. **Réseau et sous-réseau** : ⟨à relever⟩ (attendu `default` / `default`).
5. **IP externe** : ⟨oui/non, adresse éphémère⟩.

## Part 6 — Réseau `[G: Design choices (trade-offs)]`
1. **IP interne** : ⟨à relever⟩.
2. **IP externe** : ⟨à relever⟩, éphémère (aucune IP statique réservée, D18).
3. **Pourquoi pas d'IP externe en production** : un VM sans IP publique n'est pas joignable depuis Internet, ce qui réduit la surface d'attaque. On l'administre alors par IAP ou un bastion, et il sort sur Internet via Cloud NAT si besoin. Pour nos futurs workers (TD3), seul le contrôleur aurait besoin d'un accès.
4. **IP externe insuffisante pour le SSH** : l'adresse dit *où* est l'interface, pas *quel trafic* passe. Il faut une règle de pare-feu VPC autorisant TCP 22 (ex. `default-allow-ssh`), aucune politique d'organisation qui l'interdit, un démon SSH actif dans le VM, la clé publique acceptée (métadonnées ou OS Login) et le droit IAM correspondant.

## Part 7 — SSH et inspection depuis l'OS invité `[G: Workload and resource model]`
Comparaison API (`describe`) et OS invité (`machine_cloud_vm1.txt`) : ⟨nproc = 2 ? free = ~7,8 Gio ? modèle CPU lscpu ?⟩. L'OS voit un peu moins que 8 Go (mémoire réservée par le noyau). `lscpu` montre « Hypervisor vendor: KVM » : comme WSL2 en TD1, on mesure dans une VM.

## Part 8 — Métadonnées
`machine_info.sh` interroge le serveur de métadonnées (`instance/name`, `zone`, `machine-type`, `cpu-platform`, `image`) : le programme découvre son environnement sans rien coder en dur. On ne lit **que** ces champs : le serveur peut aussi délivrer des jetons du compte de service, à ne jamais afficher ni stocker.

## Part 9–10 — Transfert et compilation `[G: Deployment on GCP VMs]`, `[G: Technical quality and reproducibility]`
On copie le **commit** (`git archive`, D15) plutôt que le dossier, et on compile sur la VM. Vérification : `file bin/cpu_task` ⟨ELF 64-bit x86-64, statically linked⟩, empreintes md5 identiques au local. Version de Go sur la VM : ⟨à relever⟩ (différente du local go1.26.8, limite notée en D15).

## Part 12 — Local vs cloud `[G: Metrics quality]`, `[G: Interpretation and limitations]`
Tableau complet : `results/compare_local_vs_cloud_vm1.md` (12 configurations, 3 runs chacune, mêmes tailles, même runner).
1. **Le VM est-il plus rapide partout ?** ⟨à compléter avec les ratios⟩.
2. **« Cloud » n'est pas une spécification** : une VM cloud peut être plus lente ou plus rapide qu'un portable selon le type, la génération de CPU, le nombre de vCPU et le partage de l'hôte. Seule la description complète (type, plateforme CPU, zone) a un sens.
3. **Mémoire** : ⟨RSS local vs cloud⟩. Attendu : RSS quasi identique, car elle dépend du programme et de la taille, pas de la vitesse de la machine. C'est ce qui permet d'utiliser m_i comme besoin mémoire indépendant de la VM dans la contrainte de capacité.
4. **Runs identiques ?** ⟨CV cloud⟩. Non : ordonnancement de l'hyperviseur, voisins sur l'hôte, fréquence variable, cache. On garde les 3 runs bruts et on reporte le CV.
5. **Pour reproduire** : type de machine, plateforme CPU, zone, image exacte, type et taille de disque, version du compilateur, commit du code, tailles et nombre de runs. Tout est dans `data/vm_cloud_vm1.txt`, `data/machine_cloud_vm1.txt` et `data/campaign_meta_cloud_vm1.txt`.

## Part 13 — Commande à distance `[G: Orchestration and result collection]`
`scripts/gcp.sh bench` lance toute la campagne par `gcloud compute ssh --command`, sans shell interactif, puis `fetch` rapatrie les CSV. C'est le cœur du futur orchestrateur du TD3 : lancer, suivre, collecter.

## Part 14 — Cycle de vie et coûts `[G: Design choices (trade-offs)]`
- **stop** : statut `TERMINATED`, plus de facturation vCPU/RAM, mais le **disque de 20 Go** reste facturé (et une IP statique le serait aussi). Les fichiers sont conservés au redémarrage (`start`).
- **reset** : redémarrage brutal, sans arrêt propre de l'OS ; à éviter pendant une écriture.
- **delete** : supprime le VM ; le disque de démarrage aussi seulement si `autoDelete: true` (vérifié par `scripts/gcp.sh delete` avant confirmation). `inventory` contrôle ensuite qu'il ne reste ni disque, ni IP, ni snapshot.
- **Ce qui peut encore coûter après un stop** : disques persistants, IP statiques réservées, snapshots, images personnalisées, stockage Cloud Storage.
- Notre règle (D19) : stop entre deux séances, delete dès les données rapatriées et commitées ; recréer coûte deux commandes.

## Part 16 — Fonctions à connaître (lien avec la suite du projet)
| Fonction | Utilité pour notre projet |
|---|---|
| Spot VMs | beaucoup moins chères (Google annonce jusqu’à ~90 % de remise), mais interruptibles : acceptable pour nos tâches courtes et rejouables, à intégrer comme compromis coût / risque (TD5) |
| Instance templates / MIG | créer N workers identiques d'un coup (TD3) |
| Custom machine types | ajuster vCPU/RAM au besoin mesuré (RSS max) au lieu d'un type standard |
| Snapshots / custom images | figer une VM déjà configurée (Go installé) pour ne pas refaire `setup` |
| Service accounts | identité minimale si un worker doit écrire ses résultats dans Cloud Storage |
