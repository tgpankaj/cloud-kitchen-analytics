// ==========================================
// BUSINESS INSIGHTS PAGE
// ==========================================

let allInsights = [];
let currentFilter = 'all';

const TYPE_MAP = {
    success: 'promote',
    info: 'opportunity',
    warning: 'optimize',
    danger: 'review'
};

const LABEL_MAP = {
    promote: '🚀 PROMOTE',
    opportunity: '📈 GROWTH OPPORTUNITY',
    optimize: '⚙️ OPTIMIZE',
    review: '⚠️ REVIEW'
};

const ACTION_MAP = {
    promote: 'Increase promotion during peak hours',
    opportunity: 'Consider targeted campaigns and combo offers',
    optimize: 'Review pricing or reduce costs',
    review: 'Consider menu change or removal'
};


document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadInsights();
});


async function loadInsights() {
    const days = document.getElementById('daysFilterInsights')?.value || '30';

    try {
        const insights = await apiFetch(`/api/recommendations/insights?days=${days}`).catch(() => []);
        allInsights = insights || [];

        // If empty, show demo insights
        if (allInsights.length === 0) {
            allInsights = getDemoInsights();
        }

        renderInsights();
        renderAdditionalInsights();

    } catch (err) {
        console.error('Insights error:', err);
        allInsights = getDemoInsights();
        renderInsights();
        renderAdditionalInsights();
    }
}


function renderInsights() {
    const grid = document.getElementById('insightsGrid');
    if (!grid) return;

    let filtered = allInsights;
    if (currentFilter !== 'all') {
        filtered = allInsights.filter(i => TYPE_MAP[i.type] === currentFilter);
    }

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:3rem">
                <div style="font-size:3rem;margin-bottom:1rem">🎉</div>
                <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem">All good!</h3>
                <p style="color:var(--gray-500);font-size:0.9rem">No insights in this category yet.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = filtered.map((insight, idx) => {
        const cls = TYPE_MAP[insight.type] || 'opportunity';
        const label = LABEL_MAP[cls];
        const action = insight.action || ACTION_MAP[cls];

        return `
            <div class="insight-card ${cls}" style="cursor:default;display:flex;flex-direction:column">
                <span class="insight-badge">${label}</span>

                <div class="insight-body">
                    <div class="insight-content">
                        <div class="insight-title">
                            ${escapeHtml(insight.title || 'Insight')}
                        </div>
                        <div class="insight-desc">
                            ${escapeHtml(insight.description || '')}
                        </div>
                    </div>
                    <div class="insight-thumb">${getCategoryEmoji(insight.category)}</div>
                </div>

                <div style="background:#fff;border-radius:8px;padding:10px 12px;border:1px solid var(--gray-100);margin-top:2px">
                    <div style="font-size:0.68rem;font-weight:700;color:var(--gray-500);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">
                        Recommended Action
                    </div>
                    <div style="font-size:0.75rem;color:var(--gray-700);line-height:1.4">
                        ${escapeHtml(action)}
                    </div>
                </div>

                <div style="display:flex;gap:8px;margin-top:auto;padding-top:6px">
                    <a href="items.html" class="insight-cta" style="flex:1;justify-content:center;display:inline-flex">
                        View Details →
                    </a>
                </div>
            </div>
        `;
    }).join('');
}


function getCategoryEmoji(category) {
    const map = {
        'Menu': '🍛',
        'Commission': '💸',
        'Delivery': '🚚',
        'Operations': '⚙️',
        'Customers': '👥',
        'Inventory': '📦',
        'Revenue': '📈'
    };
    return map[category] || '💡';
}


