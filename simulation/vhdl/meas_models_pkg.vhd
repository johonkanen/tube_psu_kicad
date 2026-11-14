-- Measurement-path models of tube_power_5_1 (simulation/PLAN.md step 3).
--
-- One parameterised topology covers the four model groups of PLAN.md (see
-- simulation/circuits.py for the role -> refdes mapping; the parameter sets are
-- generated from the KiCad schematic into meas_params_pkg.vhd):
--
--   + leg : IN --[in_p: 1..3 sections R (|| c_par)]-- NP --[r_ref_p || c_ref_p]-- REF
--   - leg : 0  --[g:    1..3 sections R (|| c_par)]-- NN --[r_f || c_f]-- VO
--   op-amp: dx/dt = wp*(a0*(NP - NN) - x), wp = 2*pi*gbw/a0, VO = x - rout*i_out
--   output: VO --[r_o]-- OUT --[c_o]-- 0          (c_o = 0: OUT = VO, r_o unloaded)
--   REF   : the +2V5_BIAS node (vref -[r_btop]- REF -[r_bbot || c_bias]- 0, plus the
--           other circuits' + legs as one resistance r_bother) or ground
--
--   group A shunt diff amp: IN = in_scale * u (u = shunt current, in_scale = R_shunt;
--           the 4 mohm shunt's loading by the 330 ohm input, 1.2e-5, is neglected)
--   group B HV diff amp   : 3 x 1M with c_par across each section
--   group C divider + RC  : has_opamp = false, OUT = NP
--   group D non-inverting : - leg one R to ground, c_f = 0
--
-- The capacitor voltages are the states (one per capacitor). The node voltages
-- without a capacitor are solved algebraically inside the derivative. The one
-- capacitor-only loop (group B with c_ref_p, circuit 8: source - 3 x c_par - C27)
-- takes the input slope du/dt; the testbench drives a first-order-hold input,
-- so du/dt is finite (piecewise constant).
--
-- The op-amp is the same macromodel as simulation/spice/run_ac.py (no rails).
library ieee;
    use ieee.math_real.all;

package meas_models_pkg is

    type r3_t is array (1 to 3) of real;

    type meas_params_t is record
        has_opamp : boolean;
        has_bias  : boolean;
        in_scale  : real;     -- IN = in_scale * u
        n_in_p    : positive;
        r_in_p    : r3_t;
        r_ref_p   : real;
        c_ref_p   : real;     -- 0 = none
        c_par     : real;     -- across every chain section, 0 = none
        n_g       : positive;
        r_g       : r3_t;
        r_f       : real;
        c_f       : real;
        r_o       : real;
        c_o       : real;
        a0        : real;
        gbw       : real;
        rout      : real;
        vref      : real;     -- bias network
        r_btop    : real;
        r_bbot    : real;
        c_bias    : real;
        r_bother  : real;
        u0        : real;     -- input DC level of the run
        u_amp     : real;     -- dither amplitude (uniform, +-u_amp)
    end record;

    type band_t is record
        fs      : real;
        nperseg : positive;
        windows : positive;
        f_lo    : real;
        f_hi    : real;
    end record;

    -- state vector
    constant X_OA     : natural := 0;   -- op-amp gain-stage voltage
    constant V_B      : natural := 1;   -- bias capacitor (C48)
    constant VP1      : natural := 2;   -- 2..4 + chain section capacitors
    constant V_CREF   : natural := 5;   -- c_ref_p
    constant VN1      : natural := 6;   -- 6..8 - chain section capacitors
    constant V_CF     : natural := 9;   -- c_f
    constant V_CO     : natural := 10;  -- c_o
    constant N_STATES : natural := 11;

    subtype meas_state_t is real_vector(0 to N_STATES - 1);

    type meas_nodes_t is record
        np, nn, vo, y : real;
        ip            : real;   -- + leg series current, IN -> REF
        i_f           : real;   -- - leg current, VO -> 0
    end record;

    function meas_nodes (p : meas_params_t; u, dudt : real; s : real_vector) return meas_nodes_t;
    function meas_deriv (p : meas_params_t; u, dudt : real; s : real_vector) return real_vector;
    function meas_output(p : meas_params_t; u : real; s : real_vector) return real;
    -- states that satisfy the capacitor-loop constraint at input u (DC distribution)
    function meas_init  (p : meas_params_t; u : real) return real_vector;

end package meas_models_pkg;

package body meas_models_pkg is

    function rsum(r : r3_t; n : positive) return real is
        variable acc : real := 0.0;
    begin
        for k in 1 to n loop
            acc := acc + r(k);
        end loop;
        return acc;
    end function;

    function meas_nodes (p : meas_params_t; u, dudt : real; s : real_vector) return meas_nodes_t is
        variable nd      : meas_nodes_t;
        variable up, dup : real;
        variable ref     : real := 0.0;
        variable rin     : real;
        variable acc     : real;
        variable inv_c   : real;
        variable af, gf  : real;
        variable go      : real := 0.0;
        variable rg      : real;
    begin
        up  := p.in_scale * u;
        dup := p.in_scale * dudt;
        if p.has_bias then
            ref := s(V_B);
        end if;
        rin := rsum(p.r_in_p, p.n_in_p);

        -- + leg
        if p.c_par = 0.0 and p.c_ref_p = 0.0 then
            nd.ip := (up - ref) / (rin + p.r_ref_p);
            nd.np := ref + nd.ip * p.r_ref_p;
        elsif p.c_par = 0.0 then
            nd.np := ref + s(V_CREF);
            nd.ip := (up - nd.np) / rin;
        elsif p.c_ref_p = 0.0 then
            acc := 0.0;
            for k in 1 to p.n_in_p loop
                acc := acc + s(VP1 + k - 1);
            end loop;
            nd.np := up - acc;
            nd.ip := (nd.np - ref) / p.r_ref_p;
        else
            -- capacitor loop: sum of the section voltages = up - ref (ref = ground)
            assert not p.has_bias report "capacitor loop with the bias node as reference" severity failure;
            acc   := s(V_CREF) / (p.r_ref_p * p.c_ref_p);
            inv_c := 1.0 / p.c_ref_p;
            for k in 1 to p.n_in_p loop
                acc   := acc + s(VP1 + k - 1) / (p.r_in_p(k) * p.c_par);
                inv_c := inv_c + 1.0 / p.c_par;
            end loop;
            nd.ip := (dup + acc) / inv_c;
            nd.np := s(V_CREF);
        end if;

        if not p.has_opamp then
            nd.y := nd.np;
            return nd;
        end if;

        -- - leg: i_f = gf * (vo - af)
        rg := rsum(p.r_g, p.n_g);
        if p.c_par = 0.0 and p.c_f = 0.0 then
            af := 0.0;
            gf := 1.0 / (rg + p.r_f);
        elsif p.c_par = 0.0 then
            af := s(V_CF);
            gf := 1.0 / rg;
        else
            assert p.c_f = 0.0 report "c_f with a c_par chain not modelled" severity failure;
            af := 0.0;
            for k in 1 to p.n_g loop
                af := af + s(VN1 + k - 1);
            end loop;
            gf := 1.0 / p.r_f;
        end if;
        if p.c_o > 0.0 then
            go := 1.0 / p.r_o;
        end if;
        nd.vo  := (s(X_OA) + p.rout * (gf * af + go * s(V_CO))) / (1.0 + p.rout * (gf + go));
        nd.i_f := gf * (nd.vo - af);
        if p.c_par = 0.0 and p.c_f = 0.0 then
            nd.nn := nd.i_f * rg;
        elsif p.c_par = 0.0 then
            nd.nn := nd.vo - s(V_CF);
        else
            nd.nn := af;
        end if;
        if p.c_o > 0.0 then
            nd.y := s(V_CO);
        else
            nd.y := nd.vo;
        end if;
        return nd;
    end function;

    function meas_deriv (p : meas_params_t; u, dudt : real; s : real_vector) return real_vector is
        variable d  : real_vector(s'range) := (others => 0.0);
        variable nd : meas_nodes_t;
        variable wp : real;
    begin
        nd := meas_nodes(p, u, dudt, s);

        if p.has_bias then
            d(V_B) := ((p.vref - s(V_B)) / p.r_btop - s(V_B) / p.r_bbot
                       - s(V_B) / p.r_bother + nd.ip) / p.c_bias;
        end if;

        if p.c_ref_p > 0.0 then
            d(V_CREF) := (nd.ip - s(V_CREF) / p.r_ref_p) / p.c_ref_p;
        end if;
        if p.c_par > 0.0 then
            for k in 1 to p.n_in_p loop
                d(VP1 + k - 1) := (nd.ip - s(VP1 + k - 1) / p.r_in_p(k)) / p.c_par;
            end loop;
        end if;

        if p.has_opamp then
            wp        := math_2_pi * p.gbw / p.a0;
            d(X_OA)   := wp * (p.a0 * (nd.np - nd.nn) - s(X_OA));
            if p.c_par > 0.0 then
                for k in 1 to p.n_g loop
                    d(VN1 + k - 1) := (nd.i_f - s(VN1 + k - 1) / p.r_g(k)) / p.c_par;
                end loop;
            elsif p.c_f > 0.0 then
                d(V_CF) := (nd.i_f - s(V_CF) / p.r_f) / p.c_f;
            end if;
            if p.c_o > 0.0 then
                d(V_CO) := (nd.vo - s(V_CO)) / (p.r_o * p.c_o);
            end if;
        end if;
        return d;
    end function;

    function meas_output(p : meas_params_t; u : real; s : real_vector) return real is
    begin
        return meas_nodes(p, u, 0.0, s).y;
    end function;

    function meas_init (p : meas_params_t; u : real) return real_vector is
        variable s    : meas_state_t := (others => 0.0);
        variable rtot : real;
    begin
        if p.c_par > 0.0 and p.c_ref_p > 0.0 then
            rtot := rsum(p.r_in_p, p.n_in_p) + p.r_ref_p;
            for k in 1 to p.n_in_p loop
                s(VP1 + k - 1) := p.in_scale * u * p.r_in_p(k) / rtot;
            end loop;
            s(V_CREF) := p.in_scale * u * p.r_ref_p / rtot;
        end if;
        return s;
    end function;

end package body meas_models_pkg;
