# Guia Completo de Deploy na Azure

Este documento contém instruções detalhadas para todas as fases do deploy na Azure.

## FASE 1: Preparação do Docker ✅

**Status**: Concluída

Arquivos criados:
- `Dockerfile` - Imagem Docker com Python 3.13, poppler-utils, Gunicorn
- `.dockerignore` - Otimização do build
- `gunicorn_config.py` - Configuração do servidor WSGI
- `entrypoint.sh` - Script de inicialização
- `wsgi.py` - Entry point WSGI
- `app/api/tasks.py` - API protegida para processamento
- `DOCKER.md` - Guia de teste local

**Próximo passo**: Testar localmente seguindo `DOCKER.md`

---

## FASE 2: Infraestrutura na Azure

### 2.1. Criar Resource Group

**Via Portal:**
1. Acesse https://portal.azure.com
2. Clique em "Resource groups"
3. Clique em "Create"
4. Nome: `rg-notificador-iof-mg` (ou outro nome)
5. Região: Escolha uma região próxima (ex: `Brazil South`)
6. Clique em "Review + create" → "Create"

**Via CLI:**
```bash
az group create \
  --name rg-notificador-iof-mg \
  --location brazilsouth
```

### 2.2. Criar Storage Account e File Share

**Via Portal:**
1. No Resource Group, clique em "Create"
2. Busque "Storage account"
3. Clique em "Create"
4. Configurações:
   - **Subscription**: Sua assinatura
   - **Resource group**: `rg-notificador-iof-mg`
   - **Storage account name**: `stnotificadoriofmg` (deve ser único globalmente)
   - **Region**: Mesma do Resource Group
   - **Performance**: Standard
   - **Redundancy**: LRS (Locally-redundant storage)
5. Clique em "Review + create" → "Create"

**Criar File Share:**
1. Abra o Storage Account criado
2. No menu lateral, vá em "Data storage" → "File shares"
3. Clique em "+ File share"
4. Nome: `diarios-data`
5. Quota: 10 GB (ou mais, conforme necessário)
6. Clique em "Create"

**Via CLI:**
```bash
# Criar Storage Account
az storage account create \
  --name stnotificadoriofmg \
  --resource-group rg-notificador-iof-mg \
  --location brazilsouth \
  --sku Standard_LRS

# Criar File Share
az storage share create \
  --name diarios-data \
  --account-name stnotificadoriofmg \
  --quota 10
```

### 2.3. Criar Azure Container Registry (ACR)

**Via Portal:**
1. No Resource Group, clique em "Create"
2. Busque "Container Registry"
3. Clique em "Create"
4. Configurações:
   - **Registry name**: `acrnotificadoriofmg` (deve ser único, apenas minúsculas e números)
   - **Resource group**: `rg-notificador-iof-mg`
   - **Location**: Mesma do Resource Group
   - **SKU**: Basic (suficiente para começar)
5. Clique em "Review + create" → "Create"

**Via CLI:**
```bash
az acr create \
  --resource-group rg-notificador-iof-mg \
  --name acrnotificadoriofmg \
  --sku Basic \
  --admin-enabled true
```

**Obter credenciais do ACR:**
```bash
az acr credential show --name acrnotificadoriofmg
```

### 2.4. Criar App Service Plan

**Via Portal:**
1. No Resource Group, clique em "Create"
2. Busque "App Service Plan"
3. Clique em "Create"
4. Configurações:
   - **Name**: `asp-notificador-iof-mg`
   - **Resource group**: `rg-notificador-iof-mg`
   - **Operating System**: Linux
   - **Region**: Mesma do Resource Group
   - **Pricing tier**: Basic B1 (ou Standard S1 para produção)
5. Clique em "Review + create" → "Create"

**Via CLI:**
```bash
az appservice plan create \
  --name asp-notificador-iof-mg \
  --resource-group rg-notificador-iof-mg \
  --is-linux \
  --sku B1
```

### 2.5. Criar Web App for Containers

**Via Portal:**
1. No Resource Group, clique em "Create"
2. Busque "Web App"
3. Clique em "Create"
4. Configurações:
   - **Name**: `notificador-iof-mg` (deve ser único, será `notificador-iof-mg.azurewebsites.net`)
   - **Publish**: Docker Container
   - **Operating System**: Linux
   - **Region**: Mesma do Resource Group
   - **App Service Plan**: `asp-notificador-iof-mg`
5. Clique em "Next: Docker"
6. **Docker**:
   - **Options**: Azure Container Registry
   - **Registry**: `acrnotificadoriofmg`
   - **Image**: `notificador-iof-mg:latest` (será configurado depois)
   - **Tag**: `a`
7. Clique em "Review + create" → "Create"

**Via CLI:**
```bash
az webapp create \
  --name notificador-iof-mg \
  --resource-group rg-notificador-iof-mg \
  --plan asp-notificador-iof-mg \
  --deployment-container-image-name acrnotificadoriofmg.azurecr.io/notificador-iof-mg:latest
```

