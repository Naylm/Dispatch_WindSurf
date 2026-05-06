/**
 * home.js - Logic for Home Dashboard (View switching, Filtering, Notes, Tech View)
 */

// ==========================================
// VIEW MANAGEMENT
// ==========================================

window.currentView = 'kanban';

window.switchView = function (viewName) {
  // Save preference
  localStorage.setItem('adminViewPreference', viewName);

  // Show/hide zoom controls
  const zoomControls = document.getElementById('kanbanZoomControls');
  if (zoomControls) {
    zoomControls.style.display = (viewName === 'kanban') ? '' : 'none';
  }

  // Hide all views
  document.querySelectorAll('.view-container').forEach(v => {
    v.classList.remove('active');
    v.style.display = 'none';
  });

  // Show selected view
  const selectedView = document.getElementById(`${viewName}-view`);
  if (selectedView) {
    selectedView.classList.add('active');
    selectedView.style.display = 'block';
  }

  // Update buttons
  document.querySelectorAll('.view-btn').forEach(btn => {
    const isActive = btn.dataset.view === viewName;
    if (isActive) {
      btn.classList.remove('btn-outline-primary');
      btn.classList.add('btn-primary', 'active');
    } else {
      btn.classList.remove('btn-primary', 'active');
      btn.classList.add('btn-outline-primary');
    }
  });

  // Update global variable
  window.currentView = viewName;

  // Re-apply filters
  if (typeof window.applySearchAndFilters === 'function') {
    window.applySearchAndFilters();
  }

  // Re-apply badge styles
  if (window.applyDataAttributesStyles) {
    window.applyDataAttributesStyles();
  }

  // Reset Bootstrap Accordion for Grouped View
  if (viewName === 'grouped') {
    if (typeof bootstrap !== 'undefined') {
      const collapses = document.querySelectorAll('#groupedAccordion .accordion-collapse');
      collapses.forEach(collapse => {
        try {
          const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapse, { toggle: false });
          bsCollapse.hide();
        } catch (e) {
          console.log('Bootstrap collapse non initialisé:', e);
        }
      });
    }
  }
};

window.initializeView = function () {
  const savedView = localStorage.getItem('adminViewPreference') || 'kanban';
  setTimeout(() => {
    if (window.switchView) {
      window.switchView(savedView);
    } else {
      setTimeout(window.initializeView, 100);
    }
  }, 50);
};

// ==========================================
// KANBAN ZOOM MANAGEMENT
// ==========================================
window.kanbanZoomLevel = 1.0;

window.zoomKanban = function (delta, reset = false) {
  const container = document.getElementById('kanban-view');
  if (!container) return;

  if (reset) {
    window.kanbanZoomLevel = 1.0;
  } else {
    window.kanbanZoomLevel += delta;
    // Restrict zoom level between 50% and 150%
    if (window.kanbanZoomLevel < 0.5) window.kanbanZoomLevel = 0.5;
    if (window.kanbanZoomLevel > 1.5) window.kanbanZoomLevel = 1.5;
  }

  container.style.zoom = window.kanbanZoomLevel;

  const label = document.getElementById('kanbanZoomLevel');
  if (label) {
    label.textContent = Math.round(window.kanbanZoomLevel * 100) + '%';
  }

  localStorage.setItem('kanbanZoomLevel', window.kanbanZoomLevel.toString());
};

window.applySavedZoom = function () {
  const savedZoom = localStorage.getItem('kanbanZoomLevel');
  if (savedZoom) {
    window.kanbanZoomLevel = parseFloat(savedZoom) || 1.0;
    window.zoomKanban(0); // apply current level
  }
};

// ==========================================
// TECH ZOOM MANAGEMENT
// ==========================================
window.techZoomLevel = 1.0;

window.zoomTech = function (delta, reset = false) {
  const container = document.getElementById('userView');
  if (!container) return;

  if (reset) {
    window.techZoomLevel = 1.0;
  } else {
    window.techZoomLevel += delta;
    // Restrict zoom level between 50% and 150%
    if (window.techZoomLevel < 0.5) window.techZoomLevel = 0.5;
    if (window.techZoomLevel > 1.5) window.techZoomLevel = 1.5;
  }

  container.style.zoom = window.techZoomLevel;

  const label = document.getElementById('techZoomLevel');
  if (label) {
    label.textContent = Math.round(window.techZoomLevel * 100) + '%';
  }

  localStorage.setItem('techZoomLevel', window.techZoomLevel.toString());
};

