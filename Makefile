# TD1 + TD2 — benchmark pipeline, identical on the laptop and on every VM. `make help` lists targets.
# TAG names the machine: local (TD1 laptop), cloud_vm1 (TD2 Compute Engine VM), ...
WORKLOADS := cpu_task memory_task matrix_task sort_task
BINS      := $(addprefix bin/,$(WORKLOADS))
RUNS      ?= 3
TAG       ?= local
A         ?= local
B         ?= cloud_vm1

.PHONY: deploy-all run-all help check machine build calibrate bench analyze compare memprobe pmatrix figures all clean
help:      ## list targets (variables: TAG=local|cloud_vm1, RUNS=3, A/B for compare)
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/ —/'
check:     ## verify the toolchain is installed
	@for t in git make gcc go; do command -v $$t >/dev/null && echo "ok  $$t" || echo "MISSING $$t"; done
	@test -x /usr/bin/time && echo "ok  /usr/bin/time (GNU time)" || echo "MISSING GNU time (sudo apt install time)"
machine:   ## write data/machine_$(TAG).txt
	@bash scripts/machine_info.sh $(TAG)
build: $(BINS) ## compile the Go workloads into bin/
bin/%: workloads/%.go
	@mkdir -p bin
	go build -trimpath -o $@ $<
	@file $@
calibrate: build ## one quick run per configured size (nothing recorded)
	@bash scripts/calibrate.sh
bench: build ## run the campaign -> data/benchmark_$(TAG).csv
	@bash scripts/campaign.sh -r $(RUNS) -t $(TAG)
analyze:   ## summary + profile + plot for $(TAG)
	@bash scripts/analyze.sh data/benchmark_$(TAG).csv
compare:   ## results/compare_$(A)_vs_$(B).md (both profiles must exist)
	@bash scripts/compare.sh $(A) $(B)
memprobe: build ## memory_task user/sys/page-fault split -> data/memprobe_$(TAG).csv
	@bash scripts/memprobe.sh $(TAG)
pmatrix:   ## data/p_matrix.csv: mean runtime of every task on every measured machine
	@bash scripts/pmatrix.sh local cloud_vm1 cloud_vm1_std2
figures:   ## results/td2_machines.png (needs matplotlib)
	@python3 scripts/plot_machines.py results
deploy-all: ## TD3: same static binaries on every VM of VMS + md5 + smoke test
	@bash scripts/deploy_all.sh
run-all:   ## TD3: run $(ALLOC) on the VMs (default data/allocation_manual.csv) -> results/td3/<name>/
	@bash scripts/run_all.sh $(ALLOC)
all: check machine build bench analyze ## everything, in order
clean:     ## remove binaries (keeps data!)
	rm -rf bin/*
