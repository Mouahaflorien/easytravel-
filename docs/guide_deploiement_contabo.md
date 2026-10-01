# 🚀 Guide de Déploiement et d'Exploitation EasyTravel sur VPS Contabo

Ce guide vous accompagne pas à pas pour déployer et administrer la plateforme **EasyTravel** sur un serveur VPS Linux chez **Contabo** avec une passerelle de paiement **CinetPay** sécurisée.

---

## 📋 Prérequis Recommandés

1. **Serveur VPS Contabo** :
   - Formule : **Cloud VPS S** (4 vCPU, 8 Go RAM) ou supérieure.
   - Système d'exploitation : **Ubuntu 22.04 LTS** ou **Ubuntu 24.04 LTS**.
   - Emplacement : Allemagne (ou centre européen de votre choix).
2. **Nom de domaine** :
   - Ex: `easytravel.cm` ou `monvoyage.cm`.
   - Les enregistrements DNS de type **A** doivent pointer vers l'adresse IP publique de votre VPS Contabo :
     - `@` -> `IP_DU_VPS_CONTABO`
     - `www` -> `IP_DU_VPS_CONTABO`
3. **Compte Marchand CinetPay** :
   - `CINETPAY_SITE_ID`
   - `CINETPAY_API_KEY`
   - Compte activé pour le Cameroun (MTN Mobile Money, Orange Money, Cartes Bancaires).

---

## 🛠️ Étape 1 : Connexion au VPS Contabo en SSH

Depuis votre terminal (PowerShell, Git Bash ou macOS/Linux) :

```bash
ssh root@VOTRE_IP_CONTABO
```

*(Entrez le mot de passe root fourni par email par Contabo lors de la commande).*

---

## 📥 Étape 2 : Récupération du Code Source

Clonez votre dépôt Git dans le répertoire officiel de production `/var/www/easytravel` :

```bash
# Mise à jour rapide et installation de git si nécessaire
apt update && apt install -y git

# Clônage du projet
mkdir -p /var/www
git clone https://github.com/votre-compte/easytravel.git /var/www/easytravel
cd /var/www/easytravel
```

---

## ⚡ Étape 3 : Exécution du Script d'Installation Automatisé (1-Clic)

Nous avons conçu un script qui configure l'ensemble du serveur de A à Z (PostgreSQL, Nginx, Python, Firewall, Gunicorn, Fail2ban) :

```bash
chmod +x /var/www/easytravel/deploy/scripts/setup_contabo.sh
sudo /var/www/easytravel/deploy/scripts/setup_contabo.sh
```

> **Ce que fait ce script automatiquement :**
> - Installe Python 3, pip, PostgreSQL, Nginx, UFW, Fail2ban, Certbot.
> - Configure le pare-feu UFW (ports 22, 80, 443 ouverts, le reste verrouillé).
> - Crée la base de données PostgreSQL `easytravel_db` et l'utilisateur `easytravel_user`.
> - Génère un mot de passe aléatoire hautement sécurisé pour la base de données.
> - Configure Nginx et le service Gunicorn sous `systemd`.

**Notez précieusement les identifiants PostgreSQL affichés à la fin du script !**

---

## 🔑 Étape 4 : Configuration des Variables d'Environnement (`.env`)

Créez le fichier de configuration de production sur le serveur :

```bash
cp /var/www/easytravel/.env.example /var/www/easytravel/.env
nano /var/www/easytravel/.env
```

Renseignez les valeurs réelles :

