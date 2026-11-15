# Burst : session session_20261113_2002

Unité : la plus rapide vue = 1.746 s (= vitesse 1).

| phase | VM | flux | durée (s) | vitesse au début | vitesse à la fin | burst tenu (s) | crédits (vCPU·s au-dessus du régime de base) |
|---|---|---:|---:|---:|---:|---:|---:|
| deplete | cloudopt-vm1 | 2 | 421 | 1.39 | 1.39 | pas de burst | — |
| deplete | cloudopt-vm2 | 2 | 422 | 1.40 | 0.69 | 122.0 | 86.8 |
| deplete | cloudopt-vm3 | 1 | 421 | 0.96 | 0.48 | 123.0 | 59.0 |
| recover_60 | cloudopt-vm1 | 1 | 90 | 0.98 | 0.98 | pas de burst | — |
| recover_60 | cloudopt-vm2 | 2 | 91 | 1.40 | 1.42 | toute la sonde | ≥ 66.3 |
| recover_60 | cloudopt-vm3 | 1 | 92 | 0.98 | 0.72 | 61.0 | 29.8 |
| recover_180 | cloudopt-vm1 | 1 | 91 | 0.98 | 0.98 | pas de burst | — |
| recover_180 | cloudopt-vm2 | 2 | 90 | 1.42 | 1.40 | toute la sonde | ≥ 63.3 |
| recover_180 | cloudopt-vm3 | 1 | 91 | 0.98 | 0.97 | toute la sonde | ≥ 45.5 |
| recover_600 | cloudopt-vm1 | 1 | 91 | 0.98 | 0.98 | pas de burst | — |
| recover_600 | cloudopt-vm2 | 2 | 91 | 1.42 | 1.42 | toute la sonde | ≥ 66.1 |
| recover_600 | cloudopt-vm3 | 1 | 90 | 0.99 | 0.98 | toute la sonde | ≥ 46.0 |
