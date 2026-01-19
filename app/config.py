"""Configurações da aplicação."""
import os
from typing import Dict, Type


class Config:
    """Configuração base."""
    
    # Aplicação
    APP_NAME = os.getenv('APP_NAME', 'notificador-iof-mg')
    APP_ENV = os.getenv('APP_ENV', 'development')
    CLIENT_URL = os.getenv('CLIENT_URL', 'http://localhost:5173')
    DIARIOS_DIR = os.getenv('DIARIOS_DIR', 'diarios')
    
    # Segurança
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Banco de Dados
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///local.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # IOF
    IOF_USERNAME = os.getenv('IOF_USERNAME', '')
    IOF_PASSWORD = os.getenv('IOF_PASSWORD', '')
    
    # Email
    MAIL_SERVER = os.getenv('MAIL_SMTP_HOST', '')
    MAIL_PORT = int(os.getenv('MAIL_SMTP_PORT', '587'))
    # Para Gmail na porta 587, TLS é obrigatório
    # Se MAIL_USE_TLS não estiver definido, inferir baseado na porta
    mail_port_str = os.getenv('MAIL_SMTP_PORT', '587')
    mail_host = os.getenv('MAIL_SMTP_HOST', '').lower()
    
    # Gmail sempre requer TLS na porta 587
    if 'gmail' in mail_host and mail_port_str == '587':
        default_use_tls = True
    elif mail_port_str in ('587', '25'):
        default_use_tls = True
    elif mail_port_str == '465':
        default_use_tls = False  # Porta 465 usa SSL, não TLS
    else:
        default_use_tls = False
    
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', '').lower()
    if MAIL_USE_TLS == '':
        MAIL_USE_TLS = default_use_tls
    else:
        MAIL_USE_TLS = MAIL_USE_TLS == 'true'
    
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_SMTP_USER', '')
    MAIL_PASSWORD = os.getenv('MAIL_SMTP_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_FROM_ADDRESS', 'noreply@example.com')
    
    # Redis (para RQ)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configuração para produção."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Configuração para testes."""
    DEBUG = True
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'


# Mapeamento de nomes de configuração para classes
config_by_name: Dict[str, Type[Config]] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