### 2.6. Configurar Variáveis de Ambiente

**Via Portal:**
1. Abra o Web App criado
2. No menu lateral, vá em "Configuration" → "Application settings"
3. Clique em "+ New application setting"
4. Adicione todas as variáveis do seu `.env`:
   - `APP_ENV` = `production`
   - `SECRET_KEY` = (gere uma chave forte)
   - `API_KEY` = (gere um token forte)
   - `DATABASE_URL` = `sqlite:///local.db`
   - `DIARIOS_DIR` = `diarios`
   - `IOF_USERNAME` = (seu usuário)
   - `IOF_PASSWORD` = (sua senha)
   - `MAIL_SMTP_HOST` = (seu servidor SMTP)
   - `MAIL_SMTP_PORT` = `587`
   - `MAIL_USE_TLS` = `true`
   - `MAIL_SMTP_USER` = (seu usuário email)
   - `MAIL_SMTP_PASSWORD` = (sua senha email)
   - `MAIL_FROM_ADDRESS` = (seu email)
   - `PORT` = `8000`
5. Clique em "Save"

**Via CLI:**
```bash
az webapp config appsettings set \
  --resource-group rg-notificador-iof-mg \
  --name notificador-iof-mg \
  --settings \
    APP_ENV=production \
    SECRET_KEY="sua-chave-secreta" \
    API_KEY="seu-token-api" \
    DATABASE_URL="sqlite:///local.db" \
    DIARIOS_DIR="diarios" \
    PORT=8000
```

**Gerar SECRET_KEY e API_KEY:**
```python
import secrets
print("SECRET_KEY:", secrets.token_urlsafe(32))
print("API_KEY:", secrets.token_urlsafe(32))
```

### 2.7. Configurar Persistent Storage (CRÍTICO)

**Via Portal:**
1. No Web App, vá em "Configuration" → "Path mappings"
2. Clique em "+ New mount path"
3. Configurações:
   - **Name**: `diarios`
   - **Mount path**: `/app/diarios`
   - **Type**: Azure Files
   - **Storage account**: Selecione o Storage Account criado
   - **Storage account access key**: Copie a chave do Storage Account
   - **Share name**: `diarios-data`
4. Clique em "OK"
5. Clique em "Save"

**Obter chave do Storage Account:**
```bash
az storage account keys list \
  --resource-group rg-notificador-iof-mg \
  --account-name stnotificadoriofmg
```

**Via CLI:**
```bash
# Obter connection string
STORAGE_KEY=$(az storage account keys list \
  --resource-group rg-notificador-iof-mg \
  --account-name stnotificadoriofmg \
  --query "[0].value" -o tsv)

# Configurar mount (requer Azure CLI 2.30+)
az webapp config storage-account add \
  --resource-group rg-notificador-iof-mg \
  --name notificador-iof-mg \
  --custom-id diarios \
  --storage-type AzureFiles \
  --share-name diarios-data \
  --account-name stnotificadoriofmg \
  --access-key $STORAGE_KEY \
  --mount-path /app/diarios
```

### 2.8. Deploy Manual da Primeira Imagem

**Build e push local:**
```bash
# Login no ACR
az acr login --name acrnotificadoriofmg

# Build da imagem
docker build -t acrnotificadoriofmg.azurecr.io/notificador-iof-mg:latest .

# Push para ACR
docker push acrnotificadoriofmg.azurecr.io/notificador-iof-mg:latest
```

**Atualizar Web App:**
```bash
az webapp config container set \
  --name notificador-iof-mg \
  --resource-group rg-notificador-iof-mg \
  --docker-custom-image-name acrnotificadoriofmg.azurecr.io/notificador-iof-mg:latest \
  --docker-registry-server-url https://acrnotificadoriofmg.azurecr.io \
  --docker-registry-server-user acrnotificadoriofmg \
  --docker-registry-server-password "SUA_SENHA_ACR"
```

**Reiniciar Web App:**
```bash
az webapp restart \
  --name notificador-iof-mg \
  --resource-group rg-notificador-iof-mg
```

**Verificar logs:**
```bash
az webapp log tail \
  --name notificador-iof-mg \
  --resource-group rg-notificador-iof-mg
```

**Testar aplicação:**
- Interface web: `https://notificador-iof-mg.azurewebsites.net`
- API: `https://notificador-iof-mg.azurewebsites.net/api/features`

---

## FASE 3: CI/CD com GitHub Actions

### 3.1. Criar Service Principal no Azure

```bash
# Substituir pelos seus valores
SUBSCRIPTION_ID="seu-subscription-id"
RESOURCE_GROUP="rg-notificador-iof-mg"
APP_NAME="notificador-iof-mg"

# Criar Service Principal
az ad sp create-for-rbac \
  --name "sp-notificador-iof-mg" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth
```