window.applySavedTechZoom = function () {
  const savedZoom = localStorage.getItem('techZoomLevel');
  if (savedZoom) {
    window.techZoomLevel = parseFloat(savedZoom) || 1.0;
    window.zoomTech(0); // apply current level
  }
};

// ==========================================
// SEARCH & FILTERS
// ==========================================

window.matchesFilters = function (cardElem) {
  const searchInput = document.querySelector('#searchInput');
  const filterEtat = document.querySelector('#filterEtat');
  const filterUrgence = document.querySelector('#filterUrgence');
  const filterSite = document.querySelector('#filterSite');

  if (!searchInput || !filterEtat || !filterUrgence || !filterSite) return true;

  const txtSearch = searchInput.value.trim().toLowerCase();
  const selEtat = filterEtat.value.toLowerCase();
  const selUrg = filterUrgence.value.toLowerCase();
  const selSite = filterSite.value.toLowerCase();

  const numero = (cardElem.dataset.numero || '').toLowerCase();
  const site = (cardElem.dataset.site || '').toLowerCase();
  const sujet = (cardElem.dataset.sujet || '').toLowerCase();
  const urgence = (cardElem.dataset.urgence || '').toLowerCase();
  const etat = (cardElem.dataset.etat || '').toLowerCase();

  if (txtSearch !== '') {
    const txtOK = numero.includes(txtSearch) || site.includes(txtSearch) || sujet.includes(txtSearch);
    if (!txtOK) return false;
  }
  if (selEtat && !etat.includes(selEtat)) return false;
  if (selUrg && !urgence.includes(selUrg)) return false;
  if (selSite && !site.includes(selSite)) return false;
  return true;
};

window.applySearchAndFilters = function () {
  const viewMap = {
    'kanban': { selector: '.incident-card-col', display: 'block' },
    'list': { selector: '.incident-row-list', display: '' },
    'table': { selector: '.incident-row-table', display: '' },
    'grouped': { selector: '.incident-card-grouped', display: 'block' }
  };

  const config = viewMap[window.currentView];
  if (!config) return;

  document.querySelectorAll(config.selector).forEach((el) => {
    el.style.display = window.matchesFilters(el) ? config.display : 'none';
  });
};

// ==========================================
// SORTING
// ==========================================

window.applySorting = function () {
  const sortValue = document.querySelector('#sortBy')?.value;
  if (!sortValue) return;

  const [criteria, order] = sortValue.split('-');
  const priorityOrder = { 'basse': 1, 'moyenne': 2, 'haute': 3, 'critique': 4 };

  function compareElements(a, b) {
    let valA, valB;

    switch (criteria) {
      case 'urgence':
        valA = priorityOrder[(a.dataset.urgence || '').toLowerCase()] || 0;
        valB = priorityOrder[(b.dataset.urgence || '').toLowerCase()] || 0;
        break;
      case 'date':
        valA = a.dataset.dateAffectation || a.innerText || '';
        valB = b.dataset.dateAffectation || b.innerText || '';
        break;
      case 'site':
        valA = (a.dataset.site || '').toLowerCase();
        valB = (b.dataset.site || '').toLowerCase();
        break;
      case 'numero':
        valA = (a.dataset.numero || '').toLowerCase();
        valB = (b.dataset.numero || '').toLowerCase();
        break;
      default:
        return 0;
    }

    if (order === 'asc') {
      return valA > valB ? 1 : valA < valB ? -1 : 0;
    } else {
      return valA < valB ? 1 : valA > valB ? -1 : 0;
    }
  }

  if (window.currentView === 'kanban') {
    document.querySelectorAll('.incident-list-col').forEach(list => {
      const cards = Array.from(list.querySelectorAll('.incident-card-col'));
      cards.sort(compareElements);
      cards.forEach(card => list.appendChild(card));
    });
  } else if (window.currentView === 'list') {
    document.querySelectorAll('.list-group').forEach(group => {
      const rows = Array.from(group.querySelectorAll('.incident-row-list'));
      rows.sort(compareElements);
      rows.forEach(row => group.appendChild(row));
    });
  } else if (window.currentView === 'table') {
    const tbody = document.querySelector('#table-view tbody');
    if (tbody) {
      const rows = Array.from(tbody.querySelectorAll('.incident-row-table'));
      rows.sort(compareElements);
      rows.forEach(row => tbody.appendChild(row));
    }
  } else if (window.currentView === 'grouped') {
    document.querySelectorAll('.accordion-body').forEach(body => {
      const cards = Array.from(body.querySelectorAll('.incident-card-grouped'));
      cards.sort(compareElements);
      const container = body.querySelector('.row');
      if (container) {
        container.innerHTML = '';
        cards.forEach(card => {
          const col = document.createElement('div');
          col.className = 'col-md-6 col-lg-4';
          col.appendChild(card);
          container.appendChild(col);
        });
      }
    });
  }
};

