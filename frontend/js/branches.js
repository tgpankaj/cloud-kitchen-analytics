// ==========================================
// BRANCH COMPARISON LOGIC
// ==========================================

let revenueChart = null;
let ordersChart = null;

const KITCHEN_COLORS = [
    '#ff6b35', '#3b82f6', '#22c55e', '#8b5cf6',
    '#f59e0b', '#ec4899', '#14b8a6', '#6366f1'
];

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadBranches();
});

async function loadBranches() {
    const days = document.getElementById('daysFilter').value;

    try {
        const [comparison, consolidated, kitchens] = await Promise.all([
            apiFetch(`/api/branches/compare?days=${days}`),
            apiFetch(`/api/branches/consolidated?days=${days}`),
            apiFetch(`/api/branches/list?days=${days}`)
        ]);

        renderKpis(consolidated.kpis);
        renderComparisonTable(comparison);
        renderCharts(comparison);
        renderTopByKitchen(consolidated.top_by_kitchen);
        renderKitchenCards(kitchens);

    } catch (err) {
        showAlert('Failed to load branches: ' + err.message, 'error');
    }
}

function renderKpis(kpis) {
    document.getElementById('kpiKitchens').textContent =
        formatNumber(kpis.total_kitchens);
    document.getElementById('kpiOrders').textContent =
        formatNumber(kpis.total_orders);
    document.getElementById('kpiNetRevenue').textContent =
        formatCurrency(kpis.net_revenue);
    document.getElementById('kpiCustomers').textContent =
        formatNumber(kpis.unique_customers);
}

function renderComparisonTable(rows) {
    const tbody = document.getElementById('compareBody');

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="muted center">No kitchens yet. Click "Add Kitchen".</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map((r, i) => {
        const rankClass = i < 3 ? `rank-${i + 1}` : '';
        const cancelClass = r.cancel_rate > 15 ? 'negative' : (r.cancel_rate > 8 ? '' : 'positive');

        return `
            <tr class="${rankClass}">
                <td>
                    <div class="kitchen-name-cell">
                        ${i === 0 ? '🥇 ' : i === 1 ? '🥈 ' : i === 2 ? '🥉 ' : ''}
                        ${escapeHtml(r.name)}
                    </div>
                    ${r.city ? `<span class="kitchen-city">${escapeHtml(r.city)}</span>` : ''}
                </td>
                <td class="num">${formatNumber(r.total_orders)}</td>
                <td class="num">${formatCurrency(r.gross_revenue)}</td>
                <td class="num" style="font-weight:600;color:var(--success)">${formatCurrency(r.net_revenue)}</td>
                <td class="num negative">${formatCurrency(r.commission_paid)}</td>
                <td class="num">${formatCurrency(r.avg_order_value)}</td>
                <td class="num">${formatNumber(r.unique_customers)}</td>
                <td class="num">${r.avg_delivery_time} min</td>
                <td class="num cell-profit ${cancelClass}">${r.cancel_rate}%</td>
            </tr>
        `;
    }).join('');
}

