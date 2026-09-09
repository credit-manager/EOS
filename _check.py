import sys, io, psycopg2
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
conn = psycopg2.connect('postgresql://eos:0100@127.0.0.1:5432/eos_main')
cur = conn.cursor()

# Commerce items columns
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", ('dbp_commerce_items',))
print("=== dbp_commerce_items ===")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")

# Commerce stock columns
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", ('dbp_commerce_stock',))
print("\n=== dbp_commerce_stock ===")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")

conn.close()
