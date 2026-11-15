# Calibration du modèle de durée (4 runs réels, 12 points VM)

Modèle : partage du processeur, c cœurs effectifs par VM, chaque tâche en cours avance à la vitesse min(1, c/n) ; finish = SSH + fin de la dernière tâche. SSH = 3.0 s (TD3).

| hypothèse sur p_ij | c ajusté | erreur moyenne (MAE) | erreur relative (MAPE) | validation croisée (MAE, run laissé de côté) |
|---|---:|---:|---:|---:|
| H1 : chaque VM avec la colonne de son type | 2.53 | 3.07 s | 28.1 % | 3.54 s |
| H2 : toutes les VMs à la vitesse e2-standard-2 | 1.25 | 0.78 s | 8.5 % | 0.82 s |

| run | VM | tâches | mesuré (s) | prédit H1 (s) | prédit H2 (s) |
|---|---|---|---:|---:|---:|
| results/td3/allocation_manual | cloudopt-vm1 | 3 | 17.6 | 12.9 | 15.7 |
| results/td3/allocation_manual | cloudopt-vm2 | 3 | 11.0 | 9.7 | 8.4 |
| results/td3/allocation_manual | cloudopt-vm3 | 3 | 10.5 | 16.1 | 11.0 |
| results/td3/allocation_manual_packed | cloudopt-vm1 | 7 | 23.5 | 15.8 | 23.8 |
| results/td3/allocation_manual_packed | cloudopt-vm2 | 1 | 4.8 | 6.1 | 4.5 |
| results/td3/allocation_manual_packed | cloudopt-vm3 | 1 | 4.9 | 9.1 | 6.6 |
| results/td4/allocation_rr | cloudopt-vm1 | 3 | 15.8 | 12.9 | 15.7 |
| results/td4/allocation_rr | cloudopt-vm2 | 3 | 8.3 | 9.7 | 8.4 |
| results/td4/allocation_rr | cloudopt-vm3 | 3 | 12.0 | 16.1 | 11.0 |
| results/td4/allocation_rr_reordered | cloudopt-vm1 | 3 | 5.4 | 4.6 | 5.6 |
| results/td4/allocation_rr_reordered | cloudopt-vm2 | 3 | 18.7 | 21.6 | 18.8 |
| results/td4/allocation_rr_reordered | cloudopt-vm3 | 3 | 10.2 | 10.2 | 9.7 |
