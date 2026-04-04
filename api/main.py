from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shocktalk import DSGE, talk2dsge, dsge2latex

app = FastAPI(title="ShockTalk API")


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class SimulateRequest(BaseModel):
    laws: list[str]
    parameters: dict[str, float]
    shocks: Optional[dict[str, float]] = None
    T: int = 40


class SimulateResponse(BaseModel):
    data: dict[str, list[float]]


class Talk2DSGERequest(BaseModel):
    prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_retries: int = 2


class Talk2DSGEResponse(BaseModel):
    equations: list[str]
    parameters: dict[str, float]


class DSGE2LatexRequest(BaseModel):
    laws: list[str]


class DSGE2LatexResponse(BaseModel):
    latex: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    try:
        model = DSGE(req.laws)
        irf = model.simulate(
            parameters=req.parameters,
            shocks=req.shocks,
            T=req.T,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return SimulateResponse(data={col: irf[col].tolist() for col in irf.columns})


@app.post("/talk2dsge", response_model=Talk2DSGEResponse)
def nl_to_dsge(req: Talk2DSGERequest):
    try:
        result = talk2dsge(
            req.prompt,
            model=req.model,
            temperature=req.temperature,
            max_retries=req.max_retries,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return Talk2DSGEResponse(
        equations=result["equations"],
        parameters=result["parameters"],
    )


@app.post("/dsge2latex", response_model=DSGE2LatexResponse)
def to_latex(req: DSGE2LatexRequest):
    return DSGE2LatexResponse(latex=dsge2latex(req.laws))
