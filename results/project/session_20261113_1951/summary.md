# Session session_20261113_1951 : Round-Robin vs LPT vs opt sur les vraies VMs

5 répétitions par allocation, ordre tourné à chaque répétition ; p_ij mesurés dans la même session (`p_matrix_now.csv`).
Makespan mesuré = dernière fin − premier lancement (horloge du contrôleur, SSH compris).

| scénario | méthode | prédit (s) | mesuré moyen (s) | min – max (s) | vs Round-Robin (mesuré) |
|---|---|---:|---:|---:|---:|
| A | rr | 15.4 | 15.7 | 15.0 – 16.1 | — |
| A | opt | 12.6 | 12.5 | 12.3 – 12.7 | -20 % |
| B | rr | 20.2 | 21.1 | 19.7 – 25.2 | — |
| B | lpt | 15.8 | 16.4 | 16.2 – 16.9 | -22 % |
| B | opt | 15.8 | 16.2 | 16.1 – 16.4 | -23 % |

Mesures brutes (s) : A_rr = 16.1, 15.0, 15.4, 15.8, 15.9 ; A_opt = 12.5, 12.3, 12.7, 12.4, 12.6 ; B_rr = 20.2, 19.7, 20.1, 25.2, 20.1 ; B_lpt = 16.3, 16.2, 16.3, 16.9, 16.3 ; B_opt = 16.1, 16.3, 16.2, 16.2, 16.4

Plateforme : voir `platform.txt` ; p_ij du jour : `p_matrix_now_corrected.csv`.
