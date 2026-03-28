import re
from typing import Tuple, List

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

F_RE   = re.compile(r'F\[(\w+)\]')   # F[x]  → forward expectation
L_RE   = re.compile(r'L\[(\w+)\]')   # L[x]  → one-period lag
SYM_RE = re.compile(r'[A-Za-z_]\w*') # all identifiers


def to_pizza(expr: str) -> str:
    """
    Translate user-syntax expression to econpizza notation.

    * ``F[x]`` → ``xPrime``
    * ``L[x]`` → ``xLag``
    """
    expr = F_RE.sub(lambda m: m.group(1) + 'Prime', expr)
    expr = L_RE.sub(lambda m: m.group(1) + 'Lag',   expr)
    return expr


def all_identifiers(text: str) -> set[str]:
    """Return every identifier token in *text* (after F/L substitution)."""
    return set(SYM_RE.findall(to_pizza(text)))


# ---------------------------------------------------------------------------
# Symbol inference
# ---------------------------------------------------------------------------

def infer_symbols(laws: List[str]) -> Tuple[
    List[str], List[str], List[str], List[str]
]:
    """
    Infer variables, shock processes, white-noise inputs, and parameters from
    the list of equation strings.

    Returns
    -------
    variables : list[str]
        Non-shock endogenous variables, in original encounter order.
    shocks : list[str]
        Shock-process variables (``eps_*``), in encounter order.
    noise : list[str]
        White-noise inputs (``e_*``), one per shock, in encounter order.
    parameters : list[str]
        Everything else, in encounter order.  For any shock that does not
        have an explicit AR(1) equation in ``laws``, the corresponding
        ``rho_*`` persistence parameter is automatically included here so
        that the user is required to supply it at simulation time.
    """
    lhs_set:   set[str] = set()
    base_set:  set[str] = set()  # base names inferred from Prime/Lag forms
    all_syms:  set[str] = set()

    for law in laws:
        pizza = to_pizza(law)
        lhs, _ = pizza.split('=', 1)
        lhs_set.add(lhs.strip())
        ids = set(SYM_RE.findall(pizza))
        all_syms |= ids

        for s in ids:
            if s.endswith('Prime'):
                base_set.add(s[:-5])
            elif s.endswith('Lag'):
                base_set.add(s[:-3])
            elif s.startswith('eps_'):
                # Bare eps_* on a RHS counts as an endogenous shock process
                # even if the user never wrote an explicit AR(1) equation for it.
                base_set.add(s)

    base_vars = lhs_set | base_set

    # Preserve encounter order (deterministic, reproducible)
    _seen: dict[str, None] = {}
    for law in laws:
        pizza = to_pizza(law)
        lhs, _ = pizza.split('=', 1)
        _seen.setdefault(lhs.strip(), None)
        for s in SYM_RE.findall(pizza):
            if s.endswith('Prime'):
                _seen.setdefault(s[:-5], None)
            elif s.endswith('Lag'):
                _seen.setdefault(s[:-3], None)
            elif s in base_vars:
                _seen.setdefault(s, None)

    ordered_base = list(_seen.keys())
    shocks    = [v for v in ordered_base if v.startswith('eps_')]
    variables = [v for v in ordered_base if not v.startswith('eps_')]

    noise_ordered: dict[str, None] = {}
    for law in laws:
        for s in SYM_RE.findall(to_pizza(law)):
            if s.startswith('e_') and not s.endswith('Prime') and not s.endswith('Lag'):
                noise_ordered.setdefault(s, None)
    noise = list(noise_ordered.keys())

    dynamic_forms: set[str] = set()
    for v in ordered_base:
        dynamic_forms |= {v, v + 'Prime', v + 'Lag'}

    param_ordered: dict[str, None] = {}
    for law in laws:
        for s in SYM_RE.findall(to_pizza(law)):
            if (s not in dynamic_forms
                    and s not in noise_ordered
                    and s != 'e'):        # 'e' from scientific notation
                param_ordered.setdefault(s, None)

    # For every shock whose AR(1) process is auto-generated (i.e. the shock
    # does not appear on any LHS), the rho_* persistence parameter will be
    # written into the YAML by build_yaml but would otherwise be invisible to
    # _validate_parameters and mod['pars'].update().  Add them here so they
    # are treated as required parameters from the user's perspective.
    for shock in shocks:
        if shock not in lhs_set:
            rho_par = 'rho_' + shock[4:]   # eps_d → rho_d
            param_ordered.setdefault(rho_par, None)

    parameters = list(param_ordered.keys())

    return variables, shocks, noise, parameters