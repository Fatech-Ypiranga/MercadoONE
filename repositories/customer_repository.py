import sqlite3

class CustomerRepository:

    @staticmethod
    def find_all(cursor: sqlite3.Cursor) -> list:
        query = "SELECT id, nome, cpf, email, telefone FROM clientes;"
        cursor.execute(query)
        return cursor.fetchall()

    @staticmethod
    def find_by_id(cursor: sqlite3.Cursor, customer_id: int) -> tuple:
        query = "SELECT id, nome, cpf, email, telefone FROM clientes WHERE id = ?;"
        cursor.execute(query, (customer_id,))
        return cursor.fetchone()

    @staticmethod
    def find_by_email(cursor: sqlite3.Cursor, email: str) -> tuple:
        query = "SELECT id, nome, cpf, email, telefone FROM clientes WHERE email = ?;"
        cursor.execute(query, (email,))
        return cursor.fetchone()

    @staticmethod
    def create(cursor: sqlite3.Cursor, nome: str, cpf: str, email: str, telefone: str) -> int:
        query = "INSERT INTO clientes (nome, cpf, email, telefone) VALUES (?, ?, ?, ?);"
        cursor.execute(query, (nome, cpf, email, telefone))
        return cursor.lastrowid

    @staticmethod
    def update(cursor: sqlite3.Cursor, customer_id: int, nome: str, cpf: str, email: str, telefone: str) -> bool:
        query = "UPDATE clientes SET nome = ?, cpf = ?, email = ?, telefone = ? WHERE id = ?;"
        cursor.execute(query, (nome, cpf, email, telefone, customer_id))
        return cursor.rowcount > 0