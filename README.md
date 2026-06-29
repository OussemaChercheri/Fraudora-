# FraudGuard AI

Système de détection d'anomalies et d'analyse OCR pour factures.

## Démarrage rapide

### 1. Prérequis

- **Docker** (PostgreSQL 15)
- **Python 3.12+**
- **Node.js 20+**
- **Tesseract OCR** (installé sur la machine hôte)
  - Windows : https://github.com/UB-Mannheim/tesseract/wiki
  - Ubuntu : `sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils`
  - macOS : `brew install tesseract tesseract-lang poppler`

### 2. Lancer la base de données

```bash
docker compose up -d
```

La base PostgreSQL est accessible sur `localhost:5433`.

### 3. Configurer le backend

```bash
cd backend
cp .env.example .env
# Éditer .env si nécessaire (les valeurs par défaut fonctionnent en dev)
```

Installer les dépendances :

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Lancer les migrations :

```bash
alembic upgrade head
```

Démarrer le serveur :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

L'API est disponible sur `http://localhost:8000/docs`.

### 4. Lancer le frontend

```bash
cd frontend
npm install
npm run dev
```

Le frontend est disponible sur `http://localhost:5173`.

Un proxy Vite redirige `/api` vers `http://localhost:8000`.

### 5. Créer les données de démo

```bash
# Depuis le répertoire backend (avec le venv activé et le serveur en marche)
curl -X POST http://localhost:8000/api/v1/dev/seed
```

Ou utiliser l'endpoint `/api/v1/dev/seed` dans Swagger UI (`/docs`).

## Comptes de test

| Email | Mot de passe | Rôle |
|---|---|---|
| `admin@fraudguard.tn` | `Admin@2026` | ADMIN |
| `comptable@demo-client.tn` | `Demo@2026` | COMPTABLE |

### Rôles disponibles

- **ADMIN** : accès complet à toutes les fonctionnalités + gestion des utilisateurs et seuils d'alerte
- **FINANCE** : accès aux rapports, analyses, exports PDF/Excel
- **COMPTABLE** : accès aux factures, anomalies, saisie manuelle
- **VIEWER** : consultation uniquement

## Fonctionnalités principales

- **OCR** : extraction automatique des champs des factures (PDF/JPG/PNG)
- **Détection d'anomalies** : montants anormaux, nouveaux fournisseurs à risque, pics de prix
- **Détection de doublons** : correspondances exactes et floues entre factures
- **Dashboard** : indicateurs clés avec exports PDF et Excel
- **Rapports fournisseurs** : analyse détaillée par fournisseur avec score de risque
- **Évolution des dépenses** : comparaison N vs N-1 par jour/semaine/mois
- **Notifications** : alertes anomalies et doublons (interface + email quotidien optionnel)
- **Seuils d'alerte configurables** : administration des seuils via l'interface

## Variables d'environnement

Voir `backend/.env.example` pour la configuration complète.

Email quotidien désactivé par défaut (`SMTP_ENABLED=false`). Les notifications sont visibles dans l'interface.

## Tests E2E

```bash
python test_e2e.py
```
