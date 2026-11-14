-- One testbench for all measurement paths (simulation/PLAN.md step 3).
--
-- g_circuit selects the parameter set (meas_params_pkg, generated from the
-- schematic), g_band the sample rate / length (BANDS). The run:
--
--   1. DC operating point at u0 and u0 + u_amp: L-stable TR-BDF2 with long
--      steps from the initial state -> the DC gain (#CONFIG dc_*)
--   2. from the u0 operating point: uniform dither u0 +- u_amp, one new value
--      per sample, joined by straight lines (first-order hold) so the input
--      seen by the model is continuous and band-limited; y is sampled at the
--      sample instants. Compared with the zero-order hold of the hVHDL_ode
--      examples, this needs no half-sample deskew and works the same whether
--      the circuit is slow or fast compared with the sample rate (the
--      Welch H1 estimate then equals H(f) * sinc^2(f/fs) plus aliases, which
--      compare.py applies to the ngspice reference).
--   3. columns time, u - u0, y - y(u0) of every sample to meas.dat in the
--      test output path (deviations: write_to prints 7 significant digits),
--      with the #CONFIG lines of hVHDL_ode test_plot.py (freq_pair_H)
--
-- Solver: generic_trbdf2 (A/L-stable): the op-amp loops reach 140 MHz while
-- the low bands step at 0.5 ms.
library ieee;
    use ieee.math_real.all;
    use std.textio.all;

library vunit_lib;
    context vunit_lib.vunit_context;

library ode;
    use ode.write_pkg.all;
    use ode.ode_pkg.all;

library meas;
    use meas.meas_models_pkg.all;
    use meas.meas_params_pkg.all;

entity meas_circuit_tb is
    generic (
        runner_cfg : string;
        g_circuit  : natural := 1;
        g_band     : natural := 0;
        g_seed     : positive := 1
    );
end entity;

architecture sim of meas_circuit_tb is
begin

    main : process
        constant p    : meas_params_t := MEAS_PARAMS(g_circuit);
        constant band : band_t        := BANDS(g_band);
        constant h    : real          := 1.0 / band.fs;
        constant n_samples : natural  := band.nperseg * band.windows;

        variable t0, u_cur, u_next : real := 0.0;   -- the current step: [t0, t0 + h]
        variable seed1 : positive := g_seed;
        variable seed2 : positive := 7;
        variable rnd   : real;

        impure function deriv(t : real; s : real_vector) return real_vector is
            constant slope : real := (u_next - u_cur) / h;
        begin
            return meas_deriv(p, u_cur + slope * (t - t0), slope, s);
        end function;

        procedure trbdf2 is new generic_trbdf2 generic map(deriv => deriv);

        variable state, s_dc : meas_state_t;
        variable y0, y1      : real;
        variable realtime    : real := 0.0;

        -- DC operating point at input u: constant input, long L-stable steps
        procedure dc_state(u : real; s : out meas_state_t) is
            variable sv : meas_state_t;
        begin
            sv     := meas_init(p, u);
            u_cur  := u;
            u_next := u;
            t0     := 0.0;
            for i in 1 to 60 loop
                trbdf2(0.0, sv, 1.0e-4);
            end loop;
            s := sv;
        end procedure;

        file f : text;
    begin
        test_runner_setup(runner, runner_cfg);

        dc_state(p.u0 + p.u_amp, s_dc);
        y1    := meas_output(p, p.u0 + p.u_amp, s_dc);
        dc_state(p.u0, state);
        y0    := meas_output(p, p.u0, state);

        file_open(f, output_path(runner_cfg) & "meas.dat", write_mode);
        write_plot_config(f, "title", "measurement circuit c" & integer'image(g_circuit)
                          & ", band " & integer'image(g_band));
        write_plot_config(f, "circuit", "c" & integer'image(g_circuit));
        write_plot_config(f, "band", integer'image(g_band));
        write_plot_config(f, "dc_u0", real'image(p.u0));
        write_plot_config(f, "dc_du", real'image(p.u_amp));
        write_plot_config(f, "dc_y0", real'image(y0));
        write_plot_config(f, "dc_y1", real'image(y1));
        write_plot_config(f, "dc_bias", real'image(state(V_B)));
        write_plot_config(f, "freq_fs", real'image(band.fs));
        write_plot_config(f, "freq_nperseg", integer'image(band.nperseg));
        write_plot_config(f, "freq_f_lo", real'image(band.f_lo));
        write_plot_config(f, "freq_f_hi", real'image(band.f_hi));
        write_plot_config(f, "freq_input_hold", "foh");
        write_plot_config(f, "freq_pair_H", "B_u0,B_y0");
        write_plot_config(f, "label_H", "y/u (hVHDL_ode TR-BDF2)");
        init_simfile(f, ("time", "B_u0", "B_y0"));

        uniform(seed1, seed2, rnd);
        u_next := p.u0 + (2.0 * rnd - 1.0) * p.u_amp;
        for n in 0 to n_samples - 1 loop
            u_cur := u_next;
            uniform(seed1, seed2, rnd);
            u_next := p.u0 + (2.0 * rnd - 1.0) * p.u_amp;
            -- deviations from the operating point: write_to prints 7 significant
            -- digits, so the small responses (-150 dB) need the DC removed first
            write_to(f, (realtime, u_cur - p.u0, meas_output(p, u_cur, state) - y0));
            t0 := realtime;
            trbdf2(realtime, state, h);
            realtime := realtime + h;
        end loop;
        file_close(f);

        info("c" & integer'image(g_circuit) & " band " & integer'image(g_band) & ": "
             & integer'image(n_samples) & " samples, DC gain " & real'image((y1 - y0) / p.u_amp)
             & ", y(u0) " & real'image(y0));
        test_runner_cleanup(runner);
        wait;
    end process;

end architecture;
