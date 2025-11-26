# 🔔 Patch pour intégrer le système de notifications

## Modifications à apporter à `app.py`

### 1. Imports à ajouter en haut du fichier (après les imports existants)

```python
# Système de notifications
from notification_helpers import (
    emit_new_assignment_notification,
    emit_status_change_notification,
    emit_urgent_update_notification,
    emit_reassignment_notification,
    is_urgent
)
```

---

### 2. Route `add_incident` - Ligne ~897

**REMPLACER :**
```python
@app.route("/add", methods=["GET", "POST"])
def add_incident():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    techniciens = db.execute("SELECT * FROM techniciens").fetchall()
    sujets = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()

    if request.method == "POST":
        numero = request.form["numero"]
        site = request.form["site"]
        sujet = request.form["sujet"]
        urgence = request.form["urgence"]
        collab = request.form["collaborateur"]
        date_aff = request.form["date_affectation"]
        note_dispatch = request.form.get("note_dispatch", "")
        localisation = request.form.get("localisation", "")

        sql = """
          INSERT INTO incidents (
            numero, site, sujet, urgence,
            collaborateur, etat, note_dispatch,
            valide, date_affectation, archived, localisation
          ) VALUES (?, ?, ?, ?, ?, 'Affecté', ?, 0, ?, 0, ?)
        """
        db.execute(sql, (numero, site, sujet, urgence, collab, note_dispatch, date_aff, localisation))
        db.commit()
        socketio.emit("incident_update", {"action": "add"})
        return redirect(url_for("home"))
```

**PAR :**
```python
@app.route("/add", methods=["GET", "POST"])
def add_incident():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()
    techniciens = db.execute("SELECT * FROM techniciens WHERE actif=1").fetchall()
    sujets = db.execute("SELECT * FROM sujets ORDER BY nom").fetchall()
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()

    if request.method == "POST":
        numero = request.form["numero"]
        site = request.form["site"]
        sujet = request.form["sujet"]
        urgence = request.form["urgence"]
        collab = request.form["collaborateur"]
        date_aff = request.form["date_affectation"]
        note_dispatch = request.form.get("note_dispatch", "")
        localisation = request.form.get("localisation", "")

        sql = """
          INSERT INTO incidents (
            numero, site, sujet, urgence,
            collaborateur, etat, note_dispatch,
            valide, date_affectation, archived, localisation
          ) VALUES (?, ?, ?, ?, ?, 'Affecté', ?, 0, ?, 0, ?)
        """
        db.execute(sql, (numero, site, sujet, urgence, collab, note_dispatch, date_aff, localisation))
        db.commit()

        # Récupérer l'ID du nouvel incident
        incident_id = db.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

        # Préparer les données pour la notification
        incident_data = {
            "id": incident_id,
            "numero": numero,
            "site": site,
            "sujet": sujet,
            "urgence": urgence,
            "note_dispatch": note_dispatch,
            "localisation": localisation
        }

        # Émettre la notification de nouveau ticket
        emit_new_assignment_notification(socketio, incident_data, collab)

        # Émettre aussi l'event classique pour le refresh
        socketio.emit("incident_update", {"action": "add"})

        return redirect(url_for("home"))
```

---

### 3. Route `assign_incident` - Ligne ~383

**REMPLACER :**
```python
@app.route("/incidents/assign", methods=["POST"])
def assign_incident():
    if "user" not in session or session["role"] != "admin":
        return "", 403

    incident_id = request.form.get("id")
    new_collab = request.form.get("collaborateur")
    if not incident_id or not new_collab:
        return jsonify({"status": "error", "message": "Paramètres manquants"}), 400

    try:
        db = get_db()
        db.execute("BEGIN")
        db.execute(
            "UPDATE incidents SET collaborateur=? WHERE id=?", (new_collab, incident_id)
        )
        db.commit()
        socketio.emit("incident_update", {"action": "reassign", "incident_id": incident_id, "new_collab": new_collab}, broadcast=True)
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur assign_incident: {e}")
        return jsonify({"status": "error", "message": "Erreur serveur"}), 500
```

