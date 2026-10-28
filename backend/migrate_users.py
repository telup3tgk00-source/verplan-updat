import sqlite3

def run():
    conn = sqlite3.connect('pln_kwh.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN unit_penugasan VARCHAR(200)")
        print("Added 'unit_penugasan' column to 'users' table.")
    except sqlite3.OperationalError as e:
        print(f"Skipping 'unit_penugasan': {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run()
