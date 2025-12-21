// ==============================
// DASHBOARD STATISTIQUES JS
// Logique complète pour le dashboard avec scroll dans tableaux
// ==============================

// Variables globales
let charts = {};
let currentFilters = {
    start_date: null,
    end_date: null,
    tech_ids: [],
    site_ids: [],
    status_ids: [],
    priority_ids: []
};
let debounceTimer = null;

// Initialisation au chargement
document.addEventListener('DOMContentLoaded', function() {
    initializeDateFilters();
    initializeThemeToggle();
    setupEventListeners();
    applyFilters(); // Charger les données initiales
});

// =====================
// INITIALISATION
// =====================

function initializeDateFilters() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    document.getElementById('filterStart').value = firstDayOfMonth.toISOString().slice(0, 10);
    document.getElementById('filterEnd').value = today.toISOString().slice(0, 10);
    
    // Preset "Ce mois" sélectionné par défaut
    document.getElementById('datePreset').value = 'month';
}

function initializeThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark');
        themeToggle.textContent = '☀️';
    }
    
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark');
        const isDark = document.body.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        themeToggle.textContent = isDark ? '☀️' : '🌙';
    });
}

function setupEventListeners() {
    // Bouton Appliquer avec debouncing
    document.getElementById('btnApply').addEventListener('click', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(applyFilters, 300);
    });
    
    // Bouton Réinitialiser
    document.getElementById('btnReset').addEventListener('click', resetFilters);
    
    // Preset de dates
    document.getElementById('datePreset').addEventListener('change', function() {
        applyDatePreset(this.value);
    });
    
    // Exports
    document.getElementById('btnExportExcel').addEventListener('click', exportExcel);
    document.getElementById('btnExportPDF').addEventListener('click', exportPDF);
    document.getElementById('btnExportCSV').addEventListener('click', exportCSV);
    document.getElementById('btnPrint').addEventListener('click', window.print);
    
    // Debouncing sur les changements de filtres
    ['filterStart', 'filterEnd', 'filterTech', 'filterSite'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(applyFilters, 500);
            });
        }
    });
}

// =====================
// FILTRES
// =====================

function applyDatePreset(preset) {
    const today = new Date();
    let start, end;
    
    switch(preset) {
        case 'today':
            start = end = today;
            break;
        case 'week':
            start = new Date(today);
            start.setDate(today.getDate() - 7);
            end = today;
            break;
        case 'month':
            start = new Date(today.getFullYear(), today.getMonth(), 1);
            end = today;
            break;
        case 'quarter':
            const quarter = Math.floor(today.getMonth() / 3);
            start = new Date(today.getFullYear(), quarter * 3, 1);
            end = today;
            break;
        case 'year':
            start = new Date(today.getFullYear(), 0, 1);
            end = today;
            break;
        default:
            return;
    }
    
    document.getElementById('filterStart').value = start.toISOString().slice(0, 10);
    document.getElementById('filterEnd').value = end.toISOString().slice(0, 10);
}

function resetFilters() {
    initializeDateFilters();
    document.getElementById('filterTech').selectedIndex = -1;
    document.getElementById('filterSite').selectedIndex = -1;
    document.querySelectorAll('#filterStatus input[type="checkbox"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('#filterPriority input[type="checkbox"]').forEach(cb => cb.checked = false);
    applyFilters();
}

function getFilters() {
    const startDate = document.getElementById('filterStart').value;
    const endDate = document.getElementById('filterEnd').value;
    const techIds = Array.from(document.getElementById('filterTech').selectedOptions).map(opt => parseInt(opt.value));
    const siteIds = Array.from(document.getElementById('filterSite').selectedOptions).map(opt => parseInt(opt.value));
    const statusIds = Array.from(document.querySelectorAll('#filterStatus input[type="checkbox"]:checked')).map(cb => parseInt(cb.value));
    const priorityIds = Array.from(document.querySelectorAll('#filterPriority input[type="checkbox"]:checked')).map(cb => parseInt(cb.value));
    
    return {
        start_date: startDate || null,
        end_date: endDate || null,
        tech_ids: techIds.length > 0 ? techIds : null,
        site_ids: siteIds.length > 0 ? siteIds : null,
        status_ids: statusIds.length > 0 ? statusIds : null,
        priority_ids: priorityIds.length > 0 ? priorityIds : null
    };
}

function applyFilters() {
    showLoading();
    const filters = getFilters();
    currentFilters = filters;
    
    const params = new URLSearchParams();
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.tech_ids) filters.tech_ids.forEach(id => params.append('tech_ids[]', id));
    if (filters.site_ids) filters.site_ids.forEach(id => params.append('site_ids[]', id));
    if (filters.status_ids) filters.status_ids.forEach(id => params.append('status_ids[]', id));
    if (filters.priority_ids) filters.priority_ids.forEach(id => params.append('priority_ids[]', id));
    
    fetch(`/api/stats/data?${params.toString()}`)
        .then(response => {
            if (response.status === 401) {
                // Session expirée, rediriger vers login
                alert('Session expirée. Vous allez être redirigé vers la page de connexion.');
                window.location.href = '/';
                return Promise.reject('Unauthorized');
            }
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            if (data && data.kpis) {
                updateKPIs(data.kpis);
                updateCharts(data.charts);
                updateTables(data.tables);
                hideLoading();
            } else if (data && data.error) {
                throw new Error(data.error);
            }
        })
        .catch(error => {
            console.error('Erreur lors du chargement des données:', error);
            hideLoading();
            const message = error.error || error.message || 'Erreur lors du chargement des données. Veuillez réessayer.';
            alert(message);
        });
}

