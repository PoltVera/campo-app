from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
import os
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    capturas: Optional[dict] = {}
    coordenadas_lat: Optional[float] = None
    coordenadas_lon: Optional[float] = None
    observacion: Optional[str] = None

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "fundomuto2024")

# ─── App principal ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def inicio():
    with open("index.html", "r") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    with open("admin.html", "r") as f:
        return f.read()

# ─── Listas dinámicas ──────────────────────────────────────
@app.get("/lugares")
def get_lugares():
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT nombre FROM lugares WHERE activo = TRUE ORDER BY nombre;")
    lugares = [row[0] for row in cur.fetchall()]
    cur.close(); con.close()
    return {"lugares": lugares}

@app.get("/tipos_trampa")
def get_tipos_trampa():
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT nombre FROM tipos_trampa WHERE activo = TRUE ORDER BY nombre;")
    tipos = [row[0] for row in cur.fetchall()]
    cur.close(); con.close()
    return {"tipos_trampa": tipos}

@app.get("/especies")
def get_especies():
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT nombre FROM especies WHERE activo = TRUE ORDER BY nombre;")
    especies = [row[0] for row in cur.fetchall()]
    cur.close(); con.close()
    return {"especies": especies}

# ─── Registro de trampas ────────────────────────────────────
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

        capturas = data.capturas or {}
        machos_ceratitis  = capturas.get("Ceratitis capitata", {}).get("machos", 0)
        hembras_ceratitis = capturas.get("Ceratitis capitata", {}).get("hembras", 0)
        machos_anastrepha  = capturas.get("Anastrepha spp.", {}).get("machos", 0)
        hembras_anastrepha = capturas.get("Anastrepha spp.", {}).get("hembras", 0)

        cur.execute("""
            INSERT INTO trampas_moscas
            (fecha, lugar, lote, tipo_trampa, numero_trampa,
             machos_ceratitis, hembras_ceratitis,
             machos_anastrepha, hembras_anastrepha,
             coordenadas_lat, coordenadas_lon, observacion)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.fecha, data.lugar, data.lote, data.tipo_trampa, numero_trampa,
            machos_ceratitis, hembras_ceratitis,
            machos_anastrepha, hembras_anastrepha,
            data.coordenadas_lat, data.coordenadas_lon, data.observacion
        ))

        con.commit(); cur.close(); con.close()
        return {"mensaje": "Registro guardado", "numero_trampa": numero_trampa}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── Admin: leer datos ──────────────────────────────────────
@app.get("/admin/datos")
def admin_datos():
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT id, nombre, activo FROM lugares ORDER BY nombre;")
    lugares = [{"id": r[0], "nombre": r[1], "activo": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT id, nombre, activo FROM tipos_trampa ORDER BY nombre;")
    tipos = [{"id": r[0], "nombre": r[1], "activo": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT id, nombre, activo FROM especies ORDER BY nombre;")
    especies = [{"id": r[0], "nombre": r[1], "activo": r[2]} for r in cur.fetchall()]
    cur.close(); con.close()
    return {"lugares": lugares, "tipos_trampa": tipos, "especies": especies}

# ─── Admin: lugares ─────────────────────────────────────────
@app.post("/admin/lugar")
async def agregar_lugar(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO lugares (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING;", (body["nombre"].upper(),))
        con.commit()
        return {"mensaje": "Lugar agregado"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        cur.close(); con.close()

@app.patch("/admin/lugar/{id}")
async def toggle_lugar(id: int, request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    cur.execute("UPDATE lugares SET activo = NOT activo WHERE id = %s;", (id,))
    con.commit(); cur.close(); con.close()
    return {"mensaje": "Actualizado"}

@app.delete("/admin/lugar/{id}")
async def eliminar_lugar(id: int, request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    cur.execute("DELETE FROM lugares WHERE id = %s;", (id,))
    con.commit(); cur.close(); con.close()
    return {"mensaje": "Lugar eliminado"}

# ─── Admin: tipos de trampa ─────────────────────────────────
@app.post("/admin/tipo_trampa")
async def agregar_tipo_trampa(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO tipos_trampa (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING;", (body["nombre"].upper(),))
        con.commit()
        return {"mensaje": "Tipo agregado"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        cur.close(); con.close()

@app.patch("/admin/tipo_trampa/{id}")
async def toggle_tipo_trampa(id: int, request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    cur.execute("UPDATE tipos_trampa SET activo = NOT activo WHERE id = %s;", (id,))
    con.commit(); cur.close(); con.close()
    return {"mensaje": "Actualizado"}

@app.delete("/admin/tipo_trampa/{id}")
async def eliminar_tipo_trampa(id: int, request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    cur.execute("DELETE FROM tipos_trampa WHERE id = %s;", (id,))
    con.commit(); cur.close(); con.close()
    return {"mensaje": "Tipo eliminado"}

# ─── Admin: especies ────────────────────────────────────────
@app.post("/admin/especie")
async def agregar_especie(request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO especies (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING;", (body["nombre"],))
        con.commit()
        return {"mensaje": "Especie agregada"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        cur.close(); con.close()

@app.patch("/admin/especie/{id}")
async def toggle_especie(id: int, request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    cur.execute("UPDATE especies SET activo = NOT activo WHERE id = %s;", (id,))
    con.commit(); cur.close(); con.close()
    return {"mensaje": "Actualizado"}

@app.delete("/admin/especie/{id}")
async def eliminar_especie(id: int, request: Request):
    body = await request.json()
    if body.get("password") != ADMIN_PASSWORD:
        return JSONResponse(status_code=401, content={"error": "Contraseña incorrecta"})
    con = get_con()
    cur = con.cursor()
    cur.execute("DELETE FROM especies WHERE id = %s;", (id,))
    con.commit(); cur.close(); con.close()
    return {"mensaje": "Especie eliminada"}