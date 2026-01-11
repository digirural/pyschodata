import sqlite3

def upgrade_db():
    conn = sqlite3.connect('cash_collection.db')
    c = conn.cursor()
    
    # Check if 'role' column exists in 'users' table
    try:
        c.execute('SELECT role FROM users LIMIT 1')
    except sqlite3.OperationalError:
        print("Adding 'role' column to users table...")
        c.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "agent"')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade_db()
    print("Database schema upgraded successfully.")
