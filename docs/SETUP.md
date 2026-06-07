markdown
# Setup Hechicero - Reconstruction du Système

## 1. Installation des dépendances de base
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-smbus i2c-tools git apache2 php jq
2. Configuration I2C
Activer I2C via raspi-config :

bash
sudo raspi-config
# Interfacing Options -> I2C -> Enable
3. Configuration du serveur Web (Lien symbolique recommandé)
Ne supprime pas /var/www/html si tu veux garder la config Apache par défaut. Préfère créer un lien symbolique vers le fichier status.json ou configurer un alias Apache.

Exemples sûrs :

Option A — Lien symbolique pour status.json seulement

bash
# s'assurer que le dossier web existe
mkdir -p /home/thomas/hechicero/web

# rendre status.json lisible par Apache
sudo chown thomas:www-data /home/thomas/hechicero/web/status.json
sudo chmod 644 /home/thomas/hechicero/web/status.json

# créer lien symbolique unique
sudo ln -sf /home/thomas/hechicero/web/status.json /var/www/html/status.json
Option B — Alias Apache (préférable si tu veux servir tout le dossier web)
Ajouter dans un VirtualHost (ex. /etc/apache2/sites-available/000-default.conf) :

Code
Alias /hechicero/ /home/thomas/hechicero/web/
<Directory /home/thomas/hechicero/web/>
    Require all granted
    Options Indexes FollowSymLinks
</Directory>
Puis :

bash
sudo systemctl reload apache2
4. Permissions minimales recommandées
bash
sudo chown -R thomas:thomas /home/thomas/hechicero
sudo chmod 755 /home/thomas
sudo chmod 755 /home/thomas/hechicero
sudo chmod 755 /home/thomas/hechicero/scripts
sudo chmod 775 /home/thomas/hechicero/data
sudo chown thomas:www-data /home/thomas/hechicero/web/status.json
sudo chmod 644 /home/thomas/hechicero/web/status.json
5. Service Monitoring (systemd)
Créer /etc/systemd/system/hechicero.service (exemple durci) et activer :

bash
sudo systemctl daemon-reload
sudo systemctl enable --now hechicero.service
sudo systemctl status hechicero.service --no-pager
6. Vérifications post-install
curl -s http://localhost/status.json | jq . doit renvoyer JSON valide.

Ouvrir l’UI et forcer reload (Ctrl+F5).

journalctl -u hechicero.service -n 200 --no-pager pour logs service.

Code

---

### Commit message recommandé
```text
docs: standardize docs, add numbered backlog tickets and setup/permissions guidance