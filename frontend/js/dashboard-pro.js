/* ============================================================
   KitchenIQ Pro — Dashboard JS
   Connects new dashboard UI to backend APIs.
   ============================================================ */

// ============================================================
// CONFIG
// ============================================================
const API_BASE = window.API_URL || window.API_BASE || 'http://127.0.0.1:5000';
const REFRESH_MS = 30000;                  // auto-refresh every 30s
const DASHBOARD_DAYS = 7;                  // 7 / 30 / 90

// ============================================================
// AUTH HELPER
// ============================================================
function getToken() {
    // Match existing project pattern (check auth.js/config.js for exact key)
    return localStorage.getItem('token')
        || localStorage.getItem('jwt_token')
        || localStorage.getItem('kitcheniq_token')
        || sessionStorage.getItem('token');
}

async function apiFetch(path, options = {}) {
    const token = getToken();
    if (!token) {
        console.warn('No JWT token found — redirecting to login');
        window.location.href = '/login.html';
        return null;
    }

    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
        'Authorization': `Bearer ${token}`,
    };

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        console.warn('Token expired — redirecting to login');
        localStorage.clear();
        window.location.href = '/login.html';
        return null;
    }

    if (!res.ok) {
        const err = await res.text();
        throw new Error(`API ${path} failed (${res.status}): ${err}`);
    }

    return res.json();
}

// ============================================================
// FORMATTERS
// ============================================================
function formatINR(num) {
    const n = Number(num) || 0;
    return '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function formatINRShort(num) {
    const n = Number(num) || 0;
    if (n >= 10000000) return '₹' + (n / 10000000).toFixed(2) + 'Cr';
    if (n >= 100000)   return '₹' + (n / 100000).toFixed(2) + 'L';
    if (n >= 1000)     return '₹' + (n / 1000).toFixed(1) + 'k';
    return '₹' + n;
}

function formatNumber(num) {
    return (Number(num) || 0).toLocaleString('en-IN');
}

function formatPct(num, withSign = true) {
    const n = Number(num) || 0;
    const sign = withSign && n > 0 ? '+' : '';
    return sign + n.toFixed(1) + '%';
}

// ============================================================
// KPI UPDATE
// ============================================================
function updateKPIs(kpis) {
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    };

    setText('kpi-revenue', formatINR(kpis.total_revenue));
    setText('kpi-orders', formatNumber(kpis.total_orders));
    setText('kpi-profit', formatINR(kpis.net_profit));
    setText('kpi-rating', kpis.avg_rating ? kpis.avg_rating.toFixed(1) + ' / 5' : '— / 5');

    // Update growth badges (first span inside each card)
    const growths = [
        { id: 'kpi-revenue', pct: kpis.revenue_growth_pct },
        { id: 'kpi-orders',  pct: kpis.orders_growth_pct },
        { id: 'kpi-profit',  pct: kpis.profit_growth_pct ?? kpis.revenue_growth_pct },
        { id: 'kpi-rating',  pct: 0 },
    ];

    growths.forEach(({ id, pct }) => {
        const el = document.getElementById(id);
        if (!el) return;
        const card = el.closest('.bg-white');
        if (!card) return;
        const badge = card.querySelector('.text-xs span');
        if (!badge) return;
        const positive = (pct || 0) >= 0;
        badge.className = `font-medium flex items-center px-1.5 py-0.5 rounded ${positive ? 'text-emerald-600 bg-emerald-50' : 'text-rose-600 bg-rose-50'}`;
        badge.innerHTML = `<i class="fa-solid fa-arrow-trend-${positive ? 'up' : 'down'} mr-1 text-[10px]"></i> ${formatPct(Math.abs(pct))}`;
    });
}

// ============================================================
// CHARTS
// ============================================================
let trendChartInstance = null;
let platformChartInstance = null;

const rupeeFormatter = (value) => {
    if (value >= 100000) return '₹' + (value / 100000).toFixed(1) + 'L';
    if (value >= 1000)   return '₹' + (value / 1000).toFixed(1) + 'k';
    return '₹' + value;
};

