# Cœurs partagés (e2-medium) : quand utiliser le burst ? (`scripts/burst_cost.py`)

Mesuré (session_20261113_2002), en « vCPU à pleine vitesse » (1 = un fil seul sur un cœur libre) :

| | e2-standard-2 | e2-medium en burst | e2-medium sans crédits |
|---|---:|---:|---:|
| 2 vCPU occupés | 1.39 | 1.40 | 0.69 |
| 1 vCPU occupé | 0.98 | 0.96 | 0.48 |
| prix ($/h, europe-west1, à la demande) | 0.0737 | 0.0369 | 0.0369 |
| vitesse par $/h (2 vCPU) | 18.8 | 37.9 | 18.6 |

- Réserve après 10 min de repos : burst tenu 122 s (2 vCPU) et 122 s (1 vCPU), soit 87 et 59 vCPU·s au-dessus du régime de base.
- Recharge : 1.03 s de burst regagnée par seconde de repos (sondes qui ont épuisé leurs crédits) ; les sondes qui ont tenu jusqu'au bout donnent seulement un minimum (1 vCPU : ≥ 0.5, 2 vCPU : ≥ 1.5). Le modèle prend la valeur prudente 1.03.

## Règle de décision

- Job court : tant que le travail tient dans le burst (≈ 170 s de travail à 2 vCPU, 122 s de calcul), l'e2-medium va aussi vite que l'e2-standard-2 pour **50 % du prix**.
- Charge intermittente : si la VM calcule moins de **51 %** du temps, ce qu'elle regagne pendant les pauses couvre le burst : pleine vitesse en permanence.
- Charge continue : l'e2-medium retombe à 0.69 vCPU. Le coût par travail reste 101 % de celui de l'e2-standard-2 (moitié de vitesse pour moitié de prix), mais c'est 2.0× plus long.

## Quelles VMs louer pour nos lots (prédit par l'optimiseur, p_ij du jour)

| lot | flotte | prix ($/h) | e2-medium | makespan (s) | coût du lot (cents $) |
|---|---|---:|---|---:|---:|
| A | 3 × e2-standard-2 + 0 × e2-medium | 0.2211 | — | 12.6 | 0.0776 |
| A | 2 × e2-standard-2 + 0 × e2-medium | 0.1474 | — | 15.8 | 0.0645 |
| A | 1 × e2-standard-2 + 0 × e2-medium | 0.0737 | — | 27.6 | 0.0565 |
| A | 2 × e2-standard-2 + 1 × e2-medium | 0.1843 | crédits pleins | 12.6 | 0.0646 |
| A | 2 × e2-standard-2 + 1 × e2-medium | 0.1843 | sans crédits | 13.7 | 0.0700 |
| A | 1 × e2-standard-2 + 2 × e2-medium | 0.1475 | crédits pleins | 12.6 | 0.0517 |
| A | 1 × e2-standard-2 + 2 × e2-medium | 0.1475 | sans crédits | 15.9 | 0.0652 |
| A | 1 × e2-standard-2 + 1 × e2-medium | 0.1106 | crédits pleins | 15.7 | 0.0482 |
| A | 1 × e2-standard-2 + 1 × e2-medium | 0.1106 | sans crédits | 19.4 | 0.0597 |
| A | 0 × e2-standard-2 + 3 × e2-medium | 0.1107 | crédits pleins | 12.6 | 0.0388 |
| A | 0 × e2-standard-2 + 3 × e2-medium | 0.1107 | sans crédits | 22.6 | 0.0695 |
| A | 0 × e2-standard-2 + 2 × e2-medium | 0.0738 | crédits pleins | 15.7 | 0.0322 |
| A | 0 × e2-standard-2 + 2 × e2-medium | 0.0738 | sans crédits | 28.9 | 0.0593 |
| B | 3 × e2-standard-2 + 0 × e2-medium | 0.2211 | — | 15.9 | 0.0978 |
| B | 2 × e2-standard-2 + 0 × e2-medium | 0.1474 | — | 20.5 | 0.0841 |
| B | 1 × e2-standard-2 + 0 × e2-medium | 0.0737 | — | 38.0 | 0.0779 |
| B | 2 × e2-standard-2 + 1 × e2-medium | 0.1843 | crédits pleins | 15.8 | 0.0811 |
| B | 2 × e2-standard-2 + 1 × e2-medium | 0.1843 | sans crédits | 18.1 | 0.0924 |
| B | 1 × e2-standard-2 + 2 × e2-medium | 0.1475 | crédits pleins | 15.8 | 0.0649 |
| B | 1 × e2-standard-2 + 2 × e2-medium | 0.1475 | sans crédits | 21.0 | 0.0860 |
| B | 1 × e2-standard-2 + 1 × e2-medium | 0.1106 | crédits pleins | 20.5 | 0.0630 |
| B | 1 × e2-standard-2 + 1 × e2-medium | 0.1106 | sans crédits | 26.5 | 0.0815 |
| B | 0 × e2-standard-2 + 3 × e2-medium | 0.1107 | crédits pleins | 15.8 | 0.0487 |
| B | 0 × e2-standard-2 + 3 × e2-medium | 0.1107 | sans crédits | 29.2 | 0.0898 |
| B | 0 × e2-standard-2 + 2 × e2-medium | 0.0738 | crédits pleins | 20.5 | 0.0421 |
| B | 0 × e2-standard-2 + 2 × e2-medium | 0.0738 | sans crédits | 38.7 | 0.0794 |
