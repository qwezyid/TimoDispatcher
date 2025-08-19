-- Расширения
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Города
CREATE TABLE IF NOT EXISTS cities(
  city_id SERIAL PRIMARY KEY,
  name_norm TEXT UNIQUE NOT NULL,
  name_display TEXT NOT NULL
);

-- Псевдонимы городов
CREATE TABLE IF NOT EXISTS city_aliases (
  alias_norm TEXT PRIMARY KEY,
  city_id INT NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS city_aliases_city_id_idx ON city_aliases(city_id);

-- Исполнители
CREATE TABLE IF NOT EXISTS performers (
  performer_id SERIAL PRIMARY KEY,
  fio TEXT NOT NULL,
  phone_norm TEXT NOT NULL,
  geo_zone TEXT DEFAULT '',
  note TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS performers_phone_fio_uidx ON performers(phone_norm, fio);
CREATE INDEX IF NOT EXISTS performers_phone_gin ON performers USING GIN(phone_norm gin_trgm_ops);

-- Варианты маршрутов
CREATE TABLE IF NOT EXISTS route_variants (
  variant_id SERIAL PRIMARY KEY,
  name TEXT DEFAULT '',
  stops INT[] NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT stops_min_two CHECK(cardinality(stops) >= 2)
);

-- Позиции городов в маршруте
CREATE TABLE IF NOT EXISTS route_variant_positions (
  variant_id INT NOT NULL REFERENCES route_variants(variant_id) ON DELETE CASCADE,
  city_id INT NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
  pos INT NOT NULL,
  PRIMARY KEY(variant_id, city_id)
);
CREATE INDEX IF NOT EXISTS rvp_city_variant_pos_idx ON route_variant_positions(city_id, variant_id, pos);

-- Привязка маршрут ↔ исполнитель
CREATE TABLE IF NOT EXISTS performer_variants (
  performer_id INT NOT NULL REFERENCES performers(performer_id) ON DELETE CASCADE,
  variant_id INT NOT NULL REFERENCES route_variants(variant_id) ON DELETE CASCADE,
  PRIMARY KEY(performer_id, variant_id)
);

-- Сделки
CREATE TABLE IF NOT EXISTS deals(
  deal_id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  performer_id INT REFERENCES performers(performer_id),
  city_from INT REFERENCES cities(city_id),
  city_to INT REFERENCES cities(city_id),
  variant_id INT REFERENCES route_variants(variant_id),
  cost_rub NUMERIC(12,2) DEFAULT 0,
  status TEXT DEFAULT 'new',
  payload JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS deals_perf_idx ON deals(performer_id);
CREATE INDEX IF NOT EXISTS deals_route_idx ON deals(city_from, city_to);

-- Журнал аудита
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id BIGSERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  op TEXT NOT NULL,
  pk JSONB,
  old_row JSONB,
  new_row JSONB,
  changed_at TIMESTAMPTZ DEFAULT now(),
  changed_by TEXT DEFAULT current_user,
  txid BIGINT DEFAULT txid_current()
);

-- Нормализация/ensure
CREATE OR REPLACE FUNCTION norm_text(t TEXT) RETURNS TEXT AS $$
BEGIN
  RETURN trim(regexp_replace(lower(coalesce(t,'')), '\s+', ' ', 'g'));
END; $$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION norm_phone(t TEXT) RETURNS TEXT AS $$
BEGIN
  RETURN regexp_replace(coalesce(t,''), '\D', '', 'g');
END; $$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION ensure_city(t TEXT) RETURNS INT AS $$
DECLARE
  nn TEXT := norm_text(t);
  cid INT;
BEGIN
  IF nn = '' THEN RETURN NULL; END IF;
  
  SELECT c.city_id INTO cid
  FROM city_aliases a JOIN cities c ON c.city_id = a.city_id
  WHERE a.alias_norm = nn;
  IF cid IS NOT NULL THEN RETURN cid; END IF;
  
  SELECT city_id INTO cid FROM cities WHERE name_norm = nn;
  IF cid IS NOT NULL THEN RETURN cid; END IF;
  
  INSERT INTO cities(name_norm, name_display) VALUES (nn, initcap(nn))
  RETURNING city_id INTO cid;
  
  INSERT INTO city_aliases(alias_norm, city_id) VALUES (nn, cid) ON CONFLICT DO NOTHING;
  RETURN cid;
END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION ensure_performer(p_fio TEXT, p_phone TEXT) RETURNS INT AS $$
DECLARE
  nn_phone TEXT := right(norm_phone(p_phone), 11);
  pid INT;
BEGIN
  IF coalesce(p_fio,'') = '' OR coalesce(nn_phone,'') = '' THEN RETURN NULL; END IF;
  
  SELECT performer_id INTO pid FROM performers WHERE phone_norm = nn_phone AND fio = p_fio;
  IF pid IS NOT NULL THEN
    UPDATE performers SET updated_at = now() WHERE performer_id = pid;
    RETURN pid;
  END IF;
  
  INSERT INTO performers(fio, phone_norm) VALUES (p_fio, nn_phone) RETURNING performer_id INTO pid;
  RETURN pid;
END; $$ LANGUAGE plpgsql; 