function buildTrendChart(trend) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    if (trendChartInstance) trendChartInstance.destroy();

    const grad = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    grad.addColorStop(0, 'rgba(14, 165, 233, 0.2)');
    grad.addColorStop(1, 'rgba(14, 165, 233, 0)');

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.labels,
            datasets: [
                {
                    label: 'Total Revenue',
                    data: trend.revenue,
                    borderColor: '#0ea5e9',
                    backgroundColor: grad,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#0ea5e9',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                },
                {
                    label: 'Net Profit',
                    data: trend.profit,
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: false,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#10b981',
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 6, font: { size: 11 } } },
                tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${rupeeFormatter(c.raw)}` } },
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9', drawBorder: false }, ticks: { callback: rupeeFormatter, maxTicksLimit: 6 } },
                x: { grid: { display: false, drawBorder: false } },
            },
            interaction: { mode: 'index', intersect: false },
        },
    });
}

function buildPlatformChart(platforms) {
    const ctx = document.getElementById('platformBarChart');
    if (!ctx) return;

    if (platformChartInstance) platformChartInstance.destroy();

    platformChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: platforms.labels,
            datasets: [
                {
                    label: 'Gross Revenue',
                    data: platforms.gross_revenue,
                    backgroundColor: '#3b82f6',
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.8,
                },
                {
                    label: 'Commissions & Fees',
                    data: platforms.commission,
                    backgroundColor: '#f43f5e',
                    borderRadius: 4,
                    barPercentage: 0.6,
                    categoryPercentage: 0.8,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', align: 'end', labels: { usePointStyle: true, boxWidth: 6, font: { size: 11 } } },
                tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${rupeeFormatter(c.raw)}` } },
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9', drawBorder: false }, ticks: { callback: rupeeFormatter, maxTicksLimit: 5 } },
                x: { grid: { display: false, drawBorder: false } },
            },
        },
    });
}

// ============================================================
// INTEGRATIONS BAR (top)
// ============================================================
function updateIntegrationsBar(integrations) {
    if (!integrations || integrations.length === 0) return;

    integrations.forEach((integ) => {
        // Find the card for this platform (Zomato/Swiggy/Uber Eats)
        const cards = document.querySelectorAll('.grid.grid-cols-1.sm\\:grid-cols-3 > div');
        cards.forEach((card) => {
            const platformName = card.querySelector('p.text-sm.font-semibold');
            if (!platformName) return;
            if (platformName.textContent.toLowerCase().trim() !== integ.platform.toLowerCase()) return;

            const statusLine = card.querySelector('p.text-\\[10px\\]');
            if (!statusLine) return;

            const isConnected = integ.status === 'connected';
            const dotColor = isConnected ? 'bg-emerald-500' : 'bg-rose-500';
            const textColor = isConnected ? 'text-emerald-600' : 'text-rose-500';
            const pulseClass = isConnected ? 'animate-pulse' : '';
            const label = isConnected ? 'Connected' : (integ.status || 'Disconnected');
            const lastSync = integ.last_sync_at ? ` · ${new Date(integ.last_sync_at).toLocaleTimeString()}` : '';

            statusLine.className = `text-[10px] ${textColor} mt-1 flex items-center`;
            statusLine.innerHTML = `<span class="h-1.5 w-1.5 rounded-full ${dotColor} mr-1 ${pulseClass}"></span> ${label}${lastSync}`;
        });
    });
}

