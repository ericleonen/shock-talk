from typing import List
from .symbols import to_pizza

# ---------------------------------------------------------------------------
# YAML generation
# ---------------------------------------------------------------------------

def build_yaml(
    variables:  List[str],
    shocks:     List[str],
    noise:      List[str],
    parameters: List[str],
    laws:       List[str],
) -> str:
    """
    Construct an econpizza-compatible YAML string for a log-linearised model.

    Steady-state values are fixed to zero for all endogenous quantities
    (valid for log-linearised / deviation-from-steady-state models).
    AR(1) shock processes are auto-generated for any shock that does not
    already have an explicit equation.  The corresponding ``rho_*`` and
    ``e_*`` names are expected to already be present in ``parameters`` and
    ``noise`` respectively — ``infer_symbols`` is responsible for that.

    Parameters
    ----------
    variables : list[str]
        Non-shock endogenous variable names.
    shocks : list[str]
        Shock-process variable names (``eps_*``).
    noise : list[str]
        White-noise input names (``e_*``).
    parameters : list[str]
        Parameter names (including ``rho_*`` for auto-generated shocks).
    laws : list[str]
        User-supplied equation strings (raw syntax).

    Returns
    -------
    str
        Complete econpizza YAML text.
    """
    all_endo = variables + shocks

    # Translate equations to econpizza residual form
    lhs_defined = {law.split('=')[0].strip() for law in laws}
    eq_lines: List[str] = []
    for law in laws:
        pizza_lhs, pizza_rhs = to_pizza(law).split('=', 1)
        eq_lines.append(f"    ~ {pizza_lhs.strip()} - ({pizza_rhs.strip()})")

    # Auto-generate AR(1) processes for shocks not explicitly defined.
    # rho_* and e_* are already in parameters/noise courtesy of infer_symbols.
    for shock in shocks:
        if shock not in lhs_defined:
            suffix  = shock[4:]        # eps_d → d
            rho_par = f'rho_{suffix}'
            e_noise = f'e_{suffix}'
            eq_lines.append(
                f"    ~ {shock} - {rho_par}*{shock}Lag - {e_noise}"
            )

    # YAML sections
    var_str   = ', '.join(all_endo)
    par_str   = ', '.join(parameters)
    shock_str = ', '.join(noise)

    ss_lines = '\n'.join(f'        {v}: 0' for v in all_endo)

    yaml = (
        f"name: dsge_model\n"
        f"\n"
        f"variables: [{var_str}]\n"
        f"parameters: [{par_str}]\n"
        f"shocks: [{shock_str}]\n"
        f"\n"
        f"equations:\n"
        + '\n'.join(eq_lines) + '\n'
        f"\n"
        f"steady_state:\n"
        f"    fixed_values:\n"
        f"{ss_lines}\n"
    )
    return yaml