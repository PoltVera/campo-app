from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import psycopg2
import os
from datetime import date

app = FastAPI()

# Manejar CORS manualmente
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

def get_con():
    return psycopg2.connect(
        host="ep-frosty-butterfly-ai2vgwrp.c-4.us-east-1.aws.neon.tech",
        dbname="neondb",
        user="neondb_owner",
        password=os.getenv("DB_PASSWORD"),
        port=5432,
        sslmode="require"
    )

class RegistroTrampa(BaseModel):
    fecha: date
    lugar: str
    lote: Optional[str] = None
    tipo_trampa: str
    machos_ceratitis: int = 0
    hembras_ceratitis: int = 0
    machos_anastrepha: int = 0
    hembras_anastrepha: int = 0
    coordenadas_lat: Optional[float] = None
    coordenadas_lon: Optional[float] = None
    observacion: Optional[str] = None

@app.get("/")
def inicio():
    return {"mensaje": "Campo App API funcionando"}

@app.post("/registro")
def guardar_registro(data: RegistroTrampa):
    try:
        con = get_con()
        cur = con.cursor()

        cur.execute(
            "SELECT COALESCE(MAX(numero_trampa), 0) + 1 FROM trampas_moscas WHERE lugar = %s AND fecha = %s",
            (data.lugar, data.fecha)
        )
        numero_trampa = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO trampas_moscas 
            (fecha, lugar, lote, tipo_trampa, numero_trampa, 
             machos_ceratitis, hembras_ceratitis, 
             machos_anastrepha, hembras_anastrepha,
             coordenadas_lat, coordenadas_lon, observacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.fecha, data.lugar, data.lote, data.tipo_trampa, numero_trampa,
            data.machos_ceratitis, data.hembras_ceratitis,
            data.machos_anastrepha, data.hembras_anastrepha,
            data.coordenadas_lat, data.coordenadas_lon, data.observacion
        ))

        con.commit()
        cur.close()
        con.close()

        return {"mensaje": "Registro guardado", "numero_trampa": numero_trampa}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/trampas/{lugar}")
def contar_trampas(lugar: str):
    con = get_con()
    cur = con.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM trampas_moscas WHERE lugar = %s AND fecha = CURRENT_DATE",
        (lugar,)
    )
    total = cur.fetchone()[0]
    cur.close()
    con.close()
    return {"lugar": lugar, "total_trampas_hoy": total}