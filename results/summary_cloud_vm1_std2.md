# Benchmark summary — cloud_vm1_std2

Source: `benchmark_cloud_vm1_std2.csv` (36 raw runs). Machine: see `data/machine_cloud_vm1_std2.txt`.

| workload | size | n | mean (s) | std (s) | CV % | min–max (s) | mean RSS (MB) | x size | x time | exponent k (t ∝ size^k) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cpu_task | 5000000 | 3 | 3.600 | 0.010 | 0.3 | 3.59–3.61 | 3.6 | – | – | – |
| cpu_task | 10000000 | 3 | 9.637 | 0.107 | 1.1 | 9.57–9.76 | 3.6 | 2.00 | 2.68 | 1.42 |
| cpu_task | 20000000 | 3 | 26.157 | 0.531 | 2.0 | 25.84–26.77 | 3.6 | 2.00 | 2.71 | 1.44 |
| matrix_task | 1000 | 3 | 1.490 | 0.052 | 3.5 | 1.46–1.55 | 25.7 | – | – | – |
| matrix_task | 1500 | 3 | 5.400 | 0.078 | 1.4 | 5.35–5.49 | 54.3 | 1.50 | 3.62 | 3.18 |
| matrix_task | 2000 | 3 | 12.660 | 0.020 | 0.2 | 12.64–12.68 | 94.5 | 1.33 | 2.34 | 2.96 |
| memory_task | 512 | 3 | 0.560 | 0.010 | 1.8 | 0.55–0.57 | 516.4 | – | – | – |
| memory_task | 1024 | 3 | 1.097 | 0.006 | 0.5 | 1.09–1.10 | 1029.0 | 2.00 | 1.96 | 0.97 |
| memory_task | 2048 | 3 | 2.190 | 0.017 | 0.8 | 2.18–2.21 | 2054.0 | 2.00 | 2.00 | 1.00 |
| sort_task | 10000000 | 3 | 1.483 | 0.006 | 0.4 | 1.48–1.49 | 80.0 | – | – | – |
| sort_task | 20000000 | 3 | 3.103 | 0.084 | 2.7 | 3.05–3.20 | 156.1 | 2.00 | 2.09 | 1.07 |
| sort_task | 40000000 | 3 | 6.367 | 0.015 | 0.2 | 6.35–6.38 | 309.6 | 2.00 | 2.05 | 1.04 |

*x size / x time*: ratio to the previous size of the same workload. *k*: empirical growth exponent
(k≈1 linear, k≈3 cubic). CV = std/mean, measures run-to-run variability.
