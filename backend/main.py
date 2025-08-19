import os, json
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

# ---- ENV
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
CORS_REGEX = os.getenv("CORS_REGEX")  # например: https://.*\.vercel\.app$

# ---- APP
app = FastAPI(title="Dispatcher API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else [],
    allow_origin_regex=CORS_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ---- MODELS
class SearchRequest(BaseModel):
    from_city: int
    to_city: int
    mode: str = "exact"

class DealPatch(BaseModel):
    status: Optional[str] = None
    cost_rub: Optional[float] = None
    payload: Optional[dict] = None

class Performer(BaseModel):
    fio: str
    phone_norm: str
    geo_zone: Optional[str] = ""
    note: Optional[str] = ""

class RouteVariant(BaseModel):
    name: Optional[str] = ""
    stops: List[int]

# ---- ROUTES
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/cities")
def search_cities(q: str = "", limit: int = 50):
    sql = """
      SELECT city_id, name_display
      FROM cities
      WHERE name_norm ILIKE %(q)s OR name_display ILIKE %(q)s
      ORDER BY name_display
      LIMIT %(l)s
    """
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"q": f"%{q}%", "l": limit})
        return cur.fetchall()

@app.post("/search")
def search_performers(params: SearchRequest):
    """
    exact   — первый город варианта = from_city и последний = to_city (или наоборот).
    partial — вариант проходит через оба города и позиция(from) < позиция(to).
    """
    a = params.from_city
    b = params.to_city

    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        if params.mode == "exact":
            # Находим старт/финиш каждого варианта по min(position)/max(position)
            sql = """
            WITH first_pos AS (
              SELECT r1.variant_id, r1.city_id AS start_city
              FROM route_variant_positions r1
              JOIN (
                SELECT variant_id, MIN(position) AS min_pos
                FROM route_variant_positions
                GROUP BY variant_id
              ) s ON s.variant_id = r1.variant_id AND s.min_pos = r1.position
            ),
            last_pos AS (
              SELECT r2.variant_id, r2.city_id AS end_city
              FROM route_variant_positions r2
              JOIN (
                SELECT variant_id, MAX(position) AS max_pos
                FROM route_variant_positions
                GROUP BY variant_id
              ) e ON e.variant_id = r2.variant_id AND e.max_pos = r2.position
            )
            SELECT DISTINCT
              p.performer_id,
              p.fio,
              p.phone_norm,
              pv.variant_id
            FROM performers p
            JOIN performer_variants pv ON pv.performer_id = p.performer_id
            JOIN first_pos f ON f.variant_id = pv.variant_id
            JOIN last_pos  t ON t.variant_id = pv.variant_id
            WHERE (f.start_city = %(a)s AND t.end_city = %(b)s)
               OR (f.start_city = %(b)s AND t.end_city = %(a)s)
            ORDER BY p.fio, pv.variant_id;
            """
            cur.execute(sql, {"a": a, "b": b})

        else:
            # В варианте есть обе точки, причём позиция(from) < позиция(to)
            sql = """
            SELECT DISTINCT
              p.performer_id,
              p.fio,
              p.phone_norm,
              pv.variant_id
            FROM performers p
            JOIN performer_variants pv ON pv.performer_id = p.performer_id
            JOIN route_variant_positions f
              ON f.variant_id = pv.variant_id AND f.city_id = %(a)s
            JOIN route_variant_positions t
              ON t.variant_id = pv.variant_id AND t.city_id = %(b)s
            WHERE f.position < t.position
            ORDER BY p.fio, pv.variant_id;
            """
            cur.execute(sql, {"a": a, "b": b})

        return cur.fetchall()

@app.get("/deals")
def deals(limit: int = 100, offset: int = 0, performer_id: Optional[int] = None):
    # добавлен джоин к cities для имён городов
    base = """
      SELECT
        d.deal_id,
        d.created_at,
        d.city_from,
        cf.name_display AS city_from_name,
        d.city_to,
        ct.name_display AS city_to_name,
        d.cost_rub,
        d.performer_id,
        d.status,
        d.payload
      FROM deals d
      LEFT JOIN cities cf ON cf.city_id = d.city_from
      LEFT JOIN cities ct ON ct.city_id = d.city_to
    """
    where = ""
    args = {"l": limit, "o": offset}
    if performer_id:
        where = "WHERE d.performer_id = %(pid)s"
        args["pid"] = performer_id
    q = f"{base} {where} ORDER BY d.created_at DESC, d.deal_id DESC LIMIT %(l)s OFFSET %(o)s"
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, args)
        return cur.fetchall()

@app.patch("/deals/{deal_id}")
def update_deal(deal_id: int, body: DealPatch):
    sets, params = [], {"id": deal_id}
    if body.status is not None:
        sets.append("status=%(status)s"); params["status"] = body.status
    if body.cost_rub is not None:
        sets.append("cost_rub=%(cost)s"); params["cost"] = body.cost_rub
    if body.payload is not None:
        sets.append("payload=%(payload)s"); params["payload"] = json.dumps(body.payload)
    if not sets:
        raise HTTPException(400, "Nothing to update")
    sql = f"UPDATE deals SET {', '.join(sets)} WHERE deal_id=%(id)s RETURNING *"
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        c.commit()
        return row

# ---- Performers CRUD
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

# ---- Route Variants
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
        cur.execute("SELECT rebuild_variant_positions(%s)", (row["variant_id"],))
        c.commit()
        return row

@app.put("/route-variants/{variant_id}")
def update_route_variant(variant_id: int, rv: RouteVariant):
    sql = "UPDATE route_variants SET name=%(name)s, stops=%(stops)s WHERE variant_id=%(id)s RETURNING *"
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
        cur.execute("DELETE FROM performer_variants WHERE performer_id=%s AND variant_id=%s", (performer_id, variant_id))
        c.commit()
        return {"ok": True}