**PAR :**
```python
@app.route("/incidents/assign", methods=["POST"])
def assign_incident():
    if "user" not in session or session["role"] != "admin":
        return "", 403

    incident_id = request.form.get("id")
    new_collab = request.form.get("collaborateur")
    if not incident_id or not new_collab:
        return jsonify({"status": "error", "message": "Paramètres manquants"}), 400

    try:
        db = get_db()
        db.execute("BEGIN")

        # Récupérer les données de l'incident AVANT modification
        incident = db.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not incident:
            return jsonify({"status": "error", "message": "Incident introuvable"}), 404

        old_collab = incident['collaborateur']

        # Mise à jour
        db.execute(
            "UPDATE incidents SET collaborateur=? WHERE id=?", (new_collab, incident_id)
        )
        db.commit()

        # Préparer les données pour la notification
        incident_data = {
            "id": incident_id,
            "numero": incident['numero'],
            "site": incident['site'],
            "sujet": incident['sujet'],
            "urgence": incident['urgence'],
            "note_dispatch": incident.get('note_dispatch', ''),
            "localisation": incident.get('localisation', '')
        }

        # Émettre la notification de réaffectation
        emit_reassignment_notification(socketio, incident_data, old_collab, new_collab)

        # Émettre aussi l'event classique pour le refresh
        socketio.emit("incident_update", {
            "action": "reassign",
            "incident_id": incident_id,
            "new_collab": new_collab
        }, broadcast=True)

        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur assign_incident: {e}")
        return jsonify({"status": "error", "message": "Erreur serveur"}), 500
```

---

### 4. Route `update_etat` - Ligne ~1230

**AJOUTER après la mise à jour du statut :**

```python
@app.route("/update_etat/<int:id>", methods=["POST"])
def update_etat(id):
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    try:
        db.execute("BEGIN")
        inc = db.execute("SELECT * FROM incidents WHERE id=?", (id,)).fetchone()
        new = request.form["etat"]

        if inc["etat"] != new:
            db.execute("UPDATE incidents SET etat=? WHERE id=?", (new, id))
            hist_sql = """
              INSERT INTO historique (
                incident_id, champ, ancienne_valeur,
                nouvelle_valeur, modifie_par, date_modification
              ) VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute(
                hist_sql,
                (
                    id,
                    "etat",
                    inc["etat"],
                    new,
                    session["user"],
                    datetime.now().strftime("%d-%m-%Y %H:%M"),
                ),
            )

            # ⭐ NOUVEAU : Notification de changement de statut
            emit_status_change_notification(
                socketio,
                id,
                inc["numero"],
                inc["etat"],
                new,
                inc["collaborateur"]
            )

            # Si passage à un état critique sur ticket urgent
            if is_urgent(inc["urgence"]) and new in ["Suspendu", "En intervention"]:
                emit_urgent_update_notification(
                    socketio,
                    id,
                    inc["numero"],
                    f"Statut changé: {new}",
                    inc["collaborateur"]
                )

        db.commit()
        socketio.emit("incident_update", {"action": "etat"})
    except Exception as e:
        db.rollback()
        app.logger.error(f"Erreur update_etat: {e}")
        flash("Conflit de modification", "warning")

    return redirect(url_for("home"))
```

---

## Modifications à apporter à `templates/home.html`

### Ajouter avant la fermeture `</body>` :

