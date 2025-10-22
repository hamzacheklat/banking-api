# Étape 1 : base image
FROM python:3.12-slim

# Étape 2 : définir le répertoire de travail
WORKDIR /app

# Étape 4 : installer les dépendance
# Étape 6 : copier le dossier volumineux du modèle
COPY models/embeddings/all-MiniLM-L6-v2/ ./app/models/embeddings/all-MiniLM-L6-v2/

# Étape 7 : commande de lancement
CMD ["python", "app/server.py"]
