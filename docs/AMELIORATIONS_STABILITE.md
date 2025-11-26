# Plan d'Amélioration de la Stabilité et des Performances

## 📋 Résumé des problèmes identifiés

### 1. **Gestion des erreurs backend (app.py)**
- ❌ Plusieurs routes manquent de try/except appropriés
- ❌ Pas de gestion cohérente des transactions DB
- ❌ Risques de demi-écritures (ticket créé sans historique)
- ❌ Fermeture de connexions DB incohérente
- ❌ Pas de gestion des conflits d'écriture concurrente

### 2. **JavaScript frontend**
- ❌ Appels fetch sans gestion d'erreur `.catch()`
- ❌ Pas de retry sur échec réseau
- ❌ Race conditions possibles (double-clic rapide)
- ❌ Pas de feedback utilisateur clair pendant les actions

### 3. **Temps réel / Rafraîchissement**
- ✅ WebSocket déjà implémenté avec Socket.IO
- ⚠️ Rafraîchissement complet de la page au lieu de mises à jour partielles
- ⚠️ Pas de debouncing sur les actions rapides

### 4. **Performance SQL**
- ❌ Pas d'index sur les colonnes frequently queried (collaborateur, archived, etat)
- ❌ JOIN non optimisé dans les stats
- ❌ Pas de pagination sur les listes longues

### 5. **Actions concurrentes**
- ❌ Pas de système de verrou
- ❌ Pas de détection de modification simultanée
- ❌ Boutons non désactivés pendant l'action en cours

---

## 🎯 Solutions proposées

### Phase 1: Stabilité Backend (PRIORITÉ HAUTE)

#### A. Wrapper de transaction atomique
```python
from contextlib import contextmanager

@contextmanager
def db_transaction(conn=None):
    """Context manager pour des transactions atomiques PostgreSQL"""
    db = conn if conn else get_db()
    created_connection = conn is None

    try:
        db.execute("BEGIN")
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        app.logger.error(f"Transaction rollback: {e}")
        raise
    finally:
        if created_connection:
            db.close()
```

#### B. Décorateur de gestion d'erreur uniforme
```python
from functools import wraps

def handle_errors(f):
    """Décorateur pour gérer les erreurs de manière cohérente"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Erreur dans {f.__name__}: {e}", exc_info=True)
            if request.is_json:
                return jsonify({"error": "Erreur serveur", "details": str(e)}), 500
            else:
                flash("Une erreur est survenue. Veuillez réessayer.", "danger")
                return redirect(url_for("home"))
    return decorated_function
```

#### C. Récriture des routes critiques avec transactions

**Exemple: assign_incident (ligne 383)**
```python
@app.route("/incidents/assign", methods=["POST"])
@handle_errors
def assign_incident():
    if "user" not in session or session["role"] != "admin":
        return jsonify({"error": "Non autorisé"}), 403

    incident_id = request.form.get("id")
    new_collab = request.form.get("collaborateur")

    if not incident_id or not new_collab:
        return jsonify({"error": "Paramètres manquants"}), 400

    with db_transaction() as db:
        # Récupérer l'incident
        incident = db.execute(
            "SELECT * FROM incidents WHERE id=?", (incident_id,)
        ).fetchone()

        if not incident:
            return jsonify({"error": "Incident introuvable"}), 404

        old_collab = incident['collaborateur']

        # Mise à jour atomique
        db.execute(
            "UPDATE incidents SET collaborateur=? WHERE id=?",
            (new_collab, incident_id)
        )

        # Historique dans la même transaction
        db.execute("""
            INSERT INTO historique (
                incident_id, champ, ancienne_valeur,
                nouvelle_valeur, modifie_par, date_modification
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            incident_id, "collaborateur", old_collab,
            new_collab, session["user"],
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ))

    # Notifier via WebSocket APRÈS le commit
    socketio.emit("incident_update", {
        "action": "reassign",
        "incident_id": incident_id,
        "old_collab": old_collab,
        "new_collab": new_collab
    }, broadcast=True)

    return jsonify({"status": "ok"})
```

---

### Phase 2: Frontend robuste (PRIORITÉ HAUTE)

#### A. Wrapper fetch avec retry et gestion d'erreur
```javascript
// Ajouter dans home_content.html
async function fetchWithRetry(url, options = {}, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return response;
        } catch (error) {
            console.error(`Tentative ${i + 1} échouée:`, error);

            if (i === retries - 1) {
                // Dernière tentative échouée
                showNotification('Erreur réseau. Veuillez réessayer.', 'danger');
                throw error;
            }

            // Attendre avant de réessayer (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
    }
}

function showNotification(message, type = 'info') {
    // Créer une notification Bootstrap toast
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    const container = document.getElementById('toast-container') || (() => {
        const c = document.createElement('div');
        c.id = 'toast-container';
        c.className = 'toast-container position-fixed top-0 end-0 p-3';
        c.style.zIndex = '9999';
        document.body.appendChild(c);
        return c;
    })();

    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    setTimeout(() => toast.remove(), 5000);
}
```

