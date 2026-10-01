#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DE PROVISIONING AUTOMATISÉ EASYTRAVEL SUR VPS CONTABO (UBUNTU 22.04 / 24.04)
# ==============================================================================
# Exécution sur le serveur Contabo :
#   chmod +x setup_contabo.sh
#   sudo ./setup_contabo.sh
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo "🚀 Initialisation et Déploiement EasyTravel sur Contabo"
echo "=========================================================="

# Vérification des droits root / sudo
if [ "$EUID" -ne 0 ]; then
  echo "❌ Ce script doit être exécuté en tant que root ou avec sudo."
  exit 1
fi

APP_DIR="/var/www/easytravel"
APP_USER="www-data"
APP_GROUP="www-data"
LOG_DIR="/var/log/easytravel"
DB_NAME="easytravel_db"
DB_USER="easytravel_user"
# Génération d'un mot de passe PostgreSQL aléatoire sécurisé
DB_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 20)

echo "📦 1. Mise à jour du système d'exploitation..."
apt update && apt upgrade -y

echo "📦 2. Installation des paquets essentiels..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libpq-dev \
    postgresql \
    postgresql-contrib \
    nginx \
    git \
    curl \
    ufw \
    fail2ban \
    certbot \
    python3-certbot-nginx

echo "🛡️ 3. Configuration du pare-feu UFW..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "🛡️ 4. Activation de Fail2ban (protection contre les attaques brute-force)..."
systemctl enable fail2ban
systemctl start fail2ban

echo "🐘 5. Configuration de la base de données PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Création de l'utilisateur et de la base si inexistants
sudo -u postgres psql -c "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
  ELSE
    ALTER ROLE $DB_USER WITH PASSWORD '$DB_PASS';
  END IF;
END
\$\$;"

sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "📁 6. Préparation des répertoires applicatifs..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p /var/www/certbot
mkdir -p "$APP_DIR/media"
mkdir -p "$APP_DIR/staticfiles"

chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
chmod 755 "$LOG_DIR"

echo "🐍 7. Création de l'environnement virtuel Python..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR/venv"

echo "⚙️ 8. Configuration des services Nginx et Systemd..."
if [ -f "$APP_DIR/deploy/systemd/easytravel.service" ]; then
    cp "$APP_DIR/deploy/systemd/easytravel.service" /etc/systemd/system/easytravel.service
    systemctl daemon-reload
    systemctl enable easytravel
fi

if [ -f "$APP_DIR/deploy/nginx/easytravel.conf" ]; then
    cp "$APP_DIR/deploy/nginx/easytravel.conf" /etc/nginx/sites-available/easytravel.conf
    # Remplacement du site par défaut si actif
    if [ -f /etc/nginx/sites-enabled/default ]; then
        rm -f /etc/nginx/sites-enabled/default
    fi
    ln -sf /etc/nginx/sites-available/easytravel.conf /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
fi

echo "=========================================================="
echo "✅ Installation système terminée avec succès !"
echo "=========================================================="
echo ""
echo "🔑 Identifiants PostgreSQL générés :"
echo "   Base : $DB_NAME"
echo "   Utilisateur : $DB_USER"
echo "   Mot de passe : $DB_PASS"
echo "   DATABASE_URL : postgres://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME"
echo ""
echo "📝 Prochaines étapes :"
echo "1. Créez votre fichier '$APP_DIR/.env' avec les variables de production (voir .env.example)"
echo "2. Activez le venv et installez les dépendances :"
echo "   source $APP_DIR/venv/bin/activate"
echo "   pip install -r $APP_DIR/requirements.txt"
echo "   python $APP_DIR/manage.py migrate"
echo "   python $APP_DIR/manage.py collectstatic --noinput"
echo "3. Démarrez l'application :"
echo "   sudo systemctl restart easytravel"
echo "4. Activez SSL HTTPS gratuit avec Let's Encrypt :"
echo "   sudo certbot --nginx -d votre-domaine.cm -d www.votre-domaine.cm"
echo "=========================================================="
