"""Motor de busca SQLite FTS5 para documentos do Diário Oficial."""
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import List
from urllib.parse import quote


class Trigger(str, Enum):
    """Tipo de trigger que gerou a busca."""
    BACKTEST = "backtest"
    CRON = "cron"


@dataclass
class Term:
    """Termo de busca."""
    term: str
    exact: bool = False


@dataclass
class Highlight:
    """Destaque encontrado na busca."""
    page: int
    content: str
    term: str
    page_url: str


@dataclass
class Report:
    """Relatório de busca."""
    publish_date: date
    highlights: List[Highlight]
    search_terms: List[Term]
    trigger: Trigger
    count: int


@dataclass
class Pagina:
    """Página do Diário Oficial."""
    titulo: str
    num_pagina: int
    descricao: str
    conteudo: str
    data_publicacao: date


def pagina_url(publish_date: date, page_num: int, notebook_id: int = 326074) -> str:
    """
    Gera o link profundo para uma página específica de uma edição do Diário Oficial.
    
    O link utiliza o novo formato com parâmetro ?dados= contendo um JSON codificado
    que carrega o estado da aplicação diretamente na página correta.
    
    Args:
        publish_date: Data de publicação
        page_num: Número da página
        notebook_id: ID numérico interno da edição (padrão: 326074 para Executivo)
        
    Returns:
        URL da página no formato: https://www.jornalminasgerais.mg.gov.br/edicao-do-dia?dados=...
    """
    date_str = publish_date.strftime("%Y-%m-%d")
    
    # Montagem do dicionário de estado da aplicação
    payload = {
        "dataPublicacaoSelecionada": f"{date_str}T03:00:00.000Z",
        "idCadernoEdicaoSelecionado": notebook_id,
        "paginaSelecionada": page_num
    }
    
    # Conversão para JSON compactado (sem espaços) e URL Encoding
    json_payload = json.dumps(payload, separators=(',', ':'))
    encoded_payload = quote(json_payload)
    
    base_url = "https://www.jornalminasgerais.mg.gov.br/edicao-do-dia?dados="
    return base_url + encoded_payload


class SearchSource:
    """Fonte de dados para busca full-text usando SQLite FTS5."""
    
    def __init__(self, db_path: str):
        """
        Inicializa a fonte de busca.
        
        Args:
            db_path: Caminho para o arquivo SQLite
        """
        self.db_path = db_path
        
        # Configurar pragmas do SQLite
        pragmas = [
            ('busy_timeout', '5000'),
            ('journal_mode', 'WAL'),
            ('synchronous', 'NORMAL'),
            ('foreign_keys', 'ON'),
        ]
        
        # Criar conexão
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=5.0
        )
        self.conn.row_factory = sqlite3.Row
        
        # Aplicar pragmas
        for pragma, value in pragmas:
            self.conn.execute(f"PRAGMA {pragma} = {value}")
        
        # Criar schema
        self._init_schema()
    
    def _init_schema(self):
        """Inicializa o schema do banco de dados."""
        schema_path = Path(__file__).parent / 'schema.sql'
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        self.conn.executescript(schema)
        self.conn.commit()
    
    def import_pages(self, pages: List[Pagina]) -> None:
        """
        Importa páginas para o banco de dados.
        
        Args:
            pages: Lista de páginas para importar
        """
        query = """
        REPLACE INTO documentos (titulo, num_pagina, descricao, conteudo, data_publicacao)
        VALUES (?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.cursor()
        try:
            for page in pages:
                cursor.execute(query, (
                    page.titulo,
                    page.num_pagina,
                    page.descricao,
                    page.conteudo,
                    page.data_publicacao.strftime('%Y-%m-%d')
                ))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
    
    def lookup(
        self,
        trigger: Trigger,
        publish_date: date,
        terms: List[Term]
    ) -> Report:
        """
        Busca termos nos documentos de uma data específica.
        
        Args:
            trigger: Tipo de trigger (backtest ou cron)
            publish_date: Data de publicação
            terms: Lista de termos para buscar
            
        Returns:
            Relatório com os resultados da busca
        """
        highlights: List[Highlight] = []
        date_str = publish_date.strftime('%Y-%m-%d')
        
        for term in terms:
            # Preparar termo para busca FTS5
            search_term = term.term
            if term.exact:
                # Para busca exata, usar aspas
                search_term = f'"{search_term}"'
            
            query = """
            SELECT
                doc.num_pagina,
                snippet(documentos_fts, 0, '<b>', '</b>', '...', 32) AS trecho
            FROM documentos_fts doc_fts
            INNER JOIN documentos doc ON doc_fts.rowid = doc.id
            WHERE doc.data_publicacao = ?
            AND documentos_fts MATCH ?
            """
            
            cursor = self.conn.cursor()
            cursor.execute(query, (date_str, search_term))
            
            for row in cursor.fetchall():
                page_num = row['num_pagina']
                content = row['trecho']
                
                highlights.append(Highlight(
                    page=page_num,
                    content=content,
                    term=term.term,
                    page_url=pagina_url(publish_date, page_num)
                ))
        
        return Report(
            publish_date=publish_date,
            highlights=highlights,
            search_terms=terms,
            trigger=trigger,
            count=len(highlights)
        )
    
    def has_pages(self, publish_date: date) -> bool:
        """
        Verifica se existem páginas importadas para uma data.
        
        Args:
            publish_date: Data de publicação
            
        Returns:
            True se existem páginas, False caso contrário
        """
        query = "SELECT COUNT(*) FROM documentos WHERE data_publicacao = ?"
        date_str = publish_date.strftime('%Y-%m-%d')
        
        cursor = self.conn.cursor()
        cursor.execute(query, (date_str,))
        count = cursor.fetchone()[0]
        
        return count > 0
    
    def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

