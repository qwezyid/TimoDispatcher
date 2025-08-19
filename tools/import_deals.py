# import_deals.py — импорт CSV в PostgreSQL
import argparse, json, re, sys
import chardet
import pandas as pd
import psycopg2

def detect_encoding(path):
    with open(path, 'rb') as f:
        raw = f.read(1000000)
        enc = chardet.detect(raw)['encoding'] or 'utf-8'
        return enc

def read_csv_any(path):
    enc = detect_encoding(path)
    for sep in [None, ';', ',']:
        try:
            df = pd.read_csv(path, sep=sep, engine='python', encoding=enc)
            if len(df.columns) > 1:
                return df
        except Exception:
            continue
    raise RuntimeError('Не удалось прочитать CSV. Сохраните в UTF-8 с ; или ,')

def find_col(cols, candidates):
    cl = {c.lower().strip(): c for c in cols}
    for name in candidates:
        if name.lower() in cl:
            return cl[name.lower()]
    for c in cols:
        lo = c.lower()
        if any(x.lower() in lo for x in candidates):
            return c
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='PostgreSQL URL')
    ap.add_argument('--csv', required=True, help='Path to CSV')
    args = ap.parse_args()

    df = read_csv_any(args.csv)
    cols = list(df.columns)
    
    col_from = find_col(cols, ['Откуда полный', 'Откуда', 'origin', 'город отправления'])
    col_to = find_col(cols, ['Куда полный', 'Куда', 'destination', 'город назначения'])
    col_fio = find_col(cols, ['ФИО', 'fullname', 'ФИО клиента', 'контактное лицо'])
    col_phone = find_col(cols, ['Номер телефона', 'телефон', 'тел.', 'phone'])
    col_cost = find_col(cols, ['СЕБЕСТОИМОСТЬ МАРШРУТА', 'Стоимость', 'Цена', 'Итоговая цена'])
    col_route = find_col(cols, ['Маршрут', 'Путь', 'трек'])
    
    miss = [k for k, v in {
        'from': col_from, 'to': col_to, 'fio': col_fio, 'phone': col_phone
    }.items() if v is None]
    
    if miss:
        print('Не найдены обязательные колонки:', miss, file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(args.db)
    conn.autocommit = False
    cur = conn.cursor()
    
    # ensure helper functions exist
    cur.execute("""
        CREATE OR REPLACE FUNCTION norm_text(t TEXT) RETURNS TEXT AS $$
        BEGIN RETURN trim(regexp_replace(lower(coalesce(t,'')), '\s+', ' ', 'g')); END; $$ LANGUAGE plpgsql IMMUTABLE;
        
        CREATE OR REPLACE FUNCTION norm_phone(t TEXT) RETURNS TEXT AS $$
        BEGIN RETURN regexp_replace(coalesce(t,''), '\D', '', 'g'); END; $$ LANGUAGE plpgsql IMMUTABLE;
        
        CREATE OR REPLACE FUNCTION ensure_city(t TEXT) RETURNS INT AS $$
        DECLARE nn TEXT := norm_text(t); cid INT;
        BEGIN
          IF nn = '' THEN RETURN NULL; END IF;
          SELECT c.city_id INTO cid FROM city_aliases a JOIN cities c ON c.city_id = a.city_id WHERE a.alias_norm = nn;
          IF cid IS NOT NULL THEN RETURN cid; END IF;
          SELECT city_id INTO cid FROM cities WHERE name_norm = nn;
          IF cid IS NOT NULL THEN RETURN cid; END IF;
          INSERT INTO cities(name_norm, name_display) VALUES (nn, initcap(nn)) RETURNING city_id INTO cid;
          INSERT INTO city_aliases(alias_norm, city_id) VALUES (nn, cid) ON CONFLICT DO NOTHING;
          RETURN cid;
        END; $$ LANGUAGE plpgsql;
        
        CREATE OR REPLACE FUNCTION ensure_performer(p_fio TEXT, p_phone TEXT) RETURNS INT AS $$
        DECLARE nn TEXT := right(norm_phone(p_phone), 11); pid INT;
        BEGIN
          IF coalesce(p_fio,'') = '' OR coalesce(nn,'') = '' THEN RETURN NULL; END IF;
          SELECT performer_id INTO pid FROM performers WHERE phone_norm = nn AND fio = p_fio;
          IF pid IS NOT NULL THEN UPDATE performers SET updated_at = now() WHERE performer_id = pid; RETURN pid; END IF;
          INSERT INTO performers(fio, phone_norm) VALUES (p_fio, nn) RETURNING performer_id INTO pid;
          RETURN pid;
        END; $$ LANGUAGE plpgsql;
    """)
    conn.commit()
    
    inserted = 0
    for _, r in df.iterrows():
        from_name = str(r.get(col_from, '') or '').strip()
        to_name = str(r.get(col_to, '') or '').strip()
        fio = str(r.get(col_fio, '') or '').strip()
        phone = str(r.get(col_phone, '') or '').strip()
        
        if not (from_name and to_name and fio and phone):
            continue
            
        route_str = str(r.get(col_route, '') or '')
        cost_raw = str(r.get(col_cost, '') or '').replace(' ', '').replace(',', '.')
        try:
            cost = float(cost_raw) if cost_raw else 0.0
        except:
            cost = 0.0
            
        cur.execute("SELECT ensure_city(%s), ensure_city(%s)", (from_name, to_name))
        cf, ct = cur.fetchone()
        
        cur.execute("SELECT ensure_performer(%s,%s)", (fio, phone))
        (pid,) = cur.fetchone()
        
        cur.execute(
            """INSERT INTO deals(performer_id, city_from, city_to, cost_rub, payload)
               VALUES (%s,%s,%s,%s,%s)""",
            (pid, cf, ct, cost, json.dumps({'route_str': route_str}))
        )
        inserted += 1
        
        if inserted % 1000 == 0:
            conn.commit()
    
    conn.commit()
    print(f'Inserted deals: {inserted}')

if __name__ == '__main__':
    main() 