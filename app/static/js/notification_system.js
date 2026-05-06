class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.unreadCount = 0;
        this.soundEnabled = localStorage.getItem('notification_sound') !== 'false';
        this.loadNotifications();
        this.initializeUI();
        this.requestNotificationPermission();

        // Check for incident to open from URL after a short delay to let the dashboard load
        setTimeout(() => this.checkUrlParams(), 1000);

        // Cross-tab synchronization
        window.addEventListener('storage', (e) => {
            const storageKey = `dispatch_notifications_${window.CURRENT_USER || 'guest'}`;
            if (e.key === storageKey && e.newValue) {
                try {
                    const parsed = JSON.parse(e.newValue);
                    const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
                    this.notifications = parsed.notifications
                        .filter(n => new Date(n.timestamp).getTime() > weekAgo)
                        .map(n => ({ ...n, timestamp: new Date(n.timestamp) }));
                    this.updateBadge();
                    const panel = document.getElementById('notificationPanel');
                    if (panel && panel.style.display !== 'none') {
                        this.renderNotifications();
                    }
                } catch (err) {
                    console.error("Error syncing notifications across tabs", err);
                }
            }
        });
    }

    /**
     * Vérifie les paramètres de l'URL pour des actions automatiques
     */
    checkUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const incidentId = params.get('open_incident');
        if (incidentId) {
            console.log('🔍 Tentative d\'ouverture auto de l\'incident:', incidentId);

            // Remove query param from URL without refreshing
            const newUrl = window.location.pathname + window.location.search.replace(/[?&]open_incident=[^&]+/, '').replace(/^&/, '?');
            window.history.replaceState({}, document.title, newUrl);

            this.scrollToIncident(incidentId);
        }
    }

    /**
     * Initialise l'interface utilisateur des notifications
     */
    initializeUI() {
        // ⚠️ ANTI-DUPLICATION : Vérifier si déjà initialisé
        if (document.getElementById('notificationBell')) {
            console.warn('Système de notifications déjà initialisé, skip');
            return;
        }

        // Créer le conteneur de notifications dans la navbar
        const navbar = document.querySelector('.navbar .container-fluid');
        if (!navbar) {
            console.warn('Navbar non trouvée, système de notifications désactivé');
            return;
        }

        const notifButton = document.createElement('div');
        notifButton.className = 'position-relative me-2'; // me-2 pour espacement
        notifButton.innerHTML = `
            <button class="btn btn-outline-secondary btn-sm position-relative" id="notificationBell" title="Notifications">
                🔔
                <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger"
                      id="notificationBadge" style="display: none;">
                    0
                </span>
            </button>
        `;

        // ⚠️ PLACEMENT : Insérer AVANT le toggle thème (bouton 🌙/☀️)
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle && themeToggle.parentElement) {
            // Insérer avant le toggle thème
            themeToggle.parentElement.insertBefore(notifButton, themeToggle.parentElement.firstChild);
        } else {
            // Fallback : avant le bouton de déconnexion
            const logoutBtn = navbar.querySelector('a[href*="logout"]');
            if (logoutBtn && logoutBtn.parentElement) {
                logoutBtn.parentElement.insertBefore(notifButton, logoutBtn.parentElement.firstChild);
            } else {
                navbar.appendChild(notifButton);
            }
        }

        // Créer le panneau de notifications
        this.createNotificationPanel();

        // Event listeners
        const bell = document.getElementById('notificationBell');
        if (bell) {
            bell.addEventListener('click', () => this.togglePanel());
            document.addEventListener('click', (e) => {
                if (!e.target.closest('#notificationBell') && !e.target.closest('#notificationPanel')) {
                    this.closePanel();
                }
            });
        }
    }

    /**
     * Crée le panneau déroulant des notifications
     */
    createNotificationPanel() {
        const panel = document.createElement('div');
        panel.id = 'notificationPanel';
        panel.className = 'notification-panel';
        panel.style.display = 'none';
        panel.innerHTML = `
            <div class="notification-panel-header">
                <h6 class="mb-0">Notifications</h6>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-link p-0" id="notifSoundToggle" title="Activer/Désactiver le son">
                        ${this.soundEnabled ? '🔊' : '🔇'}
                    </button>
                    <button class="btn btn-sm btn-link p-0" id="markAllRead" title="Tout marquer comme lu">
                        ✓
                    </button>
                    <button class="btn btn-sm btn-link p-0" id="clearNotifications" title="Effacer tout">
                        🗑️
                    </button>
                </div>
            </div>
            <div class="notification-panel-body" id="notificationList">
                <div class="text-center text-muted py-3">
                    <small>Aucune notification</small>
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // Event listeners avec vérifications
        const soundToggle = document.getElementById('notifSoundToggle');
        const markAllRead = document.getElementById('markAllRead');
        const clearNotifs = document.getElementById('clearNotifications');

        if (soundToggle) soundToggle.addEventListener('click', () => this.toggleSound());
        if (markAllRead) markAllRead.addEventListener('click', () => this.markAllAsRead());
        if (clearNotifs) clearNotifs.addEventListener('click', () => this.clearAll());
    }

    /**
     * Demande la permission pour les notifications desktop
     */
    async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            await Notification.requestPermission();
        }
    }

    /**
     * Toggle le panneau de notifications
     */
    togglePanel() {
        const panel = document.getElementById('notificationPanel');
        if (panel.style.display === 'none') {
            this.openPanel();
        } else {
            this.closePanel();
        }
    }

    /**
     * Ouvre le panneau de notifications
     */
    openPanel() {
        const panel = document.getElementById('notificationPanel');
        const button = document.getElementById('notificationBell');
        const rect = button.getBoundingClientRect();

        panel.style.display = 'block';
        panel.style.top = `${rect.bottom + 10}px`;
        panel.style.right = `${window.innerWidth - rect.right}px`;

        this.renderNotifications();
    }

    /**
     * Ferme le panneau de notifications
     */
    closePanel() {
        document.getElementById('notificationPanel').style.display = 'none';
    }

    /**
     * Ajoute une nouvelle notification
     */
    addNotification(notification) {
        const notif = {
            id: Date.now() + Math.random(),
            timestamp: new Date(),
            read: false,
            ...notification
        };

        this.notifications.unshift(notif);

        // Limiter à 50 notifications
        if (this.notifications.length > 50) {
            this.notifications = this.notifications.slice(0, 50);
        }

        this.updateBadge();
        this.renderNotifications();

        // Jouer un son selon la priorité
        if (this.soundEnabled) {
            this.playNotificationSound(notification.priority);
        }

        // Notification desktop (si autorisée)
        this.showDesktopNotification(notification);

        // Sauvegarder dans localStorage
        this.saveNotifications();
    }

    /**
     * Notification pour un nouveau ticket assigné
     */
    notifyNewAssignment(data) {
        const { incident_id, numero, site, sujet, urgence, technicien, note_dispatch, is_urgent } = data;

        const isUrgent = is_urgent === true;
        const priority = isUrgent ? 'urgent' : 'normal';

        const displayNumero = numero || 'N/A';
        const displaySite = site || 'Site inconnu';
        const displaySujet = sujet || 'Sans sujet';
        const byText = data.triggered_by_display ? ` (par ${data.triggered_by_display})` : '';

        this.addNotification({
            type: 'new_assignment',
            priority: priority,
            title: (isUrgent ? '🚨 URGENT - Nouveau ticket' : '📋 Nouveau ticket assigné') + byText,
            message: `${displayNumero} - ${displaySite} / ${displaySujet}`,
            details: note_dispatch || '',
            urgence: urgence,
            incident_id: incident_id,
            action: {
                label: 'Voir le ticket',
                type: 'scroll_to_incident',
                incident_id: incident_id
            }
        });

        // Auto-refresh the dashboard so the tech doesn't need to press F5
        setTimeout(() => {
            if (window.refreshIncidents) {
                window.refreshIncidents();
            } else if (window.scheduleIncidentReload && incident_id) {
                window.scheduleIncidentReload(incident_id);
            } else if (window.requestBulkRefresh) {
                window.requestBulkRefresh('new_assignment');
            }
        }, 1500);
    }

    /**
     * Notification pour un changement de statut
     */
    notifyStatusChange(data) {
        const { incident_id, numero, old_status, new_status } = data;
        const byText = data.triggered_by_display ? ` (par ${data.triggered_by_display})` : '';

        this.addNotification({
            type: 'status_change',
            priority: 'info',
            title: '🔄 Changement de statut' + byText,
            message: `${numero}: ${old_status} → ${new_status}`,
            incident_id: incident_id,
            action: {
                label: 'Voir',
                type: 'scroll_to_incident',
                incident_id: incident_id
            }
        });
    }

    /**
     * Notification pour un ticket urgent modifié
     */
    notifyUrgentUpdate(data) {
        const { incident_id, numero, message } = data;
        const byText = data.triggered_by_display ? ` (par ${data.triggered_by_display})` : '';

        this.addNotification({
            type: 'urgent_update',
            priority: 'urgent',
            title: '⚠️ Mise à jour urgente' + byText,
            message: `${numero}: ${message}`,
            incident_id: incident_id,
            action: {
                label: 'Voir',
                type: 'scroll_to_incident',
                incident_id: incident_id
            }
        });
    }

    /**
     * Notification pour une demande de mise à jour Wiki
     */
    notifyWikiUpdateRequested(data) {
        const { article_id, title, requested_by, request_type } = data;
        const reason = request_type === 'outdated' ? 'Signalé obsolète' : 'Mise à jour demandée';

        this.addNotification({
            type: 'wiki_update_requested',
            priority: 'info',
            title: `📝 ${reason}`,
            message: `${title || 'Article'} — par ${requested_by || 'quelqu\'un'}`,
            action: article_id ? {
                label: "Voir l'article",
                type: 'link',
                url: `/wiki/article/${article_id}`
            } : null
        });
    }

    /**
     * Rendu des notifications dans le panneau
     */
    renderNotifications() {
        const listContainer = document.getElementById('notificationList');

        if (this.notifications.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <small>Aucune notification</small>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = this.notifications.map(notif => `
            <div class="notification-item ${notif.read ? 'read' : 'unread'} ${notif.priority}"
                 data-id="${notif.id}">
                <div class="notification-content">
                    <div class="notification-title">
                        ${notif.title}
                        ${!notif.read ? '<span class="badge bg-primary ms-1" style="font-size: 0.6rem;">NEW</span>' : ''}
                    </div>
                    <div class="notification-message">${notif.message}</div>
                    ${notif.details ? `<div class="notification-details">${notif.details}</div>` : ''}
                    ${notif.urgence ? `<span class="badge ${this.getUrgencyClass(notif.urgence)} mt-1">${notif.urgence}</span>` : ''}
                    <div class="notification-time">${this.formatTime(notif.timestamp)}</div>
                </div>
                <div class="notification-actions">
                    ${notif.action ? `
                        <button class="btn btn-sm btn-primary notif-action-btn" data-id="${notif.id}">
                            ${notif.action.label}
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-secondary notif-dismiss-btn" data-id="${notif.id}">
                        ✕
                    </button>
                </div>
            </div>
        `).join('');

        // Event listeners pour les actions
        listContainer.querySelectorAll('.notif-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const notifId = parseFloat(btn.dataset.id);
                this.handleNotificationAction(notifId);
            });
        });

        listContainer.querySelectorAll('.notif-dismiss-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const notifId = parseFloat(btn.dataset.id);
                this.removeNotification(notifId);
            });
        });

        // Marquer comme lu au clic sur l'item (mais pas sur les boutons)
        listContainer.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('button')) {
                    const notifId = parseFloat(item.dataset.id);
                    this.markAsRead(notifId);
                }
            });
        });
    }

    /**
     * Gère l'action d'une notification (redirection, scroll, etc.)
     */
    handleNotificationAction(notifId) {
        const notif = this.notifications.find(n => n.id === notifId);
        if (!notif || !notif.action) return;

        const action = notif.action;
        this.markAsRead(notifId);
        this.closePanel();

        if (action.type === 'scroll_to_incident') {
            this.scrollToIncident(action.incident_id);
        } else if (action.type === 'link') {
            window.location.href = action.url;
        }
    }

    /**
     * Met à jour le badge de notifications non lues
     */
    updateBadge() {
        this.unreadCount = this.notifications.filter(n => !n.read).length;
        const badge = document.getElementById('notificationBadge');
        if (!badge) return;

        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }

    /**
     * Marque une notification comme lue
     */
    markAsRead(notifId) {
        const notif = this.notifications.find(n => n.id === notifId);
        if (notif && !notif.read) {
            notif.read = true;
            this.updateBadge();
            this.renderNotifications();
            this.saveNotifications();
        }
    }

    /**
     * Marque toutes les notifications comme lues
     */
    markAllAsRead() {
        this.notifications.forEach(n => n.read = true);
        this.updateBadge();
        this.renderNotifications();
        this.saveNotifications();
    }

    /**
     * Supprime une notification
     */
    removeNotification(notifId) {
        this.notifications = this.notifications.filter(n => n.id !== notifId);
        this.updateBadge();
        this.renderNotifications();
        this.saveNotifications();
    }

    /**
     * Efface toutes les notifications
     */
    clearAll() {
        if (confirm('Effacer toutes les notifications ?')) {
            this.notifications = [];
            this.updateBadge();
            this.renderNotifications();
            this.saveNotifications();
        }
    }

    /**
     * Toggle le son des notifications
     */
    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('notification_sound', this.soundEnabled);

        const btn = document.getElementById('notifSoundToggle');
        btn.textContent = this.soundEnabled ? '🔊' : '🔇';
        btn.title = this.soundEnabled ? 'Désactiver le son' : 'Activer le son';

        // Feedback sonore
        if (this.soundEnabled) {
            this.playNotificationSound('normal');
        }
    }

    /**
     * Joue un son de notification
     */
    playNotificationSound(priority = 'normal') {
        if (!this.soundEnabled) return;

        // Utiliser Web Audio API pour générer des sons
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        // Fréquences selon la priorité
        const frequencies = {
            urgent: [800, 1000, 800],  // Son d'alerte
            normal: [600, 800],         // Son doux
            info: [500]                 // Son simple
        };

        const freqSequence = frequencies[priority] || frequencies.normal;
        let time = audioContext.currentTime;

        freqSequence.forEach((freq, i) => {
            oscillator.frequency.setValueAtTime(freq, time);
            gainNode.gain.setValueAtTime(0.3, time);
            gainNode.gain.exponentialRampToValueAtTime(0.01, time + 0.15);
            time += 0.2;
        });

        oscillator.start(audioContext.currentTime);
        oscillator.stop(time);
    }

    /**
     * Affiche une notification desktop (navigateur)
     */
    showDesktopNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const options = {
                body: notification.message,
                icon: '/static/img/favicon.ico',
                badge: '/static/img/favicon.ico',
                tag: notification.incident_id ? `incident-${notification.incident_id}` : undefined,
                requireInteraction: notification.priority === 'urgent',
                silent: !this.soundEnabled
            };

            const desktopNotif = new Notification(notification.title, options);

            desktopNotif.onclick = () => {
                window.focus();
                if (notification.action) {
                    this.handleNotificationAction(notification.id);
                } else if (notification.incident_id) {
                    this.scrollToIncident(notification.incident_id);
                }
                desktopNotif.close();
            };

            // Auto-fermer après 10 secondes (sauf si urgent)
            if (notification.priority !== 'urgent') {
                setTimeout(() => desktopNotif.close(), 10000);
            }
        }
    }

    /**
     * Scroll vers un incident spécifique (avec redirection vers l'accueil si nécessaire)
     */
    scrollToIncident(incidentId) {
        console.log(`🚀 scrollToIncident called for: ${incidentId}`);
        // If not on the home page, redirect there with the open_incident parameter
        const path = window.location.pathname;
        if (path !== '/' && path !== '/home' && path !== '/home/') {
            console.log('🔄 Not on home page, redirecting...');
            window.location.href = '/?open_incident=' + incidentId;
            return;
        }

        // Si on est sur l'accueil, s'assurer que les filtres ne cachent pas le ticket
        if (window.resetFilters) {
            console.log('🧹 Resetting filters...');
            window.resetFilters();
        } else {
            console.log('🧹 Resetting filters (fallback)...');
            const search = document.getElementById('searchInput') || document.getElementById('searchInputTech');
            if (search) search.value = '';
            if (window.applySearchAndFilters) window.applySearchAndFilters();
            if (window.applyFiltersTech) window.applyFiltersTech();
        }

        let attempts = 0;
        const maxAttempts = 15; // Increased

        const findAndScroll = () => {
            console.log(`🔍 findAndScroll attempt ${attempts + 1}/${maxAttempts}`);
            const cards = document.querySelectorAll(`[data-incident-id="${incidentId}"]`);
            console.log(`Found ${cards.length} cards with id ${incidentId}`);

            if (cards.length > 0) {
                // Determine which card to use. Try visible one first.
                let card = Array.from(cards).find(c => c.offsetParent !== null);

                if (!card) {
                    console.log('⚠️ No visible card found, trying to switch views...');
                    card = cards[0];
                    const viewContainer = card.closest('.view-container') || card.closest('#userView');

                    if (viewContainer) {
                        const viewId = viewContainer.id;
                        let viewName = viewId === 'userView' ? 'tech' : viewId.replace('-view', '');

                        if (window.switchView) {
                            console.log(`🔄 Force switching to view: ${viewName}`);
                            window.switchView(viewName);
                        }
                    }
                }

                // Wait a tiny bit for layout if we just switched views or cleared filters
                setTimeout(() => {
                    const finalCards = document.querySelectorAll(`[data-incident-id="${incidentId}"]`);
                    const finalCard = Array.from(finalCards).find(c => c.offsetParent !== null) || finalCards[0];

                    if (finalCard) {
                        console.log('📍 Final card identified, scrolling and animating...', finalCard);
                        finalCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

                        // Force animation re-trigger
                        finalCard.classList.remove('animate-highlight-pulse');
                        void finalCard.offsetWidth; // Trigger reflow
                        finalCard.classList.add('animate-highlight-pulse');
                        console.log('✨ Class animate-highlight-pulse added to card');

                        // S'assurer que le parent est visible (accordéon)
                        let parent = finalCard.parentElement;
                        while (parent) {
                            if (parent.classList.contains('collapse') && !parent.classList.contains('show')) {
                                console.log('📂 Opening parent collapse...');
                                const bsCollapse = bootstrap.Collapse.getInstance(parent) || new bootstrap.Collapse(parent);
                                bsCollapse.show();
                            }
                            parent = parent.parentElement;
                        }

                        setTimeout(() => {
                            finalCard.classList.remove('animate-highlight-pulse');
                            console.log('🏁 Animation class removed');
                        }, 6000);
                    }
                }, 150); // Small buffer for DOM to update
                return true;
            }

            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(findAndScroll, 600);
            } else {
                console.error(`❌ Incident ${incidentId} NOT FOUND after ${maxAttempts} attempts.`);
            }
            return false;
        };

        // Added a 100ms delay to findAndScroll to let resetFilters finish its job
        setTimeout(findAndScroll, 100);
    }

    /**
     * Formate un timestamp en texte relatif
     */
    formatTime(timestamp) {
        const now = new Date();
        const diff = now - timestamp;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'À l\'instant';
        if (minutes < 60) return `Il y a ${minutes} min`;
        if (hours < 24) return `Il y a ${hours}h`;
        if (days < 7) return `Il y a ${days}j`;
        return timestamp.toLocaleDateString('fr-FR');
    }

    /**
     * Retourne la classe CSS correspondant à l'urgence
     */
    getUrgencyClass(urgence) {
        if (!urgence) return 'bg-secondary';
        const u = urgence.toLowerCase();
        if (u.includes('critique')) return 'bg-danger';
        if (u.includes('haute')) return 'bg-danger';
        if (u.includes('moyenne')) return 'bg-warning text-dark';
        if (u.includes('basse')) return 'bg-info text-dark';
        return 'bg-secondary';
    }

    /**
     * Sauvegarde les notifications dans localStorage
     */
    saveNotifications() {
        try {
            const data = {
                notifications: this.notifications.slice(0, 50), // Garder jusqu'à 50 (comme dans addNotification)
                timestamp: Date.now()
            };
            const storageKey = `dispatch_notifications_${window.CURRENT_USER || 'guest'}`;
            localStorage.setItem(storageKey, JSON.stringify(data));
        } catch (e) {
            console.error('Erreur lors de la sauvegarde des notifications:', e);
        }
    }

    /**
     * Charge les notifications depuis localStorage
     */
    loadNotifications() {
        try {
            const storageKey = `dispatch_notifications_${window.CURRENT_USER || 'guest'}`;
            const data = localStorage.getItem(storageKey);
            if (data) {
                const parsed = JSON.parse(data);

                // Supprimer les notifications de plus de 7 jours
                const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
                this.notifications = parsed.notifications
                    .filter(n => new Date(n.timestamp).getTime() > weekAgo)
                    .map(n => ({ ...n, timestamp: new Date(n.timestamp) }));

                this.updateBadge();
            }
        } catch (e) {
            console.error('Erreur lors du chargement des notifications:', e);
        }
    }

    /**
     * Gère les mises à jour de configuration en temps réel (couleurs, etc.)
     */
    handleConfigUpdate(data) {
        const { config_type, item } = data;

        // Si pas d'item précis (ex: suppression), on peut proposer un refresh léger
        if (!item || !item.nom) {
            console.log(`🔄 Refresh suggéré pour type config: ${config_type}`);
            // Si on est sur une page qui supporte le refresh auto (home)
            if (window.loadIncidents) {
                window.loadIncidents();
            }
            return;
        }

        console.log(`🎨 Mise à jour dynamique des styles pour: ${config_type} (${item.nom} -> ${item.couleur || 'N/A'})`);

        let selector = '';
        let dataAttr = '';

        if (config_type === 'site') {
            selector = '.site-badge';
            dataAttr = 'data-site-name';
        } else if (config_type === 'priorite') {
            selector = '.priority-badge';
            dataAttr = 'data-priority-name';
        } else if (config_type === 'statut') {
            selector = '.status-badge';
            dataAttr = 'data-status-name';
        }

        if (selector && item.couleur) {
            const badges = document.querySelectorAll(`${selector}[${dataAttr}="${item.nom}"]`);
            const contrastColor = this.getContrastColor(item.couleur);

            badges.forEach(badge => {
                badge.style.setProperty('background-color', item.couleur, 'important');
                badge.style.setProperty('color', contrastColor, 'important');

                // Petit effet visuel pour montrer que ça a changé
                badge.style.transition = 'all 0.5s ease';
                badge.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    badge.style.transform = 'scale(1)';
                }, 500);
            });
        }
    }

    /**
     * Calcule une couleur de contraste (noir ou blanc) pour une couleur hex
     */
    getContrastColor(hexcolor) {
        if (!hexcolor || hexcolor.length < 3) return '#ffffff';

        let r, g, b;
        let hex = hexcolor.replace('#', '');

        if (hex.length === 3) {
            r = parseInt(hex[0] + hex[0], 16);
            g = parseInt(hex[1] + hex[1], 16);
            b = parseInt(hex[2] + hex[2], 16);
        } else if (hex.length === 6) {
            r = parseInt(hex.slice(0, 2), 16);
            g = parseInt(hex.slice(2, 4), 16);
            b = parseInt(hex.slice(4, 6), 16);
        } else {
            return '#ffffff';
        }

        // Formule YIQ pour la luminosité perçue
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        return (yiq >= 128) ? '#000000' : '#ffffff';
    }

    /**
     * Connecte le système aux événements Socket.IO globaux
     */
    connectSocket(socket) {
        if (!socket) return;

        console.log('🔗 Connexion du système de notifications au Socket.IO');

        socket.on('notification', (data) => {
            console.log('🔔 Notification reçue:', data.type, data);

            // Ignorer les notifications déclenchées par l'utilisateur actuel
            if (data.triggered_by_username && window.CURRENT_USER && data.triggered_by_username === window.CURRENT_USER) {
                console.log('🔇 Notification ignorée (déclenchée par l\'utilisateur lui-même)');
                return;
            }

            switch (data.type) {
                case 'new_assignment':
                case 'reassignment_new':
                    this.notifyNewAssignment(data);
                    break;
                case 'status_change':
                    this.notifyStatusChange(data);
                    break;
                case 'urgent_update':
                    this.notifyUrgentUpdate(data);
                    break;
                case 'wiki_update_requested':
                    this.notifyWikiUpdateRequested(data);
                    break;
                case 'config_updated':
                    this.handleConfigUpdate(data);
                    break;
                default:
                    console.log('Type de notification non géré:', data.type);
            }
        });
    }
}

