-- Нормализация/ensure для импорта через psql/Adminer
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