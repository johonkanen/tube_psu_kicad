#!/usr/bin/env python3
"""Net classes, isolation domains and JLC board minimums of kicad_next/tube_psu_5_2.kicad_pro.

    python3 tools/next/setup_project.py           update the project file
    python3 tools/next/setup_project.py --check   fail if a net has no domain, two domains, or the
                                                  project file is not up to date
    python3 tools/next/setup_project.py --list    print every net with its domain and class

Domains come from the 5.2 schematic netlist (kicad-cli sch export netlist): a flood fill from the
domain ground nets through every part except the barrier parts (BARRIERS); a net reached from two
grounds means a part bridges a barrier (error). Isolator pins that are not connected get the domain of
their side (ISO_SIDE2). Inside a domain the class is HV (HV_NETS), a power rail (*_LV, RAILS) or
SIGNAL (primary only; other domains have one LV class). Every net gets exactly one class by an exact
name pattern, so the creepage rules in tube_psu_5_2.kicad_dru (conditions on net classes) see every
net. The derivation of the spacings is in kicad_next/README.md.
"""
import collections
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRO = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_pro")
SCH = os.path.join(ROOT, "kicad_next", "tube_psu_5_2.kicad_sch")
CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")

# --- domains ----------------------------------------------------------------------------------------
GROUNDS = {"PRIMARY": "GND", "SECONDARY": "ISO_GND", "HEATER": "HT_GND"}  # UART: phase 2 adds "ISO_UART_GND"
BARRIERS = {"TR1", "TR2", "TR3", "ISO1", "ISO2"}          # parts whose pins sit in two domains
ISO_SIDE2 = {"ISO1": "HEATER", "ISO2": "SECONDARY"}       # Si8661: pins 1-8 primary, 9-16 side 2
EARTH = {"/05 PFC/PE"}                                     # protective earth (Y caps to primary)

# --- HV nets (> ~60 V to the domain ground or floating with a switch node) ---------------------------
HV_NETS = {
    "PRIMARY": {
        "DC+", "AC1", "AC2", "/05 PFC/IN2", "/05 PFC/L1_PRI2", "/05 PFC/L2_PRI2", "/05 PFC/RES_IN",
        "Net-(RL1-COM)", "Net-(L1-1)", "Net-(L2-2)",                     # mains, inrush, PFC drains
        "DHB_HI_SOURCE", "/07 DHB/TRANS_PRI", "/07 DHB/DHB_CAP",           # DAB primary bridge
        "DHB_HI_GATE", "Net-(Q19-G)", "Net-(D30-PadA)", "Net-(DRV5-VDDB)", "Net-(D19-K)",  # high side
        "/06 Heaters/HEATER_HI_SOURCE", "/06 Heaters/HEATER_CAP_MEAS",    # heater LLC bridge / tank
        "/06 Heaters/HEATER_HI_GATE", "Net-(DRV3-OUT+)", "Net-(DRV3-OUT-)", "Net-(DRV3-VDD2)", "Net-(D11-K)",
        "/01 AUX supply/FLY_C", "Net-(D7-K)", "Net-(C12-Pad2)",                   # flyback drain / clamp
        "Net-(R114-Pad1)", "Net-(R115-Pad1)", "Net-(R15-Pad1)", "Net-(R10-Pad1)",  # dividers from DC+
        "Net-(R4-Pad1)", "Net-(R5-Pad1)", "Net-(R47-Pad2)", "Net-(R48-Pad2)", "Net-(R50-Pad2)",
        "Net-(R51-Pad2)", "Net-(R109-Pad1)", "Net-(R111-Pad1)",
    },
    "SECONDARY": {
        "420V", "/07 DHB/TRANS_SEC", "DHB_HI_SOURCE_SEC", "DHB_HI_GATE_SEC", "Net-(Q21-G)",
        "Net-(D31-PadA)", "Net-(DRV6-VDDA)", "Net-(D18-K)", "-100V BIAS", "Net-(D8-K)",
        "Net-(R23-Pad2)", "Net-(R34-Pad2)",
    },
}
RAILS = {"GND", "15V", "5V", "+3V3", "+1V65_BIAS"}   # primary low-voltage supply nets -> PRIMARY_LV
DOMAIN_CLASS = {"SECONDARY": "SECONDARY_LV", "HEATER": "HEATER", "UART": "UART_ISO", "EARTH": "PE_EARTH"}

# --- net classes: (name, clearance, track, via, drill) mm; clearance = functional, all layers --------
# The domain-to-domain and HV outer-layer spacings are custom rules in tube_psu_5_2.kicad_dru.
CLASSES = [
    ("Default", 0.15, 0.2, 0.6, 0.3),
    ("SIGNAL", 0.15, 0.2, 0.6, 0.3),
    ("PRIMARY_LV", 0.2, 0.5, 0.8, 0.4),
    ("HV_PRIMARY", 0.5, 1.0, 1.0, 0.5),
    ("SECONDARY_LV", 0.2, 0.3, 0.8, 0.4),
    ("HV_SECONDARY", 0.5, 1.0, 1.0, 0.5),
    ("HEATER", 0.2, 1.0, 0.8, 0.4),
    ("UART_ISO", 0.15, 0.2, 0.6, 0.3),
    ("PE_EARTH", 0.5, 1.5, 1.0, 0.5),
]
COLORS = {"HV_PRIMARY": "rgba(220, 40, 40, 0.800)", "HV_SECONDARY": "rgba(230, 120, 0, 0.800)",
          "PRIMARY_LV": "rgba(180, 90, 90, 0.800)", "SECONDARY_LV": "rgba(200, 160, 40, 0.800)",
          "HEATER": "rgba(60, 160, 60, 0.800)", "UART_ISO": "rgba(60, 120, 220, 0.800)",
          "PE_EARTH": "rgba(40, 170, 170, 0.800)"}