// ==========================================
// STYLES & RENDERING
// ==========================================

window.applyDataAttributesStyles = function () {
  document.querySelectorAll('[data-bg-color]').forEach(el => {
    el.style.setProperty('background-color', el.dataset.bgColor, 'important');
    if (el.dataset.textColor) {
      el.style.setProperty('color', el.dataset.textColor, 'important');
    }
  });
};

window.applyBadgeContrast = window.applyDataAttributesStyles;

window.getIncidentVersion = function (incidentId, contextEl) {
  if (contextEl) {
    const scoped = contextEl.closest('[data-version]');
    if (scoped && scoped.dataset.version) {
      const parsed = parseInt(scoped.dataset.version, 10);
      if (!Number.isNaN(parsed) && parsed > 0) return parsed;
    }
  }
  const card = document.querySelector(`[data-incident-id="${incidentId}"][data-version]`);
  if (!card || !card.dataset.version) return null;
  const parsed = parseInt(card.dataset.version, 10);
  return Number.isNaN(parsed) ? null : parsed;
};

window.setIncidentVersion = function (incidentId, version) {
  if (version === undefined || version === null) return;
  document.querySelectorAll(`[data-incident-id="${incidentId}"], [data-id="${incidentId}"]`).forEach(el => {
    el.dataset.version = String(version);
  });
};

