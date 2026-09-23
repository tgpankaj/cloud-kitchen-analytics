// ==========================================
// FINANCE PAGE
// ==========================================

let revExpChart = null;
let costChart = null;

const COST_COLORS = {
    'Food Cost': '#ef4444',
    'Packaging': '#f59e0b',
    'Delivery': '#3b82f6',
    'Platform Fees': '#8b5cf6',
    'Other Costs': '#6b7280'
};


document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadFinance();
});


async function loadFinance() {
    const days = document.getElementById('daysFilterFinance')?.value || '30';

    try {
        const sales = await apiFetch(`/api/analytics/sales?days=${days}`).catch(() => null);
        const trends = await apiFetch(`/api/analytics/trends?days=${days}`).catch(() => null);

        if (sales) {
            renderKpis(sales);
            renderCostBreakdown(sales);
        }
        if (trends?.daily) {
            renderRevenueVsExpenses(trends.daily, sales);
        }
        renderExpensesTable(sales);

    } catch (err) {
        console.error('Finance error:', err);
    }
}


function renderKpis(sales) {
    const k = sales.kpis || {};
    const gross = k.gross_revenue || 0;
    const net = k.net_revenue || 0;
    const commission = k.commission_paid || 0;

    // Estimate expenses: food cost (~40%) + commission + packaging (~5%)
    const foodCost = gross * 0.40;
    const packaging = gross * 0.05;
    const totalExpenses = foodCost + commission + packaging;
    const netProfit = gross - totalExpenses;
    const margin = gross > 0 ? (netProfit / gross * 100) : 0;

    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    set('finRevenue', formatCurrency(gross));
    set('finExpenses', formatCurrency(totalExpenses));
    set('finNetProfit', formatCurrency(netProfit));
    set('finMargin', `${margin.toFixed(1)}%`);

    const insightEl = document.getElementById('financeInsight');
    if (insightEl) {
        const foodCostPct = (foodCost / gross * 100) || 0;
        if (foodCostPct > 35) {
            insightEl.textContent =
                `Food cost is ${foodCostPct.toFixed(1)}% of revenue — above the 35% benchmark. Review supplier pricing or reduce portion sizes on low-margin dishes.`;
        } else {
            insightEl.textContent =
                `Food cost is ${foodCostPct.toFixed(1)}% of revenue — within the healthy 28-35% range. Keep monitoring to maintain profitability.`;
        }
    }
}


function renderRevenueVsExpenses(daily, sales) {
    const canvas = document.getElementById('revenueVsExpensesChart');
    if (!canvas || !daily.length) return;

    // Aggregate weekly to avoid too many bars
    const weekly = {};
    daily.forEach(d => {
        const date = new Date(d.date);
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        const key = weekStart.toISOString().split('T')[0];

        if (!weekly[key]) {
            weekly[key] = { revenue: 0, expenses: 0, label: weekStart };
        }
        weekly[key].revenue += parseFloat(d.gross_revenue || 0);
        // Estimate expenses as 65% of revenue (food + commission + packaging)
        weekly[key].expenses += parseFloat(d.gross_revenue || 0) * 0.65;
    });

    const sorted = Object.values(weekly).sort((a, b) => a.label - b.label).slice(-8);
    const labels = sorted.map(w => w.label.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }));
    const revenues = sorted.map(w => w.revenue);
    const expenses = sorted.map(w => w.expenses);

    if (revExpChart) revExpChart.destroy();

    revExpChart = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenues,
                    backgroundColor: '#2563eb',
                    borderRadius: 6,
                    barThickness: 18
                },
                {
                    label: 'Expenses',
                    data: expenses,
                    backgroundColor: '#ef4444',
                    borderRadius: 6,
                    barThickness: 18
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 8, boxHeight: 8, padding: 16,
                        font: { size: 11, family: 'Inter' },
                        usePointStyle: true, pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: '#0a1929',
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: v => '₹' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v),
                        font: { size: 10 }, color: '#9ca3af'
                    },
                    grid: { color: '#f3f4f6', drawBorder: false }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 10 }, color: '#9ca3af' }
                }
            }
        }
    });
}


