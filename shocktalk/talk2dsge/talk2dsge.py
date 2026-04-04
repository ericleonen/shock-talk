"""
talk2dsge.py
------------
Translates a natural-language list of DSGE model assumptions into ShockTalk
equations and suggested parameter values by calling an LLM via the OpenAI SDK.

The OpenAI SDK is compatible with many providers (OpenAI, Azure, Groq, etc.)
by swapping the `base_url` and `api_key` arguments on the client.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_TEMPLATE_FILE = "prompt.j2"
_EXAMPLES_FILE = _HERE / "examples.yaml"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_examples() -> list[dict[str, Any]]:
    with open(_EXAMPLES_FILE) as f:
        return yaml.safe_load(f)


def _render_prompt(nl_prompt: str) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_HERE)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # tojson is built into Jinja2's default environment; no extra filter needed.
    template = env.get_template(_TEMPLATE_FILE)
    return template.render(
        examples=_load_examples(),
        nl_prompt=nl_prompt,
    )


def _validate_result(result: dict[str, Any]) -> str | None:
    """
    Run all ShockTalk syntax checks on a parsed LLM result.

    Returns an error message string if validation fails, or ``None`` if the
    result is valid.
    """
    if "equations" not in result or "parameters" not in result:
        missing = [k for k in ("equations", "parameters") if k not in result]
        return (
            f"The JSON response is missing required key(s): {missing}.\n"
            "Your response must be a JSON object with exactly the keys "
            "'equations' (list of strings) and 'parameters' (object of floats)."
        )

    from dsge import DSGE
    try:
        model = DSGE(result["equations"])
    except ValueError as exc:
        return str(exc)

    provided = set(result["parameters"].keys())
    required = set(model.parameters)
    missing  = required - provided
    extra    = provided - required

    if missing or extra:
        lines = []
        if missing:
            lines.append(f"Missing parameter(s): {sorted(missing)}")
            # Call out auto-generated shock persistence params specifically,
            # since the LLM may not realise they are required when no explicit
            # AR(1) equation was written for the shock.
            auto_rho = sorted(p for p in missing if re.match(r'^rho_\w+$', p))
            if auto_rho:
                shock_names = ['eps_' + p[4:] for p in auto_rho]
                lines.append(
                    f"Note: {auto_rho} are persistence parameters for the "
                    f"auto-generated AR(1) equations of {shock_names}. "
                    "Add them to 'parameters' with a value in [0, 1)."
                )
        if extra:
            lines.append(f"Unexpected parameter(s): {sorted(extra)}")
        lines.append(f"Required parameters: {sorted(required)}")
        return (
            "The 'parameters' object does not match the model's inferred parameters.\n"
            + "\n".join(lines)
            + "\nEnsure every parameter that appears in the equations is assigned a value, "
            "and no extra parameters are included."
        )

    return None


def _retry_message(error: str, attempt: int, max_retries: int) -> str:
    return (
        f"Your response contains ShockTalk syntax errors "
        f"(attempt {attempt} of {max_retries + 1}). "
        f"Please fix the errors below and return a corrected JSON object.\n\n"
        f"Errors:\n{error}\n\n"
        "Return only the corrected JSON object, nothing else."
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def talk2dsge(
    nl_prompt: str,
    *,
    model: str = "gpt-5.4-mini",
    api_key: str | None = None,
    client: OpenAI | None = None,
    temperature: float = 0.2,
    max_retries: int = 0,
    return_invalid: bool = False,
) -> dict[str, Any]:
    """
    Translate a natural-language description of DSGE model assumptions into
    ShockTalk equations and default parameter values.

    Parameters
    ----------
    nl_prompt : str
        A natural-language description of the model assumptions (bullet points
        or prose).
    model : str, optional
        LLM model identifier understood by the OpenAI-compatible client.
        Defaults to ``"gpt-4o"``.
    api_key : str, optional
        API key for the OpenAI-compatible client. Defaults to the
        ``OPENAI_API_KEY`` environment variable. Ignored if ``client`` is
        provided.
    client : openai.OpenAI, optional
        A pre-configured OpenAI (or compatible) client. If ``None``, a default
        client is constructed using ``api_key``.
    temperature : float, optional
        Sampling temperature. Low values (0.0–0.3) produce more deterministic,
        structured output. Defaults to 0.2.
    max_retries : int, optional
        Number of additional attempts to make if the LLM output fails
        ShockTalk syntax validation. On each retry the bad output and the
        specific error are appended to the conversation so the LLM can
        self-correct. Defaults to 0 (no retries).
    return_invalid : bool, optional
        If ``True``, return the last attempt's result even if it failed
        validation, instead of raising a ``ValueError``. Defaults to ``False``.

    Returns
    -------
    dict
        A dictionary with two keys:

        ``"laws"`` : list[str]
            ShockTalk equation strings, one per endogenous variable.
        ``"parameters"`` : dict[str, float]
            Suggested default parameter values.

    Raises
    ------
    ValueError
        If all attempts fail validation, with a summary of every attempt's
        error.
    """
    if client is None:
        client = OpenAI(api_key=api_key if api_key is not None else os.environ["OPENAI_API_KEY"])

    system_prompt = _render_prompt(nl_prompt)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": nl_prompt},
    ]

    errors: list[str] = []
    last_result: dict[str, Any] | None = None

    for attempt in range(1 + max_retries):
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = response.choices[0].message.content

        # Parse JSON
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            error = (
                "The response was not valid JSON. "
                "Return only a raw JSON object — no markdown fences, no prose."
            )
            errors.append(error)
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": _retry_message(error, attempt + 1, max_retries)})
            continue

        # Validate structure + ShockTalk syntax
        error = _validate_result(result)
        if error is None:
            return result

        last_result = result
        errors.append(error)
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": _retry_message(error, attempt + 1, max_retries)})

    # All attempts exhausted
    if return_invalid and last_result is not None:
        return last_result

    attempts_word = "attempt" if 1 + max_retries == 1 else "attempts"
    error_summary = "\n\n".join(
        f"Attempt {i + 1}:\n{e}" for i, e in enumerate(errors)
    )
    raise ValueError(
        f"Could not generate valid ShockTalk equations after "
        f"{1 + max_retries} {attempts_word}.\n\n"
        f"{error_summary}\n\n"
        "Try rephrasing your model assumptions so they describe a log-linear "
        "system, or increase max_retries."
    )
