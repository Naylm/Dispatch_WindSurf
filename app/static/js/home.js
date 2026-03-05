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
    'list': { selector: '.incident-row-list', display: '' }, // default display for list items
    'table': { selector: '.incident-row-table', display: '' }, // default for table rows
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
        // Try to find date in text content if data attribute not available
        // Note: Ideally use data-date-affectation attribute
        valA = a.innerText || '';
        valB = b.innerText || '';
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

  // Sort based on current view
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
        // Re-append sorted cards wrapped in cols
        // This is tricky because cards are inside cols.
        // Simplified: just sort, but implementation depends on DOM structure
        // Assuming cards are direct children for now or handling cols
        // The original code was creating new cols.
        container.innerHTML = ''; // Clear
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

// Alias for compatibility
window.applyBadgeContrast = window.applyDataAttributesStyles;


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
    if (currentLength > maxLength * 0.9) {
      charCount.classList.add('danger');
    } else if (currentLength > maxLength * 0.75) {
      charCount.classList.add('warning');
    }
  }
  // Auto-resize
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

window.saveNote = function (button, incidentId, noteType) {
  const wrapper = button.closest('.note-wrapper');
  const textarea = wrapper.querySelector('.note-edit-textarea');
  const newValue = textarea.value.trim();
  const saveBtn = button;

  saveBtn.disabled = true;
  saveBtn.classList.add('saving');
  const originalText = saveBtn.textContent;
  saveBtn.textContent = 'Sauvegarde...';

  let route, payload;
  if (noteType === 'dispatch') {
    route = '/edit_note_dispatch/' + incidentId;
    payload = { note_dispatch: newValue };
  } else {
    route = '/edit_note_inline/' + incidentId;
    payload = { note: newValue };
  }

  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  fetch(route, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify(payload)
  })
    .then(response => {
      if (!response.ok) throw new Error('HTTP error ' + response.status);
      return response.json();
    })
    .then(data => {
      if (data.success) {
        window.updateViewMode(wrapper, newValue, noteType);
        wrapper.classList.add('note-save-animation');
        setTimeout(() => wrapper.classList.remove('note-save-animation'), 500);
        saveBtn.textContent = '✓ Sauvegardé';
        setTimeout(() => { saveBtn.textContent = originalText; }, 1000);
      } else {
        throw new Error(data.error || 'Erreur sauvegarde');
      }
    })
    .catch(err => {
      console.error('Erreur:', err);
      alert('Erreur: ' + err.message);
      saveBtn.textContent = originalText;
    })
    .finally(() => {
      saveBtn.disabled = false;
      saveBtn.classList.remove('saving');
    });
};

window.cancelEdit = function (button) {
  if (event) event.preventDefault(); // Prevent accidental form submit if any
  const wrapper = button.closest('.note-wrapper');
  const textarea = wrapper.querySelector('.note-edit-textarea');
  const viewMode = wrapper.querySelector('.note-view-mode');
  const editMode = wrapper.querySelector('.note-edit-mode');
  const viewContent = viewMode.querySelector('.note-content');

  // Restore logic
  // Use textContent directly which contains the raw text or the empty message
  // But wait, the viewContent might contain <span class="note-empty">...</span>
  // We should check the data-value or just use the text if it's not the empty message.

  // Actually, simpler: just hide edit mode. Textarea value reset is optional but nice.

  // If we really want to reset:
  /*
  const emptyEl = viewContent.querySelector('.note-empty');
  if (!emptyEl) {
    textarea.value = viewContent.textContent.trim(); 
  } else {
    textarea.value = '';
  }
  */
  // For now, simply toggling visibility is enough to "cancel" the *view* of editing.
  // The user can re-open it and see their draft or original text.
  // If we want to discard changes, we should reset textarea.value to original.

  editMode.style.display = 'none';
  viewMode.style.display = 'block';
};

window.updateViewMode = function (wrapper, newText, noteType) {
  const viewMode = wrapper.querySelector('.note-view-mode');
  const editMode = wrapper.querySelector('.note-edit-mode');
  const viewContent = viewMode.querySelector('.note-content');
  const textarea = wrapper.querySelector('.note-edit-textarea');

  if (viewContent) {
    if (newText && newText.trim() !== '') {
      viewContent.textContent = newText;
    } else {
      let emptyMsg = 'Pas de note';
      if (noteType === 'dispatch') emptyMsg = 'Pas de note dispatch';
      else if (noteType === 'tech') emptyMsg = 'Pas encore de note';
      viewContent.innerHTML = `<span class="note-empty">${emptyMsg}</span>`;
    }
  }
  textarea.value = newText;
  editMode.style.display = 'none';
  viewMode.style.display = 'block';

  // Re-check overflow after update
  setTimeout(() => window.checkNoteOverflow(wrapper), 10);
};

