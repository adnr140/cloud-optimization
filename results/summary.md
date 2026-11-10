# TD1 — local benchmark summary

Source: `benchmark_local.csv` (36 raw runs). Machine: see `data/machine_local.txt`.

| workload | size | n | mean (s) | std (s) | CV % | min–max (s) | mean RSS (MB) | x size | x time | exponent k (t ∝ size^k) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cpu_task | 5000000 | 3 | 0.973 | 0.015 | 1.6 | 0.96–0.99 | 2.3 | – | – | – |
| cpu_task | 10000000 | 3 | 2.577 | 0.021 | 0.8 | 2.56–2.60 | 2.5 | 2.00 | 2.65 | 1.41 |
| cpu_task | 20000000 | 3 | 6.830 | 0.035 | 0.5 | 6.81–6.87 | 2.5 | 2.00 | 2.65 | 1.41 |
| matrix_task | 1000 | 3 | 1.083 | 0.015 | 1.4 | 1.07–1.10 | 25.8 | – | – | – |
| matrix_task | 1500 | 3 | 3.847 | 0.086 | 2.2 | 3.77–3.94 | 54.4 | 1.50 | 3.55 | 3.13 |
| matrix_task | 2000 | 3 | 9.367 | 0.057 | 0.6 | 9.32–9.43 | 94.4 | 1.33 | 2.43 | 3.09 |
| memory_task | 512 | 3 | 0.900 | 0.017 | 1.9 | 0.88–0.91 | 515.2 | – | – | – |
| memory_task | 1024 | 3 | 1.477 | 0.015 | 1.0 | 1.46–1.49 | 1027.8 | 2.00 | 1.64 | 0.71 |
| memory_task | 2048 | 3 | 2.730 | 0.098 | 3.6 | 2.65–2.84 | 2053.0 | 2.00 | 1.85 | 0.89 |
| sort_task | 10000000 | 3 | 1.430 | 0.026 | 1.9 | 1.41–1.46 | 79.2 | – | – | – |
| sort_task | 20000000 | 3 | 3.067 | 0.112 | 3.6 | 2.94–3.15 | 155.4 | 2.00 | 2.14 | 1.10 |
| sort_task | 40000000 | 3 | 6.250 | 0.173 | 2.8 | 6.15–6.45 | 308.4 | 2.00 | 2.04 | 1.03 |

*x size / x time*: ratio to the previous size of the same workload. *k*: empirical growth exponent
(k≈1 linear, k≈3 cubic). CV = std/mean, measures run-to-run variability.