function renderCharts(rows) {
    if (!rows || rows.length === 0) return;

    const labels = rows.map(r => r.name);
    const netRevenues = rows.map(r => r.net_revenue);
    const orders = rows.map(r => r.total_orders);

    // Revenue chart
    const ctx1 = document.getElementById('revenueChart').getContext('2d');
    if (revenueChart) revenueChart.destroy();

    revenueChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Net Revenue',
                data: netRevenues,
                backgroundColor: labels.map((_, i) => KITCHEN_COLORS[i % KITCHEN_COLORS.length] + 'cc'),
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Net Revenue: ${formatCurrency(ctx.parsed.y)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (v) => '₹' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v)
                    },
                    grid: { color: '#f3f4f6' }
                },
                x: { grid: { display: false } }
            }
        }
    });

    // Orders chart
    const ctx2 = document.getElementById('ordersChart').getContext('2d');
    if (ordersChart) ordersChart.destroy();

    ordersChart = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: orders,
                backgroundColor: labels.map((_, i) => KITCHEN_COLORS[i % KITCHEN_COLORS.length]),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 10, font: { size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? (ctx.parsed / total * 100).toFixed(1) : 0;
                            return `${ctx.label}: ${ctx.parsed} orders (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderTopByKitchen(data) {
    const container = document.getElementById('topByKitchen');

    if (!data || data.length === 0) {
        container.innerHTML = '<p class="muted small">No data yet.</p>';
        return;
    }

    container.innerHTML = data.map(k => `
        <div class="kitchen-top-card">
            <h4>${escapeHtml(k.kitchen_name)}</h4>
            ${k.items.map((item, i) => `
                <div class="top-item-row">
                    <span class="top-item-rank">${i + 1}</span>
                    <span class="top-item-name">${escapeHtml(item.name)}</span>
                    <span class="top-item-rev">${formatCurrency(item.revenue)}</span>
                </div>
            `).join('')}
        </div>
    `).join('');
}

function renderKitchenCards(kitchens) {
    const container = document.getElementById('kitchenCards');

    if (!kitchens || kitchens.length === 0) {
        container.innerHTML = '<p class="muted">No kitchens yet. Click "Add Kitchen" to start.</p>';
        return;
    }

    container.innerHTML = kitchens.map(k => `
        <div class="kitchen-card">
            <div class="kitchen-card-header">
                <h4>${escapeHtml(k.name)}</h4>
                <span class="kitchen-status ${k.is_active ? 'active' : 'inactive'}">
                    ${k.is_active ? 'Active' : 'Inactive'}
                </span>
            </div>
            ${k.city ? `<div class="kitchen-card-location">📍 ${escapeHtml(k.city)}</div>` : ''}

            <div class="kitchen-card-stats">
                <div class="kitchen-stat">
                    <span class="kitchen-stat-label">Orders</span>
                    <span class="kitchen-stat-value">${formatNumber(k.total_orders)}</span>
                </div>
                <div class="kitchen-stat">
                    <span class="kitchen-stat-label">Net Revenue</span>
                    <span class="kitchen-stat-value positive">${formatCurrency(k.net_revenue)}</span>
                </div>
                <div class="kitchen-stat">
                    <span class="kitchen-stat-label">AOV</span>
                    <span class="kitchen-stat-value">${formatCurrency(k.avg_order_value)}</span>
                </div>
                <div class="kitchen-stat">
                    <span class="kitchen-stat-label">Customers</span>
                    <span class="kitchen-stat-value">${formatNumber(k.unique_customers)}</span>
                </div>
            </div>

            <div class="kitchen-card-actions">
                <button onclick="editKitchen(${k.id})" class="btn btn-secondary">✏️ Edit</button>
                <button onclick="switchToKitchen(${k.id})" class="btn btn-primary">Switch →</button>
            </div>
        </div>
    `).join('');
}

// ==========================================
// KITCHEN MODAL
// ==========================================

let allKitchens = [];

async function openAddKitchen() {
    document.getElementById('kitchenModalTitle').textContent = 'Add Kitchen';
    document.getElementById('kitchenForm').reset();
    document.getElementById('kitchenId').value = '';
    document.getElementById('kitchenModal').style.display = 'flex';
}

async function editKitchen(id) {
    try {
        const k = await apiFetch(`/api/branches/${id}`);
        document.getElementById('kitchenModalTitle').textContent = 'Edit Kitchen';
        document.getElementById('kitchenId').value = id;
        document.getElementById('kitchenName').value = k.name;
        document.getElementById('kitchenCity').value = k.city;
        document.getElementById('kitchenAddress').value = k.address;
        document.getElementById('kitchenModal').style.display = 'flex';
    } catch (err) {
        showAlert('Failed to load kitchen: ' + err.message, 'error');
    }
}

function closeKitchenModal() {
    document.getElementById('kitchenModal').style.display = 'none';
}

async function saveKitchen(e) {
    e.preventDefault();

    const id = document.getElementById('kitchenId').value;
    const data = {
        name: document.getElementById('kitchenName').value.trim(),
        city: document.getElementById('kitchenCity').value.trim(),
        address: document.getElementById('kitchenAddress').value.trim()
    };

    const btn = document.getElementById('kitchenSaveBtn');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        if (id) {
            await apiFetch(`/api/branches/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            showAlert('Kitchen updated', 'success');
        } else {
            await apiFetch('/api/branches/create', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showAlert('Kitchen added', 'success');
        }
        closeKitchenModal();
        loadBranches();
    } catch (err) {
        showAlert(err.message || 'Failed to save', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save';
    }
}

function switchToKitchen(id) {
    localStorage.setItem('active_kitchen_id', id);
    window.location.href = 'dashboard.html';
}

