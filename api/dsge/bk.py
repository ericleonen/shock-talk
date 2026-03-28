import jax
import jax.numpy as jnp
import numpy as np
from typing import List, Tuple
from .symbols import F_RE, to_pizza

# ---------------------------------------------------------------------------
# Blanchard–Kahn check
# ---------------------------------------------------------------------------

def count_forward_looking(laws: List[str]) -> int:
    """
    Count jump (non-predetermined) variables for the BK order condition.

    A variable is a jump variable if it appears as ``F[x]`` anywhere in the
    system — meaning its period-0 value is a free choice that selects the
    stable saddle path.  Variables that only appear with lags or not at all
    in forward terms (e.g. a no-smoothing Taylor rule ``r = phi_pi*pi + ...``)
    are not jump variables and do not count.

    The BK order condition requires exactly this many eigenvalues of the
    system matrix to lie outside the unit circle.

    Parameters
    ----------
    laws : list[str]
        Raw equation strings in user syntax.

    Returns
    -------
    int
        Number of jump variables.
    """
    forward: set[str] = set()
    for law in laws:
        forward.update(F_RE.findall(law))
    return len(forward)


def bk_check(mod, parameters: dict) -> Tuple[int, np.ndarray]:
    """
    Perform a Blanchard–Kahn determinacy check via generalised eigenvalues.

    The number of eigenvalues of the pencil ``(-B, A)`` that lie outside the
    unit circle must equal the number of jump variables (those appearing as
    ``F[x]``) for the model to have a unique stable equilibrium.

    Parameters
    ----------
    mod : econpizza.PizzaModel
        Loaded and steady-state-solved econpizza model.
    parameters : dict
        Mapping from parameter name to numeric value.

    Returns
    -------
    n_unstable : int
        Number of eigenvalues outside the unit circle.
    finite_eigs : np.ndarray
        Array of finite generalised eigenvalues (for diagnostics).
    """
    from scipy.linalg import eig as scipy_eig

    func = mod['context']['func_eqns']
    par  = jnp.array([parameters[p] for p in mod['par_names']])
    stst = jnp.array(list(mod['stst'].values()))
    zero_shocks = jnp.zeros(len(mod.get('shocks') or []))

    # Jacobians: A = df/dX_{t+1},  B = df/dX_t
    A = np.array(jax.jacfwd(
        lambda xp: func(stst, stst, xp, stst, par, zero_shocks)
    )(stst))
    B = np.array(jax.jacfwd(
        lambda x: func(stst, x, stst, stst, par, zero_shocks)
    )(stst))

    # Generalised eigenvalues of the pencil (-B, A):
    # eigenvalue λ satisfies  -B v = λ A v
    eigs = scipy_eig(-B, A, right=False)
    finite_eigs = eigs[np.isfinite(eigs)]
    n_unstable  = int(np.sum(np.abs(finite_eigs) > 1 + 1e-8))
    return n_unstable, finite_eigs