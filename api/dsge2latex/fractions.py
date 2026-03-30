import re
from sympy import Symbol, sympify, latex as sym_latex


def _convert_fractions(s: str) -> str:
    """Convert a/b and (expr)/b etc. to \\frac{}{} using SymPy."""
    i = 0
    out: list[str] = []

    while i < len(s):
        if s[i] != '/':
            out.append(s[i])
            i += 1
            continue

        # --- extract numerator from what we've already built ---
        while out and out[-1] == ' ':
            out.pop()

        if out and out[-1] == ')':
            depth, k = 0, len(out) - 1
            while k >= 0:
                if out[k] == ')': depth += 1
                elif out[k] == '(': depth -= 1
                if depth == 0: break
                k -= 1
            num = ''.join(out[k + 1:-1])   # strip outer parens
            out = out[:k]
        else:
            k = len(out) - 1
            while k >= 0 and (out[k].isalnum() or out[k] in ('_', '.')):
                k -= 1
            k += 1
            num = ''.join(out[k:])
            out = out[:k]

        while out and out[-1] == ' ':
            out.pop()

        # --- extract denominator from the remaining string ---
        i += 1
        while i < len(s) and s[i] == ' ':
            i += 1

        if i < len(s) and s[i] == '(':
            depth, k = 0, i
            while k < len(s):
                if s[k] == '(': depth += 1
                elif s[k] == ')': depth -= 1
                if depth == 0: break
                k += 1
            denom = s[i + 1:k]   # strip outer parens
            i = k + 1
        else:
            k = i
            while k < len(s) and (s[k].isalnum() or s[k] in ('_', '.')):
                k += 1
            denom = s[i:k]
            i = k
        
        idents = set(re.findall(r'[A-Za-z_]\w*', num + '+' + denom))
        local_syms = {name: Symbol(name) for name in idents}
        frac = sym_latex(sympify(f"({num})/({denom})", locals=local_syms))
        out.extend(frac)

    return ''.join(out)
