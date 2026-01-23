# Guia de Deploy & CI/CD na Azure com Containers (App Service + ACR + GitHub Actions OIDC)

**Autor/uso:** material de referência criado a partir do primeiro deploy do projeto *Notificador IOF MG*.

---

## Resumo executivo (leitura rápida)

Este guia ensina, do **zero**, como publicar uma aplicação containerizada na **Azure** usando **Azure App Service (Web App for Containers)** e **Azure Container Registry (ACR)**, e como automatizar o deploy com **GitHub Actions** usando **OIDC (OpenID Connect)** — ou seja, **sem** armazenar credenciais de longa duração no GitHub.

### Mapa do fluxo (visão geral)

```text
┌─────────────────────────┐
│        GitHub Repo       │
│  (código + Dockerfile)   │
└─────────────┬───────────┘
              │ push / tag
              ▼
┌─────────────────────────┐
│      GitHub Actions      │
│  - build imagem Docker   │
│  - push para ACR         │
│  - update WebApp         │
│    (linuxFxVersion)      │
└───────┬─────────┬───────┘
        │         │
        │ OIDC     │ docker push
        ▼         ▼
┌─────────────────┐   ┌──────────────────────┐
│  Microsoft Entra │   │ Azure Container       │
│  (Federated      │   │ Registry (ACR)        │
│  Credential)     │   │ - guarda imagens      │
└─────────┬────────┘   └──────────┬───────────┘
          │ token curto            │ docker pull
          ▼                        ▼
┌──────────────────────────────────────────┐
│ Azure App Service (Web App for Containers)│
│ - puxa imagem do ACR (Managed Identity)   │
│ - expõe HTTPS (WEBSITES_PORT)             │
│ - persiste dados em /home (storage)       │
└──────────────────────────────────────────┘
```

### O que você vai conseguir replicar em qualquer novo projeto
- **Containerizar** sua aplicação (Dockerfile + entrypoint)
- Fazer **build/push** da imagem no **ACR**
- Executar a imagem no **App Service** (configuração de porta e variáveis)
- Configurar **persistência** para apps que gravam em disco (ex.: SQLite) usando **`/home`**
- Configurar **SMTP** (ex.: Gmail com App Password) para envio de e-mails
- Configurar **CI/CD** em dois modos:
  - **CI**: deploy automático em todo *push* no `main`
  - **PROD**: deploy controlado por **tag/release** com **GitHub Environments + approval**

### Componentes e conceitos-chave
- **App Service Plan**: define CPU/RAM e custo (paga-se pelo *plan*, não por app individual).
- **Web App (container)**: executa sua imagem e recebe tráfego HTTP/HTTPS.
- **ACR**: registry privado de imagens.
- **Managed Identity (Web App → ACR)**: o App Service puxa a imagem do ACR sem usuário/senha.
- **OIDC (GitHub Actions → Azure)**: autenticação segura com tokens de curta duração.

> Referências de apoio: OIDC do GitHub para Azure exige `permissions: id-token: write` e configuração de credencial federada (federated credential) no Entra ID. Consulte: Microsoft Learn e GitHub Docs. citeturn19search119turn19search120

---

## Checklist de 5 minutos (novo projeto)

Use este checklist para validar rapidamente se um novo projeto está pronto para seguir o guia completo.

### (1) Projeto & Container
- [ ] Tenho um **Dockerfile** que: define `WORKDIR`, copia o app, instala deps e inicia o servidor.
- [ ] A aplicação escuta em `0.0.0.0` (não em `localhost`).
- [ ] Sei qual é a **porta interna** do container (ex.: 8000).

### (2) App Service (execução)
- [ ] Vou configurar `WEBSITES_PORT=<porta>` no Web App (ex.: `8000`).
- [ ] Logs do app saem em **stdout/stderr** (para o Log Stream).