// --- Show More / Less Logic ---
window.toggleNoteExpansion = function (btn, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const wrapper = btn.closest('.note-wrapper');
  const content = wrapper.querySelector('.note-content');
  if (!content) return;

  const isExpanded = content.classList.toggle('expanded');
  btn.textContent = isExpanded ? 'Réduire' : 'Afficher plus';

  // If we just collapsed, scroll back to the top of the card if it's out of view
  if (!isExpanded) {
    const card = wrapper.closest('.incident-card-col, .small-card, .incident-card-grouped');
    if (card) {
      const rect = card.getBoundingClientRect();
      if (rect.top < 0) {
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }
};

window.checkNoteOverflow = function (wrapper) {
  const content = wrapper.querySelector('.note-content');
  const btn = wrapper.querySelector('.note-toggle-btn');
  if (!content || !btn) return;

  // Reset to measure real scrollHeight
  const wasExpanded = content.classList.contains('expanded');
  content.classList.remove('expanded');

  // Check if it overflows (scrollHeight > clientHeight + 5px margin of error)
  const isOverflowing = content.scrollHeight > content.clientHeight + 5;

  btn.style.display = isOverflowing ? 'block' : 'none';
  if (isOverflowing) {
    content.classList.add('is-overflowing');
  } else {
    content.classList.remove('is-overflowing');
  }

  // Restore state
  if (wasExpanded) content.classList.add('expanded');
};

// ==========================================
// TECH VIEW (Drag & Drop, Filters)
// ==========================================

window.initTechView = function () {
  console.log('👷 Initializing Tech View...');
  const config = window.dispatchConfig || {};
  console.log('📦 Config:', config);
  const TECH_USERNAME = config.username;
  const SITE_ORDER_LIST = config.siteOrder || [];
  const STATUT_ORDER_LIST = config.statutOrder || [];
  const PRIORITY_LEVELS = config.priorities || [];
  const ORDER_STORAGE_KEY = `tech-order:${(TECH_USERNAME || '').toLowerCase()}`;

  function getUserView() {
    return document.getElementById('userView');
  }

  function getCards() {
    const userView = getUserView();
    return userView ? Array.from(userView.querySelectorAll('.small-card')) : [];
  }

  // Helper to build order maps
  function buildOrderMap(list) {
    const map = {};
    if (Array.isArray(list)) {
      list.forEach((name, index) => {
        if (name) map[String(name).toLowerCase()] = index + 1;
      });
    }
    return map;
  }

  const siteOrderMap = buildOrderMap(SITE_ORDER_LIST);
  const statutOrderMap = buildOrderMap(STATUT_ORDER_LIST);
  const priorityOrderMap = {};
  if (Array.isArray(PRIORITY_LEVELS)) {
    PRIORITY_LEVELS.forEach(priority => {
      const name = (priority?.nom || '').toLowerCase();
      const level = Number(priority?.niveau);
      if (name) priorityOrderMap[name] = Number.isFinite(level) ? level : 999;
    });
  }

  // --- Persistence Functions ---
  function readStoredOrder() {
    try {
      const raw = localStorage.getItem(ORDER_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch (e) { return []; }
  }

  function writeStoredOrder(order) {
    try { localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(order)); } catch (e) { }
  }

  function saveOrderFromDom() {
    const cards = getCards();
    const order = cards.map(card => String(card.dataset.incidentId || '')).filter(Boolean);
    if (order.length) writeStoredOrder(order);
  }

  // --- Sorting & Ordering ---
  function normalizeOrder(order, cards) {
    const ids = cards.map(card => String(card.dataset.incidentId || ''));
    const normalized = order.filter(id => ids.includes(id));
    ids.forEach(id => {
      if (id && !normalized.includes(id)) normalized.push(id);
    });
    return normalized;
  }

  function applyTechOrder() {
    const userView = getUserView();
    if (!userView) return;
    const cards = getCards();
    if (!cards.length) return;

    const stored = readStoredOrder();
    const order = normalizeOrder(stored, cards);
    const cardMap = new Map(cards.map(card => [String(card.dataset.incidentId || ''), card]));

    order.forEach(id => {
      const card = cardMap.get(id);
      if (card) userView.appendChild(card);
    });
    writeStoredOrder(order);
  }

  function applySortingTech() {
    const sortByTech = document.getElementById('sortByTech');
    const userView = getUserView();
    if (!sortByTech || !userView) return;
    const sortValue = sortByTech.value;
    if (!sortValue) return;

    const [criteria, order] = sortValue.split('-');
    const cards = getCards();

    cards.sort((a, b) => {
      let valA, valB;
      switch (criteria) {
        case 'site':
          valA = siteOrderMap[(a.dataset.site || '').toLowerCase()] || 999;
          valB = siteOrderMap[(b.dataset.site || '').toLowerCase()] || 999;
          break;
        case 'urgence':
          valA = priorityOrderMap[(a.dataset.urgence || '').toLowerCase()] || 999;
          valB = priorityOrderMap[(b.dataset.urgence || '').toLowerCase()] || 999;
          break;
        case 'statut':
          valA = statutOrderMap[(a.dataset.etat || '').toLowerCase()] || 999;
          valB = statutOrderMap[(b.dataset.etat || '').toLowerCase()] || 999;
          break;
        case 'localisation':
          valA = a.dataset.localisation || '';
          valB = b.dataset.localisation || '';
          break;
        case 'date':
          valA = a.dataset.dateAffectation || '';
          valB = b.dataset.dateAffectation || '';
          break;
        default:
          return 0;
      }

      let cmp = 0;
      // Simplified comparison for brevity
      if (typeof valA === 'string' && typeof valB === 'string') cmp = valA.localeCompare(valB);
      else cmp = (valA > valB) ? 1 : (valA < valB) ? -1 : 0;

      return order === 'asc' ? cmp : -cmp;
    });

    cards.forEach(card => userView.appendChild(card));
  }

  function applyOrderingTech() {
    const sortByTech = document.getElementById('sortByTech');
    if (sortByTech && sortByTech.value) {
      applySortingTech();
    } else {
      applyTechOrder();
    }
  }

  // --- Filters Tech ---
  function matchesFiltersTech(card, filters) {
    const searchText = filters.searchText;
    const selectedSite = filters.selectedSite;
    const selectedUrgence = filters.selectedUrgence;

    const numero = (card.dataset.numero || '').toLowerCase();
    const site = (card.dataset.site || '').toLowerCase();
    const localisation = (card.dataset.localisation || '').toLowerCase();
    const sujet = (card.dataset.sujet || '').toLowerCase();
    const urgence = (card.dataset.urgence || '').toLowerCase();

    if (searchText !== '') {
      const matchesSearch = numero.includes(searchText) || site.includes(searchText) || localisation.includes(searchText) || sujet.includes(searchText);
      if (!matchesSearch) return false;
    }
    if (selectedSite !== '' && site !== selectedSite.toLowerCase()) return false;
    if (selectedUrgence !== '' && urgence !== selectedUrgence.toLowerCase()) return false;

    return true;
  }

  function applyFiltersTech() {
    const searchInputTech = document.getElementById('searchInputTech');
    const filterSiteTech = document.getElementById('filterSiteTech');
    const filterUrgenceTech = document.getElementById('filterUrgenceTech');
    const userView = getUserView();
    if (!userView || !searchInputTech || !filterSiteTech || !filterUrgenceTech) return;

    const filters = {
      searchText: searchInputTech.value.trim().toLowerCase(),
      selectedSite: filterSiteTech.value,
      selectedUrgence: filterUrgenceTech.value
    };

    const cards = getCards();
    cards.forEach(card => {
      if (matchesFiltersTech(card, filters)) {
        card.style.removeProperty('display');
      } else {
        card.style.display = 'none'; // Use display:none instead of visibility:hidden for better layout behavior
      }
    });
  }

  // --- Drag & Drop ---
  function toggleDragAvailability() {
    const sortByTech = document.getElementById('sortByTech');
    const allowDrag = !sortByTech || !sortByTech.value;
    getCards().forEach(card => {
      card.setAttribute('draggable', allowDrag ? 'true' : 'false');
      card.classList.toggle('drag-disabled', !allowDrag);
    });
  }

  function initDrag() {
    const userView = getUserView();
    if (!userView || userView.dataset.dragInit === 'true') return;
    userView.dataset.dragInit = 'true';

    let draggedCard = null;

    userView.addEventListener('dragstart', (event) => {
      const card = event.target.closest('.small-card');
      if (!card || card.getAttribute('draggable') !== 'true') {
        if (card && card.getAttribute('draggable') !== 'true') event.preventDefault();
        return;
      }
      if (event.target.closest('input, textarea, select, button, a')) return;

      draggedCard = card;
      card.classList.add('dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', card.dataset.incidentId || '');
    });

    userView.addEventListener('dragover', (event) => {
      if (!draggedCard) return;
      event.preventDefault();
      const card = event.target.closest('.small-card');
      if (!card || card === draggedCard) return;

      const rect = card.getBoundingClientRect();
      const before = event.clientX < rect.left + rect.width / 2;
      if (before) userView.insertBefore(draggedCard, card);
      else userView.insertBefore(draggedCard, card.nextSibling);
    });

    userView.addEventListener('dragend', () => {
      if (draggedCard) draggedCard.classList.remove('dragging');
      draggedCard = null;
      saveOrderFromDom();
    });
  }

  // --- Init Tech View ---
  const searchInputTech = document.getElementById('searchInputTech');
  const filterSiteTech = document.getElementById('filterSiteTech');
  const filterUrgenceTech = document.getElementById('filterUrgenceTech');
  const sortByTech = document.getElementById('sortByTech');
  const clearFiltersTechBtn = document.getElementById('clearFiltersTechBtn');

  if (searchInputTech && searchInputTech.dataset.techInit !== 'true') {
    searchInputTech.dataset.techInit = 'true';
    searchInputTech.addEventListener('input', applyFiltersTech);
    filterSiteTech.addEventListener('change', applyFiltersTech);
    filterUrgenceTech.addEventListener('change', applyFiltersTech);
    sortByTech.addEventListener('change', () => {
      applyOrderingTech();
      applyFiltersTech();
      toggleDragAvailability();
    });
    clearFiltersTechBtn.addEventListener('click', () => {
      searchInputTech.value = '';
      filterSiteTech.value = '';
      filterUrgenceTech.value = '';
      sortByTech.value = '';
      applyOrderingTech();
      applyFiltersTech();
      toggleDragAvailability();
    });
  }

  initDrag();
  applyOrderingTech();
  applyFiltersTech();
  toggleDragAvailability();
};

// ==========================================
// INITIALIZATION
// ==========================================

// Global initialization
(function () {
  console.log('🚀 Home JS initialized');

  // Init View Preference
  window.initializeView();
  window.applySavedZoom();

  // Initialize Technician View if applicable
  if (typeof window.initTechView === 'function') {
    window.initTechView();
  }

  // Listeners for Note System (delegated)
  document.body.addEventListener('click', function (e) {
    if (e.target.matches('.note-edit-btn') || e.target.closest('.note-edit-btn')) {
      const btn = e.target.closest('.note-edit-btn') || e.target;
      window.enterEditMode(btn);
      e.stopPropagation();
    } else if (e.target.closest('.note-save-btn')) {
      const btn = e.target.closest('.note-save-btn');
      window.saveNote(btn, btn.dataset.incidentId, btn.dataset.noteType);
      e.stopPropagation();
    } else if (e.target.closest('.note-cancel-btn')) {
      const btn = e.target.closest('.note-cancel-btn');
      window.cancelEdit(btn);
      e.stopPropagation();
    }
  });

  // ==========================================
  // COPY BUTTON (Copy incident number)
  // ==========================================
  document.addEventListener('click', function (e) {
    const copyBtn = e.target.closest('.copy-btn');
    if (copyBtn) {
      e.preventDefault();
      e.stopPropagation();
      const numero = copyBtn.dataset.numero;
      if (numero && navigator.clipboard) {
        navigator.clipboard.writeText(numero).then(() => {
          const orig = copyBtn.textContent;
          copyBtn.textContent = '✅';
          setTimeout(() => copyBtn.textContent = orig, 1500);
        });
      }
    }
  });

  // ==========================================
  // DELETE BUTTON (Delete incident)
  // ==========================================
  window._pendingDeleteId = null;
  window._pendingDeleteNumero = null;

  window.deleteIncident = function (btn, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    window._pendingDeleteId = btn.dataset.incidentId;
    window._pendingDeleteNumero = btn.dataset.numero || '';

    // Update modal text
    const modalText = document.getElementById('deleteIncidentModalText');
    if (modalText) {
      modalText.textContent = 'Supprimer le ticket ' + window._pendingDeleteNumero + ' ?';
    }

    // Show Bootstrap modal
    const modalEl = document.getElementById('deleteIncidentModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.show();
    } else {
      // Fallback to confirm() if modal not available
      if (confirm('Supprimer le ticket ' + window._pendingDeleteNumero + ' ? Cette action est irréversible.')) {
        window._executeDeleteIncident();
      }
    }
  };

  window._executeDeleteIncident = function () {
    const incidentId = window._pendingDeleteId;
    if (!incidentId) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    fetch('/delete/' + incidentId, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({ csrf_token: csrfToken })
    })
      .then(response => {
        if (response.ok) {
          window.location.reload();
        } else {
          alert("Erreur lors de la suppression de l'incident.");
        }
      })
      .catch(err => {
        console.error(err);
        alert("Erreur réseau lors de la suppression de l'incident.");
      });
  };

  // Wire up the modal's confirm button
  const confirmDeleteBtn = document.getElementById('confirmDeleteIncidentBtn');
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', function () {
      // Hide modal
      const modalEl = document.getElementById('deleteIncidentModal');
      if (modalEl) {
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
      }
      window._executeDeleteIncident();
    });
  }

  // ==========================================
  // STATUS SELECTOR (Change incident status)
  // ==========================================
  document.addEventListener('change', function (e) {
    if (e.target.matches('.status-selector-col, .status-selector-list')) {
      const select = e.target;
      const incidentId = select.dataset.incidentId;
      const newEtat = select.value;
      const currentEtat = select.dataset.current || '';

      if (newEtat === currentEtat) return;

      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      fetch(`/update_etat/${incidentId}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({ etat: newEtat })
      })
        .then(r => r.json())
        .then(d => {
          if (d.status === 'ok') {
            select.dataset.current = newEtat;
            // Update status badge on the card
            const card = select.closest('.incident-card-col, .small-card');
            if (card) {
              const badge = card.querySelector('.status-badge');
              if (badge && d.couleur) {
                badge.style.backgroundColor = d.couleur;
                badge.style.color = d.text_color || '#fff';
                badge.textContent = newEtat;
              }
              card.dataset.etat = newEtat.toLowerCase();

              // Refresh the entire card to show/hide dynamic fields (RDV, Relance)
              if (window.reloadIncidentCard) {
                window.reloadIncidentCard(incidentId);
              }
            }
          } else {
            alert('Erreur: ' + (d.message || 'Échec de la mise à jour'));
            select.value = currentEtat;
          }
        })
        .catch(() => {
          alert('Erreur réseau lors de la mise à jour du statut');
          select.value = currentEtat;
        });
    }
  });

  // ==========================================
  // HISTORY BUTTON (Force navigation)
  // ==========================================
  document.addEventListener('click', function (e) {
    const historyBtn = e.target.closest('.history-btn');
    if (historyBtn) {
      e.preventDefault();
      e.stopPropagation();
      const url = historyBtn.dataset.url;
      if (url) {
        window.location.href = url;
      }
    }
  });

  // Listeners for Search/Filters (Admin)
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    document.querySelectorAll('#searchInput, #filterEtat, #filterUrgence, #filterSite').forEach(el => {
      el.addEventListener('input', window.applySearchAndFilters);
      el.addEventListener('change', window.applySearchAndFilters);
    });
    document.getElementById('sortBy')?.addEventListener('change', window.applySorting);
    document.getElementById('clearFiltersBtn')?.addEventListener('click', () => {
      document.getElementById('searchInput').value = '';
      document.getElementById('filterEtat').value = '';
      document.getElementById('filterUrgence').value = '';
      document.getElementById('filterSite').value = '';
      document.getElementById('sortBy').value = '';
      window.applySearchAndFilters();
      window.applySorting();
    });
  }

  // ==========================================
  // TECH ASSIGN SELECTORS (Delegated)
  // ==========================================
  document.addEventListener('change', function (e) {
    if (e.target.matches('.tech-selector-col, .tech-selector, .tech-selector-list')) {
      const select = e.target;
      const incidentId = select.dataset.incidentId;
      const newTech = select.value;
      const currentTech = select.dataset.current || '';

      if (confirm(`Affecter le ticket à ${newTech} ?`)) {
        console.log(`📡 Tentative d'affectation: Incident=${incidentId}, NouveauTech=${newTech}`);
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!csrfToken) console.warn('⚠️ CSRF Token manquant !');

        fetch('/incidents/assign', {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ id: incidentId, collaborateur: newTech })
        }).then(r => {
          console.log(`📥 Réponse serveur: Status=${r.status}`);
          return r.json();
        }).then(d => {
          if (d.status === 'ok') {
            console.log('✅ Affectation réussie côté serveur');
            select.dataset.current = newTech;
            // Seamless reload instead of page refresh
            if (window.reloadIncidentCard) {
              console.log('🔄 Déclenchement reloadIncidentCard...');
              window.reloadIncidentCard(incidentId);
            } else {
              console.warn('⚠️ reloadIncidentCard non trouvé, refresh global...');
              window.location.reload();
            }
          } else {
            console.error('❌ Erreur serveur:', d.message);
            alert('Erreur: ' + (d.message || 'Échec de la réaffectation'));
            select.value = currentTech;
          }
        }).catch(err => {
          console.error('❌ Erreur réseau/JS:', err);
          alert('Erreur réseau');
          select.value = currentTech;
        });
      } else {
        select.value = currentTech;
      }
    }
  });

  window.resetFilters = function () {
    const adminSearch = document.getElementById('searchInput');
    const techSearch = document.getElementById('searchInputTech');

    if (adminSearch) {
      document.getElementById('searchInput').value = '';
      document.getElementById('filterEtat').value = '';
      document.getElementById('filterUrgence').value = '';
      document.getElementById('filterSite').value = '';
      document.getElementById('sortBy').value = '';
      window.applySearchAndFilters();
      window.applySorting();
    }

    if (techSearch) {
      document.getElementById('searchInputTech').value = '';
      document.getElementById('filterSiteTech').value = '';
      document.getElementById('filterUrgenceTech').value = '';
      document.getElementById('sortByTech').value = '';
      // We need to trigger the tech view filters as well
      if (typeof window.applyFiltersTech === 'function') {
        window.applyFiltersTech();
      }
      if (typeof window.initTechView === 'function') {
        // This might re-apply ordering
        // window.initTechView(); 
      }
    }
  };

  // Run initial overflow check for all notes
  setTimeout(() => {
    document.querySelectorAll('.note-wrapper').forEach(window.checkNoteOverflow);
  }, 500);

})();

