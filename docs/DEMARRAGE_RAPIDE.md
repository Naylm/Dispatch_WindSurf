# 🚀 Démarrage Rapide - Dispatch Manager v2.0

## ✨ Nouvelles fonctionnalités

### 1. 📋 Vue Liste Compacte (par défaut)
- Tous les tickets visibles dans un tableau
- Meilleure lisibilité avec beaucoup de tickets
- Actions rapides directement dans le tableau

### 2. 🎨 Badges de Couleur
- **Priorités**: Basse (vert), Moyenne (jaune), Haute (orange), Critique (rouge)
- **Sites**: Chaque site a sa propre couleur
- Entièrement configurable !

### 3. ⚙️ Onglet Configuration
- Gérer les sujets
- Gérer les priorités avec couleurs
- Gérer les sites avec couleurs
- **Accès**: Bouton "⚙️ Configuration" dans le menu admin

### 4. ✏️ Modification Complète
- Bouton crayon sur chaque ticket
- Modifier toutes les informations en un clic
- Historique complet des modifications

### 5. 🎯 Sélecteur de Technicien
- Plus de drag & drop
- Menu déroulant simple et rapide
- Confirmation avant changement

---

## 🏃‍♂️ Démarrer l'application

### Option 1 : Avec votre environnement Python existant
```bash
cd c:\Users\mebonnin\Desktop\DispatchV1\dispatch_manager
python app.py
```

### Option 2 : Avec l'environnement virtuel (si configuré)
```bash
cd c:\Users\mebonnin\Desktop\DispatchV1\dispatch_manager
venv\Scripts\activate
python app.py
```

L'application démarrera sur : **http://localhost:3000**

---

## 👤 Connexion

### Compte Admin par défaut
- **Username**: melvin
- **Password**: admin

---

## 📝 Premiers pas

1. **Lancez l'application** avec `python app.py`
2. **Connectez-vous** avec le compte admin
3. **Accédez à la Configuration** (bouton vert "⚙️ Configuration")
4. **Vérifiez les données** :
   - Sites : HD, HGRL, SJ, Periph (avec couleurs)
   - Priorités : Basse, Moyenne, Haute, Critique (avec couleurs et niveaux)
   - Sujets : Portables, PC Fixe, Imprimantes, Réseau, Matériel, Logiciel
5. **Ajoutez ou modifiez** selon vos besoins
6. **Retournez à l'accueil** et profitez de la nouvelle interface !

---

## 🎛️ Utilisation de la Vue Admin

### Basculer entre les vues
- Cliquez sur **"📋 Vue liste compacte"** pour le tableau (recommandé)
- Cliquez sur **"📊 Vue colonnes"** pour la vue par technicien

### Modifier un ticket
1. Cliquez sur le bouton **✏️** (crayon) sur le ticket
2. Modifiez les informations
3. Cliquez sur **"💾 Enregistrer les modifications"**

### Changer le technicien affecté
- **Dans la vue liste** : Utilisez le menu déroulant dans la colonne "Technicien"
- **Dans la vue colonnes** : Utilisez le menu déroulant sous chaque ticket
- Confirmez le changement

### Rechercher et filtrer
- **Barre de recherche** : Tapez un n°, site ou sujet
- **Filtre État** : Affecté, En cours, Traité, etc.
- **Filtre Priorité** : Basse, Moyenne, Haute, Critique
- **Filtre Site** : HD, HGRL, SJ, Periph, etc.
- **Réinitialiser** : Cliquez sur 🔄

---

## ⚙️ Personnaliser la Configuration

### Ajouter un nouveau site
1. Allez dans **Configuration**
2. Section **Sites** (bleue à droite)
3. Entrez le nom du site
4. Choisissez une couleur
5. Cliquez sur **"Ajouter"**

### Ajouter une nouvelle priorité
1. Allez dans **Configuration**
2. Section **Priorités** (jaune au centre)
3. Entrez le nom
4. Choisissez une couleur
5. Définissez le niveau (1-10, 1=basse, 10=critique)
6. Cliquez sur **"Ajouter"**

### Ajouter un nouveau sujet
1. Allez dans **Configuration**
2. Section **Sujets** (bleue à gauche)
3. Entrez le nom
4. Cliquez sur **"Ajouter"**

---

## 🔍 Astuces

### Pour une meilleure lisibilité
- Utilisez la **vue liste compacte** quand vous avez plus de 3-4 techniciens
- Les **badges de couleur** vous permettent de repérer rapidement les priorités
- Utilisez les **filtres** pour vous concentrer sur certains types de tickets

### Pour une gestion rapide
- Le bouton **✏️** permet de tout modifier en un clic
- Le **sélecteur de technicien** est plus rapide que le drag & drop
- L'**historique** 🕒 vous permet de voir tous les changements

### Personnalisation
- Choisissez des **couleurs contrastées** pour les sites
- Utilisez les **niveaux de priorité** pour trier automatiquement
- Ajoutez des **sujets spécifiques** à votre organisation

---

## ❓ Questions fréquentes

**Q: Les données existantes sont-elles préservées ?**  
R: Oui ! Toutes vos données (incidents, techniciens, historique) sont intactes.

**Q: Puis-je revenir à l'ancienne interface ?**  
R: Oui, le fichier `home_content_old.html` contient l'ancienne version.

**Q: Les techniciens voient-ils les changements ?**  
R: Non, la vue technicien reste simple avec leurs propres tickets seulement.

**Q: Les couleurs ne s'affichent pas ?**  
R: Assurez-vous d'avoir redémarré l'application après la première installation.

**Q: Puis-je supprimer un site/sujet/priorité ?**  
R: Oui, via le bouton 🗑️ dans la Configuration. Attention, vérifiez qu'aucun ticket ne l'utilise.

---

## 📞 Support

Pour toute question ou problème, consultez le fichier `README_AMELIORATIONS.md` qui contient la documentation complète.

---

**Version 2.0** - Améliorations novembre 2024  
Profitez de votre nouvelle interface ! 🎉