function renderAdditionalInsights() {
    const el = document.getElementById('additionalInsights');
    if (!el) return;

    const additional = [
        { icon: '⏰', text: 'Best time to promote: 7 PM – 9 PM', sub: 'Peak ordering hours for your kitchen' },
        { icon: '🍛', text: 'Top performing: Veg Biryani', sub: 'Highest revenue and repeat orders' },
        { icon: '📉', text: 'Lowest margin: Chicken Roll', sub: 'Consider pricing adjustment' },
        { icon: '👥', text: 'Loyal customers are 31.7% of your base', sub: 'Focus on retention campaigns' },
        { icon: '⚠️', text: '3 dishes need recipe costing', sub: 'Add recipes to see true profitability' }
    ];

    el.innerHTML = additional.map(item => `
        <div class="list-item" style="padding:12px 0">
            <div style="font-size:1.25rem;flex-shrink:0;width:32px;text-align:center">${item.icon}</div>
            <div class="list-item-content">
                <div class="list-item-title">${escapeHtml(item.text)}</div>
                <div class="list-item-subtitle">${escapeHtml(item.sub)}</div>
            </div>
        </div>
    `).join('');
}


function setFilter(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    renderInsights();
}


function refreshInsights() {
    loadInsights();
}


function getDemoInsights() {
    return [
        {
            type: 'success',
            category: 'Menu',
            title: 'Veg Biryani — Promote this dish',
            description: 'High profit margin (41.4%) + strong repeat rate (36%). Recommended: increase evening promotion (7 PM – 9 PM).',
            action: 'Run targeted evening promotions and bundle with cold drinks'
        },
        {
            type: 'info',
            category: 'Menu',
            title: 'Paneer Biryani — Growth Opportunity',
            description: 'Excellent rating (4.5) but lower orders. Consider targeted promotions and combo offers.',
            action: 'Feature in weekend specials and Instagram posts'
        },
        {
            type: 'warning',
            category: 'Menu',
            title: 'Chicken Roll — Optimize',
            description: 'High sales but low margin (22.9%). Review pricing or reduce costs.',
            action: 'Increase price by 10% or reduce portion size'
        },
        {
            type: 'danger',
            category: 'Menu',
            title: 'Vegetable Pulao — Review',
            description: 'Low orders and margins. Consider menu change or removal.',
            action: 'Remove from menu or replace with better-performing dish'
        }
    ];
}

// ==========================================
// BUSINESS INSIGHTS PAGE — Updated for KitchenIQ
// ==========================================

let allInsights = [];
let currentFilter = 'all';

const TYPE_MAP = {
    success: 'promote',
    info: 'opportunity',
    warning: 'optimize',
    danger: 'review'
};

const LABEL_MAP = {
    promote: '🚀 PROMOTE',
    opportunity: '📈 GROWTH OPPORTUNITY',
    optimize: '⚙️ OPTIMIZE',
    review: '⚠️ REVIEW'
};

const ACTION_MAP = {
    promote: 'Increase promotion during peak hours',
    opportunity: 'Consider targeted campaigns and combo offers',
    optimize: 'Review pricing or reduce costs',
    review: 'Consider menu change or removal'
};


document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadInsights();
    loadAdditionalInsights();
});


async function loadInsights() {
    const days = document.getElementById('daysFilterInsights')?.value || '30';

    try {
        // Use filter param — backend handles it
        const filterParam = currentFilter !== 'all' ? `&filter=${currentFilter}` : '';
        const insights = await apiFetch(
            `/api/recommendations/insights?days=${days}${filterParam}`
        ).catch(() => []);

        allInsights = insights || [];

        if (allInsights.length === 0 && currentFilter === 'all') {
            allInsights = getDemoInsights();
        }

        renderInsights();
    } catch (err) {
        console.error('Insights error:', err);
        allInsights = getDemoInsights();
        renderInsights();
    }
}


