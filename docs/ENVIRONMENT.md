# Environnement de travail et références techniques

## Machine de mesure (TD1), relevée le 2026-11-10 17:28
| Élément | Valeur |
|---|---|
| Machine | portable HP OMEN `OMEN-AdonisR`, **Ubuntu 26.04.1 LTS sous WSL2** (Windows + Hyper-V) |
| Noyau | 6.18.33.2-microsoft-standard-WSL2, x86_64 |
| CPU | AMD Ryzen 7 7840HS (Zen 4), 1 socket, **8 cœurs physiques, 2 threads/cœur → 16 CPU logiques** |
| Caches | L1d 32 Ko/cœur, L2 1 Mo/cœur (8 Mo), L3 16 Mo partagé |
| RAM visible dans WSL | **7,4 Gio** total, 6,7 Gio disponibles au repos ; swap 2 Gio |
| Stockage | disque virtuel WSL de 1 To (`sdd`, monté sur `/`) |
| Virtualisation | `Hypervisor vendor: Microsoft`, `Virtualization type: full` |
| Go | go1.26.8 linux/amd64 |

**Point important : WSL2 est lui-même une VM.** Linux tourne sur l'hyperviseur Hyper-V, comme une VM GCP tourne sur l'hyperviseur de Google. La RAM visible (7,4 Gio) est la limite fixée par WSL, pas la RAM physique du portable. Les processus Windows (navigateur, antivirus, mises à jour) partagent le même CPU sans apparaître dans `top` : c'est le « voisin bruyant » du cloud en miniature.

## Versions des outils (relevées le 2026-11-10, étape 0.2 du TD)
| Outil | Version | Rôle dans le projet |
|---|---|---|
| git | 2.53.0 | dépôt de groupe |
| GNU Make | 4.4.1 | point d'entrée unique (`make all`) |
| gcc / g++ | 15.2.0 (Ubuntu 15.2.0-16ubuntu1) | toolchain C/C++ (réimplémentation éventuelle) |
| Go | go1.26.8 linux/amd64 | compilation des workloads de référence |
| GNU time | `/usr/bin/time` (GNU Time, version affichée « UNKNOWN », build Debian/Ubuntu habituel) | mesure du temps mur (`%e`) et de la RSS max (`%M`) |

Note : `time` tout court dans bash est le mot-clé du shell, qui ne donne pas la RSS. Il faut toujours appeler **`/usr/bin/time`**.

## Commandes de référence du TD1
```bash
sudo apt install -y git make build-essential time golang-go     # 0.2
mkdir -p ~/cloud-optimization/{workloads,bin,data,results,scripts}   # 0.4
uname -a; lscpu; nproc; free -h; lsblk                          # Part 1
go build -o bin/cpu_task workloads/cpu_task.go                  # Part 2 (idem pour les 3 autres)
file bin/cpu_task                                               # vérifier ELF / lien statique
/usr/bin/time -v ./bin/cpu_task --size 500000                   # Part 4
```

## Champs utiles de `/usr/bin/time -v`
| Champ | Signification | Format `-f` |
|---|---|---|
| Elapsed (wall clock) time | temps mur (makespan, coût) | `%e` (s) |
| User time | temps CPU en mode utilisateur | `%U` |
| System time | temps CPU dans le noyau | `%S` |
| Percent of CPU this job got | (user+sys)/mur ; >100 % = parallélisme | `%P` |
| Maximum resident set size | pic de RAM physique (Ko) | `%M` |
| Major/Minor page faults | défauts de page (pression mémoire) | `%F` / `%R` |
| Voluntary/Involuntary context switches | attentes / préemptions | `%w` / `%c` |

## Références (docs officielles)
- GNU time : `man time`, https://www.gnu.org/software/time/
- Go build : `go help build`, https://pkg.go.dev/cmd/go#hdr-Compile_packages_and_dependencies
- lscpu (cœurs vs threads, « Thread(s) per core ») : `man lscpu`
- GNU Make : https://www.gnu.org/software/make/manual/
- GCP vCPU = hyperthread : https://cloud.google.com/compute/docs/cpu-platforms (pour TD2)

## Liens avec le cours
- CM1–CM2 : ressources CPU/RAM/disque d'une machine et d'une VM, « measured service » (facturation au temps).
- CM3 : makespan, heuristiques LPT/SPT, qui ont besoin de durées estimées.
- CM4 : ILP d'affectation, avec les durées p_ij et des contraintes de capacité.
- CM6 : filtrer les machines infaisables (CPU/RAM) avant de scorer, et effet de la concurrence sur les durées.
