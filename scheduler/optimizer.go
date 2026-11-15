// Optimised scheduler (project, after TD4): decides where each task runs so that the predicted
// makespan is minimal, under each VM's RAM capacity. Like round_robin.go it only WRITES the
// allocation CSV (TD3 format); scripts/run_all.sh executes it unchanged.
//
// Build: go build -o bin/optimizer scheduler/optimizer.go          (or: make optimizer)
// Run:   ./bin/optimizer -tasks data/tasks.csv -out data/allocation_opt.csv     (method opt)
//
//	./bin/optimizer -method lpt -tasks data/tasks.csv                       (one heuristic)
//	./bin/optimizer -method eval -alloc data/allocation_rr.csv              (predict only)
//
// Model (docs/OPTIMIZATION.md, calibrated on 12 measured VM finish times, scripts/fit_model.py):
//
//	x_ij = 1 if task i runs on VM j (each task on exactly one VM)
//	finish_j = SSH + shared({p_ij : i on j}, c_j)                             (0 if no task)
//	shared = processor sharing (CM6, tasks on one VM share it): VM j has c_j effective cores;
//	         while n of its tasks run, each advances at speed min(1, c_j/n); shared = end of the last.
//	makespan = max_j finish_j                                                  -> minimised
//	s.t. sum_{i on j} m_i <= RAM_j - reserve       (memory capacity, CM6 feasibility)
//	     #tasks on j     <= maxPerVM               (sshd MaxStartups limit, D24)
//
// p_ij = measured runtime of task i alone on VM j's p_column (data/p_matrix.csv, TD2),
// c_j  = effective parallel cores of VM j (data/vms.csv, fitted), m_i = max RSS (TD2).
//
// Method opt, in four stages, each from a course (the search space is M^N plans: 10 VMs and 100
// tasks give 10^100, CM4, so trying every plan does not scale):
//  1. construct (CM3): LPT, Min-Min and Max-Min; keep the best plan.          O(n^2.m)
//  2. improve   (CM5): local search with moves, swaps and 2-for-1 swaps.      polynomial per step
//  3. iterate   (CM5): iterated local search, 200 seeded kicks + descents.    reproducible
//  4. bound     (CM4): lower bound L (relaxation); if the plan reaches L it is optimal; otherwise
//     branch and bound under a time limit: OPTIMAL if the search completes, else FEASIBLE + gap.
//
// Every result is reported as the CM4 triple: plan value U, lower bound L, status.
// Ties are broken by leximax (smallest 2nd finish, then 3rd...), i.e. the most balanced plan.
// Standard library only.
package main

