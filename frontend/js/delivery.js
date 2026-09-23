// ==========================================
// DELIVERY ANALYTICS LOGIC
// ==========================================

let distributionChart = null;
let lateChart = null;
let scatterChart = null;

const PLATFORM_COLORS = {
    'Swiggy': '#fc8019',
    'Zomato': '#e23744',
    'Direct': '#22c55e'
};

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadDelivery();
});

async function loadDelivery() {
    const days = document.getElementById('daysFilter').value;

    try {
        const [stats, byPlatform, distribution, prepVsDelivery, slowDishes] = await Promise.all([
            apiFetch(`/api/delivery/stats?days=${days}`),
            apiFetch(`/api/delivery/by-platform?days=${days}`),
            apiFetch(`/api/delivery/distribution?days=${days}`),
            apiFetch(`/api/delivery/prep-vs-delivery?days=${days}`),
            apiFetch(`/api/delivery/slow-dishes?days=${days}`)
        ]);

        renderKpis(stats);
        renderDistribution(distribution);
        renderLateChart(stats);
        renderScatter(prepVsDelivery);
        renderPlatformTable(byPlatform);
        renderSlowDishes(slowDishes);

    } catch (err) {
        showAlert('Failed to load delivery data: ' + err.message, 'error');
    }
}

function renderKpis(stats) {
    document.getElementById('kpiPrep').textContent =
        `${stats.avg_prep_time} min`;
    document.getElementById('kpiDelivery').textContent =
        `${stats.avg_delivery_time} min`;
    document.getElementById('kpiTotal').textContent =
        `${stats.avg_total_time} min`;
    document.getElementById('kpiLate').textContent =
        `${stats.late_percentage}%`;
    document.getElementById('kpiLateSub').textContent =
        `${stats.late_orders} of ${stats.total_orders} orders >45 min`;
}

function renderDistribution(data) {
    const ctx = document.getElementById('distributionChart').getContext('2d');

    if (distributionChart) distributionChart.destroy();

    const labels = data.map(d => d.bucket);
    const values = data.map(d => d.orders);

    // Color code buckets
    const colors = labels.map(l => {
        if (l === '<20 min' || l === '20-30 min') return '#22c55e';
        if (l === '30-40 min') return '#f59e0b';
        if (l === '40-50 min') return '#f97316';
        return '#ef4444';
    });

    distributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Orders',
                data: values,
                backgroundColor: colors,
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
                        label: (ctx) => `${ctx.parsed.y} orders`
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderLateChart(stats) {
    const ctx = document.getElementById('lateChart').getContext('2d');

    if (lateChart) lateChart.destroy();

    const onTime = stats.total_orders - stats.late_orders;
    const late = stats.late_orders;

    lateChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['On Time (≤45 min)', 'Late (>45 min)'],
            datasets: [{
                data: [onTime, late],
                backgroundColor: ['#22c55e', '#ef4444'],
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
                            return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderScatter(data) {
    const ctx = document.getElementById('scatterChart').getContext('2d');

    if (scatterChart) scatterChart.destroy();

    if (!data || data.length === 0) return;

    const maxAmount = Math.max(...data.map(d => d.amount), 1);

    // Group by platform
    const platforms = [...new Set(data.map(d => d.platform))];

    const datasets = platforms.map(p => ({
        label: p,
        data: data.filter(d => d.platform === p).map(d => ({
            x: d.prep,
            y: d.delivery,
            r: Math.max(3, Math.sqrt(d.amount / maxAmount) * 12)
        })),
        backgroundColor: (PLATFORM_COLORS[p] || '#6b7280') + '99',
        borderColor: PLATFORM_COLORS[p] || '#6b7280',
        borderWidth: 1
    }));

    scatterChart = new Chart(ctx, {
        type: 'bubble',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: { boxWidth: 12, padding: 12, font: { size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const d = ctx.raw;
                            return [
                                `Prep: ${d.x} min`,
                                `Delivery: ${d.y} min`,
                                `Order: ${formatCurrency(d.amount)}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Prep Time (min)', font: { size: 11 } },
                    grid: { color: '#f3f4f6' }
                },
                y: {
                    title: { display: true, text: 'Delivery Time (min)', font: { size: 11 } },
                    grid: { color: '#f3f4f6' }
                }
            }
        }
    });
}

function renderPlatformTable(rows) {
    const tbody = document.getElementById('platformTableBody');

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="muted center">No data.</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(r => {
        let statusClass = 'good';
        let statusText = 'Excellent';
        if (r.late_pct > 20) {
            statusClass = 'bad';
            statusText = 'Needs Attention';
        } else if (r.late_pct > 10) {
            statusClass = 'warn';
            statusText = 'Monitor';
        }

        return `
            <tr>
                <td><strong>${escapeHtml(r.platform)}</strong></td>
                <td class="num">${r.orders}</td>
                <td class="num">${r.avg_prep} min</td>
                <td class="num">${r.avg_delivery} min</td>
                <td class="num">${formatCurrency(r.avg_order_value)}</td>
                <td class="num">${r.late_pct}%</td>
                <td><span class="rate-badge ${statusClass}">${statusText}</span></td>
            </tr>
        `;
    }).join('');
}

function renderSlowDishes(rows) {
    const tbody = document.getElementById('slowDishesBody');

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="muted center">No data.</td></tr>';
        return;
    }

    tbody.innerHTML = rows.map(r => {
        let rowClass = '';
        let recommendation = 'Monitor';

        if (r.avg_prep > 25) {
            rowClass = 'slow-row-critical';
            recommendation = 'Optimize recipe or pre-prep ingredients';
        } else if (r.avg_prep > 18) {
            rowClass = 'slow-row-warning';
            recommendation = 'Consider batch prep during peak hours';
        }

        return `
            <tr class="${rowClass}">
                <td><strong>${escapeHtml(r.name)}</strong></td>
                <td class="num">${r.avg_prep} min</td>
                <td class="num">${r.avg_delivery} min</td>
                <td class="num">${r.orders}</td>
                <td class="recommendation">${recommendation}</td>
            </tr>
        `;
    }).join('');
}