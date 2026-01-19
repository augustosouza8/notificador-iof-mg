# Configuração de Email

Este documento explica como configurar o envio de emails no sistema de notificações do Diário Oficial.

## Problema Comum: "Connection refused"

O erro `[Errno 61] Connection refused` ocorre quando o sistema tenta se conectar a um servidor SMTP que não está acessível ou não está rodando.

## Opções de Configuração

### Opção 1: Desenvolvimento Local com MailHog (Recomendado para testes)

MailHog é um servidor SMTP de teste que captura todos os emails enviados e os exibe em uma interface web.

1. **Instalar MailHog:**
   ```bash
   # macOS
   brew install mailhog
   
   # Ou baixar de: https://github.com/mailhog/MailHog/releases
   ```

2. **Iniciar MailHog:**
   ```bash
   mailhog
   ```
   O MailHog estará disponível em:
   - SMTP: `localhost:1025`
   - Interface Web: `http://localhost:8025`

3. **Configurar no arquivo `.env`:**
   ```env
   MAIL_SMTP_HOST=localhost
   MAIL_SMTP_PORT=1025
   MAIL_USE_TLS=false
   MAIL_FROM_ADDRESS=noreply@example.com
   MAIL_SMTP_USER=
   MAIL_SMTP_PASSWORD=
   ```

### Opção 2: Gmail (Produção/Testes Reais)

1. **Criar uma Senha de App no Gmail:**
   - Acesse: https://myaccount.google.com/apppasswords
   - Gere uma senha de app para "Email"

2. **Configurar no arquivo `.env`:**
   ```env
   MAIL_SMTP_HOST=smtp.gmail.com
   MAIL_SMTP_PORT=587
   MAIL_USE_TLS=true
   MAIL_USE_SSL=false
   MAIL_FROM_ADDRESS=seu-email@gmail.com
   MAIL_SMTP_USER=seu-email@gmail.com
   MAIL_SMTP_PASSWORD=sua-senha-de-app-gerada
   ```
   
   **IMPORTANTE:** 
   - `MAIL_USE_TLS=true` é **OBRIGATÓRIO** para Gmail na porta 587
   - `MAIL_USE_SSL=false` (não use SSL na porta 587, apenas TLS)
   - Use uma **Senha de App**, não sua senha normal do Gmail

### Opção 3: SendGrid (Produção)

1. **Criar conta no SendGrid:**
   - Acesse: https://sendgrid.com
   - Crie uma conta e gere uma API Key

2. **Configurar no arquivo `.env`:**
   ```env
   MAIL_SMTP_HOST=smtp.sendgrid.net
   MAIL_SMTP_PORT=587
   MAIL_USE_TLS=true
   MAIL_FROM_ADDRESS=noreply@seudominio.com
   MAIL_SMTP_USER=apikey
   MAIL_SMTP_PASSWORD=sua-api-key-sendgrid
   ```

### Opção 4: Outros Servidores SMTP

Para outros provedores (Outlook, Yahoo, servidor próprio, etc.), consulte a documentação do provedor para obter:
- Host SMTP
- Porta (geralmente 587 para TLS ou 465 para SSL)
- Se requer TLS/SSL
- Credenciais de autenticação

## Variáveis de Ambiente

Todas as configurações devem ser definidas no arquivo `.env` na raiz do projeto:

```env
# Email
MAIL_FROM_ADDRESS=noreply@example.com
MAIL_SMTP_HOST=localhost
MAIL_SMTP_PORT=1025
MAIL_USE_TLS=false
MAIL_USE_SSL=false
MAIL_SMTP_USER=
MAIL_SMTP_PASSWORD=
```

## Verificação

Após configurar, você pode testar o envio de email através do backtest na interface web. Se houver erros, as mensagens de erro agora são mais descritivas e indicam o que verificar.

## Troubleshooting

### Erro: "Connection refused"
- Verifique se o servidor SMTP está rodando (para MailHog, execute `mailhog`)
- Verifique se `MAIL_SMTP_HOST` e `MAIL_SMTP_PORT` estão corretos
- Verifique se há firewall bloqueando a conexão

### Erro: "Authentication failed"
- Verifique se `MAIL_SMTP_USER` e `MAIL_SMTP_PASSWORD` estão corretos
- Para Gmail, certifique-se de usar uma "Senha de App", não sua senha normal
- Para SendGrid, use `apikey` como usuário e sua API Key como senha

### Erro: "Timeout"
- Verifique se o servidor SMTP está acessível
- Verifique sua conexão com a internet
- Alguns provedores podem bloquear conexões de IPs não autorizados
