-- Temp staging table
DROP TABLE IF EXISTS raw_deals;
CREATE TEMP TABLE raw_deals (
  from_text TEXT,
  to_text TEXT,
  fio TEXT,
  phone TEXT,
  cost TEXT,
  route_str TEXT
);

-- После \copy переложим в deals
WITH normed AS (
  SELECT
    from_text, to_text, fio, phone,
    NULLIF(replace(replace(cost, ' ', ''), ',', '.'), '')::numeric(12,2) AS cost_rub,
    route_str
  FROM raw_deals
  WHERE coalesce(from_text, '') <> '' AND coalesce(to_text, '') <> '' AND coalesce(fio, '') <> '' AND coalesce(phone, '') <> ''
), ids AS (
  SELECT
    ensure_city(from_text) AS cf,
    ensure_city(to_text) AS ct,
    ensure_performer(fio, phone) AS pid,
    cost_rub,
    route_str
  FROM normed
)
INSERT INTO deals(performer_id, city_from, city_to, cost_rub, payload)
SELECT pid, cf, ct, cost_rub, jsonb_build_object('route_str', route_str)
FROM ids
WHERE pid IS NOT NULL AND cf IS NOT NULL AND ct IS NOT NULL; 