// ============================================================
// AI INSIGHTS (right panel)
// ============================================================
const TYPE_STYLES = {
    success:  { bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-100', accent: 'bg-emerald-500', icon: 'fa-arrow-up-right-dots', label: 'Promote' },
    info:     { bg: 'bg-blue-50',    text: 'text-blue-600',    border: 'border-blue-100',    accent: 'bg-blue-500',    icon: 'fa-lightbulb',            label: 'Opportunity' },
    warning:  { bg: 'bg-amber-50',   text: 'text-amber-600',   border: 'border-amber-100',   accent: 'bg-amber-500',   icon: 'fa-wrench',               label: 'Optimize' },
    danger:   { bg: 'bg-rose-50',    text: 'text-rose-600',    border: 'border-rose-100',    accent: 'bg-rose-500',    icon: 'fa-triangle-exclamation', label: 'Review' },
};

function renderInsights(insights) {
    // Find container — either by ID (if Step 3.2 worked) or by class (fallback)
    let container = document.getElementById('insights-container');
    if (!container) {
        // Fallback: find the scrollable div inside the AI panel
        const panels = document.querySelectorAll('div');
        for (const p of panels) {
            if (p.className.includes('p-4') && p.className.includes('overflow-y-auto') && p.className.includes('space-y-4')) {
                container = p;
                break;
            }
        }
    }
    if (!container) {
        console.warn('AI insights container not found');
        return;
    }

    if (!insights || insights.length === 0) {
        container.innerHTML = `
            <div class="text-center text-slate-400 text-xs py-8">
                <i class="fa-solid fa-inbox text-2xl mb-2"></i>
                <p>No insights yet — upload some orders first.</p>
            </div>`;
        return;
    }

    container.innerHTML = insights.slice(0, 4).map((insight) => {
        const style = TYPE_STYLES[insight.type] || TYPE_STYLES.info;
        return `
            <div class="bg-white border ${style.border} rounded-lg p-4 shadow-sm relative">
                <div class="absolute top-0 left-0 w-1 h-full ${style.accent} rounded-l-lg"></div>
                <div class="flex justify-between items-start mb-2">
                    <span class="text-[10px] font-bold tracking-wider ${style.text} uppercase flex items-center ${style.bg} px-1.5 py-0.5 rounded">
                        <i class="fa-solid ${style.icon} mr-1"></i> ${style.label}
                    </span>
                    <span class="text-[10px] text-slate-400">${insight.category || ''}</span>
                </div>
                <h3 class="text-sm font-bold text-slate-800">${insight.title || insight.item || 'Insight'}</h3>
                <p class="text-xs text-slate-600 mt-1 leading-relaxed">${insight.reason || insight.message || ''}</p>
                ${insight.suggested_action ? `
                    <div class="mt-2 bg-slate-50 p-2 rounded text-[11px] text-slate-600 border border-slate-100">
                        <strong>Action:</strong> ${insight.suggested_action}
                    </div>` : ''}
            </div>`;
    }).join('');
}

async function loadInsights() {
    try {
        const insights = await apiFetch('/api/recommendations/top?limit=4');
        if (insights) renderInsights(insights);
    } catch (e) {
        console.warn('Insights failed:', e);
    }
}

// ============================================================
// SYNC BUTTON (Phase 5 — full flow)
// ============================================================
window.syncPipeline = async function(btnElement, platform) {
    if (btnElement.disabled) return;

    const original = btnElement.innerHTML;
    btnElement.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin mr-1"></i> Syncing';
    btnElement.disabled = true;
    btnElement.classList.add('opacity-75', 'cursor-wait');

    try {
        // 1. Try sync directly
        let result;
        try {
            result = await apiFetch('/api/integrations/sync', {
                method: 'POST',
                body: JSON.stringify({ platform }),
            });
        } catch (err) {
            // If not connected yet, auto-connect then sync
            if (err.message.includes('400') || err.message.includes('not connected')) {
                btnElement.innerHTML = '<i class="fa-solid fa-link mr-1"></i> Connecting';
                await apiFetch('/api/integrations/connect', {
                    method: 'POST',
                    body: JSON.stringify({ platform }),
                });
                btnElement.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin mr-1"></i> Syncing';
                result = await apiFetch('/api/integrations/sync', {
                    method: 'POST',
                    body: JSON.stringify({ platform }),
                });
            } else {
                throw err;
            }
        }

        // 2. Success
        const created = result?.created ?? 0;
        btnElement.innerHTML = `<i class="fa-solid fa-check text-emerald-600 mr-1"></i> +${created}`;
        btnElement.classList.remove('opacity-75', 'cursor-wait');
        btnElement.classList.add('bg-emerald-50', 'border-emerald-200', 'text-emerald-700');

        // 3. Refresh dashboard after short delay
        setTimeout(() => loadDashboard(), 800);

        // 4. Reset button after 3s
        setTimeout(() => {
            btnElement.innerHTML = original;
            btnElement.disabled = false;
            btnElement.classList.remove('bg-emerald-50', 'border-emerald-200', 'text-emerald-700');
        }, 3000);

    } catch (e) {
        console.error('Sync failed:', e);
        btnElement.innerHTML = '<i class="fa-solid fa-xmark text-rose-600 mr-1"></i> Failed';
        btnElement.classList.remove('opacity-75', 'cursor-wait');
        btnElement.classList.add('bg-rose-50', 'border-rose-200', 'text-rose-700');

        // Show error tooltip
        btnElement.title = e.message || 'Sync failed';

        setTimeout(() => {
            btnElement.innerHTML = original;
            btnElement.disabled = false;
            btnElement.classList.remove('bg-rose-50', 'border-rose-200', 'text-rose-700');
            btnElement.title = '';
        }, 3000);
    }
};

// ============================================================
// MAIN LOADER
// ============================================================
async function loadDashboard() {
    try {
        const data = await apiFetch(`/api/dashboard/summary?days=${DASHBOARD_DAYS}`);
        if (!data) return;

        updateKPIs(data.kpis || {});
        buildTrendChart(data.trend || { labels: [], revenue: [], profit: [] });
        buildPlatformChart(data.platforms || { labels: [], gross_revenue: [], commission: [] });
        updateIntegrationsBar(data.integrations || []);

        // Insights load separately (different endpoint)
        loadInsights();

    } catch (e) {
        console.error('Dashboard load failed:', e);
        // Optionally show toast/error state
    }
}


// ============================================================
// CONNECT PLATFORM (for disconnected integrations)
// ============================================================
window.connectPlatform = async function(btnElement, platform) {
    if (btnElement.disabled) return;

    const original = btnElement.innerHTML;
    btnElement.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>';
    btnElement.disabled = true;

    try {
        await apiFetch('/api/integrations/connect', {
            method: 'POST',
            body: JSON.stringify({ platform }),
        });

        btnElement.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Connected';
        btnElement.classList.remove('bg-slate-800', 'hover:bg-slate-900');
        btnElement.classList.add('bg-emerald-600', 'hover:bg-emerald-700');

        setTimeout(() => loadDashboard(), 800);

    } catch (e) {
        console.error('Connect failed:', e);
        btnElement.innerHTML = '<i class="fa-solid fa-xmark mr-1"></i> Failed';
        btnElement.classList.add('bg-rose-600');

        setTimeout(() => {
            btnElement.innerHTML = original;
            btnElement.disabled = false;
            btnElement.classList.remove('bg-rose-600');
        }, 2500);
    }
};

// ============================================================
// BOOT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Chart.js defaults
    if (window.Chart) {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#64748b';
        Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 6;
    }

    // Mobile sidebar toggle
    const sidebar = document.getElementById('sidebar');
    const openBtn = document.getElementById('openSidebar');
    const closeBtn = document.getElementById('closeSidebar');
    const overlay = document.getElementById('sidebarOverlay');

    function toggleSidebar() {
        if (!sidebar) return;
        const isClosed = sidebar.classList.contains('-translate-x-full');
        sidebar.classList.toggle('-translate-x-full', !isClosed);
        if (overlay) overlay.classList.toggle('hidden', !isClosed);
    }
    openBtn?.addEventListener('click', toggleSidebar);
    closeBtn?.addEventListener('click', toggleSidebar);
    overlay?.addEventListener('click', toggleSidebar);

    // Initial load + auto-refresh
    loadDashboard();
    setInterval(loadDashboard, REFRESH_MS);
});


