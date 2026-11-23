"""Add MKF outputs (leakage, inductances, losses) to the MAS files and grab MKF log messages."""
import json, os, om_tr2 as m, PyOpenMagnetics as P
m.load()
leak = json.load(open('out/leak.json')); loss = json.load(open('out/loss.json'))
logs = {}
for ns in (1, 2):
    fn = f'mas/tr2_ns{ns}_N97_ungapped_220k.json'
    mas = json.load(open(fn))
    c = loss[f'ns{ns}']['cases']['N97_ungapped_220k']
    lk = leak[f'ns{ns}']
    mas['outputs'] = [{
        "origin": "PyOpenMagnetics 1.7.41 (MKF) via run_tr2.py",
        "leakageInductance_primaryReferred_PA_parallel_PB": {
            "S1_shorted_S2_open_H": lk['mkf_S1_uH'] * 1e-6, "secondary_ends_shorted_H": lk['mkf_series_uH'] * 1e-6},
        "inductanceMatrix_uH_order_PA_S1_S2_PB": lk['L_matrix_uH'],
        "windingLosses": {"total": c['winding_loss_W'], "perWinding": c['winding_loss_per']},
        "coreLosses": {"iGSE": c['core']['IGSE'], "steinmetz": c['core']['STEINMETZ'], "roshen": c['core']['ROSHEN'],
                       "magneticFluxDensityPeak_mkf": c['core']['Bpk_T']},
        "temperature_mkf_Rth_25C_ambient": c.get('T_mkf_core_Rth_total_at_40C_amb')}]
    json.dump(mas, open(fn, 'w'))
    P.set_log_level('warning')
    try:
        P.clear_logs(); P.enable_string_sink()
        P.calculate_winding_losses(mas['magnetic'], mas['inputs']['operatingPoints'][0], 100.0)
        logs[f'ns{ns}'] = P.get_logs()
    except Exception as e:
        logs[f'ns{ns}'] = f'error {e}'
json.dump(logs, open('out/mkf_logs.json', 'w'), indent=1)
print({k: (v[:1500] if isinstance(v, str) else v) for k, v in logs.items()})
