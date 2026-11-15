// TD4 Round-Robin baseline scheduler (based on the instructor reference implementation).
// It only DECIDES where each task goes: it writes a CSV and never opens SSH or starts a workload
// (that is the job of the TD3 orchestrator, scripts/run_all.sh).
// Go standard library only; no GCP dependency is needed to generate allocations.
//
// Build: go build -o bin/round_robin_scheduler scheduler/round_robin.go   (or: make scheduler)
// Run:   ./bin/round_robin_scheduler data/tasks.csv data/machines.csv data/allocation_rr.csv
//
// Inputs : tasks.csv    task_id,workload,size   (what to run, no VM)
//          machines.csv vm                      (which VMs exist, in the order used by the cycle)
// Output : allocation   task_id,workload,size,vm (exactly the TD3 format)
package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// readCSV reads a whole CSV file, checks that its header is exactly expectedHeader,
// and returns the data rows (header removed). encoding/csv already rejects rows whose
// number of fields differs from the header.
func readCSV(path string, expectedHeader []string) ([][]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	if len(records) == 0 {
		return nil, fmt.Errorf("%s is empty", path)
	}
	if len(records[0]) != len(expectedHeader) {
		return nil, fmt.Errorf("%s: expected columns %s", path, strings.Join(expectedHeader, ","))
	}
	for i, name := range expectedHeader {
		if strings.TrimSpace(records[0][i]) != name {
			return nil, fmt.Errorf("%s: column %d must be %q", path, i+1, name)
		}
	}
	return records[1:], nil
}

// schedule assigns the task at position i to machine i % len(vmNames).
// It ignores task duration, CPU, RAM and price on purpose: this is the baseline.
func schedule(tasks [][]string, machines [][]string) ([][]string, error) {
	if len(machines) == 0 {
		return nil, fmt.Errorf("no VMs available: machines.csv must contain at least one VM")
	}

	vmNames := make([]string, 0, len(machines))
	seenMachines := make(map[string]bool)
	for i, row := range machines {
		vm := strings.TrimSpace(row[0])
		if vm == "" || seenMachines[vm] {
			return nil, fmt.Errorf("invalid or duplicated VM in machines.csv, data row %d", i+1)
		}
		seenMachines[vm] = true
		vmNames = append(vmNames, vm)
	}

	assigned := make([][]string, 0, len(tasks))
	seenTasks := make(map[string]bool)
	for i, row := range tasks {
		id := strings.TrimSpace(row[0])
		workload := strings.TrimSpace(row[1])
		size := strings.TrimSpace(row[2])
		if id == "" || workload == "" || size == "" {
			return nil, fmt.Errorf("missing task field in tasks.csv, data row %d", i+1)
		}
		if seenTasks[id] {
			return nil, fmt.Errorf("duplicate task ID %q", id)
		}
		seenTasks[id] = true
		vm := vmNames[i%len(vmNames)] // <- THE Round-Robin rule: position i -> VM i mod M (0,1,2,0,1,2,...)
		assigned = append(assigned, []string{id, workload, size, vm})
	}
	return assigned, nil
}

// writeAllocation writes the TD3 header + rows to a temporary file, then renames it,
// so a crash never leaves a half-written allocation that run_all.sh could execute.
func writeAllocation(path string, allocations [][]string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return fmt.Errorf("create output directory: %w", err)
	}

	tmp, err := os.CreateTemp(filepath.Dir(path), ".rr-allocation-*")
	if err != nil {
		return fmt.Errorf("create output: %w", err)
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName)

	writer := csv.NewWriter(tmp)
	err = writer.Write([]string{"task_id", "workload", "size", "vm"})
	if err == nil {
		err = writer.WriteAll(allocations)
	}
	writer.Flush()
	if err == nil {
		err = writer.Error()
	}
	if closeErr := tmp.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		return fmt.Errorf("write output: %w", err)
	}
	if err = os.Rename(tmpName, path); err != nil {
		return fmt.Errorf("save output: %w", err)
	}
	return nil
}

func run(args []string) error {
	if len(args) != 3 {
		return fmt.Errorf("usage: round_robin_scheduler <tasks.csv> <machines.csv> <allocation.csv>")
	}
	tasks, err := readCSV(args[0], []string{"task_id", "workload", "size"})
	if err != nil {
		return err
	}
	machines, err := readCSV(args[1], []string{"vm"})
	if err != nil {
		return err
	}
	assignments, err := schedule(tasks, machines)
	if err != nil {
		return err
	}
	if err := writeAllocation(args[2], assignments); err != nil {
		return err
	}
	fmt.Printf("Scheduled %d tasks across %d VMs: %s\n", len(tasks), len(machines), args[2])
	return nil
}

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
}
