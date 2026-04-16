import sqlite3

c = sqlite3.connect('rate.db')
c.execute('PRAGMA foreign_keys = ON')
c.execute('DELETE FROM reservations')  # d'abord les enfants
c.execute('DELETE FROM rooms')          # ensuite les parents
try:
    c.execute('DELETE FROM sqlite_sequence WHERE name IN ("rooms", "reservations")')
except:
    pass  # sqlite_sequence n'existe pas encore si jamais rien n'a été inséré
c.commit()
c.close()
print('✅ Tables vidées + IDs reset')