// Styles CSS modernisés (Glassmorphism + Dark Mode support)
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification-panel {
        position: fixed;
        width: 400px;
        max-height: 600px;
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        z-index: 10001;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        animation: slideInDown 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .light-mode .notification-panel {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(0, 0, 0, 0.1);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    }

    /* Dark mode override */
    body:not(.light-mode) .notification-panel {
        background: rgba(30, 30, 45, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #e1e1e6;
    }

    .notification-panel-header {
        padding: 14px 18px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(255, 255, 255, 0.05);
    }

    .notification-panel-body {
        overflow-y: auto;
        max-height: 500px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
    }

    .notification-item {
        padding: 14px 18px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        gap: 12px;
        position: relative;
    }

    .notification-item:hover {
        background: rgba(255, 255, 255, 0.08);
    }

    .notification-item.unread {
        background: rgba(13, 110, 253, 0.1);
    }

    .notification-item.unread::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: #0d6efd;
    }

    .notification-item.urgent {
        background: rgba(220, 53, 69, 0.05);
    }

    .notification-item.urgent::before {
        background: #dc3545;
        width: 4px;
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
    }

    .notification-item.urgent.unread {
        background: rgba(220, 53, 69, 0.15);
        animation: urgentGlow 2s infinite;
    }

    .notification-content {
        flex: 1;
    }

    .notification-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 3px;
    }

    .notification-message {
        font-size: 0.85rem;
        opacity: 0.9;
        margin-bottom: 6px;
        line-height: 1.4;
    }

    .notification-details {
        font-size: 0.8rem;
        opacity: 0.7;
        font-style: italic;
        padding: 4px 8px;
        background: rgba(0, 0, 0, 0.1);
        border-radius: 4px;
        margin-bottom: 8px;
    }

    .notification-time {
        font-size: 0.75rem;
        opacity: 0.5;
    }

    .notification-actions {
        display: flex;
        flex-direction: column;
        gap: 6px;
        justify-content: center;
    }

    .notif-action-btn {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 6px;
        white-space: nowrap;
    }

    .notif-dismiss-btn {
        background: none;
        border: none;
        color: inherit;
        opacity: 0.4;
        transition: opacity 0.2s;
        padding: 4px;
        font-size: 1rem;
    }

    .notif-dismiss-btn:hover {
        opacity: 1;
    }

    @keyframes urgentGlow {
        0%, 100% { box-shadow: inset 0 0 0 rgba(220, 53, 69, 0); }
        50% { box-shadow: inset 0 0 15px rgba(220, 53, 69, 0.3); }
    }

    @keyframes slideInDown {
        from { opacity: 0; transform: translateY(-10px) scale(0.98); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }

    #notificationBadge {
        font-size: 0.65rem;
        padding: 0.35em 0.5em;
        border: 2px solid var(--bg-panel, #222);
    }

    .light-mode #notificationBadge {
        border-color: #fff;
    }

    @media (max-width: 768px) {
        .notification-panel {
            width: calc(100vw - 20px);
            right: 10px !important;
            left: 10px !important;
            max-height: 80vh;
        }
    }