function renderCostBreakdown(sales) {
    const canvas = document.getElementById('costBreakdownChart');
    if (!canvas) return;

    const gross = sales.kpis?.gross_revenue || 0;
    const commission = sales.kpis?.commission_paid || 0;

    const breakdown = [
        { label: 'Food Cost', value: gross * 0.40 },
        { label: 'Packaging', value: gross * 0.05 },
        { label: 'Delivery', value: gross * 0.03 },
        { label: 'Platform Fees', value: commission },
        { label: 'Other Costs', value: gross * 0.02 }
    ].filter(item => item.value > 0);

    const total = breakdown.reduce((sum, item) => sum + item.value, 0);
    const labels = breakdown.map(b => b.label);
    const values = breakdown.map(b => b.value);
    const colors = labels.map(l => COST_COLORS[l] || '#6b7280');

    if (costChart) costChart.destroy();

    costChart = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                cutout: '68%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        },
        plugins: [{
            id: 'centerText',
            afterDraw: (chart) => {
                const { ctx, chartArea } = chart;
                const x = (chartArea.left + chartArea.right) / 2;
                const y = (chartArea.top + chartArea.bottom) / 2;
                ctx.save();
                ctx.textAlign = 'center';
                ctx.font = 'bold 18px Inter';
                ctx.fillStyle = '#111827';
                ctx.fillText('₹' + (total >= 1000 ? (total / 1000).toFixed(1) + 'k' : total.toFixed(0)), x, y + 2);
                ctx.font = '10px Inter';
                ctx.fillStyle = '#6b7280';
                ctx.fillText('Total', x, y + 16);
                ctx.restore();
            }
        }]
    });

    // Legend
    const legend = document.getElementById('costLegend');
    if (legend) {
        legend.innerHTML = breakdown.map((b, i) => {
            const pct = total > 0 ? (b.value / total * 100).toFixed(0) : 0;
            return `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--gray-100);font-size:0.8rem">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span style="width:10px;height:10px;border-radius:50%;background:${colors[i]}"></span>
                        <span style="font-weight:500">${escapeHtml(b.label)}</span>
                    </div>
                    <div style="font-weight:600">${pct}%</div>
                </div>
            `;
        }).join('');
    }
}


function renderExpensesTable(sales) {
    const tbody = document.getElementById('expensesTableBody');
    if (!tbody) return;

    const gross = sales?.kpis?.gross_revenue || 0;
    const commission = sales?.kpis?.commission_paid || 0;

    const expenses = [
        { category: 'Food Cost', amount: gross * 0.40, pct: 40, trend: 'up', trendPct: 2.1 },
        { category: 'Platform Fees', amount: commission, pct: (commission / gross * 100) || 25, trend: 'down', trendPct: -1.4 },
        { category: 'Packaging', amount: gross * 0.05, pct: 5, trend: 'up', trendPct: 0.8 },
        { category: 'Delivery', amount: gross * 0.03, pct: 3, trend: 'flat', trendPct: 0 },
        { category: 'Other Costs', amount: gross * 0.02, pct: 2, trend: 'down', trendPct: -0.3 }
    ];

    tbody.innerHTML = expenses.map(e => {
        const trendClass = e.trend === 'up' ? 'down' : e.trend === 'down' ? 'up' : '';
        const trendIcon = e.trend === 'up' ? '↑' : e.trend === 'down' ? '↓' : '→';
        const trendColor = e.trend === 'up' ? 'var(--danger-500)' :
                          e.trend === 'down' ? 'var(--success-500)' : 'var(--gray-500)';

        return `
            <tr>
                <td><strong>${e.category}</strong></td>
                <td class="num">${formatCurrency(e.amount)}</td>
                <td class="num">${e.pct.toFixed(1)}%</td>
                <td style="color:${trendColor};font-weight:600;font-size:0.8rem">
                    ${trendIcon} ${Math.abs(e.trendPct).toFixed(1)}%
                </td>
            </tr>
        `;
    }).join('');
}


function exportFinance() {
    alert('Finance export coming soon!');
}

function viewAllExpenses(e) {
    if (e) e.preventDefault();
    alert('Full expense breakdown coming soon!');
}

// ==========================================
// FINANCE PAGE — Updated for KitchenIQ
// ==========================================

let revExpChart = null;
let costChart = null;

const COST_COLORS = {
    'Food Cost': '#ef4444',
    'Packaging': '#f59e0b',
    'Delivery': '#3b82f6',
    'Platform Fees': '#8b5cf6',
    'Other Costs': '#6b7280'
};


document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadFinance();
});


async function loadFinance() {
    const days = document.getElementById('daysFilterFinance')?.value || '30';

    try {
        const [kpis, revExp, breakdown, expenses, insight] = await Promise.all([
            apiFetch(`/api/finance/kpis?days=${days}`).catch(() => null),
            apiFetch(`/api/finance/revenue-vs-expenses?days=${days}`).catch(() => null),
            apiFetch(`/api/finance/cost-breakdown?days=${days}`).catch(() => null),
            apiFetch(`/api/finance/expenses?days=${days}`).catch(() => null),
            apiFetch(`/api/finance/insight?days=${days}`).catch(() => null)
        ]);

        if (kpis) renderKpis(kpis);
        if (revExp) renderRevenueVsExpenses(revExp);
        if (breakdown) renderCostBreakdown(breakdown);
        if (expenses) renderExpensesTable(expenses);
        if (insight) renderInsight(insight);

    } catch (err) {
        console.error('Finance error:', err);
    }
}


