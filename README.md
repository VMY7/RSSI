# RSSI

## 🚀 Objectifs du projet

L’assistant vise à :

- Répondre aux questions sur les normes et réglementations (ISO 27001, NIST, RGPD, LPM, SOC 2…)
- Résumer et analyser des alertes de cybersécurité (CVE, CERT-FR…)
- Aider à la rédaction de rapports et documents de sécurité
- Réaliser une veille automatisée sur les nouvelles menaces
- Permettre une interaction via une **interface web** ou un **chatbot**

---

## 🧱 Architecture du système

Le projet est organisé autour de plusieurs modules :

### 1. Moteur LLM
- Modèle open-source (Llama, Falcon, GPT-J…)
- Support du fine-tuning sur corpus spécialisé
- Déploiement local pour garantir la confidentialité

### 2. Base de connaissances
- Intègre normes, guides, politiques et bonnes pratiques
- Indexation avec un moteur de recherche (ex : Elasticsearch)
- Documents internes ajoutables par le RSSI

### 3. Interface utilisateur
- Web App (FastAPI, Flask, ou équivalent)
- Chatbot (Slack, Teams, Web UI)

### 4. Module de veille
- Collecte automatique des alertes : CVE, CERT-FR, etc.
- Parsing, classification et résumé

### 5. Auditabilité
- Journalisation sécurisée
- Tracabilité complète des réponses
- Vérification des sources documentaires

---

## ⚙️ Contraintes techniques

- Déploiement **sur serveur local**
- Utilisation d’un **LLM open-source**
- Intégration d’un moteur de recherche documentaire (Elasticsearch)
- Respect strict des contraintes de sécurité, confidentialité et conformité

---

## 🔑 Fonctionnalités principales

- FAQ automatisée sur les bonnes pratiques cybersécurité  
- Analyse et résumé d’alertes de sécurité (CVE, CERT-FR…)  
- Assistance à la conformité (ISO 27001, RGPD, SOC 2…)  
- Synthèse de documents (rapports, audits, politiques internes)  
- Personnalisation via ajout de documents internes  