### (3) Persistência (se usar SQLite/arquivos)
- [ ] Vou usar **`/home`** para dados persistentes (ex.: `/home/instance`, `/home/diarios`).
- [ ] Vou habilitar `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`.
- [ ] `DATABASE_URL` (SQLite) aponta para `sqlite:////home/.../local.db`.

### (4) E-mail (se usar SMTP)
- [ ] Tenho variáveis `MAIL_*` definidas.
- [ ] Se for Gmail, vou usar **App Password** (com 2FA).

### (5) CI/CD
- [ ] Tenho secrets no GitHub: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
- [ ] Meu workflow tem `permissions: id-token: write`.
- [ ] Tenho dois workflows (opcional):
  - [ ] `deploy-ci.yml` (push no `main`)
  - [ ] `deploy-prod.yml` (tags `v*` + environment `production` com approval)

> Dica: depois de configurar tudo, valide com: `az webapp config show --query linuxFxVersion` e um `curl -I` na URL do app.

---

# Guia passo a passo (Azure App Service + ACR + GitHub Actions OIDC)
**Exemplo real: Notificador IOF MG (Flask + Docker + SQLite + SMTP)**

> **Objetivo do guia:** você conseguir repetir o mesmo processo com qualquer app futuro:
> - Containerizar (Dockerfile + entrypoint)
> - Subir no **Azure App Service (Web App for Containers)**
> - Publicar imagens no **Azure Container Registry (ACR)**
> - Configurar variáveis/porta/persistência
> - Habilitar logs e validar
> - Configurar **CI/CD** com **GitHub Actions** usando **OIDC** (sem secrets long-lived)
>
> Referências principais: OIDC GitHub→Azure e Azure Login com OIDC. citeturn19search119turn19search120

---