function renderKpis(k) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    set('finRevenue', formatCurrency(k.revenue?.value || 0));
    set('finExpenses', formatCurrency(k.expenses?.value || 0));
    set('finNetProfit', formatCurrency(k.net_profit?.value || 0));
    set('finMargin', `${k.margin?.value || 0}%`);
}


function renderRevenueVsExpenses(data) {
    const canvas = document.getElementById('revenueVsExpensesChart');
    if (!canvas || !data.length) return;

    const labels = data.map(w => shortDate(w.week));
    const revenues = data.map(w => parseFloat(w.revenue || 0));
    const expenses = data.map(w => parseFloat(w.expenses || 0));

    if (revExpChart) revExpChart.destroy();

    revExpChart = new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenues,
                    backgroundColor: '#2563eb',
                    borderRadius: 6,
                    barThickness: 18
                },
                {
                    label: 'Expenses',
                    data: expenses,
                    backgroundColor: '#ef4444',
                    borderRadius: 6,
                    barThickness: 18
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 8, boxHeight: 8, padding: 16,
                        font: { size: 11, family: 'Inter' },
                        usePointStyle: true, pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: '#0a1929',
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: v => '₹' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v),
                        font: { size: 10 }, color: '#9ca3af'
                    },
                    grid: { color: '#f3f4f6', drawBorder: false }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 10 }, color: '#9ca3af' }
                }
            }
        }
    });
}


function renderCostBreakdown(data) {
    const canvas = document.getElementById('costBreakdownChart');
    if (!canvas || !data.breakdown?.length) return;

    const labels = data.breakdown.map(b => b.label);
    const values = data.breakdown.map(b => b.value);
    const colors = labels.map(l => COST_COLORS[l] || '#6b7280');
    const total = data.total;

    if (costChart) costChart.destroy();

    costChart = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                cutout: '68%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        },
        plugins: [{
            id: 'centerText',
            afterDraw: (chart) => {
                const { ctx, chartArea } = chart;
                const x = (chartArea.left + chartArea.right) / 2;
                const y = (chartArea.top + chartArea.bottom) / 2;
                ctx.save();
                ctx.textAlign = 'center';
                ctx.font = 'bold 18px Inter';
                ctx.fillStyle = '#111827';
                ctx.fillText('₹' + (total >= 1000 ? (total / 1000).toFixed(1) + 'k' : total.toFixed(0)), x, y + 2);
                ctx.font = '10px Inter';
                ctx.fillStyle = '#6b7280';
                ctx.fillText('Total', x, y + 16);
                ctx.restore();
            }
        }]
    });

    // Legend
    const legend = document.getElementById('costLegend');
    if (legend) {
        legend.innerHTML = data.breakdown.map((b, i) => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--gray-100);font-size:0.8rem">
                <div style="display:flex;align-items:center;gap:8px">
                    <span style="width:10px;height:10px;border-radius:50%;background:${colors[i]}"></span>
                    <span style="font-weight:500">${escapeHtml(b.label)}</span>
                </div>
                <div style="font-weight:600">${b.pct}%</div>
            </div>
        `).join('');
    }
}


function renderExpensesTable(expenses) {
    const tbody = document.getElementById('expensesTableBody');
    if (!tbody) return;

    if (!expenses || expenses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--gray-500);padding:2rem">No data yet.</td></tr>';
        return;
    }

    tbody.innerHTML = expenses.map(e => {
        const trendIcon = e.trend === 'up' ? '↑' : e.trend === 'down' ? '↓' : '→';
        const trendColor = e.trend === 'up' ? 'var(--danger-500)' :
                          e.trend === 'down' ? 'var(--success-500)' : 'var(--gray-500)';

        return `
            <tr>
                <td><strong>${escapeHtml(e.category)}</strong></td>
                <td class="num">${formatCurrency(e.amount)}</td>
                <td class="num">${e.pct.toFixed(1)}%</td>
                <td style="color:${trendColor};font-weight:600;font-size:0.8rem">
                    ${trendIcon} ${Math.abs(e.trend_pct).toFixed(1)}%
                </td>
            </tr>
        `;
    }).join('');
}


function renderInsight(insight) {
    const el = document.getElementById('financeInsight');
    if (!el) return;

    el.textContent = insight.text || 'No insight available.';

    // Update card color based on status
    const card = el.closest('.panel');
    if (card) {
        if (insight.status === 'warning') {
            card.style.background = 'linear-gradient(90deg, var(--warning-50), #fff 60%)';
            card.style.borderLeftColor = 'var(--warning-500)';
        }
    }
}


function shortDate(str) {
    if (!str) return '';
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