// =====================
// KPIs
// =====================

function updateKPIs(kpis) {
    const container = document.getElementById('kpiCards');
    const variations = kpis.variations || {};
    
    const kpiData = [
        {
            label: 'Total Incidents',
            value: kpis.total_incidents || 0,
            variation: variations.total_incidents,
            icon: '📊',
            class: 'primary'
        },
        {
            label: 'Taux de Résolution',
            value: (kpis.taux_resolution || 0).toFixed(1) + '%',
            variation: variations.taux_resolution,
            icon: '✅',
            class: 'success'
        },
        {
            label: 'Temps Moyen',
            value: (kpis.temps_moyen_jours || 0).toFixed(1) + ' jours',
            variation: null,
            icon: '⏱️',
            class: 'info'
        },
        {
            label: 'En Cours',
            value: kpis.en_cours || 0,
            variation: variations.en_cours,
            icon: '🔄',
            class: 'warning'
        },
        {
            label: 'Urgents',
            value: kpis.urgents || 0,
            variation: variations.urgents,
            icon: '🚨',
            class: 'danger'
        },
        {
            label: 'Traités',
            value: kpis.traites || 0,
            variation: null,
            icon: '✔️',
            class: 'success'
        }
    ];
    
    container.innerHTML = kpiData.map(kpi => `
        <div class="col-md-4 col-sm-6">
            <div class="card kpi-card ${kpi.class} p-3">
                <div class="kpi-icon">${kpi.icon}</div>
                <div class="kpi-label">${kpi.label}</div>
                <div class="kpi-value">${kpi.value}</div>
                ${kpi.variation !== null && kpi.variation !== undefined ? `
                    <div class="kpi-variation ${kpi.variation >= 0 ? 'positive' : 'negative'}">
                        ${kpi.variation >= 0 ? '↑' : '↓'} ${Math.abs(kpi.variation).toFixed(1)}% vs période précédente
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// =====================
// GRAPHIQUES
// =====================

function updateCharts(chartsData) {
    updateChartParTechnicien(chartsData.par_technicien);
    updateChartParSite(chartsData.par_site);
    updateChartTopSujets(chartsData.top_sujets);
    updateChartEvolution(chartsData.evolution);
    updateChartPerformance(chartsData.par_technicien);
}

function updateChartParTechnicien(data) {
    const ctx = document.getElementById('chartParTechnicien').getContext('2d');
    
    // Grouper par technicien
    const techMap = {};
    data.forEach(item => {
        if (!techMap[item.collaborateur]) {
            techMap[item.collaborateur] = {};
        }
        techMap[item.collaborateur][item.statut] = item.count;
    });
    
    const techs = Object.keys(techMap);
    const statuts = [...new Set(data.map(d => d.statut))];
    
    const datasets = statuts.map((statut, idx) => {
        const colors = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0', '#6f42c1'];
        return {
            label: statut,
            data: techs.map(tech => techMap[tech][statut] || 0),
            backgroundColor: colors[idx % colors.length] + '80',
            borderColor: colors[idx % colors.length],
            borderWidth: 1
        };
    });
    
    if (charts.parTechnicien) {
        charts.parTechnicien.destroy();
    }
    
    charts.parTechnicien = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: techs,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true
                }
            }
        }
    });
}

