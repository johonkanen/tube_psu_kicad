#!/usr/bin/env python3
"""Measurement circuits cut out of the KiCad schematic netlist (PLAN.md step 1).

The netlist is exported with `kicad-cli sch export netlist` (tools/p2k/bin/kicad-cli) to
simulation/out/tube_psu.net (5.1, kicad/) or simulation/out/5.2/tube_psu_5_2.net (`--rev 5.2`,
kicad_next/), re-exported whenever a .kicad_sch of that folder is newer. Every value
used by the ngspice netlists and the VHDL parameter package comes from here.

    python3 simulation/spice/extract.py --check     # golden check vs simulation/INVENTORY.md
    python3 simulation/spice/extract.py --show c1   # parts, values, pins of one circuit
    python3 simulation/spice/extract.py --rev 5.2 --check

5.2 has no hand inventory: its golden check compares every part value of the circuits and the
bias network with circuits.GOLDEN_52 (kicad_next/CHANGES_5_2.md), checks that the removed
parts are gone, the bias-buffer wiring, and the same role topology check as 5.1.

The golden check compares, for every circuit 1-9 and the bias network, the parts, values
and pin -> net lists with the hand inventory. Named nets must match by name; the Proteus
'#00nnn' nets of the inventory must map one-to-one onto the KiCad nets. It also checks the
role assignment of circuits.py against the netlist topology (see circuits.py docstring).
"""
import re
import subprocess
import sys
from pathlib import Path

SIM = Path(__file__).resolve().parents[1]
REPO = SIM.parent
sys.path.insert(0, str(SIM))
import circuits as C  # noqa: E402
OUT = C.OUT
NETFILE = C.NETFILE
KICAD_CLI = REPO / "tools/p2k/bin/kicad-cli"
INVENTORY = SIM / "INVENTORY.md"

SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "R": 1.0, "r": 1.0,
      "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}


def parse_value(text):
    """'6.8k' / '6k8' / '1n2' / '330R' / '4m' / '1M' -> float; 'na' (not fitted) -> None."""
    t = text.strip()
    if t.lower() in ("na", "nf", "dnp", "-"):
        return None
    t = t.split()[0]                                 # '15k 0.1%' -> '15k'
    t = t.replace("Ω", "").replace("ohm", "")
    if re.fullmatch(r".*\d[pnuµ]?[fF]", t):        # '22pf', '100nF'
        t = t[:-1]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([pnuµmRrkKMG]?)(\d*)", t)
    if not m:
        raise ValueError(f"cannot parse value {text!r}")
    num, unit, frac = m.groups()
    if frac:
        num = f"{num}.{frac}"
    return float(num) * SI.get(unit, 1.0) if unit else float(num)


def short_net(name):
    """'/04 MCU connector/AUX_MEAS' -> 'AUX_MEAS' (local labels carry the sheet path)."""
    return name.rsplit("/", 1)[-1] if not name.startswith("Net-(") else name


