import psycopg2
conn = psycopg2.connect('postgresql://eos:eos_secret@localhost:5432/eos_main')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = cur.fetchall()
print(f'Total tables: {len(tables)}')
for t in tables[:10]:
    print(f'  {t[0]}')
cur.close()
conn.close()
" > D:\EOS\Eos final\eos-system\_check_tables.py