#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DE DÉPLOIEMENT ET MISE À JOUR RAPIDE (1-CLIC) EASYTRAVEL
# ==============================================================================
# Usage sur le serveur :
#   cd /var/www/easytravel
#   sudo ./deploy/scripts/deploy.sh
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo "🔄 Déploiement de la dernière version EasyTravel..."
echo "=========================================================="

APP_DIR="/var/www/easytravel"
cd "$APP_DIR"

echo "📥 1. Récupération des dernières modifications Git..."
git fetch origin main
git reset --hard origin/main

echo "🐍 2. Activation de l'environnement virtuel et installation..."
source "$APP_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️ 3. Application des migrations de base de données..."
python manage.py migrate --noinput

echo "📦 4. Collecte et compression des fichiers statiques..."
python manage.py collectstatic --noinput

echo "🔒 5. Ajustement des permissions de fichiers..."
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"

echo "🚀 6. Redémarrage des services d'application..."
systemctl restart easytravel
systemctl reload nginx

echo "🩺 7. Vérification de l'état du service..."
if systemctl is-active --quiet easytravel; then
    echo "=========================================================="
    echo "✅ EasyTravel est en ligne et fonctionne parfaitement !"
    echo "=========================================================="
else
    echo "❌ ATTENTION : Le service easytravel n'a pas pu redémarrer."
    echo "Consultez les logs : journalctl -u easytravel -n 50 --no-pager"
    exit 1
fi