# ------------------------------------------------------------------ netlist export / parse
def export_netlist(force=False):
    sch = sorted(C.SCHEMATIC.parent.glob("*.kicad_sch"))
    newest = max(p.stat().st_mtime for p in sch)
    if force or not NETFILE.exists() or NETFILE.stat().st_mtime < newest:
        OUT.mkdir(parents=True, exist_ok=True)
        cmd = [str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
               "-o", str(NETFILE), str(C.SCHEMATIC)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not NETFILE.exists():
            raise SystemExit(f"kicad-cli netlist export failed:\n{r.stdout}\n{r.stderr}")
    return NETFILE


def _sexpr(text):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack, cur = [], []
    for t in tok:
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return cur[0]


def _find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


class Netlist:
    def __init__(self, path=None):
        root = _sexpr(Path(path or export_netlist()).read_text())
        self.value, self.part = {}, {}
        for comp in _find(_find(root, "components")[0], "comp"):
            ref = _find(comp, "ref")[0][1]
            self.value[ref] = _find(comp, "value")[0][1]
            ls = _find(comp, "libsource")
            self.part[ref] = _find(ls[0], "part")[0][1] if ls else ""
        self.pins = {}                   # ref -> {pin: net}
        for net in _find(_find(root, "nets")[0], "net"):
            name = short_net(_find(net, "name")[0][1])
            for node in _find(net, "node"):
                self.pins.setdefault(_find(node, "ref")[0][1], {})[_find(node, "pin")[0][1]] = name

    def val(self, ref):
        return parse_value(self.value[ref])

    def nets_of(self, ref):
        return self.pins.get(ref, {})

    def two_pin(self, ref):
        p = self.pins[ref]
        return p["1"], p["2"]


# ------------------------------------------------------------------ circuit parameters
def opamp_pins(nl, c):
    ref, unit = c["opamp"]
    model = C.OPAMPS[nl.value[ref]]
    plus, minus, out = model["pins"][unit]
    p = nl.pins[ref]
    return p[plus], p[minus], p[out]


def ref_net(c):
    return C.BIAS_NET if c["ref"] == "bias" else c["ref"]


def chain_nodes(nl, refs, start):
    """Walk a series chain from net `start`; return the list of nets (start .. end)."""
    nodes = [start]
    for r in refs:
        a, b = nl.two_pin(r)
        if a == nodes[-1]:
            nodes.append(b)
        elif b == nodes[-1]:
            nodes.append(a)
        else:
            raise AssertionError(f"{r} ({a}, {b}) does not continue the chain at {nodes[-1]}")
    return nodes


def check_topology(nl, c):
    """The circuits.py roles against the netlist: raises AssertionError on a mismatch."""
    ro = c["roles"]
    gnd = c["ref"] if c["ref"] in C.GROUNDS else "GND"

    def between(ref, a, b, what):
        if ref is None:
            return
        got = set(nl.two_pin(ref))
        assert got == {a, b}, f"{c['id']}: {what} {ref} on {sorted(got)}, expected {sorted({a, b})}"

    if c["group"] == "A":
        sh = nl.two_pin(ro["shunt"])
        assert sh == (c["input"]["net"], "GND"), f"{c['id']}: shunt {ro['shunt']} on {sh}"
    in_net = c["input"]["net"]
    np_net = chain_nodes(nl, ro["in_p"], in_net)[-1]
    between(ro["ref_p"], np_net, ref_net(c), "ref_p")
    between(ro["c_ref_p"], np_net, ref_net(c), "c_ref_p")
    if c["opamp"] is None:
        assert np_net == c["out"], f"{c['id']}: divider tap {np_net} != output {c['out']}"
        return
    plus, minus, vo = opamp_pins(nl, c)
    assert plus == np_net, f"{c['id']}: + leg ends at {np_net}, op-amp + is {plus}"
    if c["group"] == "E":
        assert minus == vo, f"{c['id']}: follower - input {minus} != output {vo}"
        between(ro["o"], vo, c["out"], "o")
        between(ro.get("c_o"), c["out"], gnd, "c_o")
        return
    g_start = c["input"].get("hold") and next(iter(c["input"]["hold"])) or gnd
    nn = chain_nodes(nl, ro["g"], g_start)[-1]
    assert nn == minus, f"{c['id']}: - leg ends at {nn}, op-amp - is {minus}"
    between(ro["f"], minus, vo, "f")
    between(ro["c_f"], minus, vo, "c_f")
    between(ro["o"], vo, c["out"], "o")
    between(ro["c_o"], c["out"], gnd, "c_o")


def circuit_params(nl, c):
    """Values by role (the VHDL parameter set); None = not present / not fitted."""
    ro = c["roles"]

    def v(ref):
        return None if ref is None else nl.val(ref)

    p = dict(in_p=[v(r) for r in ro["in_p"]], ref_p=v(ro["ref_p"]), c_ref_p=v(ro["c_ref_p"]))
    p["shunt"] = v(ro.get("shunt"))
    if c["opamp"]:
        p.update(g=[v(r) for r in ro.get("g", [])], f=v(ro.get("f")), c_f=v(ro.get("c_f")),
                 o=v(ro["o"]), c_o=v(ro.get("c_o")),
                 opamp=dict(C.OPAMPS[nl.value[c["opamp"][0]]], part=nl.value[c["opamp"][0]]))
    p["follower"] = c["group"] == "E"
    p["c_par"] = C.C_PAR_PER_MOHM if c["group"] == "B" else 0.0
    return p


def bias_load(nl, c):
    """DC resistance from the bias node to ground through the + leg of circuit c
    (its input held at 0: shunt current 0 / AC line terminal 0)."""
    p = circuit_params(nl, c)
    return sum(p["in_p"]) + p["ref_p"] + (p["shunt"] or 0.0)


def bias_network(nl):
    """5.1: REF1 source voltage that gives BIAS_VOLTAGE on the loaded bias node, and the loads.
    5.2: REF1 = 2.5 V, divider voltage vdiv (unloaded: U9 input), bias node = vdiv minus the drop
    of the loads over R131 (ideal follower), kind 'buffered'."""
    b = C.BIAS_REFS
    r_top, r_bot = nl.val(b["r_top"]), nl.val(b["r_bot"])
    loads = {c["id"]: bias_load(nl, c) for c in C.bias_circuits()}
    g_loads = sum(1.0 / r for r in loads.values())
    if b["kind"] == "buffered":
        vdiv = C.REF_VOLTAGE * r_bot / (r_top + r_bot)
        r_buf = nl.val(b["r_buf"])
        v_bias = vdiv / (1.0 + r_buf * g_loads)
        return dict(kind="buffered", r_top=r_top, r_bot=r_bot, c_bias=nl.val(b["c_bias"]),
                    c_ref=nl.val(b["c_ref"]), c_div=nl.val(b["c_div"]), r_buf=r_buf,
                    buf=nl.value[b["buf"]], loads=loads, vref=C.REF_VOLTAGE, vdiv=vdiv,
                    v_bias=v_bias, i_loads=v_bias * g_loads, r_thevenin=r_buf)
    rp = 1.0 / (1.0 / r_bot + g_loads)
    vref = C.BIAS_VOLTAGE * (r_top + rp) / rp
    return dict(kind="divider", r_top=r_top, r_bot=r_bot, c_bias=nl.val(b["c_bias"]),
                c_ref=nl.val(b["c_ref"]), loads=loads, vref=vref, v_bias=C.BIAS_VOLTAGE,
                r_thevenin=1.0 / (1.0 / r_top + 1.0 / rp))


def expected_dc_gain(nl, c):
    """Ideal DC transfer (the PLAN.md table) from the schematic values."""
    p = circuit_params(nl, c)
    rin, rref = sum(p["in_p"]), p["ref_p"]
    if c["group"] == "A":
        return p["shunt"] * p["f"] / sum(p["g"])
    div = rref / (rin + rref)
    if c["group"] in ("C", "E"):
        return div
    return div * (1.0 + p["f"] / sum(p["g"]))


# ------------------------------------------------------------------ golden check
def parse_inventory(path=INVENTORY):
    """{section: {ref: (value_text, [net pin1, net pin2])}, ...} and op-amp/ADC pin nets
    {section: {(ref, pin): net}}. Sections: 1..9 and 'bias'."""
    parts, pins, sec = {}, {}, None
    for line in Path(path).read_text().splitlines():
        m = re.match(r"## (\d+) ", line)
        if m:
            sec = int(m.group(1)) if int(m.group(1)) <= 9 else None
            continue
        if line.startswith("## "):
            sec = None
        if line.startswith("- +1V65_BIAS:"):
            sec = "bias"
        elif line.startswith("- ") and sec == "bias":
            sec = None
        if sec is None:
            continue
        body = line
        if sec != "bias":
            # rail / source-side / digital lines are not part of the analog path
            if re.match(r"\s*(Rail|Source side|Digital):", line):
                continue
            body = re.split(r"\s(?:Rail|Source side|Digital):", line)[0]
        for ref, val, inner in re.findall(r"\b([RC]\d+) (\d[\w.]*|na) \(([^)]*)\)", body):
            nets = [n.strip() for n in re.split(r"[,–]", inner)]
            parts.setdefault(sec, {})[ref] = (val, nets)
        for ref, val, a, b in re.findall(r"\b(C\d+) (\d[\w.]*) (#\d+)–(\w+)", body):
            parts.setdefault(sec, {})[ref] = (val, [a, b])
        for ref, pin, net in re.findall(r"\b((?:U|AD)\d+)-(\d+) (#\d+|[A-Za-z][\w+\-]*)", body):
            pins.setdefault(sec, {})[(ref, pin)] = net
    return parts, pins


def golden_check(nl):
    parts, pins = parse_inventory()
    errors, mapping = [], {}

    def same_net(inv, kic, where):
        if inv.startswith("#"):
            if mapping.setdefault(inv, kic) != kic:
                errors.append(f"{where}: inventory {inv} is KiCad {mapping[inv]} and {kic}")
        elif inv != kic:
            errors.append(f"{where}: inventory net {inv!r}, KiCad {kic!r}")

    for sec, entries in parts.items():
        for ref, (val, nets) in entries.items():
            if ref not in nl.value:
                errors.append(f"[{sec}] {ref} missing in the KiCad netlist")
                continue
            vi, vk = parse_value(val), nl.val(ref)
            if vi != vk and not (vi and vk and abs(vi / vk - 1) < 1e-9):
                errors.append(f"[{sec}] {ref}: inventory {val}, KiCad {nl.value[ref]}")
            for pin, inv in zip(("1", "2"), nets):
                same_net(inv, nl.pins[ref].get(pin, "?"), f"[{sec}] {ref}-{pin}")
        for (ref, pin), inv in pins.get(sec, {}).items():
            same_net(inv, nl.pins.get(ref, {}).get(pin, "?"), f"[{sec}] {ref}-{pin}")
    kic = list(mapping.values())
    for k in {k for k in kic if kic.count(k) > 1}:
        errors.append(f"KiCad net {k} is several inventory nets "
                      f"{sorted(i for i, v in mapping.items() if v == k)}")

    # the circuits.py ref sets = inventory section refs (+ the shunt, inventory 'Shared')
    for c in C.CIRCUITS:
        sec = c["inventory"]
        inv = set(parts.get(sec, {})) | {r for r, _ in pins.get(sec, {})}
        mine = set(C.circuit_refs(c)) - {c["roles"].get("shunt")}
        if inv != mine:
            errors.append(f"{c['id']}: refs differ from inventory section {sec}: "
                          f"only circuits.py {sorted(mine - inv)}, only inventory {sorted(inv - mine)}")
        try:
            check_topology(nl, c)
        except AssertionError as e:
            errors.append(str(e))
        sh = c["roles"].get("shunt")
        if sh and (nl.val(sh) != 0.004 or nl.pins[sh]["2"] != "GND"):
            errors.append(f"{c['id']}: shunt {sh} = {nl.value[sh]}, pin 2 {nl.pins[sh]['2']}")
    b = C.BIAS_REFS
    if not nl.value[b["ref"]].startswith("ISL21010CFH315Z"):
        errors.append(f"REF1 value {nl.value[b['ref']]}")
    n_parts = sum(len(e) for e in parts.values())
    n_pins = sum(len(e) for e in pins.values())
    return errors, n_parts, n_pins, mapping


def golden_check_52(nl):
    """5.2: values vs circuits.GOLDEN_52, removed parts, bias-buffer wiring, role topology."""
    errors = []
    for ref, val in C.GOLDEN_52.items():
        if ref not in nl.value:
            errors.append(f"{ref} missing in the 5.2 netlist")
        elif nl.value[ref] != val:
            errors.append(f"{ref}: expected {val!r}, netlist {nl.value[ref]!r}")
    for ref in C.REMOVED_52:
        if ref in nl.value:
            errors.append(f"{ref} should be removed in 5.2")
    b = C.BIAS_REFS
    try:
        div = nl.pins[b["buf"]]["3"]
        assert set(nl.two_pin(b["r_top"])) == {nl.pins[b["ref"]]["3"], div}, "R110 not REF1 -> U9+"
        assert set(nl.two_pin(b["r_bot"])) == {div, "GND"}, "R3 not U9+ -> GND"
        assert set(nl.two_pin(b["c_div"])) == {div, "GND"}, "C128 not on U9+"
        out = nl.pins[b["buf"]]["1"]
        assert nl.pins[b["buf"]]["4"] == out, "U9 feedback not from its output pin"
        assert set(nl.two_pin(b["r_buf"])) == {out, C.BIAS_NET}, "R131 not U9 out -> bias"
        assert set(nl.two_pin(b["c_bias"])) == {C.BIAS_NET, "GND"}, "C48 not on the bias node"
    except (AssertionError, KeyError) as e:
        errors.append(f"bias buffer: {e}")
    for c in C.CIRCUITS:
        for r in C.circuit_refs(c):
            if r not in C.GOLDEN_52 and not r.startswith("AD"):
                errors.append(f"{c['id']}: {r} has no golden value")
        try:
            check_topology(nl, c)
        except AssertionError as e:
            errors.append(str(e))
    return errors


def main(argv):
    nl = Netlist(export_netlist(force="--export" in argv))
    if "--show" in argv:
        c = C.BY_ID[argv[argv.index("--show") + 1]]
        for r in C.circuit_refs(c):
            print(f"  {r:6} {nl.value[r]:22} {nl.pins.get(r)}")
        print("  params:", circuit_params(nl, c))
        print(f"  expected DC gain {expected_dc_gain(nl, c):.6g}")
        print("  bias:", bias_network(nl))
        return 0
    if C.REV == "5.2":
        errors = golden_check_52(nl)
        print(f"golden check 5.2: {len(C.GOLDEN_52)} part values (CHANGES_5_2.md), bias buffer, "
              f"{len(C.CIRCUITS)} circuit topologies")
        for e in errors:
            print("  FAIL", e)
        print("golden check", "FAILED" if errors else "OK")
        return 1 if errors else 0
    errors, n_parts, n_pins, mapping = golden_check(nl)
    print(f"golden check: {n_parts} R/C entries, {n_pins} IC pin entries, "
          f"{len(mapping)} unnamed nets mapped, 9 circuit topologies")
    for e in errors:
        print("  FAIL", e)
    print("golden check", "FAILED" if errors else "OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
