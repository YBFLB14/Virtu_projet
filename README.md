# Gestionnaire de Machines Virtuelles KVM

Cette application web développée en Python avec le micro-framework Flask permet de gérer des machines virtuelles KVM via une interface web.

## Prérequis

### Système

- Distribution Linux avec KVM et libvirt installés

### Python

- Python 3.9 ou plus
- Dépendances Python :
  ```bash
  pip install flask flask-session
  ```
- Libvirt pour Python sous Debian :
  ```
  sudo apt install python3-libvirt
  ```

## Fonctionnalités principales

- Authentification via les identifiants système avec SSH
- Gestion de plusieurs hyperviseurs(connexion ssh) grâce au choix de l’adresse IP et donc de l'hyperviseur
- Affichage de la liste des machines virtuelles :
  - Machines virtuelles actives avec leurs caractéristiques (mémoire, vCPU, état)
  - Machines virtuelles inactives
- Création de VMs avec :
  - Nom personnalisé
  - Taille de la mémoire (en MiB)
  - Nombre de vCPU
  - Taille du disque (en Go)
  - Chemin vers un fichier ISO (optionnel)
- Démarrage et arrêt d'une VM
- Suspension et reprise d'une VM
- Sauvegarde et restauration de l’état d’une VM
- Modification des ressources mémoire et CPU (si la VM est arrêtée)
- Suppression d’une VM

## Architecture du projet


L'application est organisée de la manière suivante :

```
tp_web_kvm/
├── app.py                # Application principale Flask
├── templates/            # Fichiers HTML (login.html, index.html, create.html, etc...)
├── README.md             # Documentation du projet
```


## Lancer l'application

Depuis le dossier du projet : 
```bash
python app.py
```

Ensuite, ouvrez votre navigateur et accédez à :  
[http://localhost:5000](http://localhost:5000)


## Démonstration 

- Connexion à l'hyperviseur : [https://vimeo.com/1069060732/9e90442a97](https://vimeo.com/1069060732/9e90442a97)
- Gestion de la mise en pause et de la sauvegarde de machine :  [https://vimeo.com/1069065743/af847ec4f3](https://vimeo.com/1069065743/af847ec4f3)
- Création, modification et suppression de machine : [https://vimeo.com/1069063336/4cea447e90](https://vimeo.com/1069063336/4cea447e90)




