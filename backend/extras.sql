-- updated_at триггеры
CREATE OR REPLACE FUNCTION trg_touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS performers_touch ON performers;
CREATE TRIGGER performers_touch BEFORE UPDATE ON performers
  FOR EACH ROW EXECUTE FUNCTION trg_touch_updated_at();

DROP TRIGGER IF EXISTS route_variants_touch ON route_variants;
CREATE TRIGGER route_variants_touch BEFORE UPDATE ON route_variants
  FOR EACH ROW EXECUTE FUNCTION trg_touch_updated_at();

DROP TRIGGER IF EXISTS deals_touch ON deals;
CREATE TRIGGER deals_touch BEFORE UPDATE ON deals
  FOR EACH ROW EXECUTE FUNCTION trg_touch_updated_at();

-- Аудит
CREATE OR REPLACE FUNCTION audit_trigger() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO audit_log(table_name, op, pk, old_row, new_row)
    VALUES (TG_TABLE_NAME, TG_OP, NULL, NULL, to_jsonb(NEW));
    RETURN NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO audit_log(table_name, op, pk, old_row, new_row)
    VALUES (TG_TABLE_NAME, TG_OP, NULL, to_jsonb(OLD), to_jsonb(NEW));
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO audit_log(table_name, op, pk, old_row, new_row)
    VALUES (TG_TABLE_NAME, TG_OP, NULL, to_jsonb(OLD), NULL);
    RETURN OLD;
  END IF;
  RETURN NULL;
END; $$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_performers') THEN
    CREATE TRIGGER audit_performers AFTER INSERT OR UPDATE OR DELETE ON performers
      FOR EACH ROW EXECUTE FUNCTION audit_trigger();
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_route_variants') THEN
    CREATE TRIGGER audit_route_variants AFTER INSERT OR UPDATE OR DELETE ON route_variants
      FOR EACH ROW EXECUTE FUNCTION audit_trigger();
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_performer_variants') THEN
    CREATE TRIGGER audit_performer_variants AFTER INSERT OR UPDATE OR DELETE ON performer_variants
      FOR EACH ROW EXECUTE FUNCTION audit_trigger();
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_deals') THEN
    CREATE TRIGGER audit_deals AFTER INSERT OR UPDATE OR DELETE ON deals
      FOR EACH ROW EXECUTE FUNCTION audit_trigger();
  END IF;
END $$;

-- Пересборка позиций маршрута
CREATE OR REPLACE FUNCTION rebuild_variant_positions(p_variant_id INT) RETURNS VOID AS $$
BEGIN
  DELETE FROM route_variant_positions WHERE variant_id = p_variant_id;
  
  INSERT INTO route_variant_positions(variant_id, city_id, pos)
  SELECT p_variant_id, city_id, ord
  FROM unnest((SELECT stops FROM route_variants WHERE variant_id = p_variant_id)) WITH ORDINALITY AS t(city_id, ord);
END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION trg_variants_positions() RETURNS TRIGGER AS $$
BEGIN
  PERFORM rebuild_variant_positions(NEW.variant_id);
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS route_variants_after_insupd ON route_variants;
CREATE TRIGGER route_variants_after_insupd
  AFTER INSERT OR UPDATE OF stops ON route_variants
  FOR EACH ROW EXECUTE FUNCTION trg_variants_positions();

-- Частичный поиск
CREATE OR REPLACE FUNCTION search_performers_partial(from_id INT, to_id INT)
RETURNS TABLE(performer_id INT, fio TEXT, phone_norm TEXT, variant_id INT) AS $$
BEGIN
  RETURN QUERY
  SELECT pf.performer_id, pf.fio, pf.phone_norm, pv.variant_id
  FROM performer_variants pv
  JOIN route_variant_positions a ON a.variant_id = pv.variant_id AND a.city_id IN (from_id, to_id)
  JOIN route_variant_positions b ON b.variant_id = pv.variant_id AND b.city_id IN (from_id, to_id) AND a.city_id <> b.city_id
  JOIN performers pf ON pf.performer_id = pv.performer_id
  WHERE a.pos < b.pos;
END; $$ LANGUAGE plpgsql;

-- Точный поиск
CREATE OR REPLACE FUNCTION search_performers_exact(from_id INT, to_id INT)
RETURNS TABLE(performer_id INT, fio TEXT, phone_norm TEXT, variant_id INT) AS $$
BEGIN
  RETURN QUERY
  WITH exact_variants AS (
    SELECT rv.variant_id
    FROM route_variants rv
    JOIN route_variant_positions p1 ON p1.variant_id = rv.variant_id AND p1.pos = 1
    JOIN route_variant_positions pN ON pN.variant_id = rv.variant_id
    WHERE pN.pos = (SELECT cardinality(stops) FROM route_variants WHERE variant_id = rv.variant_id)
      AND ((p1.city_id = from_id AND pN.city_id = to_id) OR (p1.city_id = to_id AND pN.city_id = from_id))
  )
  SELECT pf.performer_id, pf.fio, pf.phone_norm, pv.variant_id
  FROM performer_variants pv
  JOIN exact_variants ev ON ev.variant_id = pv.variant_id
  JOIN performers pf ON pf.performer_id = pv.performer_id
  ORDER BY pf.fio;
END; $$ LANGUAGE plpgsql; 