// ============================================================
// PHASE 6: SMART POLLING + LIVE UX
// ============================================================

// ---------- State ----------
let lastVersion = null;
let isFirstLoad = true;
let newOrderCount = 0;

// ---------- Toast Notification ----------
function showToast(message, type = 'info') {
    const colors = {
        info: 'bg-slate-800',
        success: 'bg-emerald-600',
        warning: 'bg-amber-500',
        error: 'bg-rose-600',
    };

    // Create container if not exists
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed top-20 right-6 z-50 space-y-2';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center min-w-[240px] max-w-[320px] transform transition-all duration-300 translate-x-full opacity-0`;
    toast.innerHTML = `
        <i class="fa-solid fa-circle-info mr-2"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full', 'opacity-0');
    });

    // Auto-remove after 4s
    setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ---------- Live Indicator ----------
function ensureLiveIndicator() {
    // Find the header area
    const header = document.querySelector('header .flex.items-center.space-x-3');
    if (!header) return;

    if (document.getElementById('live-indicator')) return; // already exists

    const indicator = document.createElement('div');
    indicator.id = 'live-indicator';
    indicator.className = 'hidden lg:flex items-center bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-xs font-medium text-emerald-700';
    indicator.innerHTML = `
        <span class="relative flex h-2 w-2 mr-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        Live
    `;

    // Insert before the notification bell
    const bell = header.querySelector('button.relative');
    if (bell) {
        header.insertBefore(indicator, bell);
    } else {
        header.appendChild(indicator);
    }
}

function setLiveStatus(status) {
    const indicator = document.getElementById('live-indicator');
    if (!indicator) return;

    if (status === 'live') {
        indicator.className = 'hidden lg:flex items-center bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-xs font-medium text-emerald-700';
        indicator.innerHTML = `
            <span class="relative flex h-2 w-2 mr-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            Live
        `;
    } else if (status === 'loading') {
        indicator.className = 'hidden lg:flex items-center bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-500';
        indicator.innerHTML = `
            <i class="fa-solid fa-circle-notch fa-spin mr-2"></i>
            Syncing
        `;
    } else if (status === 'error') {
        indicator.className = 'hidden lg:flex items-center bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 text-xs font-medium text-rose-700';
        indicator.innerHTML = `
            <i class="fa-solid fa-wifi mr-2"></i>
            Offline
        `;
    }
}

// ---------- Smart Polling ----------
async function checkVersion() {
    try {
        const { version, order_count } = await apiFetch('/api/dashboard/version');
        if (!version) return;

        // First load: just save version
        if (lastVersion === null) {
            lastVersion = version;
            return;
        }

        // Data changed?
        if (version !== lastVersion) {
            const diff = order_count - (newOrderCount || 0);
            lastVersion = version;
            newOrderCount = order_count;

            // Toast notification
            if (diff > 0) {
                showToast(`${diff} new order${diff > 1 ? 's' : ''} arrived!`, 'success');
            }

            // Silent refresh
            await loadDashboard(true);
        }

        setLiveStatus('live');
    } catch (e) {
        console.warn('Version check failed:', e);
        setLiveStatus('error');
    }
}

// ---------- Override loadDashboard for silent mode ----------
const _originalLoadDashboard = window.loadDashboard || loadDashboard;
window.loadDashboard = async function(silent = false) {
    if (!silent) setLiveStatus('loading');

    try {
        await _originalLoadDashboard.call(this);
        if (!silent) setLiveStatus('live');
    } catch (e) {
        setLiveStatus('error');
        throw e;
    }
};

// ---------- Boot Phase 6 ----------
document.addEventListener('DOMContentLoaded', () => {
    // Add live indicator
    setTimeout(() => {
        ensureLiveIndicator();
        setLiveStatus('loading');
    }, 100);

    // Smart polling: every 5 seconds
    setInterval(checkVersion, 5000);

    // Full refresh: every 60 seconds as fallback
    setInterval(() => loadDashboard(true), 60000);
});

// ============================================================
// PHASE 9: NOTIFICATIONS
// ============================================================

let notifPollingTimer = null;
let notifLastUnread = 0;

function notifIcon(severity) {
    switch (severity) {
        case 'success': return 'fa-circle-check';
        case 'warning': return 'fa-triangle-exclamation';
        case 'danger':  return 'fa-circle-exclamation';
        default:        return 'fa-bell';
    }
}

function timeAgo(iso) {
    if (!iso) return '';
    const then = new Date(iso.replace(' ', 'T') + 'Z');
    const now = new Date();
    const s = Math.floor((now - then) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

function ensureNotifPanel() {
    if (document.getElementById('notif-panel')) return;

    const panel = document.createElement('div');
    panel.id = 'notif-panel';
    panel.innerHTML = `
        <div class="notif-header">
            <div class="text-sm font-bold text-slate-800">Notifications</div>
            <button id="notif-mark-all" class="text-xs text-brand-600 hover:text-brand-700 font-medium">
                Mark all read
            </button>
        </div>
        <div class="notif-list" id="notif-list">
            <div class="text-center text-xs text-slate-400 py-8">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
            </div>
        </div>
    `;
    document.body.appendChild(panel);

    document.getElementById('notif-mark-all').addEventListener('click', async () => {
        await apiFetch('/api/notifications/v2/read-all', { method: 'POST' });
        await refreshNotifications();
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!panel.classList.contains('open')) return;
        if (e.target.closest('#notif-panel')) return;
        if (e.target.closest('#notif-bell')) return;
        panel.classList.remove('open');
    });
}

function renderNotifItems(items) {
    const list = document.getElementById('notif-list');
    if (!list) return;

    if (!items || items.length === 0) {
        list.innerHTML = `
            <div class="text-center text-xs text-slate-400 py-8">
                <i class="fa-regular fa-bell-slash text-2xl mb-2"></i>
                <p>No notifications yet.</p>
            </div>`;
        return;
    }

    list.innerHTML = items.map((n) => `
        <div class="notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
            <div class="flex items-start">
                <span class="dot dot-${n.severity} mt-1.5"></span>
                <div class="flex-1 ml-1">
                    <div class="text-sm font-semibold text-slate-800">${n.title}</div>
                    ${n.message ? `<div class="text-xs text-slate-500 mt-0.5">${n.message}</div>` : ''}
                    <div class="text-[10px] text-slate-400 mt-1">${timeAgo(n.created_at)}</div>
                </div>
                ${n.is_read ? '' : '<span class="w-2 h-2 rounded-full bg-brand-500 ml-2 mt-1"></span>'}
            </div>
        </div>
    `).join('');

    // Click handler to mark read
    list.querySelectorAll('.notif-item').forEach((el) => {
        el.addEventListener('click', async () => {
            const id = el.dataset.id;
            await apiFetch(`/api/notifications/v2/${id}/read`, { method: 'POST' });
            await refreshNotifications();
        });
    });
}

async function refreshNotifications() {
    try {
        const [items, count] = await Promise.all([
            apiFetch('/api/notifications/v2/?limit=15'),
            apiFetch('/api/notifications/v2/unread-count'),
        ]);

        renderNotifItems(items || []);

        const unread = count?.unread || 0;
        updateBellBadge(unread);

        // Show toast if count increased (new notification)
        if (notifLastUnread > 0 && unread > notifLastUnread) {
            const newItem = items?.[0];
            if (newItem) {
                showToast(newItem.title, newItem.severity || 'info');
            }
        }
        notifLastUnread = unread;

    } catch (e) {
        console.warn('Notification refresh failed:', e);
    }
}

function updateBellBadge(count) {
    const bell = document.getElementById('notif-bell');
    if (!bell) return;

    let badge = bell.querySelector('.notif-badge');
    if (!badge) {
        badge = document.createElement('span');
        badge.className = 'notif-badge';
        bell.appendChild(badge);
    }

    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : String(count);
        badge.classList.remove('hidden');
        // Also add a red dot to the original bell indicator
        const originalDot = bell.querySelector('span.bg-rose-500');
        if (originalDot) originalDot.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function wireBellButton() {
    // Find the existing bell button in the header
    const header = document.querySelector('header');
    if (!header) return;

    const bellBtn = header.querySelector('button.relative');
    if (!bellBtn) return;

    bellBtn.id = 'notif-bell';
    // Remove old onclick listeners by cloning
    const newBtn = bellBtn.cloneNode(true);
    bellBtn.replaceWith(newBtn);

    newBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const panel = document.getElementById('notif-panel');
        if (!panel) return;
        panel.classList.toggle('open');
        if (panel.classList.contains('open')) {
            refreshNotifications();
        }
    });
}

// Boot
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        ensureNotifPanel();
        wireBellButton();
        refreshNotifications();

        // Poll every 15 sec
        notifPollingTimer = setInterval(refreshNotifications, 15000);
    }, 300);
});
