from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.persistencia.base import Conflicto, Invalido, MotorNoDisponible, NoEncontrado

app = FastAPI(
    title="Pasaporte BA",
    description="API con persistencia polimórfica: MySQL o HBase según el header X-Motor.",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

_ESTADOS = {NoEncontrado: 404, Conflicto: 409, Invalido: 422, MotorNoDisponible: 503}


def _manejador(estado: int):
    async def manejar(request: Request, exc: Exception):
        p = getattr(request.state, "persistencia", None)
        return JSONResponse(status_code=estado, content={
            "error": str(exc),
            "meta": p.meta() if p else None,
        })
    return manejar


for excepcion, estado in _ESTADOS.items():
    app.add_exception_handler(excepcion, _manejador(estado))
