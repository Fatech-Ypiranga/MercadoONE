import unittest
import sqlite3
import os
from database.connection import DatabaseConnection, DB_PATH

class TestDatabaseIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Roda uma vez antes de TODOS os testes começarem. Garante que as tabelas existem."""
        DatabaseConnection.run_migrations()

    def setUp(self):
        """Roda ANTES de CADA teste. Limpa as tabelas para garantir isolamento."""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            # Desativa temporariamente as FKs para poder limpar as tabelas sem erros de ordem
            conn.execute("PRAGMA foreign_keys = OFF;")
            cursor.execute("DELETE FROM itens_venda;")
            cursor.execute("DELETE FROM vendas;")
            cursor.execute("DELETE FROM produtos;")
            cursor.execute("DELETE FROM usuarios;")
            cursor.execute("DELETE FROM clientes;")
            cursor.execute("DELETE FROM fornecedores;")
            conn.execute("PRAGMA foreign_keys = ON;")

    def test_insercao_usuario_valido(self):
        """Garante que dados válidos são inseridos sem gerar exceções."""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha, cargo) VALUES (?, ?, ?, ?);",
                ("Carlos Oliveira", "carlos@email.com", "senha123", "Atendente")
            )
            
            # Valida se o registro realmente foi parar no banco
            cursor.execute("SELECT * FROM usuarios WHERE email = ?;", ("carlos@email.com",))
            usuario = cursor.fetchone()
            
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario['nome'], "Carlos Oliveira")
        self.assertEqual(usuario['cargo'], "Atendente")

    def test_violacao_constraint_check_cargo(self):
        """Garante que o banco bloqueia cargos que não estão no CHECK."""
        with self.assertRaises(sqlite3.IntegrityError) as contexto:
            with DatabaseConnection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO usuarios (nome, email, senha, cargo) VALUES (?, ?, ?, ?);",
                    ("Lucas", "lucas@email.com", "123", "Estagiario")  # Cargo inválido
                )
        # Verifica se a mensagem de erro do SQLite menciona a falha no CHECK
        self.assertIn("CHECK constraint failed", str(contexto.exception))

    def test_violacao_chave_estrangeira_produto(self):
        """Garante que o banco bloqueia produtos com fornecedor_id inexistente."""
        with self.assertRaises(sqlite3.IntegrityError) as contexto:
            with DatabaseConnection.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO produtos (nome, preco_venda, estoque_atual, fornecedor_id) VALUES (?, ?, ?, ?);",
                    ("Mouse Gamer", 150.0, 5, 999)  # Fornecedor 999 não existe
                )
        self.assertIn("FOREIGN KEY constraint failed", str(contexto.exception))

if __name__ == "__main__":
    unittest.main()