# cloud_vm1 vs cloud_vm1_std2 — same workloads, same sizes, same runner

| | cloud_vm1 | cloud_vm1_std2 |
|---|---|---|
| cpu_model | Intel(R) Xeon(R) CPU @ 2.20GHz | Intel(R) Xeon(R) CPU @ 2.20GHz |
| logical_cpus | 2 | 2 |
| threads/core | 2 | 2 |
| ram_total | 3.8Gi | 7.8Gi |
| virtualized | google | google |
| gce_machine | e2-medium | e2-standard-2 |
| gce_zone | europe-west1-b | europe-west1-b |
| gce_cpu_platform | Intel Broadwell | Intel Broadwell |
| go_version | go version go1.24.4 linux/amd64 | go version go1.24.4 linux/amd64 |

| workload | size | mean cloud_vm1 (s) | CV cloud_vm1 % | mean cloud_vm1_std2 (s) | CV cloud_vm1_std2 % | ratio cloud_vm1_std2/cloud_vm1 | RSS cloud_vm1 (MB) | RSS cloud_vm1_std2 (MB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cpu_task | 5000000 | 6.110 | 35.8 | 3.600 | 0.3 | **0.59** | 3.7 | 3.6 |
| cpu_task | 10000000 | 17.433 | 39.4 | 9.637 | 1.1 | **0.55** | 3.7 | 3.6 |
| cpu_task | 20000000 | 44.307 | 32.0 | 26.157 | 2.0 | **0.59** | 3.7 | 3.6 |
| matrix_task | 1000 | 4.260 | 46.8 | 1.490 | 3.5 | **0.35** | 25.7 | 25.7 |
| matrix_task | 1500 | 12.820 | 13.3 | 5.400 | 1.4 | **0.42** | 54.5 | 54.3 |
| matrix_task | 2000 | 28.080 | 5.7 | 12.660 | 0.2 | **0.45** | 94.7 | 94.5 |
| memory_task | 512 | 1.657 | 28.3 | 0.560 | 1.8 | **0.34** | 516.5 | 516.4 |
| memory_task | 1024 | 3.187 | 32.0 | 1.097 | 0.5 | **0.34** | 1029.1 | 1029.0 |
| memory_task | 2048 | 6.153 | 6.3 | 2.190 | 0.8 | **0.36** | 2054.2 | 2054.0 |
| sort_task | 10000000 | 3.130 | 1.9 | 1.483 | 0.4 | **0.47** | 80.0 | 80.0 |
| sort_task | 20000000 | 6.423 | 2.5 | 3.103 | 2.7 | **0.48** | 156.1 | 156.1 |
| sort_task | 40000000 | 13.400 | 0.9 | 6.367 | 0.2 | **0.48** | 308.9 | 309.6 |

ratio > 1: cloud_vm1_std2 is slower than cloud_vm1 on this configuration. Only configurations present on both machines are listed.