import (
	"encoding/csv"
	"errors"
	"flag"
	"fmt"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type task struct {
	id, workload, size string
	p                  []float64 // p[j]: predicted runtime alone on VM j (s)
	rssMB              float64
}

type vm struct {
	name, mtype string
	ramMB       float64
	pcol        string
	cores       float64 // effective parallel cores c_j
}

type model struct {
	tasks    []task
	vms      []vm
	ssh      float64
	reserve  float64
	maxPerVM int
	lb       float64 // cached lowerBound()
}

// load = what a VM carries for a set of tasks; finish() turns it into a predicted time.
// ps is kept sorted (ascending) so that shared() needs no sort.
type load struct {
	ps       []float64
	sum, max float64
	ram      float64
	n        int
}

// shared: processor sharing of c cores between the tasks of one VM. Tasks end in order of their
// work; between two ends, the n running tasks each advance at speed min(1, c/n).
func shared(ps []float64, c float64) float64 {
	t, done := 0.0, 0.0
	for k, w := range ps {
		n := float64(len(ps) - k)
		t += (w - done) / math.Min(1, c/n)
		done = w
	}
	return t
}

func (m *model) finish(j int, l load) float64 {
	if l.n == 0 {
		return 0
	}
	return m.ssh + shared(l.ps, m.vms[j].cores)
}

func (m *model) fits(j int, l load, t task) bool {
	return l.n+1 <= m.maxPerVM && l.ram+t.rssMB <= m.vms[j].ramMB-m.reserve
}

func add(l load, p, rss float64) load {
	k := sort.SearchFloat64s(l.ps, p)
	ps := make([]float64, 0, len(l.ps)+1)
	ps = append(append(append(ps, l.ps[:k]...), p), l.ps[k:]...)
	return load{ps: ps, sum: l.sum + p, max: math.Max(l.max, p), ram: l.ram + rss, n: l.n + 1}
}

// ---------- input -----------------------------------------------------------------------------

func readCSV(path string) ([]string, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	recs, err := r.ReadAll()
	if err != nil {
		return nil, nil, fmt.Errorf("read %s: %w", path, err)
	}
	if len(recs) == 0 {
		return nil, nil, fmt.Errorf("%s is empty", path)
	}
	for i := range recs[0] {
		recs[0][i] = strings.TrimSpace(recs[0][i])
	}
	return recs[0], recs[1:], nil
}

func col(header []string, name, path string) (int, error) {
	for i, h := range header {
		if h == name {
			return i, nil
		}
	}
	return -1, fmt.Errorf("%s: missing column %q", path, name)
}

func num(s, what string) (float64, error) {
	v, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil || v < 0 || math.IsNaN(v) {
		return 0, fmt.Errorf("%s: %q is not a valid non-negative number", what, s)
	}
	return v, nil
}

func loadModel(tasksPath, vmsPath, pPath, rssPath string) (*model, error) {
	m := &model{}
	// VMs: vm,machine_type,ram_mb,p_column,eff_cores
	h, rows, err := readCSV(vmsPath)
	if err != nil {
		return nil, err
	}
	idx := map[string]int{}
	for _, c := range []string{"vm", "machine_type", "ram_mb", "p_column", "eff_cores"} {
		if idx[c], err = col(h, c, vmsPath); err != nil {
			return nil, err
		}
	}
	seen := map[string]bool{}
	for i, r := range rows {
		v := vm{name: strings.TrimSpace(r[idx["vm"]]), mtype: r[idx["machine_type"]], pcol: strings.TrimSpace(r[idx["p_column"]])}
		if v.name == "" || seen[v.name] {
			return nil, fmt.Errorf("%s row %d: empty or duplicated vm", vmsPath, i+1)
		}
		seen[v.name] = true
		if v.ramMB, err = num(r[idx["ram_mb"]], vmsPath+" ram_mb"); err != nil {
			return nil, err
		}
		if v.cores, err = num(r[idx["eff_cores"]], vmsPath+" eff_cores"); err != nil || v.cores == 0 {
			return nil, fmt.Errorf("%s row %d: eff_cores must be > 0", vmsPath, i+1)
		}
		m.vms = append(m.vms, v)
	}
	if len(m.vms) == 0 {
		return nil, errors.New("no VM available")
	}
	// p matrix: task,<column>... with task = workload:size
	ph, prow, err := readCSV(pPath)
	if err != nil {
		return nil, err
	}
	pcols := make([]int, len(m.vms))
	for j, v := range m.vms {
		if pcols[j], err = col(ph, v.pcol, pPath); err != nil {
			return nil, fmt.Errorf("vm %s: %w", v.name, err)
		}
	}
	pm := map[string][]string{}
	for _, r := range prow {
		pm[strings.TrimSpace(r[0])] = r
	}
	// RSS: workload profile (workload,size,...,max_max_rss_kb)
	rh, rrow, err := readCSV(rssPath)
	if err != nil {
		return nil, err
	}
	rw, err1 := col(rh, "workload", rssPath)
	rs, err2 := col(rh, "size", rssPath)
	rk, err3 := col(rh, "max_max_rss_kb", rssPath)
	if err = errors.Join(err1, err2, err3); err != nil {
		return nil, err
	}
	rss := map[string]float64{}
	for _, r := range rrow {
		v, err := num(r[rk], rssPath+" max_max_rss_kb")
		if err != nil {
			return nil, err
		}
		rss[strings.TrimSpace(r[rw])+":"+strings.TrimSpace(r[rs])] = v / 1024
	}
	// tasks: task_id,workload,size
	th, trow, err := readCSV(tasksPath)
	if err != nil {
		return nil, err
	}
	if strings.Join(th, ",") != "task_id,workload,size" {
		return nil, fmt.Errorf("%s: header must be task_id,workload,size", tasksPath)
	}
	seenT := map[string]bool{}
	for i, r := range trow {
		t := task{id: strings.TrimSpace(r[0]), workload: strings.TrimSpace(r[1]), size: strings.TrimSpace(r[2])}
		if t.id == "" || t.workload == "" || t.size == "" {
			return nil, fmt.Errorf("%s row %d: empty field", tasksPath, i+1)
		}
		if seenT[t.id] {
			return nil, fmt.Errorf("duplicate task ID %q", t.id)
		}
		seenT[t.id] = true
		key := t.workload + ":" + t.size
		pr, ok := pm[key]
		if !ok {
			return nil, fmt.Errorf("task %s: no measured runtime for %s in %s (measure it first)", t.id, key, pPath)
		}
		for j := range m.vms {
			v, err := num(pr[pcols[j]], pPath+" "+key)
			if err != nil {
				return nil, err
			}
			t.p = append(t.p, v)
		}
		if t.rssMB, ok = rss[key]; !ok {
			return nil, fmt.Errorf("task %s: no measured RSS for %s in %s", t.id, key, rssPath)
		}
		m.tasks = append(m.tasks, t)
	}
	if len(m.tasks) == 0 {
		return nil, errors.New("no task to schedule")
	}
	return m, nil
}

// ---------- evaluation ------------------------------------------------------------------------

// evaluate returns per-VM loads and finish times for assign[i] = VM index of task i.
func (m *model) evaluate(assign []int) ([]load, []float64, error) {
	loads := make([]load, len(m.vms))
	for i, j := range assign {
		t := m.tasks[i]
		if !m.fits(j, loads[j], t) {
			return nil, nil, fmt.Errorf("infeasible: task %s does not fit on %s (RAM %.0f+%.0f MB > %.0f MB, or more than %d tasks)",
				t.id, m.vms[j].name, loads[j].ram, t.rssMB, m.vms[j].ramMB-m.reserve, m.maxPerVM)
		}
		loads[j] = add(loads[j], t.p[j], t.rssMB)
	}
	fin := make([]float64, len(m.vms))
	for j := range m.vms {
		fin[j] = m.finish(j, loads[j])
	}
	return loads, fin, nil
}

// sortedDesc returns the finish times, largest first (the leximax key).
func sortedDesc(f []float64) []float64 {
	s := append([]float64(nil), f...)
	sort.Sort(sort.Reverse(sort.Float64Slice(s)))
	return s
}

const eps = 1e-9

// tol: a plan within tol seconds of the lower bound is reported OPTIMAL (bound computed to tol/10).
const tol = 1e-5

// better: smaller makespan, then smaller 2nd finish, ... (leximax).
func better(a, b []float64) bool {
	for k := range a {
		if a[k] < b[k]-eps {
			return true
		}
		if a[k] > b[k]+eps {
			return false
		}
	}
	return false
}

// lowerBound (CM4: a value no plan can beat; the gap U-L is measured against it).
// L0: SSH + max(longest task on its fastest VM, all the work spread on every effective core).
// L1, sharper on big instances: the smallest T that passes three NECESSARY conditions:
//
//	(a) each task fits alone on some VM by T: SSH + p_ij <= T and m_i <= RAM_j - reserve;
//	(b) work: sum_i (smallest p_ij among those VMs) <= sum_j c_j.(T - SSH), since VM j does at most
//	    c_j seconds of work per second;
//	(c) "big" tasks: on VM j two tasks need p_aj + p_bj <= c_j.(T - SSH) (same reason). A task
//	    that is big (p_ij > c_j.(T - SSH)/2) on every VM it fits needs a VM of its own: those
//	    tasks must be matched to distinct VMs (bipartite matching, augmenting paths).
//
// The conditions only get easier when T grows, so L1 is found by bisection.
func (m *model) lowerBound() float64 {
	if m.lb > 0 {
		return m.lb
	}
	longest, work, cores := 0.0, 0.0, 0.0
	for _, t := range m.tasks {
		best := math.Inf(1)
		for j := range m.vms {
			best = math.Min(best, t.p[j])
		}
		longest = math.Max(longest, best)
		work += best
	}
	for _, v := range m.vms {
		cores += v.cores
	}
	lo := m.ssh + math.Max(longest, work/cores)
	if !m.relaxedOK(lo) {
		hi := lo
		for !m.relaxedOK(hi) {
			hi = 2*hi + 1
			if hi > 1e9 {
				m.lb = lo // nothing fits at all: let the methods report infeasibility
				return lo
			}
		}
		for hi-lo > tol/10 {
			if mid := (lo + hi) / 2; m.relaxedOK(mid) {
				hi = mid
			} else {
				lo = mid
			}
		}
	} // lo failed a necessary condition, so no plan finishes by lo: lo is a valid bound
	m.lb = lo
	return lo
}

func (m *model) relaxedOK(T float64) bool {
	room := T - m.ssh
	work, cores := 0.0, 0.0
	for _, v := range m.vms {
		cores += v.cores
	}
	var bigAllowed [][]int // VMs allowed for each big task
	for _, t := range m.tasks {
		minp, big := math.Inf(1), true
		var allowed []int
		for j, v := range m.vms {
			if t.p[j] > room+eps || t.rssMB > v.ramMB-m.reserve {
				continue
			}
			allowed = append(allowed, j)
			minp = math.Min(minp, t.p[j])
			if 2*t.p[j] <= v.cores*room+eps {
				big = false
			}
		}
		if len(allowed) == 0 {
			return false // (a)
		}
		work += minp
		if big {
			bigAllowed = append(bigAllowed, allowed)
		}
	}
	if work > cores*room+eps || len(bigAllowed) > len(m.vms) {
		return false // (b), or more big tasks than VMs
	}
	owner := make([]int, len(m.vms)) // (c) matching: owner[j] = big task on VM j, -1 if none
	for j := range owner {
		owner[j] = -1
	}
	var try func(i int, seen []bool) bool
	try = func(i int, seen []bool) bool {
		for _, j := range bigAllowed[i] {
			if seen[j] {
				continue
			}
			seen[j] = true
			if owner[j] < 0 || try(owner[j], seen) {
				owner[j] = i
				return true
			}
		}
		return false
	}
	for i := range bigAllowed {
		if !try(i, make([]bool, len(m.vms))) {
			return false
		}
	}
	return true
}

// ---------- methods ---------------------------------------------------------------------------
// The pipeline follows the courses: FILTER infeasible VMs (CM6: fits), CONSTRUCT a plan with a
// greedy rule (CM3), IMPROVE it by local search (CM5), and BOUND it (CM4): every result comes with
// a lower bound, hence a gap; the exact search can close that gap when the instance is small.

// order: tasks by decreasing longest p (big tasks first: the LPT order, and better pruning).
func (m *model) order() []int {
	ord := make([]int, len(m.tasks))
	for i := range ord {
		ord[i] = i
	}
	key := func(i int) float64 {
		k := 0.0
		for _, p := range m.tasks[i].p {
			k = math.Max(k, p)
		}
		return k
	}
	sort.SliceStable(ord, func(a, b int) bool { return key(ord[a]) > key(ord[b]) })
	return ord
}

// ect: predicted finish of VM j if task i is added to its current load (+Inf if it does not fit).
func (m *model) ect(i, j int, l load) float64 {
	t := m.tasks[i]
	if !m.fits(j, l, t) {
		return math.Inf(1)
	}
	return m.finish(j, add(l, t.p[j], t.rssMB))
}

// lpt: Longest Processing Time first, each task to the feasible VM with the earliest predicted
// finish once the task is added (ties: first VM in vms.csv). O(n log n + n.m).
func (m *model) lpt() ([]int, error) {
	assign := make([]int, len(m.tasks))
	loads := make([]load, len(m.vms))
	for _, i := range m.order() {
		bestJ, bestF := -1, math.Inf(1)
		for j := range m.vms {
			if f := m.ect(i, j, loads[j]); f < bestF-eps {
				bestJ, bestF = j, f
			}
		}
		if bestJ < 0 {
			return nil, fmt.Errorf("lpt: no VM can host task %s (RAM or task-count limit)", m.tasks[i].id)
		}
		assign[i] = bestJ
		loads[bestJ] = add(loads[bestJ], m.tasks[i].p[bestJ], m.tasks[i].rssMB)
	}
	return assign, nil
}

// minMax: Min-Min (maxmin=false) or Max-Min (maxmin=true), Braun et al. 2001 (CM3). At each step,
// every unassigned task has a best VM (earliest finish); Min-Min places the task whose best finish
// is the smallest, Max-Min the one whose best finish is the largest. O(n^2.m).
func (m *model) minMax(maxmin bool) ([]int, error) {
	n, M := len(m.tasks), len(m.vms)
	assign := make([]int, n)
	loads := make([]load, M)
	done := make([]bool, n)
	ect := make([][]float64, n)
	for i := range ect {
		ect[i] = make([]float64, M)
		for j := range ect[i] {
			ect[i][j] = m.ect(i, j, loads[j])
		}
	}
	for step := 0; step < n; step++ {
		pick, pickJ, pickF := -1, -1, 0.0
		for i := 0; i < n; i++ {
			if done[i] {
				continue
			}
			bj, bf := -1, math.Inf(1)
			for j := 0; j < M; j++ {
				if ect[i][j] < bf-eps {
					bj, bf = j, ect[i][j]
				}
			}
			if bj < 0 {
				return nil, fmt.Errorf("min/max-min: no VM can host task %s (RAM or task-count limit)", m.tasks[i].id)
			}
			if pick < 0 || (maxmin && bf > pickF+eps) || (!maxmin && bf < pickF-eps) {
				pick, pickJ, pickF = i, bj, bf
			}
		}
		done[pick], assign[pick] = true, pickJ
		loads[pickJ] = add(loads[pickJ], m.tasks[pick].p[pickJ], m.tasks[pick].rssMB)
		for i := range ect { // only VM pickJ changed
			if !done[i] {
				ect[i][pickJ] = m.ect(i, pickJ, loads[pickJ])
			}
		}
	}
	return assign, nil
}

// key: finish times sorted, largest first. Plans are compared by leximax: smallest makespan,
// then smallest 2nd finish, ... (the most balanced plan among equal makespans).
func (m *model) key(assign []int) []float64 {
	_, f, err := m.evaluate(assign)
	if err != nil {
		return nil
	}
	return sortedDesc(f)
}

// greedy: run the three constructive rules and keep the best plan (they cost almost nothing).
func (m *model) greedy() ([]int, string, error) {
	var best []int
	var bestKey []float64
	name := ""
	var errs []error
	for _, h := range []struct {
		name string
		run  func() ([]int, error)
	}{{"lpt", m.lpt}, {"minmin", func() ([]int, error) { return m.minMax(false) }}, {"maxmin", func() ([]int, error) { return m.minMax(true) }}} {
		a, err := h.run()
		if err != nil {
			errs = append(errs, err)
			continue
		}
		if k := m.key(a); bestKey == nil || better(k, bestKey) {
			best, bestKey, name = a, k, h.name
		}
	}
	if best == nil {
		return nil, "", errors.Join(errs...)
	}
	return best, name, nil
}

// remove: load l without one task of runtime p and memory rss (p is in l.ps).
func remove(l load, p, rss float64) load {
	k := sort.SearchFloat64s(l.ps, p)
	ps := make([]float64, 0, len(l.ps))
	ps = append(append(ps, l.ps[:k]...), l.ps[k+1:]...)
	mx := 0.0
	if len(ps) > 0 {
		mx = ps[len(ps)-1]
	}
	return load{ps: ps, sum: l.sum - p, max: mx, ram: l.ram - rss, n: l.n - 1}
}

func (m *model) holds(j int, l load) bool {
	return l.n <= m.maxPerVM && l.ram <= m.vms[j].ramMB-m.reserve+eps
}

// pairBetter: a move only changes two VMs, so the whole plan improves (leximax) iff the pair of
// their finish times improves: (max, min) compared lexicographically. O(1), no full re-evaluation.
func pairBetter(a1, b1, a0, b0 float64) bool {
	hi1, lo1, hi0, lo0 := math.Max(a1, b1), math.Min(a1, b1), math.Max(a0, b0), math.Min(a0, b0)
	return hi1 < hi0-eps || (hi1 < hi0+eps && lo1 < lo0-eps)
}

type lsStats struct {
	moves, swaps, swaps21 int
	timedOut              bool
}

// improve: local search (CM5), descent to a local optimum. Neighbourhood of a plan, around a VM s:
//   - move:          one task of s goes to another VM b;
//   - swap:          one task of s and one task of b exchange their VM;
//   - 2-for-1 swap:  two tasks of s against one task of b (tried only when the first two fail).
//
// Only the critical VMs (finish = makespan) are sources, since only work moved off them can lower
// the makespan; for the first one with an improving neighbour, the best neighbour is applied and
// the scan restarts. None = local optimum: stop. Every step strictly improves the leximax key, so
// the descent always ends; one scan costs O(k^2.n) finish computations (k = tasks on the VM).
func (m *model) improve(start []int, deadline time.Time) ([]int, lsStats) {
	a := append([]int(nil), start...)
	loads, fin, err := m.evaluate(a)
	var st lsStats
	if err != nil {
		return a, st
	}
	M := len(m.vms)
	type neighbour struct {
		i, i2, k, b int // tasks i (and i2) of s go to b; task k of b (or -1) goes to s
		ls, lb      load
		fs, fb      float64
	}
	for {
		if time.Now().After(deadline) {
			st.timedOut = true
			return a, st
		}
		on := make([][]int, M)
		for i, j := range a {
			on[j] = append(on[j], i)
		}
		vmOrder := make([]int, M)
		for j := range vmOrder {
			vmOrder[j] = j
		}
		sort.SliceStable(vmOrder, func(x, y int) bool { return fin[vmOrder[x]] > fin[vmOrder[y]] })
		applied := false
		for _, s := range vmOrder {
			if fin[s] < fin[vmOrder[0]]-eps {
				break // only the VMs that set the makespan: moving work off them is what can lower it
			}
			var best *neighbour
			consider := func(i, i2, k, b int, ls, lb load) {
				if !m.holds(s, ls) || !m.holds(b, lb) {
					return
				}
				fs, fb := m.finish(s, ls), m.finish(b, lb)
				if pairBetter(fs, fb, fin[s], fin[b]) && (best == nil || pairBetter(fs, fb, best.fs, best.fb)) {
					best = &neighbour{i, i2, k, b, ls, lb, fs, fb}
				}
			}
			for _, i := range on[s] {
				ti := m.tasks[i]
				ls := remove(loads[s], ti.p[s], ti.rssMB)
				for b := 0; b < M; b++ {
					if b == s {
						continue
					}
					consider(i, -1, -1, b, ls, add(loads[b], ti.p[b], ti.rssMB))
					for _, k := range on[b] {
						tk := m.tasks[k]
						if tk.workload == ti.workload && tk.size == ti.size {
							continue // same task type: swapping changes nothing
						}
						consider(i, -1, k, b, add(ls, tk.p[s], tk.rssMB), add(remove(loads[b], tk.p[b], tk.rssMB), ti.p[b], ti.rssMB))
					}
				}
			}
			if best == nil {
				for x, i := range on[s] {
					for _, i2 := range on[s][x+1:] {
						ti, ti2 := m.tasks[i], m.tasks[i2]
						ls := remove(remove(loads[s], ti.p[s], ti.rssMB), ti2.p[s], ti2.rssMB)
						for b := 0; b < M; b++ {
							if b == s {
								continue
							}
							for _, k := range on[b] {
								tk := m.tasks[k]
								consider(i, i2, k, b, add(ls, tk.p[s], tk.rssMB),
									add(add(remove(loads[b], tk.p[b], tk.rssMB), ti.p[b], ti.rssMB), ti2.p[b], ti2.rssMB))
							}
						}
					}
				}
			}
			if best == nil {
				continue
			}
			a[best.i] = best.b
			switch {
			case best.i2 >= 0:
				a[best.i2], a[best.k] = best.b, s
				st.swaps21++
			case best.k >= 0:
				a[best.k] = s
				st.swaps++
			default:
				st.moves++
			}
			loads[s], loads[best.b], fin[s], fin[best.b] = best.ls, best.lb, best.fs, best.fb
			applied = true
			break
		}
		if !applied {
			return a, st
		}
	}
}

// iterated: Iterated Local Search (CM5 metaheuristic). A descent stops in a local optimum; to leave
// it, kick the best plan (move one random task of a critical VM, and one other random task, to random
// VMs where they fit), descend again, and keep the result only if it is better (leximax).
// Fixed seed and a fixed number of kicks: the result is reproducible.
func (m *model) iterated(start []int, kicks int, seed int64, deadline time.Time) ([]int, int) {
	rnd := rand.New(rand.NewSource(seed))
	best := append([]int(nil), start...)
	bestKey := m.key(best)
	gains := 0
	for it := 0; it < kicks && time.Now().Before(deadline); it++ {
		a := append([]int(nil), best...)
		loads, fin, _ := m.evaluate(a)
		crit := 0
		for j := range fin {
			if fin[j] > fin[crit] {
				crit = j
			}
		}
		var onCrit []int
		for i, j := range a {
			if j == crit {
				onCrit = append(onCrit, i)
			}
		}
		for _, i := range []int{onCrit[rnd.Intn(len(onCrit))], rnd.Intn(len(a))} {
			b := rnd.Intn(len(m.vms))
			t := m.tasks[i]
			if b == a[i] || !m.fits(b, loads[b], t) {
				continue
			}
			loads[a[i]] = remove(loads[a[i]], t.p[a[i]], t.rssMB)
			loads[b] = add(loads[b], t.p[b], t.rssMB)
			a[i] = b
		}
		a, _ = m.improve(a, deadline)
		if k := m.key(a); k != nil && better(k, bestKey) {
			best, bestKey = a, k
			gains++
		}
	}
	return best, gains
}

type searchStats struct {
	nodes, leaves, pruned int64
	complete              bool
}

// exact: branch and bound (CM4) over every assignment, tasks in LPT order, starting from an
// incumbent (the local-search plan). A partial plan is cut when it cannot beat the incumbent:
//
//	bound = max(finish of its VMs so far, SSH + (work placed + least work left) / sum of c_j)
//
// (adding tasks never makes a VM finish earlier, and VM j does at most c_j seconds of work per s).
// Symmetry: identical VMs (same RAM, c_j and p column) are interchangeable, so a task is tried on
// only the first EMPTY one of each group. If the incumbent already equals the lower bound it is
// optimal and no search is needed. Stops at the deadline or after maxNodes nodes: the
// incumbent is then FEASIBLE but not proved optimal (like a solver with a time limit).
func (m *model) exact(incumbent []int, deadline time.Time, maxNodes int64) ([]int, searchStats) {
	st := searchStats{complete: true}
	ord := m.order()
	n, M := len(ord), len(m.vms)
	var best []int
	var bestKey []float64 // nil: no feasible plan known yet
	if incumbent != nil {
		best, bestKey = append([]int(nil), incumbent...), m.key(incumbent)
	}
	group := make([]int, M) // group[j] = first VM identical to j
	for j := range m.vms {
		group[j] = j
		for g := 0; g < j; g++ {
			if m.vms[g].ramMB == m.vms[j].ramMB && m.vms[g].cores == m.vms[j].cores && m.vms[g].pcol == m.vms[j].pcol {
				group[j] = g
				break
			}
		}
	}
	cores, minLeft := 0.0, make([]float64, n+1)
	for _, v := range m.vms {
		cores += v.cores
	}
	for k := n - 1; k >= 0; k-- {
		mp := math.Inf(1)
		for _, p := range m.tasks[ord[k]].p {
			mp = math.Min(mp, p)
		}
		minLeft[k] = minLeft[k+1] + mp
	}
	if bestKey != nil && bestKey[0] <= m.lowerBound()+tol {
		return best, st // the incumbent reaches the lower bound: already proved optimal, nothing to search
	}
	cur := make([]int, len(m.tasks))
	loads := make([]load, M)
	var dfs func(k int, partial, placed float64)
	dfs = func(k int, partial, placed float64) {
		st.nodes++
		if st.nodes > maxNodes || (st.nodes&1023 == 0 && time.Now().After(deadline)) {
			st.complete = false
			return
		}
		if b := math.Max(partial, m.ssh+(placed+minLeft[k])/cores); bestKey != nil && b > bestKey[0]+eps {
			st.pruned++
			return
		}
		if k == n {
			st.leaves++
			f := make([]float64, M)
			for j := range m.vms {
				f[j] = m.finish(j, loads[j])
			}
			if key := sortedDesc(f); bestKey == nil || better(key, bestKey) {
				bestKey, best = key, append([]int(nil), cur...)
			}
			return
		}
		i := ord[k]
		t := m.tasks[i]
	next:
		for j := range m.vms {
			if !m.fits(j, loads[j], t) {
				continue
			}
			if loads[j].n == 0 {
				for g := 0; g < j; g++ {
					if group[g] == group[j] && loads[g].n == 0 {
						continue next // same as putting it on the identical empty VM g
					}
				}
			}
			saved := loads[j]
			loads[j] = add(saved, t.p[j], t.rssMB)
			cur[i] = j
			dfs(k+1, math.Max(partial, m.finish(j, loads[j])), placed+t.p[j])
			loads[j] = saved
			if !st.complete {
				return
			}
		}
	}
	dfs(0, 0, 0)
	return best, st
}

// roundRobin: the TD4 baseline, recomputed here only to compare predictions.
func (m *model) roundRobin() []int {
	a := make([]int, len(m.tasks))
	for i := range a {
		a[i] = i % len(m.vms)
	}
	return a
}

func (m *model) readAllocation(path string) ([]int, error) {
	h, rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if strings.Join(h, ",") != "task_id,workload,size,vm" {
		return nil, fmt.Errorf("%s: header must be task_id,workload,size,vm", path)
	}
	vmIdx := map[string]int{}
	for j, v := range m.vms {
		vmIdx[v.name] = j
	}
	tIdx := map[string]int{}
	for i, t := range m.tasks {
		tIdx[t.id] = i
	}
	a := make([]int, len(m.tasks))
	for i := range a {
		a[i] = -1
	}
	for _, r := range rows {
		i, ok := tIdx[strings.TrimSpace(r[0])]
		j, ok2 := vmIdx[strings.TrimSpace(r[3])]
		if !ok || !ok2 || a[i] >= 0 {
			return nil, fmt.Errorf("%s: unknown or repeated task/VM in row %v", path, r)
		}
		a[i] = j
	}
	for i, j := range a {
		if j < 0 {
			return nil, fmt.Errorf("%s: task %s missing", path, m.tasks[i].id)
		}
	}
	return a, nil
}

// ---------- output ----------------------------------------------------------------------------

func writeAllocation(path string, m *model, assign []int) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), ".opt-allocation-*")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name())
	w := csv.NewWriter(tmp)
	w.Write([]string{"task_id", "workload", "size", "vm"})
	for i, t := range m.tasks { // same task order as tasks.csv
		w.Write([]string{t.id, t.workload, t.size, m.vms[assign[i]].name})
	}
	w.Flush()
	if err = errors.Join(w.Error(), tmp.Close()); err != nil {
		return err
	}
	return os.Rename(tmp.Name(), path)
}

