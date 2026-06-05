from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .facade import LegislativeInitiativeFacade
from .repository import JsonFileInitiativeRepository
from .schemas import (
    CommentCreate,
    InitiativeCreate,
    InitiativeResponse,
    ModificationCreate,
    MessageResponse,
    ResourceCreate,
    SignatureCreate,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPO = JsonFileInitiativeRepository(DATA_DIR / "initiatives.json")
FACADE = LegislativeInitiativeFacade(REPO)

app = FastAPI(title="Voz del Ciudadano", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Voz del Ciudadano"}


@app.get("/api/initiatives")
def list_initiatives():
    return [initiative.to_dict() for initiative in FACADE.list()]


@app.post("/api/initiatives", response_model=MessageResponse)
def create_initiative(payload: InitiativeCreate):
    initiative = FACADE.create_initiative(
        title=payload.title,
        summary=payload.summary,
        collective=payload.collective,
        subject=payload.subject,
        deadline_days=payload.deadline_days,
    )
    return MessageResponse(message="Iniciativa creada", initiative_id=initiative.id, status=initiative.status)


@app.get("/api/initiatives/{initiative_id}")
def get_initiative(initiative_id: str):
    try:
        initiative = FACADE.get(initiative_id)
        return initiative.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/initiatives/{initiative_id}/comments")
def add_comment(initiative_id: str, payload: CommentCreate):
    try:
        initiative = FACADE.add_comment(initiative_id, payload.author, payload.body)
        return MessageResponse(message="Comentario agregado", initiative_id=initiative.id, status=initiative.status)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/initiatives/{initiative_id}/modifications")
def add_modification(initiative_id: str, payload: ModificationCreate):
    try:
        initiative = FACADE.add_modification(initiative_id, payload.author, payload.body)
        return MessageResponse(message="Modificación agregada", initiative_id=initiative.id, status=initiative.status)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/initiatives/{initiative_id}/resources")
def add_resource(initiative_id: str, payload: ResourceCreate):
    try:
        initiative = FACADE.add_resource(initiative_id, payload.name, payload.kind, payload.url, payload.notes)
        return MessageResponse(message="Recurso agregado", initiative_id=initiative.id, status=initiative.status)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/initiatives/{initiative_id}/signatures")
def add_signature(initiative_id: str, payload: SignatureCreate):
    try:
        initiative = FACADE.add_signature(initiative_id, payload.citizen_name, payload.dni, payload.district)
        return MessageResponse(message="Firma registrada", initiative_id=initiative.id, status=initiative.status)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/initiatives/{initiative_id}/freeze")
def freeze(initiative_id: str):
    try:
        initiative = FACADE.freeze(initiative_id)
        return MessageResponse(message="Iniciativa congelada criptográficamente", initiative_id=initiative.id, frozen_hash=initiative.frozen_hash, status=initiative.status)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/initiatives/{initiative_id}/submit")
def submit(initiative_id: str):
    try:
        initiative = FACADE.submit_to_congress(initiative_id)
        return MessageResponse(message="Enviada a la Oficina del Congreso", initiative_id=initiative.id, status=initiative.status)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/reset")
def reset_data():
    REPO.delete_all()
    return {"message": "Datos reiniciados"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