#### B. Désactivation des boutons pendant l'action
```javascript
function disableButtonDuringAction(button, action) {
    const originalText = button.innerHTML;
    const originalDisabled = button.disabled;

    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>En cours...';

    return action()
        .finally(() => {
            button.disabled = originalDisabled;
            button.innerHTML = originalText;
        });
}

// Utilisation:
document.addEventListener('click', function(e) {
    if (e.target.matches('.delete-btn')) {
        const button = e.target;
        const incidentId = button.dataset.incidentId;
        const numero = button.dataset.numero;

        if (!confirm(`Supprimer le ticket ${numero} ?`)) return;

        disableButtonDuringAction(button, async () => {
            await fetchWithRetry(`/delete_incident/${incidentId}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            });

            showNotification(`Ticket ${numero} supprimé`, 'success');
        }).catch(error => {
            console.error('Erreur suppression:', error);
        });
    }
});
```

#### C. Debouncing pour éviter les double-clics
```javascript
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Appliquer sur les changements de statut
const handleStatusChange = debounce(async function(incidentId, newStatus) {
    window._statusUpdateInProgress = true;

    try {
        await fetchWithRetry(`/update_etat/${incidentId}`, {
            method: 'POST',
            body: new URLSearchParams({ etat: newStatus })
        });

        showNotification('Statut mis à jour', 'success');
    } catch (error) {
        console.error('Erreur mise à jour statut:', error);
    } finally {
        setTimeout(() => {
            window._statusUpdateInProgress = false;
        }, 500);
    }
}, 300);
```

---

### Phase 3: Optimisation SQL (PRIORITÉ MOYENNE)

#### A. Création des index
```sql
-- À exécuter via maintenance/migrations/apply_indexes.py

CREATE INDEX IF NOT EXISTS idx_incidents_collaborateur ON incidents(collaborateur);
CREATE INDEX IF NOT EXISTS idx_incidents_archived ON incidents(archived);
CREATE INDEX IF NOT EXISTS idx_incidents_etat ON incidents(etat);
CREATE INDEX IF NOT EXISTS idx_incidents_date_affectation ON incidents(date_affectation);
CREATE INDEX IF NOT EXISTS idx_incidents_site ON incidents(site);
CREATE INDEX IF NOT EXISTS idx_historique_incident_id ON historique(incident_id);

-- Index composites pour requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_incidents_collab_archived ON incidents(collaborateur, archived);
CREATE INDEX IF NOT EXISTS idx_incidents_archived_etat ON incidents(archived, etat);
```

#### B. Optimisation des requêtes dans app.py
```python
# Ligne 146-148: Utiliser JOIN au lieu de filtrage côté app
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    db = get_db()
    if session["role"] == "admin":
        # Optimisé: récupérer uniquement les incidents nécessaires
        incidents = db.execute("""
            SELECT i.*, s.couleur as statut_couleur, s.category as statut_category
            FROM incidents i
            LEFT JOIN statuts s ON i.etat = s.nom
            WHERE i.archived=0
            ORDER BY i.id ASC
            LIMIT 500
        """).fetchall()

        techniciens = db.execute(
            "SELECT * FROM techniciens WHERE actif=1 ORDER BY prenom"
        ).fetchall()
    else:
        incidents = db.execute("""
            SELECT i.*, s.couleur as statut_couleur, s.category as statut_category
            FROM incidents i
            LEFT JOIN statuts s ON i.etat = s.nom
            WHERE i.collaborateur=? AND i.archived=0
            ORDER BY i.id ASC
            LIMIT 200
        """, (session["user"],)).fetchall()
        techniciens = []

    # Récupérer les métadonnées en une fois
    priorites = db.execute("SELECT * FROM priorites ORDER BY niveau").fetchall()
    sites = db.execute("SELECT * FROM sites ORDER BY nom").fetchall()
    statuts = db.execute("SELECT * FROM statuts ORDER BY nom").fetchall()

    # Stats optimisées avec une seule requête
    stats_by_category = {}
    if session["role"] == "admin":
        stats = db.execute("""
            SELECT
                s.category,
                COUNT(*) as count
            FROM incidents i
            JOIN statuts s ON i.etat = s.nom
            WHERE i.archived = 0
            GROUP BY s.category
        """).fetchall()

        stats_by_category = {row['category']: row['count'] for row in stats}

    db.close()

    return render_template(
        "home.html",
        incidents=incidents,
        user=session["user"].capitalize(),
        role=session["role"],
        techniciens=techniciens,
        priorites=priorites,
        sites=sites,
        statuts=statuts,
        stats_by_category=stats_by_category,
    )
