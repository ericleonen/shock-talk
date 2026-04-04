"""
tests/dsge/test_dsge.py
-----------------------
Cross-validates DSGE.simulate() against econpizza called directly.

Strategy
--------
For each model we:
  1. Build the DSGE object.
  2. Run model.simulate() (the wrapper under test).
  3. Load model._yaml with econpizza directly and call find_path with
     identical inputs — same parameters, same shock, same horizon.
  4. Assert that the two DataFrames are numerically identical (within
     floating-point tolerance), and that both contain the expected columns.

The three models escalate in complexity:
  - Model A: single-variable AR(1) driven by a demand shock (no forward-looking
    variables, purely predetermined).
  - Model B: standard three-equation New Keynesian model (IS + NKPC + Taylor).
  - Model C: NK with interest-rate smoothing, adding a lagged Taylor rule and a
    monetary-policy shock (one extra predetermined state variable).
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from dsge import DSGE


# ---------------------------------------------------------------------------
# Helper: run econpizza directly using the YAML that DSGE generated
# ---------------------------------------------------------------------------

def _simulate_direct(
    model: DSGE,
    parameters: dict,
    shock: tuple,   # (noise_name, size)  e.g. ("e_d", 0.01)
    T: int = 40,
) -> pd.DataFrame:
    """
    Load model._yaml with econpizza and call find_path directly,
    mirroring exactly what DSGE.simulate() does internally for a single shock.
    """
    import econpizza as ep

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as fh:
        fh.write(model._yaml)
        tmp_path = fh.name

    try:
        mod = ep.load(tmp_path, verbose=False)
    finally:
        os.unlink(tmp_path)

    mod.solve_stst(verbose=False)
    mod["pars"].update(parameters)

    var_names = mod["var_names"]
    init_arr = np.array(list(mod["stst"].values()))  # all zeros
    horizon = max(T + 1, 100)

    x_raw, flag = mod.find_path(
        shock=shock,
        init_state=init_arr,
        pars=dict(parameters),
        horizon=horizon,
        verbose=False,
    )

    assert not flag[0], "Direct econpizza find_path did not converge."

    deviations = np.array(x_raw)[: T + 1, :]
    df = pd.DataFrame(deviations, columns=var_names)
    df.index.name = "period"
    return df


# ---------------------------------------------------------------------------
# Model A — single-variable AR(1)
# ---------------------------------------------------------------------------
#
#   y_t = rho_y * y_{t-1} + eps_d_t
#
# No forward-looking variables; purely predetermined. BK: 0 forward-looking,
# 0 unstable eigenvalues.  Shock: 1 % positive demand innovation.

MODEL_A_LAWS = [
    "y = rho_y*L[y] + eps_d",
]
MODEL_A_PARAMS = {"rho_y": 0.9, "rho_d": 0.8}
MODEL_A_SHOCK  = ("e_d", 0.01)


class TestModelA:
    @pytest.fixture(scope="class")
    def model(self):
        return DSGE(MODEL_A_LAWS)

    def test_construction(self, model):
        assert set(model.variables) == {"y"}
        assert set(model.shocks)    == {"eps_d"}
        assert "rho_y" in model.parameters
        assert "rho_d" in model.parameters

    def test_dsge_simulate_runs(self, model):
        df = model.simulate(
            parameters=MODEL_A_PARAMS,
            shocks={MODEL_A_SHOCK[0]: MODEL_A_SHOCK[1]},
            T=40,
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 41
        assert "y" in df.columns
        assert "eps_d" in df.columns

    def test_matches_econpizza_directly(self, model):
        dsge_df = model.simulate(
            parameters=MODEL_A_PARAMS,
            shocks={MODEL_A_SHOCK[0]: MODEL_A_SHOCK[1]},
            T=40,
        )
        direct_df = _simulate_direct(model, MODEL_A_PARAMS, MODEL_A_SHOCK, T=40)

        shared = sorted(set(dsge_df.columns) & set(direct_df.columns))
        np.testing.assert_allclose(
            dsge_df[shared].values,
            direct_df[shared].values,
            atol=1e-10,
            err_msg="DSGE.simulate() diverges from direct econpizza output (Model A).",
        )


# ---------------------------------------------------------------------------
# Model B — standard three-equation New Keynesian model
# ---------------------------------------------------------------------------
#
#   IS curve:     y_t  = E[y_{t+1}] - (1/σ)(r_t - E[π_{t+1}]) + ε^d_t
#   Phillips:     π_t  = β E[π_{t+1}] + κ y_t + ε^u_t
#   Taylor rule:  r_t  = φ_π π_t + φ_y y_t
#
# Two forward-looking variables (y, π); BK requires exactly 2 unstable
# eigenvalues — satisfied for standard calibration with φ_π > 1.
# Shock: 1 % demand innovation.

MODEL_B_LAWS = [
    "y  = F[y] - (1/sigma)*(r - F[pi]) + eps_d",
    "pi = beta*F[pi] + kappa*y + eps_u",
    "r  = phi_pi*pi + phi_y*y",
]
MODEL_B_PARAMS = {
    "sigma": 1.0, "beta": 0.99, "kappa": 0.1,
    "phi_pi": 1.5, "phi_y": 0.5,
    "rho_d": 0.8,  "rho_u": 0.8,
}
MODEL_B_SHOCK = ("e_d", 0.01)


class TestModelB:
    @pytest.fixture(scope="class")
    def model(self):
        return DSGE(MODEL_B_LAWS)

    def test_construction(self, model):
        assert set(model.variables) == {"y", "pi", "r"}
        assert set(model.shocks)    == {"eps_d", "eps_u"}

    def test_dsge_simulate_runs(self, model):
        df = model.simulate(
            parameters=MODEL_B_PARAMS,
            shocks={MODEL_B_SHOCK[0]: MODEL_B_SHOCK[1]},
            T=40,
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 41
        for col in ("y", "pi", "r", "eps_d", "eps_u"):
            assert col in df.columns

    def test_matches_econpizza_directly(self, model):
        dsge_df = model.simulate(
            parameters=MODEL_B_PARAMS,
            shocks={MODEL_B_SHOCK[0]: MODEL_B_SHOCK[1]},
            T=40,
        )
        direct_df = _simulate_direct(model, MODEL_B_PARAMS, MODEL_B_SHOCK, T=40)

        shared = sorted(set(dsge_df.columns) & set(direct_df.columns))
        np.testing.assert_allclose(
            dsge_df[shared].values,
            direct_df[shared].values,
            atol=1e-10,
            err_msg="DSGE.simulate() diverges from direct econpizza output (Model B).",
        )


# ---------------------------------------------------------------------------
# Model C — NK with habit persistence in consumption (medium complexity)
# ---------------------------------------------------------------------------
#
#   Habit IS curve:   y_t = h/(1+h) y_{t-1} + 1/(1+h) E[y_{t+1}]
#                          - (1-h)/((1+h)σ) (r_t - E[π_{t+1}]) + ε^d_t
#   Phillips curve:   π_t = β E[π_{t+1}] + κ y_t + ε^u_t
#   Taylor rule:      r_t = φ_π π_t + φ_y y_t
#
# Habit formation (h > 0) adds L[y] to the IS curve, making y both
# predetermined and forward-looking.  Two forward-looking variables (y, π);
# the standard Taylor principle (φ_π > 1) ensures BK is satisfied.
# Shock: 1 % positive demand innovation.

MODEL_C_LAWS = [
    "y  = (h/(1+h))*L[y] + (1/(1+h))*F[y] - ((1-h)/((1+h)*sigma))*(r - F[pi]) + eps_d",
    "pi = beta*F[pi] + kappa*y + eps_u",
    "r  = phi_pi*pi + phi_y*y",
]
MODEL_C_PARAMS = {
    "sigma": 1.0, "beta": 0.99, "kappa": 0.1,
    "h": 0.7,
    "phi_pi": 1.5, "phi_y": 0.5,
    "rho_d": 0.8,  "rho_u": 0.6,
}
MODEL_C_SHOCK = ("e_d", 0.01)


class TestModelC:
    @pytest.fixture(scope="class")
    def model(self):
        return DSGE(MODEL_C_LAWS)

    def test_construction(self, model):
        assert set(model.variables) == {"y", "pi", "r"}
        assert set(model.shocks)    == {"eps_d", "eps_u"}
        assert "h" in model.parameters

    def test_dsge_simulate_runs(self, model):
        df = model.simulate(
            parameters=MODEL_C_PARAMS,
            shocks={MODEL_C_SHOCK[0]: MODEL_C_SHOCK[1]},
            T=40,
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 41
        for col in ("y", "pi", "r", "eps_d", "eps_u"):
            assert col in df.columns

    def test_matches_econpizza_directly(self, model):
        dsge_df = model.simulate(
            parameters=MODEL_C_PARAMS,
            shocks={MODEL_C_SHOCK[0]: MODEL_C_SHOCK[1]},
            T=40,
        )
        direct_df = _simulate_direct(model, MODEL_C_PARAMS, MODEL_C_SHOCK, T=40)

        shared = sorted(set(dsge_df.columns) & set(direct_df.columns))
        np.testing.assert_allclose(
            dsge_df[shared].values,
            direct_df[shared].values,
            atol=1e-10,
            err_msg="DSGE.simulate() diverges from direct econpizza output (Model C).",
        )