window.makeIdempotencyKey = function (actionName, incidentId) {
  const rand = (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${actionName}:${incidentId}:${rand}`;
};

// ==========================================
// NOTE SYSTEM
// ==========================================

window.updateCharCount = function (textarea) {
  const wrapper = textarea.closest('.note-edit-mode');
  const charCount = wrapper.querySelector('.note-char-count');
  if (charCount) {
    const maxLength = textarea.maxLength || 500;
    const currentLength = textarea.value.length;
    charCount.textContent = `${currentLength}/${maxLength}`;
    charCount.classList.remove('warning', 'danger');
    if (currentLength > maxLength * 0.9) charCount.classList.add('danger');
    else if (currentLength > maxLength * 0.75) charCount.classList.add('warning');
  }
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
};

window.enterEditMode = function (button) {
  const wrapper = button.closest('.note-wrapper');
  const viewMode = wrapper.querySelector('.note-view-mode');
  const editMode = wrapper.querySelector('.note-edit-mode');
  const textarea = editMode.querySelector('.note-edit-textarea');
  viewMode.style.display = 'none';
  editMode.style.display = 'block';
  setTimeout(() => {
    window.updateCharCount(textarea);
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  }, 10);
};

window.saveNote = async function (button, incidentId, noteType, retryCount = 0) {
  const wrapper = button.closest('.note-wrapper');
  if (!wrapper) {
    console.error('saveNote: Impossible de trouver .note-wrapper parent');
    alert('Erreur: Structure HTML invalide. Rechargez la page.');
    return;
  }
  const textarea = wrapper.querySelector('.note-edit-textarea');
  if (!textarea) {
    console.error('saveNote: Impossible de trouver textarea');
    alert('Erreur: Champ de texte introuvable.');
    return;
  }
  const newValue = textarea.value.trim();
  const saveBtn = button;
  saveBtn.disabled = true;
  saveBtn.classList.add('saving');
  const originalHTML = saveBtn.innerHTML;  // Sauvegarder l'HTML complet (icône FontAwesome)
  saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';  // Icône de chargement
  
  let expectedVersion = window.getIncidentVersion(incidentId, button);
  
  // Si pas de version locale et qu'on a déjà retry, essayer de récupérer depuis le DOM
  if (!expectedVersion && retryCount > 0) {
    await window.reloadIncidentCard?.(incidentId);
    expectedVersion = window.getIncidentVersion(incidentId, button);
  }
  
  if (!expectedVersion) {
    alert('Version locale manquante. Rechargez la page.');
    saveBtn.disabled = false;
    saveBtn.classList.remove('saving');
    saveBtn.innerHTML = originalHTML;
    return;
  }
  
  let route = (noteType === 'dispatch') ? '/incident/edit_note_dispatch/' + incidentId : '/incident/edit_note_inline/' + incidentId;
  let payload = (noteType === 'dispatch') ? { note_dispatch: newValue, expected_version: expectedVersion } : { note: newValue, expected_version: expectedVersion };
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  
  try {
    const response = await fetch(route, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
        'X-Incident-Version': String(expectedVersion),
        'X-Idempotency-Key': window.makeIdempotencyKey(`note_${noteType}_${retryCount}`, incidentId)
      },
      body: JSON.stringify(payload)
    });
    
    const data = await response.json().catch(() => ({}));
    
    // Gestion automatique des conflits - retry avec nouvelle version
    if (!response.ok && data.status === 'conflict' && retryCount < 2) {
      saveBtn.innerHTML = '<i class="fas fa-sync fa-spin"></i> Conflit...';
      // Attendre un peu puis récupérer la nouvelle version
      await new Promise(r => setTimeout(r, 300));
      await window.reloadIncidentCard?.(incidentId);
      return window.saveNote(button, incidentId, noteType, retryCount + 1);
    }
    
    if (!response.ok) {
      throw new Error(data.message || data.error || ('HTTP error ' + response.status));
    }
    
    if (data.success) {
      console.log('✅ Sauvegarde réussie, mise à jour UI...');
      if (data.version) window.setIncidentVersion(incidentId, data.version);
      console.log('✅ Appel de updateViewMode...');
      window.updateViewMode(wrapper, newValue, noteType);
      console.log('✅ updateViewMode appelée');
      wrapper.classList.add('note-save-animation');
      setTimeout(() => wrapper.classList.remove('note-save-animation'), 500);
      saveBtn.innerHTML = '<i class="fas fa-check"></i>';
      setTimeout(() => {
        if (!saveBtn.disabled) saveBtn.innerHTML = originalHTML;
      }, 2000);
    } else {
      throw new Error(data.error || 'Erreur sauvegarde');
    }
  } catch (err) {
    console.error('Erreur:', err);
    if (err.message?.includes('conflict') && retryCount < 2) {
      // Retry automatique en cas de conflit
      return window.saveNote(button, incidentId, noteType, retryCount + 1);
    }
    alert('Erreur: ' + err.message);
    saveBtn.innerHTML = originalHTML;
  } finally {
    saveBtn.disabled = false;
    saveBtn.classList.remove('saving');
  }
};

window.cancelEdit = function (button) {
  const wrapper = button.closest('.note-wrapper');
  wrapper.querySelector('.note-edit-mode').style.display = 'none';
  wrapper.querySelector('.note-view-mode').style.display = 'block';
};

window.updateViewMode = function (wrapper, newText, noteType) {
  if (!wrapper) {
    console.error('updateViewMode: wrapper is null');
    return;
  }
  
  const viewContent = wrapper.querySelector('.note-view-mode .note-content');
  const textarea = wrapper.querySelector('.note-edit-textarea');
  const editMode = wrapper.querySelector('.note-edit-mode');
  const viewMode = wrapper.querySelector('.note-view-mode');
  
  console.log('📝 updateViewMode: editMode=', editMode, 'viewMode=', viewMode);
  
  if (viewContent) {
    if (newText && newText.trim() !== '') {
      viewContent.textContent = newText;
    } else {
      let emptyMsg = (noteType === 'dispatch') ? 'Pas de note dispatch' : (noteType === 'tech' ? 'Pas encore de note' : 'Pas de note');
      viewContent.innerHTML = `<span class="note-empty">${emptyMsg}</span>`;
    }
  }
  
  if (textarea) textarea.value = newText;
  
  // Changer l'affichage immédiatement
  if (editMode) {
    editMode.style.display = 'none';
    console.log('✅ editMode caché');
  } else {
    console.error('❌ editMode non trouvé!');
  }
  
  if (viewMode) {
    viewMode.style.display = 'block';
    console.log('✅ viewMode affiché');
  } else {
    console.error('❌ viewMode non trouvé!');
  }
  
  console.log('✅ Note sauvegardée, passage en mode vue');
  if (window.checkNoteOverflow) {
    window.checkNoteOverflow(wrapper);
  }
};

window.toggleNoteExpansion = function (btn, event) {
  if (event) { event.preventDefault(); event.stopPropagation(); }
  const content = btn.closest('.note-wrapper').querySelector('.note-content');
  if (!content) return;
  const isExpanded = content.classList.toggle('expanded');
  btn.textContent = isExpanded ? 'Réduire' : 'Afficher plus';
};

window.checkNoteOverflow = function (wrapper) {
  const content = wrapper.querySelector('.note-content');
  const btn = wrapper.querySelector('.note-toggle-btn');
  if (!content || !btn) return;
  const wasExpanded = content.classList.contains('expanded');
  content.classList.remove('expanded');
  const isOverflowing = content.scrollHeight > content.clientHeight + 5;
  btn.style.display = isOverflowing ? 'block' : 'none';
  content.classList.toggle('is-overflowing', isOverflowing);
  if (wasExpanded) content.classList.add('expanded');
};

// ==========================================
// TECH VIEW (Drag & Drop, Filters)
// ==========================================

window.initTechView = function () {
  console.log('👷 Initializing Tech View...');
  const config = window.dispatchConfig || {};
  const TECH_USERNAME = config.username;
  const SITE_ORDER_LIST = config.siteOrder || [];
  const STATUT_ORDER_LIST = config.statutOrder || [];
  const PRIORITY_LEVELS = config.priorities || [];
  const ORDER_STORAGE_KEY = `tech-order:${(TECH_USERNAME || '').toLowerCase()}`;

  function getUserView() { return document.getElementById('userView'); }
  function getCards() { 
    const uv = getUserView();
    return uv ? Array.from(uv.querySelectorAll('.small-card')) : []; 
  }

  const siteOrderMap = {};
  SITE_ORDER_LIST.forEach((n, i) => { if(n) siteOrderMap[n.toLowerCase()] = i + 1; });
  const statutOrderMap = {};
  STATUT_ORDER_LIST.forEach((n, i) => { if(n) statutOrderMap[n.toLowerCase()] = i + 1; });
  const priorityOrderMap = {};
  PRIORITY_LEVELS.forEach(p => { if(p?.nom) priorityOrderMap[p.nom.toLowerCase()] = Number(p.niveau) || 999; });

  function applyOrderingTech() {
    const uv = getUserView();
    const sortVal = document.getElementById('sortByTech')?.value;
    const cards = getCards();
    if (!uv || !cards.length) return;

    if (sortVal) {
      const [criteria, order] = sortVal.split('-');
      cards.sort((a, b) => {
        let vA, vB;
        switch (criteria) {
          case 'site': vA = siteOrderMap[(a.dataset.site || '').toLowerCase()] || 999; vB = siteOrderMap[(b.dataset.site || '').toLowerCase()] || 999; break;
          case 'urgence': vA = priorityOrderMap[(a.dataset.urgence || '').toLowerCase()] || 999; vB = priorityOrderMap[(b.dataset.urgence || '').toLowerCase()] || 999; break;
          case 'statut': vA = statutOrderMap[(a.dataset.etat || '').toLowerCase()] || 999; vB = statutOrderMap[(b.dataset.etat || '').toLowerCase()] || 999; break;
          case 'date': vA = a.dataset.dateAffectation || ''; vB = b.dataset.dateAffectation || ''; break;
          default: return 0;
        }
        let cmp = (vA > vB) ? 1 : (vA < vB ? -1 : 0);
        return order === 'asc' ? cmp : -cmp;
      });
    } else {
      const stored = JSON.parse(localStorage.getItem(ORDER_STORAGE_KEY) || '[]');
      const ids = cards.map(c => c.dataset.incidentId);
      const order = stored.filter(id => ids.includes(id));
      ids.forEach(id => { if(!order.includes(id)) order.push(id); });
      const cardMap = new Map(cards.map(c => [c.dataset.incidentId, c]));
      order.forEach(id => { if(cardMap.has(id)) uv.appendChild(cardMap.get(id)); });
    }
    cards.forEach(c => uv.appendChild(c));
  }

  function applyFiltersTech() {
    const s = document.getElementById('searchInputTech')?.value.toLowerCase() || '';
    const si = document.getElementById('filterSiteTech')?.value || '';
    const u = document.getElementById('filterUrgenceTech')?.value || '';
    getCards().forEach(c => {
      const num = (c.dataset.numero || '').toLowerCase();
      const site = (c.dataset.site || '').toLowerCase();
      const loc = (c.dataset.localisation || '').toLowerCase();
      const suj = (c.dataset.sujet || '').toLowerCase();
      const urg = (c.dataset.urgence || '').toLowerCase();
      const matches = (!s || num.includes(s) || site.includes(s) || loc.includes(s) || suj.includes(s)) &&
                      (!si || site === si.toLowerCase()) &&
                      (!u || urg === u.toLowerCase());
      c.style.display = matches ? '' : 'none';
    });
  }

  function toggleDrag() {
    const allow = !document.getElementById('sortByTech')?.value;
    getCards().forEach(c => {
      c.setAttribute('draggable', allow ? 'true' : 'false');
      c.classList.toggle('drag-disabled', !allow);
    });
  }

  const sIT = document.getElementById('searchInputTech');
  if (sIT && sIT.dataset.init !== 'true') {
    sIT.dataset.init = 'true';
    sIT.addEventListener('input', applyFiltersTech);
    document.getElementById('filterSiteTech').addEventListener('change', applyFiltersTech);
    document.getElementById('filterUrgenceTech').addEventListener('change', applyFiltersTech);
    document.getElementById('sortByTech').addEventListener('change', () => { applyOrderingTech(); applyFiltersTech(); toggleDrag(); });
    document.getElementById('clearFiltersTechBtn').addEventListener('click', () => {
      sIT.value = ''; document.getElementById('filterSiteTech').value = '';
      document.getElementById('filterUrgenceTech').value = ''; document.getElementById('sortByTech').value = '';
      applyOrderingTech(); applyFiltersTech(); toggleDrag();
    });
  }

  applyOrderingTech(); applyFiltersTech(); toggleDrag();
};

// ==========================================
// INITIALIZATION & DELEGATION
// ==========================================

(function () {
  console.log('🚀 Home JS Initializing...');

  window.applySavedZoom();
  window.applySavedTechZoom();
  if (typeof window.initTechView === 'function') window.initTechView();

  // DELEGATED LISTENERS
  document.addEventListener('click', function (e) {
    // Note System
    const editBtn = e.target.closest('.note-edit-btn');
    if (editBtn) return window.enterEditMode(editBtn);
    const saveBtn = e.target.closest('.note-save-btn');
    if (saveBtn) return window.saveNote(saveBtn, saveBtn.dataset.incidentId, saveBtn.dataset.noteType);
    const cancelBtn = e.target.closest('.note-cancel-btn');
    if (cancelBtn) return window.cancelEdit(cancelBtn);

    // Copy Button
    const copyBtn = e.target.closest('.copy-btn');
    if (copyBtn && navigator.clipboard) {
      navigator.clipboard.writeText(copyBtn.dataset.numero).then(() => {
        const o = copyBtn.textContent; copyBtn.textContent = '✅';
        setTimeout(() => copyBtn.textContent = o, 1500);
      });
    }

    // History Button
    const histBtn = e.target.closest('.history-btn');
    if (histBtn && histBtn.dataset.url) window.location.href = histBtn.dataset.url;

    // Filters Clear
    if (e.target.id === 'clearFiltersBtn') {
      ['searchInput', 'filterEtat', 'filterUrgence', 'filterSite', 'sortBy'].forEach(id => {
        const el = document.getElementById(id); if(el) el.value = '';
      });
      window.applySearchAndFilters();
      window.applySorting();
    }
  });

  document.addEventListener('input', function(e) {
    if (e.target.closest('#searchInput, #filterEtat, #filterUrgence, #filterSite')) window.applySearchAndFilters();
  });

  document.addEventListener('change', function(e) {
    if (e.target.closest('#searchInput, #filterEtat, #filterUrgence, #filterSite')) window.applySearchAndFilters();
    if (e.target.id === 'sortBy') window.applySorting();
    
    // Status Selectors
    if (e.target.matches('.status-selector-col, .status-selector-list')) {
      const s = e.target;
      const id = s.dataset.incidentId;
      const val = s.value;
      const old = s.dataset.current || '';
      if (val === old) return;
      const ver = window.getIncidentVersion(id, s);
      const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      
      fetch(`/incident/update_etat/${id}`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/x-www-form-urlencoded', 'X-Incident-Version': String(ver) },
        body: new URLSearchParams({ etat: val, expected_version: String(ver) })
      }).then(r => r.json()).then(d => {
        if (d.status === 'ok') {
          if (d.version) window.setIncidentVersion(id, d.version);
          if (window.reloadIncidentCard) {
            window.reloadIncidentCard(id).then(() => {
              // Mettre à jour le dataset.current après rechargement de la carte
              setTimeout(() => {
                const newSelect = document.querySelector(`.status-selector-col[data-incident-id="${id}"], .status-selector-list[data-incident-id="${id}"]`);
                if (newSelect) newSelect.dataset.current = val;
              }, 100);
            });
          } else {
            s.dataset.current = val;
          }
        } else { alert(d.message || 'Erreur'); s.value = old; }
      }).catch(() => { s.value = old; });
    }
    
    // Tech Assign Selectors
    if (e.target.matches('.tech-selector-col, .tech-selector, .tech-selector-list')) {
      const s = e.target;
      const id = s.dataset.incidentId;
      const val = s.value;
      const old = s.dataset.current || '';
      if (confirm(`Affecter le ticket à ${val} ?`)) {
        const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        const ver = window.getIncidentVersion(id, s);
        fetch('/admin/incidents/assign', {
          method: 'POST',
          headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/x-www-form-urlencoded', 'X-Incident-Version': String(ver) },
          body: new URLSearchParams({ id: id, collaborateur: val, expected_version: String(ver) })
        }).then(r => r.json()).then(d => {
          if (d.status === 'ok') {
            s.dataset.current = val;
            if (d.version) window.setIncidentVersion(id, d.version);
            if (window.reloadIncidentCard) window.reloadIncidentCard(id);
          } else { alert(d.message || 'Erreur'); s.value = old; }
        }).catch(() => { s.value = old; });
      } else s.value = old;
    }
  });

  setTimeout(() => {
    document.querySelectorAll('.note-wrapper').forEach(window.checkNoteOverflow);
    window.initializeView();
  }, 500);

})();

// RDV & RELANCE HANDLERS
window.updateRdv = function (input) {
  const id = input.dataset.incidentId;
  const ver = window.getIncidentVersion(id, input);
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  input.style.opacity = '0.5';
  fetch(`/incident/api/${id}/rdv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'X-Incident-Version': String(ver) },
    body: JSON.stringify({ date_rdv: input.value, expected_version: ver })
  }).then(r => r.json()).then(d => {
    input.style.opacity = '1';
    if (d.success) {
      if (d.version) window.setIncidentVersion(id, d.version);
    } else alert(d.error || 'Erreur');
  }).catch(() => { input.style.opacity = '1'; });
};

window.updateRelance = function (checkbox) {
  const id = checkbox.dataset.incidentId;
  const ver = window.getIncidentVersion(id, checkbox);
  const wrapper = checkbox.closest('.relances-wrapper');
  const payload = { expected_version: ver };
  wrapper.querySelectorAll('.relance-checkbox').forEach(cb => { payload[cb.dataset.field] = cb.checked; });
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  wrapper.style.opacity = '0.7';
  fetch(`/incident/api/${id}/relances`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'X-Incident-Version': String(ver) },
    body: JSON.stringify(payload)
  }).then(r => r.json()).then(d => {
    wrapper.style.opacity = '1';
    if (d.success && d.version) window.setIncidentVersion(id, d.version);
  }).catch(() => { wrapper.style.opacity = '1'; });
};