**Salve a saída JSON** - você precisará dela para configurar os secrets no GitHub.

### 3.2. Configurar Secrets no GitHub

1. Acesse seu repositório no GitHub
2. Vá em "Settings" → "Secrets and variables" → "Actions"
3. Clique em "New repository secret"
4. Adicione os seguintes secrets:

**AZURE_CREDENTIALS** (JSON completo do Service Principal):
```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

**AZURE_WEB_APP_NAME**: `notificador-iof-mg`

**AZURE_RESOURCE_GROUP**: `rg-notificador-iof-mg`

**AZURE_REGISTRY_NAME**: `acrnotificadoriofmg`

### 3.3. Testar CI/CD

1. Faça um commit e push para a branch `main`:
```bash
git add .
git commit -m "Setup CI/CD"
git push origin main
```

2. Acesse "Actions" no GitHub e verifique o workflow

3. Após o deploy, teste a aplicação novamente

---

## FASE 4: Agendamento com Azure Logic Apps

### 4.1. Criar Logic App

**Via Portal:**
1. No Resource Group, clique em "Create"
2. Busque "Logic App"
3. Clique em "Create"
4. Configurações:
   - **Name**: `la-notificador-iof-mg-daily`
   - **Resource group**: `rg-notificador-iof-mg`
   - **Region**: Mesma do Resource Group
   - **Plan type**: Consumption
5. Clique em "Review + create" → "Create"

### 4.2. Configurar Trigger e Ação

1. Abra o Logic App criado
2. Clique em "Logic app designer"
3. Selecione "Blank Logic App"
4. **Adicionar Trigger:**
   - Busque "Recurrence"
   - Configure:
     - **Frequency**: Day
     - **Interval**: 1
     - **At these hours**: 9
     - **At these minutes**: 0
     - **Time zone**: (sua timezone, ex: `(UTC-03:00) Brasilia`)

5. **Adicionar Ação:**
   - Clique em "+ New step"
   - Busque "HTTP"
   - Selecione "HTTP - HTTP"
   - Configure:
     - **Method**: POST
     - **URI**: `https://notificador-iof-mg.azurewebsites.net/api/tasks/process-daily`
     - **Headers**:
       - **Key**: `X-API-Key`
       - **Value**: `@parameters('API_KEY')` (ou o token diretamente)
       - **Key**: `Content-Type`
       - **Value**: `application/json`
     - **Body**: 
       ```json
       {
         "date": "@{formatDateTime(utcNow(), 'yyyy-MM-dd')}"
       }
       ```

6. **Adicionar tratamento de erro (opcional):**
   - Clique em "..." → "Configure run after"
   - Marque "is failed" e "is skipped"
   - Adicione uma ação de notificação (ex: enviar email)

7. Clique em "Save"

### 4.3. Configurar Parâmetro API_KEY

1. No Logic App, vá em "Settings" → "Workflow settings"
2. Em "Parameters", clique em "+ Add parameter"
3. Nome: `API_KEY`
4. Type: `string`
5. Value: Seu token API (ou use Key Vault)
6. Salve

### 4.4. Testar Logic App

1. No Logic App, clique em "Overview"
2. Clique em "Run trigger" → "Recurrence"
3. Verifique a execução em "Runs history"
4. Verifique se o Web App processou o diário

### 4.5. Ativar Agendamento

O Logic App já está configurado para executar diariamente às 09:00. Verifique se está "Enabled" no Overview.

---

## Checklist Final

- [ ] FASE 1: Docker testado localmente
- [ ] FASE 2: Recursos Azure criados
- [ ] FASE 2: Web App funcionando
- [ ] FASE 2: Persistent Storage configurado
- [ ] FASE 3: CI/CD funcionando
- [ ] FASE 4: Logic App criado e testado
- [ ] FASE 4: Agendamento ativo

---

## Troubleshooting

### Web App não inicia
- Verifique logs: `az webapp log tail`
- Verifique variáveis de ambiente
- Verifique se a imagem foi pushada corretamente

### Persistent Storage não funciona
- Verifique se o mount path está correto (`/app/diarios`)
- Verifique permissões do File Share
- Verifique se o Storage Account está acessível

### CI/CD falha
- Verifique secrets no GitHub
- Verifique permissões do Service Principal
- Verifique logs do workflow no GitHub Actions

### Logic App não executa
- Verifique se está "Enabled"
- Verifique timezone do trigger
- Verifique logs de execução
- Teste manualmente primeiro

---

## Custos Estimados (Brasil)

- **App Service Plan (Basic B1)**: ~R$ 50-70/mês
- **ACR (Basic)**: ~R$ 20-30/mês
- **Storage Account (Standard LRS)**: ~R$ 5-10/mês (10 GB)
- **Logic Apps (Consumption)**: ~R$ 1-5/mês (execução diária)
- **Total estimado**: ~R$ 80-120/mês

*Valores aproximados, podem variar conforme uso e região*
