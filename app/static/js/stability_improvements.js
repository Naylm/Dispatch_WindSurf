/**
 * Améliorations de stabilité et de performance pour l'application Dispatch Manager
 */

const CONFIG = {
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY_BASE: 1000,
    DEBOUNCE_DELAY: 300,
    TOAST_DURATION: 5000,
    ACTION_TIMEOUT: 30000
};

async function fetchWithRetry(url, options = {}, retries = CONFIG.RETRY_ATTEMPTS) {
    if (!options.headers) options.headers = {};
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken && !options.headers['X-CSRFToken']) {
        options.headers['X-CSRFToken'] = csrfToken.content;
    }

    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.ACTION_TIMEOUT);
            const response = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text().catch(() => response.statusText);
                throw new Error(\`HTTP \${response.status}: \${errorText}\`);
            }
            return response;
        } catch (error) {
            console.error(\`Tentative \${attempt}/\${retries} échouée:\`, error);
            if (attempt === retries) {
                if (error.name === 'AbortError') {
                    showNotification('La requête a pris trop de temps. Veuillez réessayer.', 'warning');
                } else {
                    showNotification('Erreur réseau. Veuillez vérifier votre connexion.', 'danger');
                }
                throw error;
            }
            await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY_BASE * Math.pow(2, attempt - 1)));
        }
    }
}

function showNotification(message, type = 'info', duration = CONFIG.TOAST_DURATION) {
    // Redirection vers le système de notifications centralisé si disponible
    if (window.notificationSystem) {
        const priorityMap = {
            success: 'info',
            danger: 'urgent',
            warning: 'urgent',
            info: 'info'
        };
        
        const titleMap = {
            success: '✅ Succès',
            danger: '❌ Erreur',
            warning: '⚠️ Attention',
            info: 'ℹ️ Info'
        };

        window.notificationSystem.addNotification({
            type: 'system',
            priority: priorityMap[type] || 'info',
            title: titleMap[type] || 'Info',
            message: message
        });
        return;
    }

    // Fallback sur l'ancien système de toasts si non initialisé
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const icons = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' };
    const icon = icons[type] || icons.info;

    const toast = document.createElement('div');
    toast.className = `toast align - items - center text - white bg - ${ type } border - 0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
                < div class= "d-flex" >
            <div class="toast-body"><strong>${icon}</strong> ${escapeHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div >
                    `;

    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: duration });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function disableButtonDuringAction(button, action) {
    const originalText = button.innerHTML;
    const originalDisabled = button.disabled;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>En cours...';
    try {
        return await action();
    } finally {
        button.disabled = originalDisabled;
        button.innerHTML = originalText;
    }
}

function debounce(func, wait = CONFIG.DEBOUNCE_DELAY) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

function handleConflictError(error, fallback) {
    if (error.message && error.message.includes('409')) {
        showNotification('Ce ticket a été modifié par quelqu\'un d\'autre. Rechargement...', 'warning');
        setTimeout(() => window.location.reload(), 2000);
    } else if (fallback) {
        fallback(error);
    } else {
        showNotification('Une erreur est survenue. Veuillez réessayer.', 'danger');
    }
}

function updateIncidentCard(incidentId, updates) {
    const cards = document.querySelectorAll(\`.incident-card-col[data-id="\${incidentId}"], .small-card[data-id="\${incidentId}"]\`);
    cards.forEach(card => {
        if (updates.etat !== undefined) {
            const statusBadge = card.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.textContent = updates.etat;
                if (updates.etat_couleur) {
                    statusBadge.style.backgroundColor = updates.etat_couleur;
                    statusBadge.style.color = updates.etat_text_color || '#fff';
                }
            }
        }
        if (updates.version !== undefined) {
            card.querySelectorAll('[data-version]').forEach(el => el.dataset.version = updates.version);
        }
    });
}

function removeIncidentCard(incidentId, numero) {
    const cards = document.querySelectorAll(\`.incident-card-col[data-id="\${incidentId}"], .small-card[data-id="\${incidentId}"]\`);
    cards.forEach(card => {
        card.style.transition = 'opacity 0.3s, transform 0.3s';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.8)';
        setTimeout(() => card.remove(), 300);
    });
    showNotification(\`Ticket \${numero} supprimé avec succès\`, 'success');
}

window.StabilityHelpers = {
    fetchWithRetry,
    showNotification,
    disableButtonDuringAction,
    debounce,
    handleConflictError,
    updateIncidentCard,
    removeIncidentCard,
    escapeHtml
};

console.log('✅ Module de stabilité chargé avec succès');