`;
document.head.appendChild(notificationStyles);

// Pattern singleton avec connexion socket retardée pour s'assurer que window.socket existe
if (!window.notificationSystem) {
    window.notificationSystem = new NotificationSystem();
    window.notificationSystem.loadNotifications();
    console.log('✅ Système de notifications initialisé');

    // Attendre que le socket soit prêt
    const checkSocket = setInterval(() => {
        if (window.socket) {
            window.notificationSystem.connectSocket(window.socket);
            clearInterval(checkSocket);
        }
    }, 500);
} else {
    console.log('ℹ️ Système de notifications déjà actif');
}

// Handler global pour les utilisateurs connectés (toutes les pages)
(function initActiveConnectionsHandler() {
    const badge = document.getElementById('activeConnectionsBadge');
    if (!badge) return; // Pas de badge sur cette page
    
    function updateBadge(count, users) {
        const plural = count > 1 ? 'S' : '';
        const text = count === 0 ? '0 CONNECTÉ' : `${count} CONNECTÉ${plural}`;
        const newHtml = `<i class="fas fa-users me-1"></i> ${text}`;
        if (badge.innerHTML !== newHtml) {
            badge.innerHTML = newHtml;
            console.log(`👥 Utilisateurs connectés: ${count}`, users);
        }
        
        // Mettre à jour la liste déroulante
        const usersList = document.getElementById('connectedUsersList');
        if (usersList && users) {
            const headerStyle = 'color: #94a3b8; font-weight: 600; border-bottom: 1px solid #334155; padding: 8px 16px;';
            const itemStyle = 'color: #e2e8f0; padding: 6px 16px;';
            const emptyStyle = 'color: #94a3b8; padding: 8px 16px; font-style: italic;';
            
            if (users.length === 0) {
                usersList.innerHTML = `
                    <li class="dropdown-header" style="${headerStyle}">Utilisateurs connectés</li>
                    <li><span class="dropdown-item-text" style="${emptyStyle}"><i class="fas fa-user-slash me-2"></i>Aucun utilisateur connecté</span></li>
                `;
            } else {
                let html = `<li class="dropdown-header" style="${headerStyle}">${users.length} utilisateur${users.length > 1 ? 's' : ''} connecté${users.length > 1 ? 's' : ''}</li>`;
                users.forEach(user => {
                    html += `<li><span class="dropdown-item-text" style="${itemStyle}"><i class="fas fa-user-circle text-success me-2" style="color: #22c55e;"></i>${user}</span></li>`;
                });
                usersList.innerHTML = html;
            }
        }
    }
    
    // Handler Socket.IO
    function handleSocketData(data) {
        if (data && typeof data.count !== 'undefined') {
            updateBadge(data.count, data.users || []);
        }
    }
    
    // Attacher au socket dès qu'il est disponible
    function attachSocketHandler() {
        if (window.socket) {
            window.socket.off('active_connections_count', handleSocketData);
            window.socket.on('active_connections_count', handleSocketData);
            window.socket.emit('request_connection_count');
            console.log('✅ Handler socket attaché');
            return true;
        }
        return false;
    }
    
    // Fallback HTTP : interroger l'API toutes les 10 secondes
    async function fetchConnectionsHttp() {
        try {
            const response = await fetch('/api/active_connections', { 
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            if (response.ok) {
                const data = await response.json();
                if (data && typeof data.count !== 'undefined') {
                    updateBadge(data.count, data.users || []);
                    console.log('👥 Données HTTP reçues:', data.count);
                }
            }
        } catch (e) {
            console.log('⚠️ Fallback HTTP indisponible');
        }
    }
    
    // Essayer d'attacher au socket immédiatement et toutes les 2s
    if (!attachSocketHandler()) {
        const attachInterval = setInterval(() => {
            if (attachSocketHandler()) clearInterval(attachInterval);
        }, 2000);
    }
    
    // Si après 3s on a toujours "?", utiliser le fallback HTTP
    setTimeout(() => {
        if (badge.textContent.includes('?')) {
            console.log('⚠️ Fallback HTTP activé');
            fetchConnectionsHttp();
            // Continuer à interroger toutes les 10s
            setInterval(fetchConnectionsHttp, 10000);
        }
    }, 3000);
    
    // Survol
    const setupHover = setInterval(() => {
        if (window.bootstrap) {
            let hoverTimeout;
            const dropdown = bootstrap.Dropdown.getOrCreateInstance(badge);
            badge.addEventListener('mouseenter', () => {
                hoverTimeout = setTimeout(() => dropdown.show(), 400);
            });
            badge.addEventListener('mouseleave', () => clearTimeout(hoverTimeout));
            const dropdownMenu = badge.nextElementSibling;
            if (dropdownMenu) {
                dropdownMenu.addEventListener('mouseleave', () => dropdown.hide());
            }
            clearInterval(setupHover);
        }
    }, 500);
})();
