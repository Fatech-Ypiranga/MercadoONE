import sqlite3
from repositories.product_repository import ProductRepository
from repositories.category_repository import CategoryRepository
from services.exceptions import ValidationError, ResourceNotFoundException, BusinessRuleException

class ProductService:

    @staticmethod
    def create_product(conn: sqlite3.Connection, name: str, description: str, price: float, category_id: int) -> int:
        cursor = conn.cursor()
        
        # 1. Validações de Campos
        if not name or not name.strip():
            raise ValidationError("O nome do produto não pode ser vazio.")
        if price <= 0:
            raise ValidationError("O preço do produto deve ser maior que zero.")
            
        # 2. Verificar se a categoria existe
        category = CategoryRepository.find_by_id(cursor, category_id)
        if not category:
            raise ResourceNotFoundException(f"Categoria com ID {category_id} não existe.")
        
        # 3. Persistência
        try:
            product_id = ProductRepository.create(cursor, name, description, price, category_id)
            conn.commit()
            return product_id
        except Exception as e:
            conn.rollback()
            raise BusinessRuleException(f"Erro ao salvar produto: {e}")

    @staticmethod
    def update_product(conn: sqlite3.Connection, product_id: int, name: str, description: str, price: float, category_id: int) -> None:
        cursor = conn.cursor()
        
        # Validações básicas
        if price <= 0:
            raise ValidationError("O preço deve ser maior que zero.")
            
        # Verificar existência do produto
        if not ProductRepository.find_by_id(cursor, product_id):
            raise ResourceNotFoundException(f"Produto com ID {product_id} não encontrado.")
            
        # Verificar existência da categoria
        if not CategoryRepository.find_by_id(cursor, category_id):
            raise ResourceNotFoundException(f"Categoria com ID {category_id} não existe.")
            
        try:
            ProductRepository.update(cursor, product_id, name, description, price, category_id)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise BusinessRuleException(f"Erro ao atualizar produto: {e}")