```html
<!-- Système de notifications -->
<script src="{{ url_for('static', filename='js/notification_system.js') }}"></script>

<script>
// Intégration avec Socket.IO existant
socket.on('notification', function(data) {
    // Filtrer les notifications selon le rôle et l'utilisateur
    const currentUser = '{{ session.user }}';
    const currentRole = '{{ session.role }}';

    // Les admins reçoivent toutes les notifications
    // Les techniciens ne reçoivent que leurs notifications
    if (currentRole === 'admin' || data.technicien === currentUser) {
        // Router vers la bonne méthode selon le type
        switch(data.type) {
            case 'new_assignment':
            case 'reassignment_new':
                window.notificationSystem.notifyNewAssignment(data);
                break;

            case 'status_change':
                window.notificationSystem.notifyStatusChange(data);
                break;

            case 'urgent_update':
                window.notificationSystem.notifyUrgentUpdate(data);
                break;

            case 'reassignment_removed':
                window.notificationSystem.addNotification({
                    type: 'info',
                    priority: 'info',
                    title: '📤 Ticket réaffecté',
                    message: `${data.numero} a été réaffecté à ${data.to_technicien}`,
                    incident_id: data.incident_id
                });
                break;
        }
    }
});
</script>
```

---

## Test du système

### 1. Tester l'ajout d'un ticket

1. Se connecter en tant qu'admin
2. Ajouter un nouveau ticket et l'assigner à un technicien
3. **Attendu :**
   - Le technicien reçoit une notification avec le 🔔
   - Badge rouge avec le nombre de notifications non lues
   - Son de notification (si activé)
   - Si ticket urgent → notification rouge + son d'alerte

### 2. Tester la réaffectation

1. Changer le technicien d'un ticket existant
2. **Attendu :**
   - L'ancien technicien reçoit "Ticket réaffecté"
   - Le nouveau technicien reçoit "Nouveau ticket assigné"

### 3. Tester le changement de statut

1. Changer le statut d'un ticket
2. **Attendu :**
   - Notification "Changement de statut"
   - Si ticket urgent + statut critique → notification urgente

### 4. Tester les permissions desktop

1. Autoriser les notifications desktop (navigateur)
2. Ajouter un ticket urgent
3. **Attendu :**
   - Notification Windows/Mac/Linux apparaît
   - Clic sur la notification → focus sur le ticket

---

## Configuration avancée

### Désactiver le son par défaut

Dans `notification_system.js`, ligne 7, changer :
```javascript
this.soundEnabled = localStorage.getItem('notification_sound') !== 'false';
```

Par :
```javascript
this.soundEnabled = localStorage.getItem('notification_sound') === 'true';
```

### Changer la durée de conservation

Dans `notification_system.js`, ligne 437, changer :
```javascript
const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
```

Par :
```javascript
const weekAgo = Date.now() - (3 * 24 * 60 * 60 * 1000); // 3 jours
```

### Personnaliser les sons

Modifier les fréquences dans `notification_system.js`, ligne 220 :
```javascript
const frequencies = {
    urgent: [800, 1000, 800],  // Son d'alerte
    normal: [600, 800],         // Son doux
    info: [500]                 // Son simple
};
```

---

## Dépannage

### Les notifications n'apparaissent pas

1. Vérifier que le script est chargé :
   ```javascript
   console.log(window.notificationSystem); // Doit afficher l'objet
   ```

2. Vérifier les logs Socket.IO :
   ```javascript
   socket.on('notification', (data) => {
       console.log('Notification reçue:', data);
   });
   ```

3. Vérifier la console pour les erreurs JS

### Le badge ne se met pas à jour

1. Recharger la page (F5)
2. Vérifier localStorage :
   ```javascript
   localStorage.getItem('dispatch_notifications');
   ```

### Le son ne joue pas

1. Vérifier que le son est activé (clic sur 🔊)
2. Vérifier les permissions du navigateur (son autorisé)
3. Tester manuellement :
   ```javascript
   window.notificationSystem.playNotificationSound('urgent');
   ```

---

**Temps d'implémentation estimé : 30 minutes**

**Fichiers modifiés :**
- `app.py` (3 routes)
- `templates/home.html` (1 script)

**Fichiers créés :**
- `notification_helpers.py` ✅
- `static/js/notification_system.js` ✅

---

**Bon courage ! 🚀**