function updateChartParSite(data) {
    const ctx = document.getElementById('chartParSite').getContext('2d');
    
    const labels = data.map(d => d.site);
    const values = data.map(d => d.count);
    const colors = generateColors(values.length);
    
    if (charts.parSite) {
        charts.parSite.destroy();
    }
    
    charts.parSite = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function updateChartTopSujets(data) {
    const ctx = document.getElementById('chartTopSujets').getContext('2d');
    
    const labels = data.map(d => d.sujet);
    const values = data.map(d => d.count);
    
    if (charts.topSujets) {
        charts.topSujets.destroy();
    }
    
    charts.topSujets = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Nombre d\'incidents',
                data: values,
                backgroundColor: '#ffc107',
                borderColor: '#ff9800',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateChartEvolution(data) {
    const ctx = document.getElementById('chartEvolution').getContext('2d');
    
    const labels = data.map(d => d.date);
    const totals = data.map(d => d.total);
    const traites = data.map(d => d.traites || 0);
    
    if (charts.evolution) {
        charts.evolution.destroy();
    }
    
    charts.evolution = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Créés',
                    data: totals,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Traités',
                    data: traites,
                    borderColor: '#198754',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateChartPerformance(data) {
    const ctx = document.getElementById('chartPerformance').getContext('2d');
    
    const techMap = {};
    data.forEach(item => {
        if (!techMap[item.collaborateur]) {
            techMap[item.collaborateur] = { traites: 0, en_cours: 0, suspendus: 0 };
        }
        if (item.statut.includes('Traité') || item.statut.includes('traite')) {
            techMap[item.collaborateur].traites += item.count;
        } else if (item.statut.includes('cours') || item.statut.includes('Affecté')) {
            techMap[item.collaborateur].en_cours += item.count;
        } else {
            techMap[item.collaborateur].suspendus += item.count;
        }
    });
    
    const techs = Object.keys(techMap);
    
    if (charts.performance) {
        charts.performance.destroy();
    }
    
    charts.performance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: techs,
            datasets: [
                {
                    label: 'Traités',
                    data: techs.map(t => techMap[t].traites),
                    backgroundColor: '#198754'
                },
                {
                    label: 'En cours',
                    data: techs.map(t => techMap[t].en_cours),
                    backgroundColor: '#ffc107'
                },
                {
                    label: 'Suspendus',
                    data: techs.map(t => techMap[t].suspendus),
                    backgroundColor: '#dc3545'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                x: {
                    stacked: false
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// =====================
// TABLEAUX SCROLLABLES
// =====================

function updateTables(tables) {
    updateTableTechnicien(tables.par_technicien);
    updateTableSite(tables.par_site);
    updateTableSujet(tables.par_sujet);
    
    // Afficher info pagination si disponible
    if (tables.pagination) {
        const total = tables.pagination.total;
        const page = tables.pagination.page;
        const perPage = tables.pagination.per_page;
        const start = (page - 1) * perPage + 1;
        const end = Math.min(page * perPage, total);
        
        document.getElementById('paginationTech').textContent = 
            `Affichage ${start}-${end} sur ${total} techniciens`;
        document.getElementById('paginationSite').textContent = 
            `Affichage ${start}-${end} sur ${total} sites`;
        document.getElementById('paginationSujet').textContent = 
            `Affichage ${start}-${end} sur ${total} sujets`;
    }
}

function updateTableTechnicien(data) {
    const tbody = document.querySelector('#tableTechnicien tbody');
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Aucune donnée</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => {
        const taux = row.total > 0 ? ((row.traites / row.total) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td><strong>${row.collaborateur}</strong></td>
                <td>${row.total}</td>
                <td>${row.traites}</td>
                <td>${row.en_cours}</td>
                <td>${row.suspendus || 0}</td>
                <td><span class="badge bg-success">${taux}%</span></td>
            </tr>
        `;
    }).join('');
}

function updateTableSite(data) {
    const tbody = document.querySelector('#tableSite tbody');
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Aucune donnée</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => {
        const taux = row.total > 0 ? ((row.traites / row.total) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td><strong>${row.site}</strong></td>
                <td>${row.total}</td>
                <td>${row.traites}</td>
                <td>${row.en_cours}</td>
                <td><span class="badge bg-success">${taux}%</span></td>
            </tr>
        `;
    }).join('');
}

function updateTableSujet(data) {
    const tbody = document.querySelector('#tableSujet tbody');
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Aucune donnée</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(row => {
        const taux = row.total > 0 ? ((row.traites / row.total) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td><strong>${row.sujet}</strong></td>
                <td>${row.total}</td>
                <td>${row.traites}</td>
                <td><span class="badge bg-success">${taux}%</span></td>
            </tr>
        `;
    }).join('');
}

// =====================
// EXPORTS
// =====================

function exportExcel() {
    const params = buildExportParams();
    window.location.href = `/dashboard/stats/export/excel?${params}`;
}

function exportPDF() {
    const params = buildExportParams();
    window.location.href = `/dashboard/stats/export/pdf?${params}`;
}

function exportCSV() {
    const params = buildExportParams();
    window.location.href = `/dashboard/stats/export/csv?${params}`;
}

function buildExportParams() {
    const params = new URLSearchParams();
    if (currentFilters.start_date) params.append('start_date', currentFilters.start_date);
    if (currentFilters.end_date) params.append('end_date', currentFilters.end_date);
    if (currentFilters.tech_ids) currentFilters.tech_ids.forEach(id => params.append('tech_ids[]', id));
    if (currentFilters.site_ids) currentFilters.site_ids.forEach(id => params.append('site_ids[]', id));
    if (currentFilters.status_ids) currentFilters.status_ids.forEach(id => params.append('status_ids[]', id));
    if (currentFilters.priority_ids) currentFilters.priority_ids.forEach(id => params.append('priority_ids[]', id));
    return params.toString();
}

// =====================
// UTILITAIRES
// =====================

function generateColors(count) {
    const colors = [
        '#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0',
        '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d'
    ];
    return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('d-none');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('d-none');
}