func fmtS(v float64) string { return strconv.FormatFloat(v, 'f', 1, 64) }

// report prints the plan, then the CM4 triple: plan value U, lower bound L, gap U-L.
func (m *model) report(label, status string, assign []int, elapsed time.Duration) (float64, error) {
	loads, fin, err := m.evaluate(assign)
	if err != nil {
		return 0, err
	}
	if len(m.tasks) <= 60 {
		fmt.Printf("%-13s %-14s %5s %8s %8s %12s %9s  %s\n", "vm", "type", "tasks", "sum_p_s", "max_p_s", "ram_MB", "finish_s", "tasks")
	}
	ms := 0.0
	for j, v := range m.vms {
		ms = math.Max(ms, fin[j])
		if len(m.tasks) > 60 {
			continue
		}
		var ids []string
		for i, a := range assign {
			if a == j {
				ids = append(ids, m.tasks[i].id)
			}
		}
		fmt.Printf("%-13s %-14s %5d %8s %8s %5.0f/%-6.0f %9s  %s\n", v.name, v.mtype, loads[j].n, fmtS(loads[j].sum),
			fmtS(loads[j].max), loads[j].ram, v.ramMB-m.reserve, fmtS(fin[j]), strings.Join(ids, " "))
	}
	lb := m.lowerBound()
	if status == "" { // heuristic: no proof, unless it reaches the lower bound
		status = "FEASIBLE"
		if ms <= lb+tol {
			status = "OPTIMAL"
		}
	}
	gap := 100 * (ms - lb) / lb
	fmt.Printf("%s: predicted makespan %s s (lower bound %s s, gap %.1f %%, %s)\n", label, fmtS(ms), fmtS(lb), gap, status)
	fmt.Printf("summary method=%s tasks=%d vms=%d makespan=%.4f lower_bound=%.4f gap_pct=%.3f status=%s time_ms=%.2f\n",
		label, len(m.tasks), len(m.vms), ms, lb, gap, status, float64(elapsed.Microseconds())/1000)
	return ms, nil
}

