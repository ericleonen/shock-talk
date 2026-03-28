"""
dsge.py
-------
A minimal interface for specifying, validating, and simulating log-linearised
DSGE models.  Models are expressed in a plain equation syntax, compiled to an
econpizza YAML on the fly, and solved with econpizza's nonlinear perfect-
foresight stacking solver.

Equation syntax
---------------
Each equation must have the form

    variable = <linear expression>

where the right-hand side is **linear** in:

* bare variables           ``y``, ``pi``, ``r``
* forward expectations     ``F[y]``, ``F[pi]``
* one-period lags          ``L[y]``, ``L[pi]``
* shock processes          ``eps_*``   (e.g. ``eps_d``, ``eps_u``)

Coefficients and intercepts may be arbitrary expressions of parameters.
Coefficients must always precede the variable in a product
(e.g. ``beta*F[pi]``, not ``F[pi]*beta``).

Symbol inference rules
----------------------
* A symbol whose name starts with ``eps_`` is a **shock process**
  (an AR(1) state variable driven by white noise).
* A symbol whose name starts with ``e_`` (and is not a shock process) is
  **white noise**; it is auto-generated and must not be written explicitly.
* Any symbol that appears on a left-hand side, or inside ``F[...]``/``L[...]``,
  is a **variable**.
* Everything else is a **parameter** that the user must supply at simulation
  time.

Example
-------
::

    model = DSGE([
        "y   = F[y] - (1/sigma)*(r - F[pi]) + eps_d",
        "pi  = beta*F[pi] + kappa*y + eps_u",
        "r   = phi_pi*pi + phi_y*y",
        "eps_d = rho_d*L[eps_d] + e_d",   # optional - auto-generated if omitted
        "eps_u = rho_u*L[eps_u] + e_u",
    ])
"""

from __future__ import annotations

import os
import tempfile
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .symbols import infer_symbols
from .validate import *
from .yaml import build_yaml
from .bk import *

# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class DSGE:
    """
    A log-linearised DSGE model specified via plain equilibrium equations.

    Parameters
    ----------
    laws : list[str]
        Equilibrium equations in the form ``variable = <expression>``.
        See module docstring for the full syntax specification.

    Raises
    ------
    ValueError
        If any equation violates the LHS convention, the linearity
        constraint, or if the equation count does not match the number of
        endogenous variables.

    Examples
    --------
    Three-equation New Keynesian model::

        model = DSGE([
            "y  = F[y] - (1/sigma)*(r - F[pi]) + eps_d",
            "pi = beta*F[pi] + kappa*y + eps_u",
            "r  = phi_pi*pi + phi_y*y",
        ])

        irf = model.simulate(
            parameters={"beta": 0.99, "kappa": 0.1, "sigma": 1.0,
                        "phi_pi": 1.5, "phi_y": 0.5,
                        "rho_d": 0.8, "rho_u": 0.8},
            shocks={"e_d": 0.01},
            T=40,
        )
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, laws: List[str]):
        # ---- basic format checks ----
        validate_lhs(laws)
        validate_shock_names(laws)

        # ---- infer symbol roles ----
        variables, shocks, noise, parameters = infer_symbols(laws)
        validate_equation_count(laws, variables, shocks)

        # ---- linearity check ----
        validate_linearity(laws, variables + shocks)

        # Ensure every shock has a corresponding e_* noise input, even when
        # the AR(1) equation was not written explicitly (auto-generated).
        noise_set = set(noise)
        for s in shocks:
            e = 'e_' + s[4:]   # eps_d -> e_d
            if e not in noise_set:
                noise.append(e)
                noise_set.add(e)

        # ---- store internals ----
        self._laws       = laws
        self._variables  = variables   # non-shock endogenous vars
        self._shocks     = shocks      # eps_* shock processes
        self._noise      = noise       # e_* white noise inputs
        self._parameters = parameters  # inferred parameter names

        # Build YAML (stored for inspection and debugging)
        self._yaml = build_yaml(
            list(variables), list(shocks), list(noise), list(parameters), laws
        )

        # Detect forward-looking variables for BK reporting
        self._n_forward = count_forward_looking(laws)

    # ------------------------------------------------------------------
    # Public read-only properties
    # ------------------------------------------------------------------

    @property
    def variables(self) -> List[str]:
        """Endogenous non-shock variables (e.g. ``['y', 'pi', 'r']``)."""
        return list(self._variables)

    @property
    def shocks(self) -> List[str]:
        """
        Shock-process variables (``eps_*``).
        Each is driven by a white-noise input ``e_*``.
        """
        return list(self._shocks)

    @property
    def parameters(self) -> List[str]:
        """
        Parameter names that must be supplied by the user at simulation time.
        """
        return list(self._parameters)

    @property
    def yaml(self) -> str:
        """The econpizza YAML string generated from the model equations."""
        return self._yaml

    # ------------------------------------------------------------------
    # BK condition check
    # ------------------------------------------------------------------

    def check_blanchard_kahn(self, parameters: Dict[str, float]) -> None:
        """
        Verify the Blanchard-Kahn order condition for determinacy.

        The model has a unique stable rational-expectations equilibrium if and
        only if the number of eigenvalues of the system matrix outside the unit
        circle equals the number of forward-looking (non-predetermined)
        variables.

        Parameters
        ----------
        parameters : dict[str, float]
            Numeric values for every parameter returned by ``self.parameters``.

        Raises
        ------
        ValueError
            If any required parameter is missing.
        RuntimeError
            If the BK condition is *not* satisfied, with a plain-English
            description of whether the model is explosive or indeterminate.

        Notes
        -----
        This method does nothing (returns ``None``) if BK is satisfied.
        """
        self._load_model(parameters, verbose=False)
        n_unstable, eigs = bk_check(self._mod, self._last_pars)

        n_forward = self._n_forward
        if n_unstable == n_forward:
            return  # BK satisfied — silent

        if n_unstable > n_forward:
            raise RuntimeError(
                f"Blanchard–Kahn condition FAILED: the model is EXPLOSIVE.\n"
                f"  Forward-looking variables : {n_forward}\n"
                f"  Unstable eigenvalues      : {n_unstable}\n\n"
                "There are more explosive directions than forward-looking "
                "variables, so no stable path back to steady state exists.\n"
                "Common causes: a Taylor-rule coefficient on inflation below "
                "1.0 (the 'Taylor principle' requires φ_π > 1), or a "
                "mis-specified equation that introduces spurious instability."
            )
        else:
            raise RuntimeError(
                f"Blanchard–Kahn condition FAILED: the model is INDETERMINATE.\n"
                f"  Forward-looking variables : {n_forward}\n"
                f"  Unstable eigenvalues      : {n_unstable}\n\n"
                "There are fewer explosive directions than forward-looking "
                "variables, so multiple equilibrium paths exist and the model "
                "does not make unique predictions.\n"
                "Common causes: passive monetary policy (φ_π < 1), or "
                "a missing equation for one of the forward-looking variables."
            )

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate(
        self,
        parameters:    Dict[str, float],
        shocks:        Optional[Dict[str, float]] = None,
        init_state:    Optional[Dict[str, float]] = None,
        T:             int = 40,
        yaml_path:     Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Simulate the model's transition back to steady state and return
        impulse-response paths as a DataFrame.

        The model is always solved at the given parameters; if the Blanchard-
        Kahn condition is not satisfied an error is raised before any
        simulation is attempted.

        Parameters
        ----------
        parameters : dict[str, float]
            Numeric values for every parameter in ``self.parameters``.
            All parameters must be provided; no defaults are assumed.
        shocks : dict[str, float], optional
            White-noise shocks to apply in period 0, as a mapping from noise
            input name to size (e.g. ``{"e_d": 0.01, "e_u": -0.005}``).
            Defaults to no shock.
        init_state : dict[str, float], optional
            Initial deviations from steady state for any subset of variables
            (e.g. ``{"y": 0.02}`` starts output 2% above normal).
            Variables not listed default to their steady-state value of zero.
            Defaults to the steady state for all variables.
        T : int, optional
            Number of periods to return (excluding the initial period 0).
            Defaults to 40.
        yaml_path : str, optional
            If provided, the generated econpizza YAML is written to this path
            for inspection.  If ``None`` a temporary file is used and deleted
            after the run.

        Returns
        -------
        pd.DataFrame
            A DataFrame with ``T + 1`` rows (periods 0 … T) and one column
            per endogenous variable (variables and shock processes).
            Values are **deviations from steady state** (which is zero by
            construction for a log-linearised model).

        Raises
        ------
        ValueError
            If a required parameter is missing, an unknown shock or variable
            name is supplied, or the solver fails to converge.
        RuntimeError
            If the Blanchard-Kahn condition is not satisfied.
        """
        # ---- validate and load ----
        self._load_model(parameters, verbose=False, yaml_path=yaml_path)

        # ---- BK check ----
        self.check_blanchard_kahn(parameters)

        # ---- build shock tuple(s) ----
        shocks = shocks or {}
        noise_names = self._noise  # e.g. ['e_d', 'e_u']
        unknown_shocks = set(shocks) - set(noise_names)
        if unknown_shocks:
            raise ValueError(
                f"Unknown shock name(s): {sorted(unknown_shocks)}.\n"
                f"Available white-noise inputs: {noise_names}."
            )

        # econpizza accepts a single (name, size) tuple or applies no shock
        # We handle multiple shocks by applying them one at a time and
        # superimposing via linearity (valid for log-linearised models).
        # For a single shock we pass it directly.
        shock_arg = None
        if len(shocks) == 1:
            shock_arg = next(iter(shocks.items()))   # (name, size)
        elif len(shocks) > 1:
            shock_arg = list(shocks.items())         # list of (name, size) — handled below

        # ---- build init_state array ----
        var_names  = self._mod['var_names']  # alphabetically sorted by econpizza
        stst_arr   = np.array(list(self._mod['stst'].values()))  # all zeros
        init_arr   = stst_arr.copy()

        if init_state:
            unknown_vars = set(init_state) - set(var_names)
            if unknown_vars:
                raise ValueError(
                    f"Unknown variable(s) in init_state: {sorted(unknown_vars)}.\n"
                    f"Available variables: {var_names}."
                )
            for vname, val in init_state.items():
                idx = var_names.index(vname)
                init_arr[idx] = val

        # ---- run solver ----
        horizon = max(T + 1, 100)  # econpizza needs enough horizon to converge

        if isinstance(shock_arg, list):
            # Multiple simultaneous shocks: superimpose via linearity
            x_total = np.zeros((horizon + 1, len(var_names)))
            for shk_name, shk_size in shock_arg:
                x_single, flag = self._mod.find_path(
                    shock=      (shk_name, shk_size),
                    init_state= init_arr,
                    pars=       self._last_pars,
                    horizon=    horizon,
                    verbose=    False,
                )
                if flag[0]:
                    raise ValueError(
                        "The econpizza solver did not converge.  "
                        "Try adjusting the parameter values or reducing "
                        "the shock size."
                    )
                x_total += np.array(x_single)
            # init_state was added once per shock — subtract extras
            x_total -= (len(shock_arg) - 1) * stst_arr[None, :]
        else:
            x_raw, flag = self._mod.find_path(
                shock=      shock_arg,
                init_state= init_arr,
                pars=       self._last_pars,
                horizon=    horizon,
                verbose=    False,
            )
            if flag[0]:
                raise ValueError(
                    "The econpizza solver did not converge.  "
                    "Try adjusting the parameter values or reducing "
                    "the shock size."
                )
            x_total = np.array(x_raw)

        # ---- package results ----
        # Deviations from steady state (= x itself since stst = 0 everywhere)
        deviations = x_total[:T + 1, :]

        df = pd.DataFrame(deviations, columns=var_names)
        df.index.name = 'period'
        return df

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_parameters(self, parameters: Dict[str, float]) -> None:
        """Raise ValueError if any required parameter is missing."""
        missing = [p for p in self._parameters if p not in parameters]
        if missing:
            raise ValueError(
                f"Missing parameter value(s): {missing}.\n"
                f"All of the following must be provided: {self._parameters}."
            )

    def _load_model(
        self,
        parameters: Dict[str, float],
        verbose:    bool = False,
        yaml_path:  Optional[str] = None,
    ) -> None:
        """
        Write the YAML, load it with econpizza, and solve the steady state.

        The loaded model and resolved parameter dict are cached on ``self``
        so that ``check_blanchard_kahn`` and ``simulate`` share the same
        compiled model.

        Parameters
        ----------
        parameters : dict[str, float]
            User-supplied parameter values.
        verbose : bool
            Passed to econpizza's loader and steady-state solver.
        yaml_path : str, optional
            If given, write the YAML here; otherwise use a temporary file.
        """
        import econpizza as ep

        self._validate_parameters(parameters)

        # ---- write YAML ----
        if yaml_path is not None:
            with open(yaml_path, 'w') as fh:
                fh.write(self._yaml)
            mod = ep.load(yaml_path, verbose=verbose)
        else:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.yaml', delete=False
            )
            try:
                tmp.write(self._yaml)
                tmp.close()
                mod = ep.load(tmp.name, verbose=verbose)
            finally:
                os.unlink(tmp.name)

        mod.solve_stst(verbose=verbose)

        # Inject parameter values (fixed_paras in YAML does not propagate
        # reliably to the pars dict used by the Jacobian routines)
        mod['pars'].update(parameters)

        self._mod       = mod
        self._last_pars = dict(parameters)