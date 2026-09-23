// ==========================================
// AI RECOMMENDATIONS LOGIC
// ==========================================

let allInsights = [];
let currentTypeFilter = 'all';
let currentCategoryFilter = '';

const ICONS = {
    'Menu': '🍔',
    'Commission': '💸',
    'Delivery': '🚚',
    'Operations': '⚙️',
    'Customers': '👥',
    'Inventory': '📦',
    'Revenue': '📈'
};

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadInsights();
});

async function loadInsights() {
    const days = document.getElementById('daysFilter').value;

    try {
        const [insights, summary] = await Promise.all([
            apiFetch(`/api/recommendations/insights?days=${days}`),
            apiFetch(`/api/recommendations/summary?days=${days}`)
        ]);

        allInsights = insights;
        renderSummary(summary);
        populateCategoryFilter(insights);
        applyFilters();

    } catch (err) {
        showAlert('Failed to load insights: ' + err.message, 'error');
    }
}

function renderSummary(summary) {
    document.getElementById('kpiCritical').textContent =
        summary.by_priority.critical || 0;
    document.getElementById('kpiWarning').textContent =
        (summary.by_type.danger || 0) + (summary.by_type.warning || 0);
    document.getElementById('kpiSuccess').textContent =
        summary.by_type.success || 0;
    document.getElementById('kpiTotal').textContent = summary.total || 0;
}

function populateCategoryFilter(insights) {
    const sel = document.getElementById('categoryFilter');
    const categories = [...new Set(insights.map(i => i.category).filter(Boolean))].sort();

    sel.innerHTML = '<option value="">All Categories</option>' +
        categories.map(c =>
            `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`
        ).join('');
}

function setFilter(filter) {
    currentTypeFilter = filter;
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    document.querySelector(`[data-filter="${filter}"]`)?.classList.add('active');
    applyFilters();
}

function setCategoryFilter() {
    currentCategoryFilter = document.getElementById('categoryFilter').value;
    applyFilters();
}

function applyFilters() {
    let filtered = allInsights;

    if (currentTypeFilter !== 'all') {
        filtered = filtered.filter(i => i.type === currentTypeFilter);
    }

    if (currentCategoryFilter) {
        filtered = filtered.filter(i => i.category === currentCategoryFilter);
    }

    renderInsights(filtered);
}

function renderInsights(insights) {
    const container = document.getElementById('insightsList');
    const empty = document.getElementById('emptyState');

    if (!insights || insights.length === 0) {
        container.innerHTML = '';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';

    container.innerHTML = insights.map(i => `
        <div class="insight-card ${i.type}">
            <div class="insight-icon">
                ${ICONS[i.category] || '💡'}
            </div>
            <div class="insight-content">
                <div class="insight-header">
                    <h3 class="insight-title">${escapeHtml(i.title)}</h3>
                    <div class="insight-badges">
                        <span class="badge-category">${escapeHtml(i.category || 'General')}</span>
                        <span class="badge-priority ${i.priority}">
                            ${i.priority.toUpperCase()}
                        </span>
                    </div>
                </div>
                <p class="insight-description">${escapeHtml(i.description)}</p>
                <div class="insight-action">${escapeHtml(i.action)}</div>
                ${renderMetrics(i.metrics)}
            </div>
        </div>
    `).join('');
}

function renderMetrics(metrics) {
    if (!metrics || Object.keys(metrics).length === 0) return '';

    const pills = Object.entries(metrics).map(([key, val]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        let display = val;

        if (typeof val === 'number') {
            if (key.includes('revenue') || key.includes('cost') || key.includes('loss') || key.includes('paid')) {
                display = formatCurrency(val);
            } else if (key.includes('pct')) {
                display = val + '%';
            } else if (key.includes('qty') || key.includes('count') || key.includes('orders')) {
                display = formatNumber(val);
            } else {
                display = val.toLocaleString('en-IN');
            }
        }

        return `<span class="metric-pill">${label}: <strong>${display}</strong></span>`;
    }).join('');

    return `<div class="insight-metrics">${pills}</div>`;
}