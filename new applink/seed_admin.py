import sqlite3
from werkzeug.security import generate_password_hash

def seed_admin():
    conn = sqlite3.connect('cash_collection.db')
    c = conn.cursor()
    
    # Defaults
    users = [
        ('Admin', '0000000000', 'admin', 'admin123', 'admin'),
        ('Sivakumar Aruchamy', '9876543210', '4819330', 'Jmtdjw24@', 'admin')
    ]
    
    for name, mobile, username, password, role in users:
        hashed_pw = generate_password_hash(password)
        try:
            c.execute('INSERT INTO users (name, mobile, username, password, role) VALUES (?, ?, ?, ?, ?)',
                      (name, mobile, username, hashed_pw, role))
            print(f"Created user: {username} with role: {role}")
        except sqlite3.IntegrityError:
            # Update permissions for existing admins
            print(f"User {username} already exists. Updating role to {role}.")
            c.execute('UPDATE users SET role = ? WHERE username = ?', (role, username))
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_admin()
