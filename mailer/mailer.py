"""Cliente de email para envio de notificações."""
from dataclasses import dataclass
from typing import List, Optional
from flask import current_app
from flask_mail import Mail, Message


@dataclass
class Email:
    """Estrutura de email."""
    to: List[str]
    subject: str
    text: str
    html: Optional[str] = None


class Mailer:
    """Cliente para envio de emails."""
    
    def __init__(self, app=None):
        """
        Inicializa o mailer.
        
        Args:
            app: Instância do Flask app (opcional, pode usar current_app)
        """
        self.app = app
        self._mail = None
    
    def _get_mail(self):
        """Obtém a instância do Mail, usando a já inicializada no app se disponível."""
        if self._mail is None:
            from flask import has_app_context, current_app
            app_to_use = self.app if self.app else (current_app if has_app_context() else None)
            
            if app_to_use:
                # Usar a instância já inicializada do mail no app
                from app.extensions import mail
                self._mail = mail
            else:
                raise RuntimeError("Mailer não inicializado. É necessário um contexto de aplicação Flask.")
        
        return self._mail
    
    def send(self, *emails: Email) -> None:
        """
        Envia um ou mais emails.
        
        Args:
            *emails: Emails para enviar
            
        Raises:
            RuntimeError: Se houver erro ao enviar
        """
        mail = self._get_mail()
        
        messages = []
        for email in emails:
            msg = Message(
                subject=email.subject,
                recipients=email.to,
                body=email.text,
                html=email.html
            )
            messages.append(msg)
        
        try:
            with mail.connect() as conn:
                for msg in messages:
                    conn.send(msg)
        except Exception as e:
            raise RuntimeError(f"Erro ao enviar email: {e}") from e
    
    def send_test_email(self, to: str) -> None:
        """
        Envia email de teste.
        
        Args:
            to: Endereço de email de destino
        """
        email = Email(
            to=[to],
            subject="Teste - Notificador IOF MG",
            text="Este é um email de teste do sistema de notificações do Diário Oficial de MG."
        )
        self.send(email)