```

---

### Phase 4: Actions concurrentes (PRIORITÉ MOYENNE)

#### A. Ajout d'un champ `updated_at` et `version` (détection optimiste de conflit)
```sql
-- Migration à ajouter
ALTER TABLE incidents ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE incidents ADD COLUMN version INTEGER DEFAULT 1;

-- Trigger PostgreSQL pour auto-update
CREATE OR REPLACE FUNCTION update_incidents_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER incidents_update_trigger
BEFORE UPDATE ON incidents
FOR EACH ROW
EXECUTE FUNCTION update_incidents_timestamp();
```

#### B. Vérification de version lors des mises à jour
```python
@app.route("/update_etat/<int:id>", methods=["POST"])
@handle_errors
def update_etat(id):
    if "user" not in session:
        return jsonify({"error": "Non authentifié"}), 403

    new_etat = request.form.get("etat")
    expected_version = request.form.get("version")  # Envoyé par le frontend

    if not new_etat:
        return jsonify({"error": "État manquant"}), 400

    with db_transaction() as db:
        inc = db.execute(
            "SELECT * FROM incidents WHERE id=?", (id,)
        ).fetchone()

        if not inc:
            return jsonify({"error": "Incident introuvable"}), 404

        # Vérification de version (optimistic locking)
        if expected_version and int(expected_version) != inc['version']:
            return jsonify({
                "error": "conflit_modification",
                "message": "Ce ticket a été modifié par quelqu'un d'autre. Rechargez la page."
            }), 409

        if inc["etat"] != new_etat:
            # Mise à jour avec version check
            result = db.execute("""
                UPDATE incidents
                SET etat=?, version=version+1, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND version=?
            """, (new_etat, id, inc['version']))

            if result.rowcount == 0:
                return jsonify({
                    "error": "conflit_modification",
                    "message": "Conflit détecté. Rechargez la page."
                }), 409

            # Historique
            db.execute("""
                INSERT INTO historique (
                    incident_id, champ, ancienne_valeur,
                    nouvelle_valeur, modifie_par, date_modification
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                id, "etat", inc["etat"], new_etat,
                session["user"],
                datetime.now().strftime("%d-%m-%Y %H:%M")
            ))

    # WebSocket après commit
    socketio.emit("incident_update", {
        "action": "etat",
        "incident_id": id,
        "new_etat": new_etat,
        "version": inc['version'] + 1
    }, broadcast=True)

    return jsonify({"status": "ok", "version": inc['version'] + 1})
```

#### C. Frontend: Envoyer la version et gérer les conflits
```javascript
document.addEventListener('change', async function(e) {
    if (e.target.matches('.status-selector-col')) {
        const incidentId = e.target.dataset.incidentId;
        const newStatus = e.target.value;
        const currentStatus = e.target.dataset.current;
        const version = e.target.dataset.version;  // Nouveau

        if (newStatus === currentStatus) return;

        window._statusUpdateInProgress = true;

        try {
            const response = await fetchWithRetry('/update_etat/' + incidentId, {
                method: 'POST',
                body: new URLSearchParams({
                    etat: newStatus,
                    version: version
                })
            });

            const data = await response.json();

            if (data.status === 'ok') {
                e.target.dataset.current = newStatus;
                e.target.dataset.version = data.version;  // Mettre à jour la version
                showNotification('Statut mis à jour', 'success');
            }
        } catch (error) {
            if (error.message.includes('409')) {
                // Conflit détecté
                showNotification(
                    'Ce ticket a été modifié par quelqu\'un d\'autre. Rechargement...',
                    'warning'
                );
                setTimeout(() => window.location.reload(), 2000);
            } else {
                console.error('Erreur:', error);
                e.target.value = currentStatus;  // Restaurer l'ancienne valeur
            }
        } finally {
            setTimeout(() => {
                window._statusUpdateInProgress = false;
            }, 500);
        }
    }
});
```

---

### Phase 5: Mise à jour temps réel optimisée (PRIORITÉ BASSE)

#### A. Rafraîchissement partiel au lieu de complet
```javascript
// Remplacer refreshIncidents() par updateIncidentCard()
function updateIncidentCard(incidentId, updates) {
    const cards = document.querySelectorAll(`.incident-card-col[data-id="${incidentId}"]`);

    cards.forEach(card => {
        if (updates.etat) {
            const statusBadge = card.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.textContent = updates.etat;
                // Mettre à jour la couleur si disponible
                if (updates.etat_couleur) {
                    statusBadge.style.backgroundColor = updates.etat_couleur;
                }
            }

            const statusSelector = card.querySelector('.status-selector-col');
            if (statusSelector) {
                statusSelector.value = updates.etat;
                statusSelector.dataset.current = updates.etat;
            }
        }

        if (updates.collaborateur) {
            // Déplacer la carte vers la colonne du nouveau technicien
            const newColumn = document.querySelector(
                `.incident-list-col[data-technicien="${updates.collaborateur}"]`
            );
            if (newColumn) {
                newColumn.appendChild(card);
                // Animation de déplacement
                card.style.animation = 'highlight 0.5s ease';
                setTimeout(() => {
                    card.style.animation = '';
                }, 500);
            }
        }

        if (updates.note) {
            const noteContent = card.querySelector('.note-view-content');
            if (noteContent) {
                noteContent.textContent = updates.note;
            }
        }

        if (updates.version) {
            const selectors = card.querySelectorAll('[data-version]');
            selectors.forEach(el => el.dataset.version = updates.version);
        }
    });
}

// Écouter les mises à jour spécifiques
socket.on('incident_update', (data) => {
    if (data.action === 'etat' && data.incident_id) {
        updateIncidentCard(data.incident_id, {
            etat: data.new_etat,
            version: data.version
        });
    } else if (data.action === 'reassign' && data.incident_id) {
        updateIncidentCard(data.incident_id, {
            collaborateur: data.new_collab,
            version: data.version
        });
    } else if (data.action === 'note_edit' && data.incident_id) {
        updateIncidentCard(data.incident_id, {
            note: data.new_note,
            version: data.version
        });
    } else {
        // Fallback: rafraîchissement complet pour les autres actions
        refreshIncidents();
    }
});
```

---

## 📊 Tableau de priorités

| Amélioration | Priorité | Impact | Complexité | Ordre |
|-------------|----------|--------|------------|-------|
| Transactions atomiques backend | 🔴 HAUTE | Très élevé | Moyenne | 1 |
| Gestion d'erreurs uniformes | 🔴 HAUTE | Élevé | Faible | 2 |
| Retry + feedback frontend | 🔴 HAUTE | Élevé | Faible | 3 |
| Désactivation boutons pendant action | 🔴 HAUTE | Moyen | Faible | 4 |
| Index SQL | 🟡 MOYENNE | Élevé | Faible | 5 |
| Optimisation requêtes | 🟡 MOYENNE | Moyen | Moyenne | 6 |
| Gestion conflits (version) | 🟡 MOYENNE | Moyen | Moyenne | 7 |
| Rafraîchissement partiel | 🟢 BASSE | Moyen | Élevée | 8 |

---

## ✅ Critères d'acceptation

### Tests à effectuer après implémentation:

1. **Stabilité**
   - [ ] Changer un statut → pas d'erreur console, historique créé
   - [ ] Affecter un technicien → pas d'erreur 500, historique créé
   - [ ] Ajouter un ticket → créé avec historique initial
   - [ ] Modifier une note → sauvegardée avec historique
   - [ ] Supprimer un ticket → supprimé proprement avec historique

2. **Actions concurrentes**
   - [ ] 2 admins changent le statut du même ticket en même temps → conflit détecté et message clair
   - [ ] Double-clic rapide sur "Supprimer" → une seule suppression
   - [ ] Modification note pendant changement de statut → pas de conflit

3. **Réseau**
   - [ ] Simuler coupure réseau (DevTools Offline) → retry automatique + message d'erreur
   - [ ] Requête lente → bouton désactivé + spinner visible

4. **Performance**
   - [ ] Dashboard avec 50+ tickets charge en < 2s
   - [ ] Filtres appliqués en < 500ms
   - [ ] Rafraîchissement après action en < 1s

5. **Temps réel**
   - [ ] Admin change statut → technicien voit la mise à jour sans F5
   - [ ] Nouveau ticket ajouté → apparaît dans dashboard sans F5
   - [ ] Technicien modifie note → admin voit la mise à jour

---

## 🚀 Prochaines étapes

1. Valider ce plan avec l'équipe
2. Créer une branche Git `feature/stability-improvements`
3. Implémenter phase par phase (1 semaine par phase)
4. Tests unitaires + tests d'intégration
5. Déploiement progressif (staging → production)
