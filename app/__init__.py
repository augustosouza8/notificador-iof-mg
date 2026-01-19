"""Factory pattern para criação da aplicação Flask."""
from flask import Flask
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


def create_app(config_name: str | None = None) -> Flask:
    """
    Factory function para criar e configurar a aplicação Flask.
    
    Args:
        config_name: Nome da configuração ('development', 'production', etc.)
                    Se None, usa APP_ENV da variável de ambiente.
    
    Returns:
        Instância configurada da aplicação Flask.
    """
    app = Flask(__name__)
    
    # Importar configuração
    from app.config import config_by_name
    
    # Determinar ambiente
    import os
    env = config_name or os.getenv('APP_ENV', 'development')
    app.config.from_object(config_by_name[env])
    
    # Inicializar extensões
    from app.extensions import db, mail
    db.init_app(app)
    mail.init_app(app)
    
    # Registrar blueprints
    from app.api import search_config, features
    app.register_blueprint(search_config.bp)
    app.register_blueprint(features.bp)
    
    # Registrar blueprint web (HTML)
    from app.web import routes as web_routes
    app.register_blueprint(web_routes.bp)
    
    return app