async function loadAdditionalInsights() {
    const el = document.getElementById('additionalInsights');
    if (!el) return;

    try {
        const days = document.getElementById('daysFilterInsights')?.value || '30';
        const additional = await apiFetch(`/api/recommendations/additional?days=${days}`).catch(() => null);

        if (!additional || additional.length === 0) {
            el.innerHTML = '<p style="color:var(--gray-500);font-size:0.85rem">No additional insights yet.</p>';
            return;
        }

        el.innerHTML = additional.map(item => `
            <div class="list-item" style="padding:12px 0">
                <div style="font-size:1.25rem;flex-shrink:0;width:32px;text-align:center">${item.icon || '💡'}</div>
                <div class="list-item-content">
                    <div class="list-item-title">${escapeHtml(item.text || '')}</div>
                    <div class="list-item-subtitle">${escapeHtml(item.sub || '')}</div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Additional insights error:', err);
    }
}


function renderInsights() {
    const grid = document.getElementById('insightsGrid');
    if (!grid) return;

    let filtered = allInsights;
    if (currentFilter !== 'all') {
        filtered = allInsights.filter(i => TYPE_MAP[i.type] === currentFilter);
    }

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:3rem">
                <div style="font-size:3rem;margin-bottom:1rem">🎉</div>
                <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem">All good!</h3>
                <p style="color:var(--gray-500);font-size:0.9rem">No insights in this category yet.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = filtered.map((insight) => {
        const cls = TYPE_MAP[insight.type] || 'opportunity';
        const label = LABEL_MAP[cls];
        const action = insight.action || ACTION_MAP[cls];

        return `
            <div class="insight-card ${cls}" style="cursor:default;display:flex;flex-direction:column">
                <span class="insight-badge">${label}</span>

                <div class="insight-body">
                    <div class="insight-content">
                        <div class="insight-title">${escapeHtml(insight.title || 'Insight')}</div>
                        <div class="insight-desc">${escapeHtml(insight.description || '')}</div>
                    </div>
                    <div class="insight-thumb">${getCategoryEmoji(insight.category)}</div>
                </div>

                <div style="background:#fff;border-radius:8px;padding:10px 12px;border:1px solid var(--gray-100);margin-top:2px">
                    <div style="font-size:0.68rem;font-weight:700;color:var(--gray-500);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">
                        Recommended Action
                    </div>
                    <div style="font-size:0.75rem;color:var(--gray-700);line-height:1.4">
                        ${escapeHtml(action)}
                    </div>
                </div>

                <div style="display:flex;gap:8px;margin-top:auto;padding-top:6px">
                    <a href="${getActionUrl(cls, insight)}" class="insight-cta" style="flex:1;justify-content:center;display:inline-flex">
                        View Details →
                    </a>
                </div>
            </div>
        `;
    }).join('');
}


function getCategoryEmoji(category) {
    const map = {
        'Menu': '🍛',
        'Commission': '💸',
        'Delivery': '🚚',
        'Operations': '⚙️',
        'Customers': '👥',
        'Inventory': '📦',
        'Revenue': '📈'
    };
    return map[category] || '💡';
}


function getActionUrl(cls, insight) {
    const category = insight.category || '';
    if (category === 'Menu') return 'items.html';
    if (category === 'Commission') return 'finance.html';
    if (category === 'Delivery') return 'delivery.html';
    if (category === 'Customers') return 'customers.html';
    if (category === 'Inventory') return 'ingredients.html';
    if (category === 'Revenue') return 'analytics.html';
    return 'dashboard.html';
}


function setFilter(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    loadInsights();
}


function refreshInsights() {
    loadInsights();
    loadAdditionalInsights();
}


function getDemoInsights() {
    return [
        {
            type: 'success',
            category: 'Menu',
            title: 'Veg Biryani — Promote this dish',
            description: 'High profit margin (41.4%) + strong repeat rate (36%). Recommended: increase evening promotion (7 PM – 9 PM).',
            action: 'Run targeted evening promotions and bundle with cold drinks'
        },
        {
            type: 'info',
            category: 'Menu',
            title: 'Paneer Biryani — Growth Opportunity',
            description: 'Excellent rating (4.5) but lower orders. Consider targeted promotions and combo offers.',
            action: 'Feature in weekend specials and Instagram posts'
        },
        {
            type: 'warning',
            category: 'Menu',
            title: 'Chicken Roll — Optimize',
            description: 'High sales but low margin (22.9%). Review pricing or reduce costs.',
            action: 'Increase price by 10% or reduce portion size'
        },
        {
            type: 'danger',
            category: 'Menu',
            title: 'Vegetable Pulao — Review',
            description: 'Low orders and margins. Consider menu change or removal.',
            action: 'Remove from menu or replace with better-performing dish'
        }
    ];
}