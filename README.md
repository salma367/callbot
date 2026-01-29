# Projet Callbot & Dashboard

Un système local de centre d'appels avec tableau de bord et callbot, comprenant un backend API et des frontends pour l'agent et le callbot.

Ce projet comporte **quatre composants principaux** :

1. **Backend API** – fournit les données des appels.
2. **Frontend Dashboard** – affiche les statistiques des appels pour les agents.
3. **Frontend Callbot** – interface de simulation d'appels.
4. **Backend Callbot** – gère les appels IA, la reconnaissance vocale (ASR), la synthèse vocale (TTS) et les rapports d'appels.

## Prérequis

* Python 3.10 (utiliser un environnement virtuel recommandé)
* Testé uniquement avec Python 3.10

## Installation

1. **Cloner le dépôt**

```bash
git clone <url-du-repo>
cd callbot
```

2. **Créer et activer un environnement virtuel**

```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

## Lancer le projet

### 1. Démarrer le Backend API

```bash
source .venv/bin/activate
python backend/api.py
```

Vous devriez voir :

```
🚀 Call Center Dashboard API
📁 Base de données: /Users/mac/callbot/calls.db
🌐 API en cours sur: http://127.0.0.1:5000
```

### 2. Démarrer le Frontend Dashboard

```bash
source .venv/bin/activate
cd frontend/dashboard
python -m http.server 8005
```

* Accéder au tableau de bord : [http://127.0.0.1:8005](http://127.0.0.1:8005)

### 3. Démarrer le Frontend Callbot

```bash
source .venv/bin/activate
cd frontend/callbot
python -m http.server 8002
```

* Accéder à l'interface Callbot : [http://127.0.0.1:8002](http://127.0.0.1:8002)

### 4. Démarrer le Backend Callbot (IA)

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload
```

* Serveur accessible sur : [http://127.0.0.1:8000](http://127.0.0.1:8000)
* Gère les appels IA, la synthèse vocale et les rapports d'appels.

---

## Notes

* Toujours **activer l'environnement virtuel** avant de lancer une commande.
* Ports utilisés :

  * Backend API : 5000
  * Frontend Dashboard : 8005
  * Frontend Callbot : 8002
  * Backend Callbot IA : 8000
