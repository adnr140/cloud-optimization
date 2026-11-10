# TD1 — local workloads & benchmarking. `make help` lists targets.
WORKLOADS := cpu_task memory_task matrix_task sort_task
BINS      := $(addprefix bin/,$(WORKLOADS))
RUNS      ?= 3

.PHONY: help check machine build calibrate bench analyze all clean
help:      ## list targets
	@grep -E '^[a-z]+:.*##' Makefile | sed 's/:.*##/ —/'
check:     ## verify the toolchain is installed
	@for t in git make gcc go; do command -v $$t >/dev/null && echo "ok  $$t" || echo "MISSING $$t"; done
	@test -x /usr/bin/time && echo "ok  /usr/bin/time (GNU time)" || echo "MISSING GNU time (sudo apt install time)"
machine:   ## write data/machine_local.txt
	@bash scripts/machine_info.sh
build: $(BINS) ## compile the Go workloads into bin/
bin/%: workloads/%.go
	@mkdir -p bin
	go build -trimpath -o $@ $<
	@file $@
calibrate: build ## one quick run per configured size (nothing recorded)
	@bash scripts/calibrate.sh
bench: build ## run the campaign -> data/benchmark_local.csv
	@bash scripts/campaign.sh -r $(RUNS)
analyze:   ## summary table + profile + plot
	@bash scripts/analyze.sh
all: check machine build bench analyze ## everything, in order
clean:     ## remove binaries (keeps data!)
	rm -rf bin/*
