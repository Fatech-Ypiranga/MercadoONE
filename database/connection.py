import sqlite3
import os
from contextlib import contextmanager

# Define caminhos dinâmicos para evitar erros de localização de arquivos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'sistema.db')
MIGRATION_PATH = os.path.join(BASE_DIR, 'database', 'migrations', '001_initial.sql')

class DatabaseConnection:
    
    @staticmethod
    @contextmanager
    def get_connection():
        """
        Gerenciador de Contexto para conexão com o SQLite.
        Garante que a conexão seja aberta, utilizada e fechada com segurança.
        """
        # Conecta ao arquivo do banco de dados (será criado se não existir)
        conn = sqlite3.connect(DB_PATH)
        
        # IMPORTANTE: Ativa o suporte a Chaves Estrangeiras nesta conexão
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Permite acessar colunas pelo nome (ex: linha['nome']) em vez de apenas índices numéricos
        conn.row_factory = sqlite3.Row 
        
        try:
            # O 'yield' passa o controle da conexão para o bloco 'with' que chamou esta função
            yield conn
            
            # Se nenhuma exceção acontecer dentro do 'with', as alterações são salvas definitivamente
            conn.commit()
        except sqlite3.Error as e:
            # Se acontecer QUALQUER erro de banco de dados, desfaz tudo o que foi feito na sessão (Rollback)
            conn.rollback()
            print(f"[Erro no Banco]: Alterações descartadas. Detalhes: {e}")
            raise e
        finally:
            # Independentemente de ter dado certo ou errado, fecha a conexão para liberar memória/arquivo
            conn.close()

    @classmethod
    def run_migrations(cls):
        """Lê o arquivo SQL inicial e aplica a estrutura das tabelas no banco."""
        if not os.path.exists(MIGRATION_PATH):
            print(f"Erro: Arquivo de migration não encontrado em: {MIGRATION_PATH}")
            return

        print("Lendo script de migração inicial...")
        with open(MIGRATION_PATH, 'r', encoding='utf-8') as arquivo_sql:
            script_sql = arquivo_sql.read()

        print("Aplicando estrutura no banco de dados...")
        with cls.get_connection() as conn:
            # executescript roda múltiplos comandos SQL separados por ';' de uma única vez
            conn.executescript(script_sql)
        print("Banco de dados configurado e tabelas criadas com sucesso!")