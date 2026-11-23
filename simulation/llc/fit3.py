"""Fit one set of build assumptions to the three documented leakage measurements (design doc p.19,
Table 4.1): 64 T flat 62 uH, 32+32 T series sandwich 24 uH, 64 || 64 T parallel sandwich 42 uH."""
import itertools, json, math, sys, warnings, numpy as np, om_tr2 as m
warnings.filterwarnings("ignore")
MEAS = {"flat": 62e-6, "series": 24e-6, "parallel": 42e-6}
m.load()
odr = m.wire_od("LITZ35")
rows = []
grid = list(itertools.product([0.866, 1.0], [1, 3, 5], [1.25e-3, None], ["bifilar", "block"], ["centre", "end"]))
par_sets = [("8 | 8+8 | 6+2", dict(flat=dict(na=64, pa_par=8, nb=0), series=dict(na=32, pa_par=8, nb=32, pb_par=8), parallel=dict(na=64, pa_par=6, nb=64, pb_par=2))),
            ("4 | 4+4 | 4+4", dict(flat=dict(na=64, pa_par=4, nb=0), series=dict(na=32, pa_par=4, nb=32, pb_par=4), parallel=dict(na=64, pa_par=4, nb=64, pb_par=4)))]
for (pset, pk), (pitch, tape, lt, order, pos) in itertools.product(par_sets, grid):
    wdt = (math.pi / 4 * odr ** 2 / lt) if lt else odr
    r = {"strands": pset, "pitch": pitch, "tape_layers": tape, "litz": "pressed 1.25" if lt else "round 1.67",
         "sec_order": order, "sec_pos": pos}
    ok = True
    for arr in ("flat", "series", "parallel"):
        kw = dict(pk[arr], tape_layers=tape, pitch_factor=pitch, litz_thk=lt, sec_order=order,
                  radial_width=4.7e-3, sec_y_offset=(7.9e-3 - 2 * wdt if pos == "end" else 0.0))
        try:
            c, rep = m.build_coil(ns=2, **kw)
        except ValueError:
            ok = False; break
        L = m.inductance_matrix({"core": m.make_core("N97", 0), "coil": c}, 220e3)
        for sec in ("S1", "series"):
            r[f"{arr}_{sec}_uH"] = m.leak_general(L, arr, sec) * 1e6
        r[f"{arr}_stack_mm"] = rep["stack_mm"]
    if not ok:
        continue
    for sec in ("S1", "series"):
        errs = [math.log(r[f"{a}_{sec}_uH"] * 1e-6 / MEAS[a]) for a in MEAS]
        r[f"rms_log_err_{sec}"] = math.sqrt(np.mean(np.square(errs)))
        r[f"errs_pct_{sec}"] = [100 * (math.exp(e) - 1) for e in errs]
    rows.append(r)
    print(json.dumps(r), flush=True)
json.dump(rows, open("out/fit3.json", "w"), indent=1)