```env
# Sécurité Django
DJANGO_SECRET_KEY=votre-cle-secrete-aleatoire-tres-longue
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=easytravel.cm,www.easytravel.cm,VOTRE_IP_CONTABO
CSRF_TRUSTED_ORIGINS=https://easytravel.cm,https://www.easytravel.cm

# Base de Données PostgreSQL (générée à l'étape 3)
DATABASE_URL=postgres://easytravel_user:MOT_DE_PASSE_GENERE@127.0.0.1:5432/easytravel_db

# Passerelle CinetPay
CINETPAY_SITE_ID=1234567
CINETPAY_API_KEY=votre_cle_api_cinetpay_officielle
CINETPAY_CURRENCY=XAF
CINETPAY_RETURN_URL=https://easytravel.cm/paiements/cinetpay/retour/
CINETPAY_NOTIFY_URL=https://easytravel.cm/paiements/cinetpay/notification/

# Clé Gemini pour l'audit anti-fraude (optionnel)
GEMINI_API_KEY=votre_cle_gemini_si_disponible

# Envoi des emails
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

*(Enregistrez avec `Ctrl+O` puis quittez avec `Ctrl+X`).*

---

## 📦 Étape 5 : Initialisation de l'Application et Première Mise en Ligne

Dans le dossier `/var/www/easytravel` :

```bash
# 1. Activation de l'environnement virtuel
source /var/www/easytravel/venv/bin/activate

# 2. Installation des paquets Python
pip install -r requirements.txt

# 3. Application des migrations de schéma vers PostgreSQL
python manage.py migrate

# 4. Collecte et compression des fichiers statiques (WhiteNoise)
python manage.py collectstatic --noinput

# 5. Création du super-administrateur de la plateforme
python manage.py createsuperuser

# 6. Démarrage de Gunicorn via systemd
sudo systemctl restart easytravel
sudo systemctl reload nginx
```

Vérifiez que le service tourne correctement :
```bash
sudo systemctl status easytravel
```

---

## 🔒 Étape 6 : Activation du Certificat SSL HTTPS Gratuit (Let's Encrypt)

Assurez-vous que votre domaine pointe bien vers l'IP de votre VPS Contabo, puis lancez :

```bash
sudo certbot --nginx -d easytravel.cm -d www.easytravel.cm
```

Certbot configure automatiquement les certificats et le renouvellement automatique (cronjob).

---

## 💳 Étape 7 : Configuration du Tableau de Bord CinetPay

Connectez-vous à votre espace marchand CinetPay :
1. Rendez-vous dans **Mon Compte** > **Configuration du Site**.
2. Renseignez :
   - **URL de Notification (IPN)** : `https://easytravel.cm/paiements/cinetpay/notification/`
   - **URL de Retour** : `https://easytravel.cm/paiements/cinetpay/retour/`
3. Vérifiez que la devise **XAF** est activée et que les canaux **Orange Money Cameroun** et **MTN Mobile Money Cameroun** sont cochés.

---

## 🔄 Étape 8 : Déploiement des Futures Mises à Jour (1 Seule Commande)

Chaque fois que vous modifiez votre code sur GitHub et souhaitez le déployer sur Contabo, connectez-vous au serveur et lancez :

```bash
cd /var/www/easytravel
sudo ./deploy/scripts/deploy.sh
```

Ce script s'occupe de tout :
- Récupère le dernier code Git (`git pull`)
- Met à jour les dépendances (`pip install`)
- Applique les nouvelles migrations (`python manage.py migrate`)
- Met à jour les fichiers statiques (`collectstatic`)
- Redémarre Gunicorn sans interruption de service !

---

## 🗄️ Étape 9 : Sauvegarde Automatique de la Base de Données

Pour sauvegarder chaque nuit la base de données PostgreSQL, ajoutez une tâche planifiée dans cron :

```bash
crontab -e
```

Ajoutez la ligne suivante (sauvegarde quotidienne à 02h00 du matin conservée dans `/var/backups/easytravel`) :

```cron
0 2 * * * pg_dump -U easytravel_user -h 127.0.0.1 easytravel_db | gzip > /var/backups/easytravel/easytravel_$(date +\%Y\%m\%d).sql.gz
```

---

## 🛠️ Commandes Utiles de Diagnostic & Maintenance

| Action | Commande |
|--------|----------|
| Voir les logs Gunicorn en direct | `sudo journalctl -u easytravel -f` |
| Voir les logs d'erreurs Nginx | `sudo tail -f /var/log/nginx/easytravel_error.log` |
| Redémarrer l'application | `sudo systemctl restart easytravel` |
| Recharger la configuration Nginx | `sudo nginx -t && sudo systemctl reload nginx` |
| Consulter les logs de paiement CinetPay | `tail -f /var/log/easytravel/gunicorn_access.log \| grep paiements` |