## Sumário
1. [Conceitos essenciais](#1-conceitos-essenciais)
2. [Checklist antes de deploy](#2-checklist-antes-de-deploy)
3. [Preparando o app para rodar em App Service](#3-preparando-o-app-para-rodar-em-app-service)
4. [Deploy manual (CLI) — do zero](#4-deploy-manual-cli--do-zero)
5. [Persistência com SQLite em /home](#5-persistência-com-sqlite-em-home)
6. [Configurar SMTP (Gmail) de forma segura](#6-configurar-smtp-gmail-de-forma-segura)
7. [Logs e troubleshooting](#7-logs-e-troubleshooting)
8. [CI/CD com GitHub Actions + OIDC (recomendado)](#8-cicd-com-github-actions--oidc-recomendado)
9. [Modo PROD por tag/release + Environments (approval)](#9-modo-prod-por-tagrelease--environments-approval)
10. [Custos estimados e dicas de economia](#10-custos-estimados-e-dicas-de-economia)
11. [Templates reutilizáveis](#11-templates-reutilizáveis)

---

# 1) Conceitos essenciais

## 1.1 O que você está construindo?
Um pipeline de containers:

**Código → Dockerfile → Imagem Docker → ACR → App Service (container)** citeturn12search96turn19search113

## 1.2 App Service Plan x Web App
- **App Service Plan**: capacidade/CPU/RAM (a “máquina”) onde os apps rodam; vários Web Apps podem compartilhar o mesmo plan. citeturn19search132  
- **Web App**: a aplicação em si (neste guia, do tipo “container”). citeturn19search132turn19search113

## 1.3 Por que `WEBSITES_PORT` importa?
Em App Service com **custom container**, o Azure encaminha o tráfego para a porta que seu container escuta. Se não for 80, configure `WEBSITES_PORT`. citeturn19search115turn19search114  

> No exemplo do Notificador, o Gunicorn escuta em **8000**, então usamos `WEBSITES_PORT=8000`. citeturn19search115turn19search114

## 1.4 Persistência em container Linux no App Service: por que `/home`?
Em containers Linux no App Service, a persistência (quando habilitada) fica em **`/home`**. Para apps que escrevem arquivos (ex.: SQLite), use `/home` e habilite `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`. citeturn19search127turn19search128

## 1.5 Identidades: Managed Identity vs OIDC
- **Managed Identity do Web App**: permite o Web App **puxar** a imagem do ACR sem usuário/senha (AcrPull); recomendação atual é usar managed identity para isso. citeturn19search113turn12search86
- **OIDC no GitHub Actions**: permite o workflow autenticar no Azure **sem** secret de longa duração; requer `id-token: write` e **Federated Credential** no Entra ID. citeturn19search120turn19search119

---

# 2) Checklist antes de deploy

## 2.1 Ferramentas locais
- Azure CLI (`az`) funcionando
- Git
- Docker (opcional; você pode usar `az acr build`)

## 2.2 Requisitos do app (regras de ouro)
- App deve escutar em `0.0.0.0` (não em `localhost`)
- Porta configurável via env (`WEBSITES_PORT` e/ou `PORT`) citeturn19search114turn19search115
- Logs em stdout/stderr
- Se usa banco em arquivo (SQLite), gravar em `/home` com storage habilitado citeturn19search127turn19search128

---

# 3) Preparando o app para rodar em App Service

## 3.1 Dockerfile (padrão)
Boas práticas:
- `WORKDIR`
- Instalar dependências
- Expor porta (ex.: 8000)
- Iniciar com Gunicorn (ou equivalente)

*(Em App Service, o `WEBSITES_PORT` deve bater com a porta interna do container.)* citeturn19search115turn19search114

## 3.2 entrypoint.sh (padrão com persistência)
Para apps que geram arquivos/SQLite:
- Criar diretórios em `/home`
- Exportar `DATABASE_URL` e diretórios de dados
- Rodar migrations antes de iniciar o servidor

> No Notificador, usamos `/home/instance` e `/home/diarios`, e `DATABASE_URL=sqlite:////home/instance/local.db`. citeturn19search127turn19search128

---

# 4) Deploy manual (CLI) — do zero

> **Quando usar?**
> - Primeira vez do projeto
> - Para entender tudo “na unha” antes do CI/CD

## 4.1 Variáveis (exemplo Notificador)
```bash
export LOCATION="brazilsouth"
export RG="rg-notificador-iof-mg-2"
export ACR="acrnotificadoriofmg2"
export PLAN="asp-notificador-iof-mg-2"
export WEBAPP="notificador-iof-mg-2"
export IMAGE_REPO="notificador-iof-mg"
export IMAGE_TAG="manual-$(date +%Y%m%d%H%M%S)"
export IMAGE_FQN="${ACR}.azurecr.io/${IMAGE_REPO}:${IMAGE_TAG}"
```

## 4.2 Criar RG, ACR, Plan e WebApp
```bash
az group create -n "$RG" -l "$LOCATION"
az acr create -g "$RG" -n "$ACR" --sku Standard
az appservice plan create -g "$RG" -n "$PLAN" -l "$LOCATION" --sku B1 --is-linux
az webapp create -g "$RG" -n "$WEBAPP" -p "$PLAN" --deployment-container-image-name "$IMAGE_FQN"
```

> `az webapp create` cria o Web App para containers; o container é definido pela imagem configurada no app. citeturn19search113turn12search96

## 4.3 Build e push da imagem (no ACR)
Dentro da pasta do projeto:
```bash
az acr build --registry "$ACR" --image "${IMAGE_REPO}:${IMAGE_TAG}" .
```

## 4.4 Configurar Managed Identity para o WebApp puxar do ACR (AcrPull)
A recomendação atual é usar managed identity para autenticar o pull no ACR. citeturn19search113turn12search86

```bash
PRINCIPAL_ID="$(az webapp identity assign -g "$RG" -n "$WEBAPP" --query principalId -o tsv)"
ACR_ID="$(az acr show -g "$RG" -n "$ACR" --query id -o tsv)"
az role assignment create --assignee "$PRINCIPAL_ID" --scope "$ACR_ID" --role "AcrPull"
az webapp config set -g "$RG" -n "$WEBAPP" --generic-configurations '{"acrUseManagedIdentityCreds": true}'
```

## 4.5 Apontar o WebApp para a imagem/tag (linuxFxVersion)
```bash
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
az resource update \
  --ids "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.Web/sites/${WEBAPP}/config/web" \
  --set properties.linuxFxVersion="DOCKER|${IMAGE_FQN}"
```

---

# 5) Persistência com SQLite em `/home`

## 5.1 Por que isso importa?
Se você grava SQLite dentro do container (ex.: `/app/instance/local.db`), pode perder dados no restart/redeploy. Para persistência, habilite storage e use `/home`. citeturn19search127turn19search128

## 5.2 App Settings recomendadas (Notificador)
- Porta:
  - `WEBSITES_PORT=8000` (porta interna do container) citeturn19search115turn19search114
- Persistência:
  - `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` citeturn19search127turn19search128
- DB:
  - `DATABASE_URL=sqlite:////home/instance/local.db`
- Diretórios:
  - `DIARIOS_DIR=/home/diarios`

```bash
az webapp config appsettings set -g "$RG" -n "$WEBAPP" --settings \
  WEBSITES_PORT=8000 \
  PORT=8000 \
  WEBSITES_ENABLE_APP_SERVICE_STORAGE=true \
  DATABASE_URL="sqlite:////home/instance/local.db" \
  DIARIOS_DIR="/home/diarios"
```

---

# 6) Configurar SMTP (Gmail) de forma segura

## 6.1 Conceitos rápidos
- Gmail SMTP padrão: `smtp.gmail.com` com TLS na porta `587` (STARTTLS). citeturn10search48
- Para apps, o recomendado é usar **App Password** (com 2FA habilitado). citeturn10search52

## 6.2 Aplicar settings sem vazar a senha no histórico
```bash
read -s -p "Cole o App Password do Gmail: " MAIL_SMTP_PASSWORD
echo
export MAIL_SMTP_PASSWORD
```

```bash
az webapp config appsettings set -g "$RG" -n "$WEBAPP" --settings \
  MAIL_FROM_ADDRESS="pythontestaugusto@gmail.com" \
  MAIL_SMTP_HOST="smtp.gmail.com" \
  MAIL_SMTP_PORT="587" \
  MAIL_SMTP_USER="pythontestaugusto@gmail.com" \
  MAIL_SMTP_PASSWORD="$MAIL_SMTP_PASSWORD" \
  MAIL_USE_TLS="true" \
  MAIL_USE_SSL="false"
```

---

# 7) Logs e troubleshooting

## 7.1 Habilitar logs do container (stdout/stderr)
```bash
az webapp log config -g "$RG" -n "$WEBAPP" --docker-container-logging filesystem
```
A CLI documenta `--docker-container-logging {filesystem, off}` para capturar stdout/stderr do container. citeturn19search141

## 7.2 Ver logs ao vivo
```bash
az webapp log tail -g "$RG" -n "$WEBAPP"
```
Para parar: `Ctrl + C`. citeturn19search141

## 7.3 Diagnósticos comuns
- Warmup ping em `/robots933456.txt` é comportamento esperado do App Service. citeturn19search128
- App não responde → porta errada → ajuste `WEBSITES_PORT`. citeturn19search115turn19search114
- SQLite some após restart → não está usando `/home` ou storage está desligado. citeturn19search127turn19search128

---

# 8) CI/CD com GitHub Actions + OIDC (recomendado)

> **Por que OIDC?**
> Evita secrets de longa duração; o GitHub emite token OIDC e o Entra troca por token curto. Requer `id-token: write`. citeturn19search120turn19search119

## 8.1 O que você vai criar
- App Registration/Service Principal no Entra
- Federated Credential vinculando repo/branch
- RBAC:
  - `AcrPush` no ACR
  - `Contributor` no WebApp (ou RG)

### 8.1.1 Criar App Registration + SP
```bash
SP_NAME="gh-notificador-iof-mg-deploy"
APP_ID="$(az ad app create --display-name "$SP_NAME" --query appId -o tsv)"
az ad sp create --id "$APP_ID" >/dev/null
SP_OBJECT_ID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"
echo "AZURE_CLIENT_ID=$APP_ID"
```

### 8.1.2 RBAC
```bash
ACR_ID="$(az acr show -g "$RG" -n "$ACR" --query id -o tsv)"
WEBAPP_ID="$(az webapp show -g "$RG" -n "$WEBAPP" --query id -o tsv)"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal --scope "$ACR_ID" --role "AcrPush"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal --scope "$WEBAPP_ID" --role "Contributor"
```

### 8.1.3 Criar Federated Credential (branch main)
O Azure CLI suporta criar federated credential via JSON (`issuer`, `subject`, `audiences`). citeturn12search106turn19search120

```bash
cat > credential.json <<'JSON'
{
  "name": "github-actions-main",
  "issuer": "https://token.actions.githubusercontent.com/",
  "subject": "repo:augustosouza8/notificador-iof-mg:ref:refs/heads/main",
  "description": "OIDC for GitHub Actions deploy",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON

az ad app federated-credential create --id "$APP_ID" --parameters credential.json
```

## 8.2 Secrets no GitHub
Crie no repo (Settings → Secrets and variables → Actions): citeturn19search119

- `AZURE_CLIENT_ID` = appId do App Registration
- `AZURE_TENANT_ID` = tenantId
- `AZURE_SUBSCRIPTION_ID` = subscriptionId
- `AZURE_WEB_APP_NAME` = `notificador-iof-mg-2`
- `AZURE_RESOURCE_GROUP` = `rg-notificador-iof-mg-2`
- `AZURE_REGISTRY_NAME` = `acrnotificadoriofmg2`

## 8.3 Workflow CI (deploy em todo push no main)
Crie/atualize: `.github/workflows/deploy-ci.yml`

```yaml
name: Deploy (CI) - push to main

on:
  push:
    branches: ["main"]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  AZURE_WEBAPP_NAME: ${{ secrets.AZURE_WEB_APP_NAME }}
  AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
  AZURE_REGISTRY_NAME: ${{ secrets.AZURE_REGISTRY_NAME }}
  IMAGE_NAME: notificador-iof-mg

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Login no ACR
        run: az acr login --name ${{ env.AZURE_REGISTRY_NAME }}

      - name: Build e push (tag = SHA)
        run: |
          IMAGE="${{ env.AZURE_REGISTRY_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> $GITHUB_ENV

      - name: Update WebApp linuxFxVersion -> SHA
        run: |
          az resource update \
            --resource-group "${{ env.AZURE_RESOURCE_GROUP }}" \
            --name "${{ env.AZURE_WEBAPP_NAME }}" \
            --resource-type "Microsoft.Web/sites" \
            --set "properties.siteConfig.linuxFxVersion=DOCKER|${{ env.IMAGE }}"

      - name: Restart WebApp
        run: az webapp restart --name "${{ env.AZURE_WEBAPP_NAME }}" --resource-group "${{ env.AZURE_RESOURCE_GROUP }}"
```

Requisitos OIDC: `permissions: id-token: write` e `azure/login@v2` com `client-id/tenant-id/subscription-id`. citeturn19search120turn19search119

---

# 9) Modo PROD por tag/release + Environments (approval)

## 9.1 Criar Environment no GitHub
No repo: **Settings → Environments → New environment**
- Nome: `production`
- Configure “Required reviewers”

O GitHub recomenda environments para controle adicional e segurança com OIDC. citeturn19search120

## 9.2 Federated credential para environment (produção)
```bash
cat > credential-prod.json <<'JSON'
{
  "name": "github-actions-production-env",
  "issuer": "https://token.actions.githubusercontent.com/",
  "subject": "repo:augustosouza8/notificador-iof-mg:environment:production",
  "description": "OIDC for GitHub Actions deploy - production environment",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON

az ad app federated-credential create --id "$APP_ID" --parameters credential-prod.json
```

## 9.3 Workflow PROD (deploy quando criar tag)
Crie: `.github/workflows/deploy-prod.yml`

```yaml
name: Deploy (PROD) - tag/release

on:
  push:
    tags:
      - "v*"

permissions:
  id-token: write
  contents: read

env:
  AZURE_WEBAPP_NAME: ${{ secrets.AZURE_WEB_APP_NAME }}
  AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
  AZURE_REGISTRY_NAME: ${{ secrets.AZURE_REGISTRY_NAME }}
  IMAGE_NAME: notificador-iof-mg

jobs:
  build-and-deploy-prod:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Azure login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Login no ACR
        run: az acr login --name ${{ env.AZURE_REGISTRY_NAME }}

      - name: Build e push (tag = release tag)
        run: |
          TAG="${GITHUB_REF_NAME}"
          IMAGE="${{ env.AZURE_REGISTRY_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${TAG}"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "IMAGE=$IMAGE" >> $GITHUB_ENV

      - name: Update WebApp linuxFxVersion -> TAG
        run: |
          az resource update \
            --resource-group "${{ env.AZURE_RESOURCE_GROUP }}" \
            --name "${{ env.AZURE_WEBAPP_NAME }}" \
            --resource-type "Microsoft.Web/sites" \
            --set "properties.siteConfig.linuxFxVersion=DOCKER|${{ env.IMAGE }}"

      - name: Restart WebApp
        run: az webapp restart --name "${{ env.AZURE_WEBAPP_NAME }}" --resource-group "${{ env.AZURE_RESOURCE_GROUP }}"
```

---

# 10) Custos estimados e dicas de economia

## 10.1 App Service (Plano)
O maior driver de custo é o **App Service Plan** (cobrança por capacidade e tempo de alocação). citeturn19search132turn19search129

Para preços exatos por região/moeda, use a página oficial/Calculadora (varia por região e câmbio). citeturn19search129turn19search132

## 10.2 ACR (Standard)
A página oficial de pricing do ACR lista **Standard = US$ 0.667/dia** e inclui 100 GB. citeturn19search139turn19search135

## 10.3 Dicas de economia
1) Use B1 enquanto for POC/baixo tráfego; escale depois. citeturn19search132turn19search129
2) Evite múltiplas instâncias com SQLite.
3) Use tags por SHA e limpe imagens antigas no ACR para reduzir custos de armazenamento. citeturn19search135turn19search139
4) Desligue logs de container quando não precisar:
```bash
az webapp log config -g "$RG" -n "$WEBAPP" --docker-container-logging off
```
citeturn19search141

---

# 11) Templates reutilizáveis

## 11.1 Checklist “novo projeto”
- [ ] App escuta em `0.0.0.0`
- [ ] Porta configurável (definir `WEBSITES_PORT`) citeturn19search115turn19search114
- [ ] Logs em stdout/stderr
- [ ] Se usa SQLite/arquivos: `/home` + `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` citeturn19search127turn19search128
- [ ] Deploy manual funcionando
- [ ] CI no main (tag SHA)
- [ ] PROD por tag com Environment approval

## 11.2 Comandos úteis de validação
Ver imagem atual no WebApp:
```bash
az webapp config show -g "$RG" -n "$WEBAPP" --query "linuxFxVersion" -o tsv
```

Ver appsettings:
```bash
az webapp config appsettings list -g "$RG" -n "$WEBAPP" -o table
```

Ver logs ao vivo:
```bash
az webapp log tail -g "$RG" -n "$WEBAPP"
```
citeturn19search141

---

## Referências oficiais (para consulta)
- Azure Login com OIDC (Microsoft Learn): citeturn19search119
- OIDC no GitHub para Azure (GitHub Docs): citeturn19search120
- `az ad app federated-credential` (CLI): citeturn12search106
- Configurar custom container no App Service: citeturn19search113
- Logs via Azure CLI (`az webapp log`): citeturn19search141
- Pricing ACR: citeturn19search139
- Conceitos de App Service Plans: citeturn19search132