// ==========================================
// RDV & RELANCE HANDLERS
// ==========================================

window.updateRdv = function (input) {
  const incidentId = input.dataset.incidentId;
  const newValue = input.value; // ISO string from datetime-local usually

  // If empty, it sends empty string.
  // Validate format if needed, but browser handles datetime-local mostly.

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

  // Visual feedback
  input.style.opacity = '0.5';

  fetch(`/api/incident/${incidentId}/rdv`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify({
      date_rdv: newValue
    })
  })
    .then(r => r.json())
    .then(data => {
      input.style.opacity = '1';
      if (data.success) {
        // Success flash or border color
        const originalBorder = input.style.borderColor;
        input.style.borderColor = '#28a745';
        setTimeout(() => { input.style.borderColor = originalBorder || ''; }, 1000);
      } else {
        alert('Erreur: ' + (data.error || 'Erreur mise à jour RDV'));
      }
    })
    .catch(err => {
      input.style.opacity = '1';
      console.error(err);
      alert('Erreur réseau');
    });
};

window.updateRelance = function (checkbox) {
  const incidentId = checkbox.dataset.incidentId;
  // We need to send ALL relance states because the API might expect them or we want to be safe.
  // Actually, the API `update_relances` accepts individual fields or all.
  // Let's gather all checkboxes for this incident to be sure, OR just send the changed one if API supports partial.
  // Looking at python code: `relance_mail = data.get("relance_mail")...` it seems to read all.
  // So we should gather all checks from the wrapper.

  const wrapper = checkbox.closest('.relances-wrapper');
  if (!wrapper) return;

  const payload = {};
  wrapper.querySelectorAll('.relance-checkbox').forEach(cb => {
    payload[cb.dataset.field] = cb.checked;
  });

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

  // Visual feedback - disable all during save?
  // Maybe just opacity
  wrapper.style.opacity = '0.7';

  fetch(`/api/incident/${incidentId}/relances`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      wrapper.style.opacity = '1';
      if (data.success) {
        // Flash effect
        wrapper.classList.add('bg-white', 'bg-opacity-25');
        setTimeout(() => wrapper.classList.remove('bg-white', 'bg-opacity-25'), 300);
      } else {
        alert('Erreur: ' + (data.error || 'Erreur mise à jour Relances'));
        // Revert checkbox?
        checkbox.checked = !checkbox.checked;
      }
    })
    .catch(err => {
      wrapper.style.opacity = '1';
      console.error(err);
      alert('Erreur réseau');
      checkbox.checked = !checkbox.checked;
    });
};
