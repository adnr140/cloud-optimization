"""English labels for the oral figures (FIG_LANG=en).

make_oral_figures.py writes its labels in French. When FIG_LANG=en, it imports this module, which
patches matplotlib so that every text drawn goes through tr(): exact phrases from EN are replaced,
and numbers switch to the English format (15,8 -> 15.8, 1 541 -> 1,541).
"""
import re

import matplotlib.text as mtext

EN = {
    # td2 machines / model
    "calcul\n(cpu 10M)": "compute\n(cpu 10M)",
    "matrices\n(matrix 1500)": "matrices\n(matrix 1500)",
    "mémoire\n(memory 1 Go)": "memory\n(memory 1 GB)",
    "tri\n(sort 20M)": "sort\n(sort 20M)",
    "durée d'une exécution (s)": "runtime of one execution (s)",
    "portable (Ryzen 7)": "laptop (Ryzen 7)",
    "GCP e2-medium (moyenne TD2)": "GCP e2-medium (TD2 mean)",
    "prédit = mesuré": "predicted = measured",
    "zone ±1 s": "±1 s band",
    "un run lent : variabilité du cloud": "one slow run: cloud variability",
    "temps de fin MESURÉ d'une VM (s)": "MEASURED finish time of a VM (s)",
    "temps de fin PRÉDIT par le modèle (s)": "finish time PREDICTED by the model (s)",
    # gantt
    "secondes depuis le lancement du lot": "seconds since the batch was launched",
    "secondes depuis le lancement": "seconds since launch",
    "Optimiseur (opt)": "Optimizer (opt)",
    "connexion SSH": "SSH connection",
    "calcul (Round-Robin)": "compute (Round-Robin)",
    "calcul (optimiseur)": "compute (optimizer)",
    "Optimiseur": "Optimizer",
    "11,7 s de CPU\npayé à ne rien faire": "11.7 s of CPU\npaid to sit idle",
    # real run
    "Optimiseur\n(opt)": "Optimizer\n(opt)",
    "Scénario A : 9 tâches": "Scenario A: 9 tasks",
    "Scénario B : 10 tâches": "Scenario B: 10 tasks",
    "LPT\n(même plan)": "LPT\n(same plan)",
    "temps pour finir le lot (s)": "time to finish the batch (s)",
    "Lot A · 9 tâches": "Batch A · 9 tasks",
    "Lot B · 10 tâches": "Batch B · 10 tasks",
    # burst
    "Falaise à 122 s": "Cliff at 122 s",
    "Burst : v = 1,40\n(= e2-standard-2)": "Burst: v = 1.40\n(= e2-standard-2)",
    "Bridé : v = 0,69 (−51 %)": "Throttled: v = 0.69 (−51%)",
    "Steal Linux < 0,4 %  (bridage invisible côté OS)": "Linux steal < 0.4%  (throttling invisible to the OS)",
    "secondes de calcul continu, après 10 min de repos": "seconds of continuous compute, after 10 min of rest",
    "vitesse (cœurs à pleine vitesse)": "speed (cores at full speed)",
    # recharge, D47
    "réserve pleine : 122 s": "full reserve: 122 s",
    "+1,03 s de burst\npar s de repos": "+1.03 s of burst\nper s of rest",
    "15 s de repos → 15,5 s\n(modèle)": "15 s of rest → 15.5 s\n(model)",
    "60 s de repos → 61 s\n(sonde mesurée)": "60 s of rest → 61 s\n(measured probe)",
    "secondes de repos": "seconds of rest",
    "secondes de burst regagnées": "seconds of burst regained",
    "dans la réserve": "inside the reserve",
    "après ≈ 120 s : × 2,07": "after ≈ 120 s: × 2.07",
    "calcul cumulé sur l'e2-medium (s)": "cumulative compute on the e2-medium (s)",
    "durée medium / standard": "runtime medium / standard",
    # cost
    "Round-Robin · 3 VMs dédiées": "Round-Robin · 3 dedicated VMs",
    "1,25 $/1000 lots · 802 lots/$": "$1.25 / 1000 batches · 802 batches/$",
    "Optimiseur · 3 VMs dédiées": "Optimizer · 3 dedicated VMs",
    "0,98 $/1000 lots · 1 023 lots/$": "$0.98 / 1000 batches · 1,023 batches/$",
    "Optimiseur + burst · 1 dédiée + 2 e2-medium": "Optimizer + burst · 1 dedicated + 2 e2-medium",
    "0,65 $/1000 lots · 1 541 lots/$ (−48 %)": "$0.65 / 1000 batches · 1,541 batches/$ (−48%)",
    "Même flotte, réserve vide": "Same fleet, empty reserve",
    "0,86 $/1000 lots (piège si enchaîné)": "$0.86 / 1000 batches (trap if run back to back)",
    "temps d'un lot B (s)": "time of one batch B (s)",
    # rule
    "Job < 2 min :\n−50 % de coût,\nmême temps": "Job < 2 min:\n−50% cost,\nsame time",
    "plus long : le prix\nremonte, le job s'allonge": "longer: the price\nrises, the job slows",
    "durée du job sur une e2-standard-2 (min)": "job length on an e2-standard-2 (min)",
    "Un job, lancé après une pause": "One job, started after a pause",
    "Seuil d'équilibre : u ≈ 51 %": "Break-even: u ≈ 51%",
    "Zone e2-medium :\n−50 % de coût\n· burst rechargé": "e2-medium zone:\n−50% cost\n· burst recharged",
    "Zone e2-standard-2 :\n2× plus rapide\nà coût égal": "e2-standard-2 zone:\n2× faster\nat equal cost",
    "part du temps où la VM calcule, u (%)": "share of time the VM computes, u (%)",
    "Une VM qui calcule par intermittence": "A VM that computes intermittently",
    "prix du calcul (% de l'e2-standard-2)": "price of compute (% of e2-standard-2)",
}

# phrases inside longer labels
PARTS = [("fin : ", "end: "), ("fin ", "end "), (" lots", " batches"), ("Lot ", "Batch "), ("lot ", "batch "),
         ("tâches", "tasks"), ("prédit", "predicted"), ("mesuré", "measured"), ("Go", "GB"), ("Mo", "MB")]


def numbers(s):
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)              # 15,8 -> 15.8
    s = re.sub(r"(\d)[   ](\d{3})\b", r"\1,\2", s)  # 1 541 -> 1,541
    s = re.sub(r"(\d) %", r"\1%", s)                    # 20 % -> 20%
    return s


def tr(s):
    if s is None:
        return s
    t = str(s)
    if t in EN:
        return EN[t]
    if any(c.isalpha() for c in t):
        for a, b in PARTS:
            t = t.replace(a, b)
    return numbers(t)


_set_text = mtext.Text.set_text


def _patched(self, s):
    return _set_text(self, tr(s))


mtext.Text.set_text = _patched