# --- board minimums (JLC multilayer capabilities, jlcpcb.com/capabilities/pcb-capabilities, 2026-11-17) --
RULES = {
    "min_clearance": 0.1,             # JLC 0.09 mm (3.5 mil) trace/space, 1 oz outer
    "min_track_width": 0.1,           # JLC 0.09 mm
    "min_connection": 0.1,
    "min_via_diameter": 0.25,         # JLC via 0.15 / 0.25 mm (6-layer: epoxy filled + capped)
    "min_through_hole_diameter": 0.15,  # JLC min drill 0.15 mm (PTH pads: annular rule in .kicad_dru)
    "min_via_annular_width": 0.05,    # (0.25 - 0.15) / 2
    "min_hole_to_hole": 0.2,          # JLC via hole-to-hole 0.2 mm (pads 0.45: .kicad_dru)
    "min_hole_clearance": 0.2,        # hole to other copper
    "min_copper_edge_clearance": 0.3, # JLC routed edge >= 0.2 mm (+0.1 margin)
    "min_text_height": 1.0,           # JLC silk text >= 1.0 mm
    "min_text_thickness": 0.15,       # JLC silk line >= 0.15 mm
    "min_silk_clearance": 0.0,
    "min_microvia_diameter": 0.2,
    "min_microvia_drill": 0.1,
    "solder_mask_to_copper_clearance": 0.0,
}


def netlist():
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "net.xml")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                       check=True, capture_output=True)
        t = ET.parse(out)
    pins = collections.defaultdict(list)
    for n in t.find("nets"):
        pins[n.get("name")]  # nets without nodes too
        for nd in n.findall("node"):
            pins[n.get("name")].append((nd.get("ref"), nd.get("pin")))
    return pins


def domains(pins):
    nets_of = collections.defaultdict(set)
    for n, ps in pins.items():
        for r, _ in ps:
            nets_of[r].add(n)
    dom = collections.defaultdict(set)
    for d, seed in GROUNDS.items():
        if seed not in pins:
            continue
        stack, seen = [seed], {seed}
        while stack:
            n = stack.pop()
            for r, _ in pins[n]:
                if r in BARRIERS:
                    continue
                for m in nets_of[r] - seen:
                    seen.add(m)
                    stack.append(m)
        for n in seen:
            dom[n].add(d)
    for n, ps in pins.items():
        if not dom[n]:
            for r, p in ps:
                if r in ISO_SIDE2 and p.isdigit():
                    dom[n].add(ISO_SIDE2[r] if int(p) >= 9 else "PRIMARY")
    for n in EARTH:
        dom[n] = {"EARTH"}
    return dom


def classify(pins):
    dom = domains(pins)
    errors, cls = [], {}
    for n in sorted(pins):
        d = dom.get(n, set())
        if len(d) != 1:
            errors.append(f"net {n!r}: domains {sorted(d) or 'none'}")
            continue
        d = next(iter(d))
        if n in HV_NETS.get(d, ()):
            cls[n] = "HV_" + d
        elif d == "PRIMARY":
            cls[n] = "PRIMARY_LV" if n in RAILS else "SIGNAL"
        else:
            cls[n] = DOMAIN_CLASS[d]
    for d, nets in HV_NETS.items():
        for n in sorted(nets - set(pins)):
            errors.append(f"HV_NETS[{d}]: {n!r} is not a net of the schematic")
    return cls, errors


def updated(pro, cls):
    d = json.loads(json.dumps(pro))
    ns = d["net_settings"]
    template = next(c for c in ns["classes"] if c["name"] == "Default")
    ns["classes"] = []
    for prio, (name, clr, tw, via, drill) in enumerate(CLASSES):
        c = dict(template)
        c.update(name=name, clearance=clr, track_width=tw, via_diameter=via, via_drill=drill,
                 priority=2147483647 if name == "Default" else prio,
                 pcb_color=COLORS.get(name, "rgba(0, 0, 0, 0.000)"))
        ns["classes"].append(c)
    ns["netclass_patterns"] = [{"netclass": c, "pattern": n} for n, c in sorted(cls.items(), key=lambda x: (x[1], x[0]))]
    ns["netclass_assignments"] = {}
    d["board"]["design_settings"]["rules"].update(RULES)
    return d


def main(argv):
    pins = netlist()
    cls, errors = classify(pins)
    for e in errors:
        print("setup_project: " + e)
    if "--list" in argv:
        for n, c in sorted(cls.items(), key=lambda x: (x[1], x[0])):
            print(f"{c:13s} {n}")
    with open(PRO) as f:
        pro = json.load(f)
    new = updated(pro, cls)
    count = collections.Counter(cls.values())
    summary = ", ".join(f"{c} {count[c]}" for c, *_ in CLASSES if count[c])
    if "--check" in argv:
        if new != pro:
            print("setup_project: kicad_next/tube_psu_5_2.kicad_pro is not up to date (run tools/next/setup_project.py)")
            return 1
        print(f"setup_project: {len(cls)}/{len(pins)} nets in one domain class each ({summary})"
              + ("" if not errors else f"; {len(errors)} errors"))
        return 1 if errors else 0
    with open(PRO, "w") as f:
        json.dump(new, f, indent=2)
        f.write("\n")
    print(f"setup_project: wrote kicad_next/tube_psu_5_2.kicad_pro ({summary})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
