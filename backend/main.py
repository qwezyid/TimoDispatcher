import os, json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

DATABASE_URL = os.getenv("DATABASE_URL")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI(title="Dispatcher API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/cities")
def search_cities(q: str = "", limit: int = 50):
    sql = """
      SELECT city_id, name_display FROM cities 
      WHERE name_norm ILIKE %(q)s OR name_display ILIKE %(q)s
      ORDER BY name_display LIMIT %(l)s
    """
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"q": f"%{q}%", "l": limit})
        return cur.fetchall()

class SearchRequest(BaseModel):
    from_city: int
    to_city: int
    mode: str = "exact"

@app.post("/search")
def search_performers(params: SearchRequest):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        if params.mode == "exact":
            cur.execute(
                "SELECT * FROM search_performers_exact(%(a)s,%(b)s)",
                {"a": params.from_city, "b": params.to_city},
            )
        else:
            cur.execute(
                "SELECT * FROM search_performers_partial(%(a)s,%(b)s)",
                {"a": params.from_city, "b": params.to_city},
            )
        return cur.fetchall()

@app.get("/deals")
def deals(limit: int = 100, offset: int = 0, performer_id: Optional[int] = None):
    q = "SELECT * FROM deals ORDER BY deal_id DESC LIMIT %(l)s OFFSET %(o)s"
    args = {"l": limit, "o": offset}
    if performer_id:
        q = "SELECT * FROM deals WHERE performer_id=%(pid)s ORDER BY deal_id DESC LIMIT %(l)s OFFSET %(o)s"
        args["pid"] = performer_id
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, args)
        return cur.fetchall()

class DealPatch(BaseModel):
    status: Optional[str] = None
    cost_rub: Optional[float] = None
    payload: Optional[dict] = None

@app.patch("/deals/{deal_id}")
def update_deal(deal_id: int, body: DealPatch):
    sets, params = [], {"id": deal_id}
    if body.status is not None:
        sets.append("status=%(status)s")
        params["status"] = body.status
    if body.cost_rub is not None:
        sets.append("cost_rub=%(cost)s")
        params["cost"] = body.cost_rub
    if body.payload is not None:
        sets.append("payload=%(payload)s")
        params["payload"] = json.dumps(body.payload)
    if not sets:
        raise HTTPException(400, "Nothing to update")
    sql = f"UPDATE deals SET {', '.join(sets)} WHERE deal_id=%(id)s RETURNING *"
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        c.commit()
        return row

# === Дополнительные CRUD (минимальные) ===
from fastapi import Body

class Performer(BaseModel):
    fio: str
    phone_norm: str
    geo_zone: Optional[str] = ""
    note: Optional[str] = ""

@app.get("/performers")
def list_performers(query: Optional[str] = None, limit: int = 50, offset: int = 0):
    where = ""
    params = {"l": limit, "o": offset}
    if query:
        where = "WHERE fio ILIKE %(q)s OR phone_norm ILIKE %(q)s"
        params["q"] = f"%{query}%"
    sql = f"SELECT * FROM performers {where} ORDER BY fio LIMIT %(l)s OFFSET %(o)s"
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()

@app.post("/performers")
def create_performer(p: Performer):
    sql = """
      INSERT INTO performers(fio, phone_norm, geo_zone, note)
      VALUES (%(fio)s, %(phone)s, %(geo)s, %(note)s)
      RETURNING *
    """
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"fio": p.fio, "phone": p.phone_norm, "geo": p.geo_zone or "", "note": p.note or ""})
        row = cur.fetchone()
        c.commit()
        return row

@app.put("/performers/{performer_id}")
def update_performer(performer_id: int, p: Performer):
    sql = """
      UPDATE performers
      SET fio=%(fio)s, phone_norm=%(phone)s, geo_zone=%(geo)s, note=%(note)s
      WHERE performer_id=%(id)s
      RETURNING *
    """
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"fio": p.fio, "phone": p.phone_norm, "geo": p.geo_zone or "", "note": p.note or "", "id": performer_id})
        row = cur.fetchone()
        c.commit()
        return row

class RouteVariant(BaseModel):
    name: Optional[str] = ""
    stops: list[int]

@app.get("/route-variants")
def list_route_variants(limit: int = 50, offset: int = 0):
    sql = "SELECT * FROM route_variants ORDER BY variant_id DESC LIMIT %(l)s OFFSET %(o)s"
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"l": limit, "o": offset})
        return cur.fetchall()

@app.post("/route-variants")
def create_route_variant(rv: RouteVariant):
    sql = """
      INSERT INTO route_variants(name, stops)
      VALUES (%(name)s, %(stops)s)
      RETURNING *
    """
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"name": rv.name or "", "stops": rv.stops})
        row = cur.fetchone()
        # пересоберём позиции
        cur.execute("SELECT rebuild_variant_positions(%s)", (row["variant_id"],))
        c.commit()
        return row

@app.put("/route-variants/{variant_id}")
def update_route_variant(variant_id: int, rv: RouteVariant):
    sql = """
      UPDATE route_variants SET name=%(name)s, stops=%(stops)s WHERE variant_id=%(id)s RETURNING *
    """
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"name": rv.name or "", "stops": rv.stops, "id": variant_id})
        row = cur.fetchone()
        cur.execute("SELECT rebuild_variant_positions(%s)", (variant_id,))
        c.commit()
        return row

@app.post("/performers/{performer_id}/variants")
def attach_variant(performer_id: int, body: dict = Body(...)):
    variant_id = int(body.get("variant_id"))
    with get_conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO performer_variants(performer_id, variant_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (performer_id, variant_id),
        )
        c.commit()
        return {"ok": True}

@app.delete("/performers/{performer_id}/variants/{variant_id}")
def detach_variant(performer_id: int, variant_id: int):
    with get_conn() as c, c.cursor() as cur:
        cur.execute(
            "DELETE FROM performer_variants WHERE performer_id=%s AND variant_id=%s",
            (performer_id, variant_id),
        )
        c.commit()
        return {"ok": True} 