func run() error {
	method := flag.String("method", "opt", "rr | lpt | minmin | maxmin | greedy | ls | ils | opt | eval")
	tasksPath := flag.String("tasks", "data/tasks.csv", "tasks: task_id,workload,size")
	vmsPath := flag.String("vms", "data/vms.csv", "VMs: vm,machine_type,ram_mb,p_column,eff_cores")
	pPath := flag.String("p", "data/p_matrix.csv", "measured runtimes p_ij (TD2)")
	rssPath := flag.String("rss", "data/workload_profile_cloud_vm1_std2.csv", "measured RSS per task (TD2)")
	out := flag.String("out", "", "allocation CSV to write (TD3 format); empty = print only")
	alloc := flag.String("alloc", "", "eval: allocation CSV to predict")
	ssh := flag.Float64("ssh", 3.0, "fixed SSH cost per task, s (TD3, fitted)")
	reserve := flag.Float64("reserve", 512, "RAM kept for the OS on every VM, MB")
	maxPer := flag.Int("max-per-vm", 10, "max simultaneous tasks per VM (sshd MaxStartups, D24)")
	limit := flag.Float64("time-limit", 10, "ls/ils/opt: computation budget, s (then the best plan found is returned)")
	kicks := flag.Int("kicks", 200, "ils/opt: number of perturbations of the iterated local search")
	seed := flag.Int64("seed", 1, "ils/opt: random seed of the perturbations (fixed: reproducible)")
	maxNodes := flag.Int64("max-nodes", math.MaxInt64, "opt: node budget (for tests)")
	flag.Parse()

	m, err := loadModel(*tasksPath, *vmsPath, *pPath, *rssPath)
	if err != nil {
		return err
	}
	m.ssh, m.reserve, m.maxPerVM = *ssh, *reserve, *maxPer
	t0 := time.Now()
	deadline := t0.Add(time.Duration(*limit * float64(time.Second)))

	var assign []int
	status := ""
	switch *method {
	case "rr":
		assign = m.roundRobin()
	case "lpt":
		assign, err = m.lpt()
	case "minmin":
		assign, err = m.minMax(false)
	case "maxmin":
		assign, err = m.minMax(true)
	case "greedy", "ls", "ils", "opt":
		var name string
		assign, name, err = m.greedy()
		if err == nil {
			fmt.Printf("construct (CM3): best of LPT, Min-Min, Max-Min = %s, makespan %s s\n", name, fmtS(m.key(assign)[0]))
		}
		if err == nil && *method != "greedy" {
			var ls lsStats
			assign, ls = m.improve(assign, deadline)
			fmt.Printf("improve (CM5 local search): %d moves, %d swaps, %d 2-for-1 swaps -> makespan %s s%s\n", ls.moves, ls.swaps, ls.swaps21,
				fmtS(m.key(assign)[0]), map[bool]string{true: " (time limit reached)", false: " (local optimum)"}[ls.timedOut])
		}
		if err == nil && (*method == "ils" || *method == "opt") {
			var gains int
			assign, gains = m.iterated(assign, *kicks, *seed, deadline)
			fmt.Printf("iterate (CM5 iterated local search): %d kicks, %d improvements -> makespan %s s\n", *kicks, gains, fmtS(m.key(assign)[0]))
		}
		if *method == "opt" {
			var st searchStats
			assign, st = m.exact(assign, deadline, *maxNodes) // works even if the heuristics found nothing
			fmt.Printf("bound (CM4 branch and bound): %d tasks x %d VMs = %.3g plans; %d nodes, %d complete plans, %d branches pruned\n",
				len(m.tasks), len(m.vms), math.Pow(float64(len(m.vms)), float64(len(m.tasks))), st.nodes, st.leaves, st.pruned)
			switch {
			case assign == nil && st.complete:
				return errors.New("no feasible plan: the tasks do not fit in the VMs' RAM (INFEASIBLE, proved)")
			case assign == nil:
				return errors.New("no feasible plan found before the time limit (UNKNOWN)")
			case st.complete && st.nodes == 0:
				status = "OPTIMAL"
				fmt.Println("status OPTIMAL: the plan reaches the lower bound, no search needed (optimum of the model)")
			case st.complete:
				status = "OPTIMAL"
				fmt.Println("status OPTIMAL: every plan was evaluated or pruned (optimum of the model)")
			default:
				status = "FEASIBLE"
				fmt.Println("status FEASIBLE: time limit reached, best plan found so far; the optimum is between the lower bound and it")
			}
			err = nil
		}
	case "eval":
		if *alloc == "" {
			return errors.New("eval needs -alloc FILE")
		}
		assign, err = m.readAllocation(*alloc)
	default:
		return fmt.Errorf("unknown method %q", *method)
	}
	if err != nil {
		return err
	}
	if _, err = m.report(*method, status, assign, time.Since(t0)); err != nil {
		return err
	}
	if *out != "" && *method != "eval" {
		if err = writeAllocation(*out, m, assign); err != nil {
			return err
		}
		fmt.Printf("written: %s\n", *out)
	}
	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
}
