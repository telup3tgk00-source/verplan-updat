import sqlite3

def run():
    conn = sqlite3.connect('pln_kwh.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE verification_records ADD COLUMN unit VARCHAR(50)")
        print("Added 'unit' column.")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'unit': {e}")
        
    try:
        cursor.execute("ALTER TABLE verification_records ADD COLUMN kode_nama_biller VARCHAR(200)")
        print("Added 'kode_nama_biller' column.")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'kode_nama_biller': {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run()
