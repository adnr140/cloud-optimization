# local vs cloud_vm1 — same workloads, same sizes, same runner

| | local | cloud_vm1 |
|---|---|---|
| cpu_model |  | Intel(R) Xeon(R) CPU @ 2.20GHz |
| logical_cpus |  | 2 |
| threads/core |  | 2 |
| ram_total |  | 3.8Gi |
| virtualized |  | google |
| gce_machine |  | e2-medium |
| gce_zone |  | europe-west1-b |
| gce_cpu_platform |  | Intel Broadwell |
| go_version |  | go version go1.24.4 linux/amd64 |

| workload | size | mean local (s) | CV local % | mean cloud_vm1 (s) | CV cloud_vm1 % | ratio cloud_vm1/local | RSS local (MB) | RSS cloud_vm1 (MB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cpu_task | 5000000 | 0.973 | 1.6 | 6.110 | 35.8 | **6.28** | 2.3 | 3.7 |
| cpu_task | 10000000 | 2.577 | 0.8 | 17.433 | 39.4 | **6.76** | 2.5 | 3.7 |
| cpu_task | 20000000 | 6.830 | 0.5 | 44.307 | 32.0 | **6.49** | 2.5 | 3.7 |
| matrix_task | 1000 | 1.083 | 1.4 | 4.260 | 46.8 | **3.93** | 25.8 | 25.7 |
| matrix_task | 1500 | 3.847 | 2.2 | 12.820 | 13.3 | **3.33** | 54.4 | 54.5 |
| matrix_task | 2000 | 9.367 | 0.6 | 28.080 | 5.7 | **3.00** | 94.4 | 94.7 |
| memory_task | 512 | 0.900 | 1.9 | 1.657 | 28.3 | **1.84** | 515.2 | 516.5 |
| memory_task | 1024 | 1.477 | 1.0 | 3.187 | 32.0 | **2.16** | 1027.8 | 1029.1 |
| memory_task | 2048 | 2.730 | 3.6 | 6.153 | 6.3 | **2.25** | 2053.0 | 2054.2 |
| sort_task | 10000000 | 1.430 | 1.9 | 3.130 | 1.9 | **2.19** | 79.2 | 80.0 |
| sort_task | 20000000 | 3.067 | 3.6 | 6.423 | 2.5 | **2.09** | 155.4 | 156.1 |
| sort_task | 40000000 | 6.250 | 2.8 | 13.400 | 0.9 | **2.14** | 308.4 | 308.9 |

ratio > 1: cloud_vm1 is slower than local on this configuration. Only configurations present on both machines are listed.
