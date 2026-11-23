"""Diagnostic: which sign of the secondary current gives MMF balance in MKF's field solver."""
import json, numpy as np, om_tr2 as m, run_tr2 as r, PyOpenMagnetics as P
m.load()
lk=json.load(open('out/leak.json'))['ns2']
mag, rep = r.mag_for(2)
t, cur, v, ipk, impk = r.waveforms(2, 220e3, 217.8, 6.578e-3, lk['mkf_S1_kA'], lk['kA_open'])
for lab, sgn, zero in (("sec sign +1 (S = -n iL)", 1.0, False), ("sec sign -1", -1.0, False), ("secondary zero", 1.0, True)):
    exc=[]
    for n in m.NAMES:
        i = cur[n]*(sgn if n.startswith('S') else 1.0)*(0.0 if (zero and n.startswith('S')) else 1.0)
        wf={"data": list(map(float,i)), "time": list(map(float,t))}
        hm=P.calculate_harmonics(wf, 220e3)
        pr=P.calculate_processed(hm, wf)
        exc.append({"name": n, "frequency": 220e3, "current": {"waveform": wf, "harmonics": hm, "processed": pr}})
    op={"name":"x","conditions":{"ambientTemperature":40.0},"excitationsPerWinding":exc}
    fo=P.calculate_magnetic_field_strength_field(op, mag)
    fpts=fo["fieldPerFrequency"][0]["data"] if "fieldPerFrequency" in fo else None
    if fpts is None: print(list(fo.keys())); break
    H=[abs(complex(p.get("real",0),p.get("imaginary",0))) for p in fpts]
    print(lab, "harmonic0 freq", fo["fieldPerFrequency"][0].get("frequency"), "max|H| %.0f A/m, mean %.0f"%(max(H), np.mean(H)), "npts", len(H))
    wl=P.calculate_winding_losses(mag, op, 100.0)
    print("   prox per winding", [round(sum((p.get("proximityEffectLosses") or {}).get("lossesPerHarmonic") or []),4) for p in wl["windingLossesPerWinding"]])
