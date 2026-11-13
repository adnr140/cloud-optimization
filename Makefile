# TD1 + TD2 — benchmark pipeline, identical on the laptop and on every VM. `make help` lists targets.
# TAG names the machine: local (TD1 laptop), cloud_vm1 (TD2 Compute Engine VM), ...
WORKLOADS := cpu_task memory_task matrix_task sort_task
BINS      := $(addprefix bin/,$(WORKLOADS))
RUNS      ?= 3
TAG       ?= local
A         ?= local
B         ?= cloud_vm1

.PHONY: oral-figures burst-study burst-cost compare-run optimizer opt test-optimizer scaling fit-model opt-run scheduler rr test-scheduler td4-run deploy-all run-all help check machine build calibrate bench analyze compare memprobe pmatrix figures all clean
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
scheduler: bin/round_robin_scheduler ## TD4: compile the Round-Robin scheduler
bin/round_robin_scheduler: scheduler/round_robin.go
	@mkdir -p bin
	go build -trimpath -o $@ $<
rr: scheduler ## TD4: tasks.csv + machines.csv -> data/allocation_rr.csv (+ reordered variant), checked
	./bin/round_robin_scheduler data/tasks.csv data/machines.csv data/allocation_rr.csv
	@bash scripts/check_allocation.sh data/tasks.csv data/machines.csv data/allocation_rr.csv
	./bin/round_robin_scheduler data/tasks_reordered.csv data/machines.csv data/allocation_rr_reordered.csv
	@bash scripts/check_allocation.sh data/tasks.csv data/machines.csv data/allocation_rr_reordered.csv
test-scheduler: scheduler ## TD4: test cases A-E + determinism + order, no VM needed
	@bash scripts/test_scheduler.sh
td4-run: rr ## TD4: execute both RR allocations on the VMs -> results/td4/<name>/ + measured makespan
	bash scripts/run_all.sh data/allocation_rr.csv results/td4/allocation_rr
	bash scripts/run_all.sh data/allocation_rr_reordered.csv results/td4/allocation_rr_reordered
	@for r in allocation_rr allocation_rr_reordered; do echo "== $$r"; bash scripts/makespan.sh results/td4/$$r; done
optimizer: bin/optimizer ## project: compile the optimised scheduler (greedy CM3 + local search CM5 + bound/B&B CM4)
bin/optimizer: scheduler/optimizer.go
	@mkdir -p bin
	go build -trimpath -o $@ $<
OPT_ALLOCS := allocation_opt allocation_b_rr allocation_b_lpt allocation_b_opt
opt: optimizer ## project: scenario A (tasks.csv) and B (tasks_b.csv) allocations -> data/, checked
	./bin/optimizer -method opt   -tasks data/tasks.csv   -out data/allocation_opt.csv
	./bin/optimizer -method rr    -tasks data/tasks_b.csv -out data/allocation_b_rr.csv
	./bin/optimizer -method lpt   -tasks data/tasks_b.csv -out data/allocation_b_lpt.csv
	./bin/optimizer -method opt   -tasks data/tasks_b.csv -out data/allocation_b_opt.csv
	@bash scripts/check_allocation.sh data/tasks.csv data/machines.csv data/allocation_opt.csv
	@for a in allocation_b_rr allocation_b_lpt allocation_b_opt; do bash scripts/check_allocation.sh data/tasks_b.csv data/machines.csv data/$$a.csv; done
test-optimizer: optimizer ## project: 48 tests without VM (optimum vs brute force, bound, RAM, determinism, 1000 tasks)
	@bash scripts/test_optimizer.sh
scaling: optimizer ## project: methods from 9 to 1000 tasks -> results/scaling.md (+ .csv), ~4 min
	@python3 scripts/scaling.py
compare-run: optimizer ## project: on the VMs: platform + p_ij measured today, re-optimise, RR vs LPT vs opt x REPS -> results/project/session_*/summary.md
	@bash scripts/compare_run.sh $(or $(REPS),5)
burst-study: ## bonus: on the VMs, e2-medium burst vs e2-standard-2 (~36 min) -> results/burst/session_*/ + figures
	@bash scripts/burst_study.sh
burst-cost: ## bonus: time / cost / fleet charts from the last burst session -> results/fig_burst_*.png, results/burst_study.md
	@python3 scripts/burst_cost.py $$(ls -d results/burst/session_* | tail -1) $$(ls -d results/project/session_* 2>/dev/null | tail -1)
oral-figures: optimizer ## README / oral figures, one message each -> results/oral_*.png
	@python3 scripts/make_oral_figures.py
fit-model: ## project: recalibrate the duration model on every real run -> results/model_fit.md
	@python3 scripts/fit_model.py
opt-run: opt ## project: execute the 4 allocations on the VMs -> results/project/<name>/ + measured makespan
	@for a in $(OPT_ALLOCS); do bash scripts/run_all.sh data/$$a.csv results/project/$$a || exit 1; done
	@for a in $(OPT_ALLOCS); do echo "== $$a"; bash scripts/makespan.sh results/project/$$a; done
all: check machine build bench analyze ## everything, in order
clean:     ## remove binaries (keeps data!)
	rm -rf bin/*
