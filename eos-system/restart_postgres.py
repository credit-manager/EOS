#!/usr/bin/env python3
import subprocess
import sys
import os

def main():
    print("=== PostgreSQL Restart Script ===\n")
    
    # Step 1: Kill existing postgres processes
    print("Step 1: Killing existing postgres processes...")
    result = subprocess.run(
        ['taskkill', '/F', '/IM', 'postgres.exe'],
        capture_output=True, text=True
    )
    print(f"  Kill result: {result.returncode}")
    import time
    time.sleep(3)
    
    # Step 2: Check current pg_hba.conf
    print("\nStep 2: Checking pg_hba.conf...")
    pg_ha_path = r'C:\Program Files\PostgreSQL\18\data\pg_hba.conf'
    try:
        with open(pg_ha_path, 'r') as f:
            content = f.read()
        has_trust = 'trust' in content.lower()
        has_scram = 'scram-sha-256' in content.lower()
        print(f"  Current pg_hba.conf has 'trust': {has_trust}")
        print(f"  Current pg_hba.conf has 'scram-sha-256': {has_scram}")
    except FileNotFoundError:
        print(f"  pg_hba.conf not found at {pg_ha_path}")
    
    # Step 3: Try to start PostgreSQL using pg_ctl
    print("\nStep 3: Trying to start PostgreSQL with pg_ctl...")
    try:
        result = subprocess.run(
            [r'C:\Program Files\PostgreSQL\18\bin\pg_ctl', 
             '-D', r'C:\Program Files\PostgreSQL\18\data',
             'start', '-w', '-O', "-c config_file='C:\Program Files\PostgreSQL\18\data\postgresql.conf'"],
            capture_output=True, text=True, timeout=30
        )
        print(f"  pg_ctl stdout: {result.stdout[:200] if result.stdout else 'empty'}")
        print(f"  pg_ctl stderr: {result.stderr[:200] if result.stderr else 'empty'}")
        print(f"  pg_ctl returncode: {result.returncode}")
    except Exception as e:
        print(f"  pg_ctl error: {e}")
    
    # Step 4: Wait and check
    import time
    time.sleep(5)
    
    # Step 5: Try connecting
    print("\nStep 5: Testing database connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost', 
            dbname='eos_main', 
            user='postgres',
            password=''
        )
        cur = conn.cursor()
        cur.execute('SELECT 1')
        print(f"  Connection SUCCESS: {cur.fetchone()}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"  Connection FAILED: {e}")
    
    print("\n=== Script Complete ===")

if __name__ == '__main__':
    main()