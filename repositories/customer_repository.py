import sqlite3

class CustomerRepository:

    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, name, email, phone FROM customers;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, customer_id: int) -> tuple:
        query = "SELECT id, name, email, phone FROM customers WHERE id = ?;"
        cursor.execute(query, (customer_id,))
        return cursor.fetchone()

    @staticmethod
    def find_by_email(cursor: sqlite3.Cursor, email: str) -> tuple:
        query = "SELECT id, name, email, phone FROM customers WHERE email = ?;"
        cursor.execute(query, (email,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor: sqlite3.Cursor, name: str, email: str, phone: str) -> int:
        query = "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?);"
        cursor.execute(query, (name, email, phone))
        return cursor.lastrowid

    @staticmethod
    def update(cursor: sqlite3.Cursor, customer_id: int, name: str, email: str, phone: str) -> bool:
        query = "UPDATE customers SET name = ?, email = ?, phone = ? WHERE id = ?;"
        cursor.execute(query, (name, email, phone, customer_id))
        return cursor.rowcount > 0