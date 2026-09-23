// ============================================================
// KITCHENIQ — ITEM PERFORMANCE + DISHES
// ============================================================
// This file safely supports BOTH:
// 1. Item Performance page
// 2. Dishes page
//
// Important:
// - No duplicate global variables
// - No duplicate function declarations
// - Page-specific initialization
// - Safe DOM checks
// - Stable ratings
// - Better error handling
// ============================================================


// ============================================================
// GLOBAL ITEM PERFORMANCE STATE
// ============================================================

let allItems = [];
let engineeringData = null;

let itemSort = {
    key: 'net_profit',
    dir: 'desc'
};

let profitChart = null;
let scatterChart = null;


// ============================================================
// GLOBAL DISHES STATE
// ============================================================

let allDishes = [];

let dishSort = {
    key: 'revenue',
    dir: 'desc'
};


// ============================================================
// STATUS COLORS
// ============================================================

const STATUS_COLORS = {
    Star: 'status-star',
    Plowhorse: 'status-plowhorse',
    Puzzle: 'status-puzzle',
    Dog: 'status-dog'
};


// ============================================================
// PAGE INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

    const session = requireAuth();

    if (!session) {
        return;
    }

    // --------------------------------------------------------
    // ITEM PERFORMANCE PAGE
    // --------------------------------------------------------

    if (document.getElementById('itemsTableBody')) {
        initItemPerformancePage();
    }


    // --------------------------------------------------------
    // DISHES PAGE
    // --------------------------------------------------------

    if (document.getElementById('dishesTableBody')) {
        initDishesPage();
    }

});


// ============================================================
// ITEM PERFORMANCE — INITIALIZATION
// ============================================================

function initItemPerformancePage() {

    setupItemSortHandlers();

    const daysFilter = document.getElementById('daysFilter');

    if (daysFilter) {
        daysFilter.addEventListener('change', loadItems);
    }

    const searchInput = document.getElementById('searchInput');

    if (searchInput) {
        searchInput.addEventListener('input', filterTable);
    }

    const categoryFilter = document.getElementById('categoryFilter');

    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterTable);
    }

    loadItems();
}


// ============================================================
// ITEM PERFORMANCE — SORT HANDLERS
// ============================================================

function setupItemSortHandlers() {

    document
        .querySelectorAll('.data-table th.sortable')
        .forEach(th => {

            // Only attach to item-performance table
            if (!th.closest('#itemsTableBody')) {
                // Header is outside tbody, so use table ID if available
            }

            th.addEventListener('click', () => {

                const key = th.dataset.sort;

                if (!key) {
                    return;
                }

                if (itemSort.key === key) {

                    itemSort.dir =
                        itemSort.dir === 'asc'
                            ? 'desc'
                            : 'asc';

                } else {

                    itemSort.key = key;
                    itemSort.dir = 'desc';

                }

                applyItemSortAndRender();

            });

        });

}


// ============================================================
// ITEM PERFORMANCE — LOAD DATA
// ============================================================

async function loadItems() {

    const days =
        document.getElementById('daysFilter')?.value || '30';

    try {

        const [items, bestWorst, engineering] =
            await Promise.all([

                apiFetch(
                    `/api/items/performance?days=${encodeURIComponent(days)}`
                ),

                apiFetch(
                    `/api/items/best-worst?days=${encodeURIComponent(days)}`
                ),

                apiFetch(
                    `/api/items/menu-engineering?days=${encodeURIComponent(days)}`
                )

            ]);


        allItems = Array.isArray(items)
            ? items
            : [];

        engineeringData = engineering || {};


        // ----------------------------------------------------
        // Merge engineering category into items
        // ----------------------------------------------------

        const categoryMap = {};

        const engineeringCategories = {
            stars: 'Star',
            plowhorses: 'Plowhorse',
            puzzles: 'Puzzle',
            dogs: 'Dog'
        };


        Object.entries(engineeringCategories).forEach(
            ([apiKey, label]) => {

                const categoryItems =
                    engineeringData[apiKey] || [];

                categoryItems.forEach(item => {

                    if (item && item.name) {
                        categoryMap[item.name] = label;
                    }

                });

            }
        );


        allItems.forEach(item => {

            item.engineering_category =
                categoryMap[item.name] || null;

        });


        // ----------------------------------------------------
        // Render sections
        // ----------------------------------------------------

        renderBestWorst(bestWorst || {});

        renderMatrix(engineeringData);

        renderItemCharts(allItems);

        populateItemCategoryFilter(allItems);

        applyItemSortAndRender();


    } catch (error) {

        console.error('Item performance error:', error);

        showAlert(
            'Failed to load items: ' + error.message,
            'error'
        );

    }

}


// ============================================================
// ITEM PERFORMANCE — BEST / WORST
// ============================================================

function renderBestWorst(data) {

    const bestEl =
        document.getElementById('bestList');

    const worstEl =
        document.getElementById('worstList');


    if (!bestEl && !worstEl) {
        return;
    }


    const best =
        Array.isArray(data.best)
            ? data.best
            : [];

    const worst =
        Array.isArray(data.worst)
            ? data.worst
            : [];


    if (bestEl) {

        if (best.length === 0) {

            bestEl.innerHTML =
                '<p class="muted small">No data yet. Upload some orders.</p>';

        } else {

            bestEl.innerHTML =
                best.map(item => `

                    <div class="bw-item">

                        <div style="flex:1;min-width:0">

                            <div class="bw-item-name">
                                ${escapeHtml(item.name || 'Unknown')}
                            </div>

                            <div class="bw-item-meta">
                                ${formatNumber(item.quantity_sold || 0)}
                                sold •
                                ${Number(item.profit_margin || 0).toFixed(1)}%
                                margin
                            </div>

                        </div>

                        <div class="bw-item-value">
                            ${formatCurrency(item.net_profit || 0)}
                        </div>

                    </div>

                `).join('');

        }

    }


    if (worstEl) {

        if (worst.length === 0) {

            worstEl.innerHTML =
                '<p class="muted small">No data yet.</p>';

        } else {

            worstEl.innerHTML =
                worst.map(item => `

                    <div class="bw-item">

                        <div style="flex:1;min-width:0">

                            <div class="bw-item-name">
                                ${escapeHtml(item.name || 'Unknown')}
                            </div>

                            <div class="bw-item-meta">
                                ${formatNumber(item.quantity_sold || 0)}
                                sold •
                                ${Number(item.profit_margin || 0).toFixed(1)}%
                                margin
                            </div>

                        </div>

                        <div class="bw-item-value ${
                            Number(item.net_profit || 0) < 0
                                ? 'negative'
                                : ''
                        }">

                            ${formatCurrency(item.net_profit || 0)}

                        </div>

                    </div>

                `).join('');

        }

    }

}


// ============================================================
// ITEM PERFORMANCE — MENU ENGINEERING MATRIX
// ============================================================

function renderMatrix(engineering) {

    const renderList = (items, containerId) => {

        const element =
            document.getElementById(containerId);

        if (!element) {
            return;
        }


        if (!Array.isArray(items) || items.length === 0) {

            element.innerHTML =
                '<p class="muted small" style="padding:0.5rem">' +
                'No items in this category.' +
                '</p>';

            return;
        }


        element.innerHTML =
            items.map(item => `

                <div class="matrix-item">

                    <span class="matrix-item-name">
                        ${escapeHtml(item.name || 'Unknown')}
                    </span>

                    <span class="matrix-item-value">
                        ${formatCurrency(item.net_profit || 0)}
                    </span>

                </div>

            `).join('');

    };


    renderList(engineering.stars, 'starsList');

    renderList(
        engineering.puzzles,
        'puzzlesList'
    );

    renderList(
        engineering.plowhorses,
        'plowhorsesList'
    );

    renderList(
        engineering.dogs,
        'dogsList'
    );

}


// ============================================================
// ITEM PERFORMANCE — CHARTS
// ============================================================

function renderItemCharts(items) {

    const profitCanvas =
        document.getElementById('profitChart');

    const scatterCanvas =
        document.getElementById('scatterChart');


    // No chart elements on current page
    if (!profitCanvas && !scatterCanvas) {
        return;
    }


    const sold =
        items.filter(item =>
            Number(item.quantity_sold || 0) > 0
        );


    if (sold.length === 0) {

        if (profitChart) {
            profitChart.destroy();
            profitChart = null;
        }

        if (scatterChart) {
            scatterChart.destroy();
            scatterChart = null;
        }

        return;
    }


    // ========================================================
    // PROFIT BAR CHART
    // ========================================================

    if (profitCanvas && typeof Chart !== 'undefined') {

        const top = [...sold]
            .sort(
                (a, b) =>
                    Number(b.net_profit || 0) -
                    Number(a.net_profit || 0)
            )
            .slice(0, 10);


        if (profitChart) {
            profitChart.destroy();
        }


        const ctx1 =
            profitCanvas.getContext('2d');


        profitChart = new Chart(ctx1, {

            type: 'bar',

            data: {

                labels:
                    top.map(item =>
                        String(item.name || '')
                            .length > 18
                            ? String(item.name).slice(0, 16) + '…'
                            : String(item.name || '')
                    ),

                datasets: [{

                    label: 'Net Profit',

                    data:
                        top.map(item =>
                            Number(item.net_profit || 0)
                        ),

                    backgroundColor:
                        top.map(item =>
                            Number(item.net_profit || 0) < 0
                                ? 'rgba(239, 68, 68, 0.7)'
                                : 'rgba(34, 197, 94, 0.7)'
                        ),

                    borderRadius: 6

                }]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            label: context =>
                                `Profit: ${formatCurrency(
                                    context.parsed.y
                                )}`

                        }

                    }

                },

                scales: {

                    y: {

                        beginAtZero: true,

                        ticks: {

                            callback: value =>
                                '₹' +
                                (
                                    Math.abs(value) >= 1000
                                        ? (value / 1000).toFixed(0) + 'k'
                                        : value
                                )

                        },

                        grid: {
                            color: '#f3f4f6'
                        }

                    },

                    x: {

                        grid: {
                            display: false
                        },

                        ticks: {

                            maxRotation: 45,

                            minRotation: 45,

                            font: {
                                size: 10
                            }

                        }

                    }

                }

            }

        });

    }


    // ========================================================
    // SCATTER / BUBBLE CHART
    // ========================================================

    if (scatterCanvas && typeof Chart !== 'undefined') {

        if (scatterChart) {
            scatterChart.destroy();
        }


        const maxRevenue =
            Math.max(
                ...sold.map(item =>
                    Number(item.gross_revenue || 0)
                ),
                1
            );


        const ctx2 =
            scatterCanvas.getContext('2d');


        scatterChart = new Chart(ctx2, {

            type: 'bubble',

            data: {

                datasets: [{

                    label: 'Items',

                    data:
                        sold.map(item => ({

                            x: Number(
                                item.quantity_sold || 0
                            ),

                            y: Number(
                                item.profit_margin || 0
                            ),

                            r: Math.max(
                                4,
                                Math.sqrt(
                                    Number(
                                        item.gross_revenue || 0
                                    ) / maxRevenue
                                ) * 20
                            ),

                            name:
                                item.name || 'Unknown'

                        })),

                    backgroundColor:
                        sold.map(item => {

                            const category =
                                item.engineering_category;

                            if (category === 'Star') {
                                return 'rgba(34, 197, 94, 0.6)';
                            }

                            if (category === 'Plowhorse') {
                                return 'rgba(245, 158, 11, 0.6)';
                            }

                            if (category === 'Puzzle') {
                                return 'rgba(59, 130, 246, 0.6)';
                            }

                            if (category === 'Dog') {
                                return 'rgba(239, 68, 68, 0.6)';
                            }

                            return 'rgba(107, 114, 128, 0.6)';

                        }),

                    borderColor: '#fff',

                    borderWidth: 2

                }]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                plugins: {

                    legend: {
                        display: false
                    },

                    tooltip: {

                        callbacks: {

                            label: context => {

                                const point =
                                    context.raw;

                                return [

                                    point.name,

                                    `Sold: ${point.x}`,

                                    `Margin: ${Number(
                                        point.y || 0
                                    ).toFixed(1)}%`

                                ];

                            }

                        }

                    }

                },

                scales: {

                    x: {

                        title: {

                            display: true,

                            text: 'Quantity Sold',

                            font: {
                                size: 11
                            }

                        },

                        grid: {
                            color: '#f3f4f6'
                        }

                    },

                    y: {

                        title: {

                            display: true,

                            text: 'Profit Margin (%)',

                            font: {
                                size: 11
                            }

                        },

                        grid: {
                            color: '#f3f4f6'
                        }

                    }

                }

            }

        });

    }

}


// ============================================================
// ITEM PERFORMANCE — CATEGORY FILTER
// ============================================================

function populateItemCategoryFilter(items) {

    const select =
        document.getElementById('categoryFilter');

    if (!select) {
        return;
    }


    const categories =
        [
            ...new Set(
                items
                    .map(item => item.category)
                    .filter(Boolean)
            )
        ].sort();


    select.innerHTML =
        '<option value="">All Categories</option>' +

        categories
            .map(category => `

                <option value="${escapeHtml(category)}">
                    ${escapeHtml(category)}
                </option>

            `)
            .join('');

}


// ============================================================
// ITEM PERFORMANCE — FILTER
// ============================================================

function filterTable() {
    applyItemSortAndRender();
}


// ============================================================
// ITEM PERFORMANCE — SORT + RENDER
// ============================================================

function applyItemSortAndRender() {

    const search =
        (
            document.getElementById('searchInput')?.value ||
            ''
        )
            .toLowerCase()
            .trim();


    const category =
        document.getElementById('categoryFilter')?.value ||
        '';


    let filtered =
        allItems.filter(item => {

            const name =
                String(item.name || '').toLowerCase();

            if (
                search &&
                !name.includes(search)
            ) {
                return false;
            }

            if (
                category &&
                item.category !== category
            ) {
                return false;
            }

            return true;

        });


    const {
        key,
        dir
    } = itemSort;


    const multiplier =
        dir === 'asc' ? 1 : -1;


    filtered.sort((a, b) => {

        let valueA = a[key];
        let valueB = b[key];


        if (typeof valueA === 'string') {

            valueA =
                valueA.toLowerCase();

            valueB =
                String(valueB || '').toLowerCase();


            if (valueA < valueB) {
                return -1 * multiplier;
            }

            if (valueA > valueB) {
                return 1 * multiplier;
            }

            return 0;

        }


        valueA =
            parseFloat(valueA) || 0;

        valueB =
            parseFloat(valueB) || 0;


        return (
            valueA - valueB
        ) * multiplier;

    });


    renderItemTable(filtered);

    updateItemSortIndicators();

}


// ============================================================
// ITEM PERFORMANCE — SORT INDICATORS
// ============================================================

function updateItemSortIndicators() {

    document
        .querySelectorAll('.data-table th.sortable')
        .forEach(th => {

            th.classList.remove(
                'sort-asc',
                'sort-desc'
            );


            if (
                th.dataset.sort === itemSort.key
            ) {

                th.classList.add(
                    itemSort.dir === 'asc'
                        ? 'sort-asc'
                        : 'sort-desc'
                );

            }

        });

}


// ============================================================
// ITEM PERFORMANCE — TABLE
// ============================================================

function renderItemTable(items) {

    const tbody =
        document.getElementById('itemsTableBody');

    if (!tbody) {
        return;
    }


    if (items.length === 0) {

        tbody.innerHTML = `

            <tr>

                <td
                    colspan="8"
                    class="muted center"
                >
                    No items match your filters.
                </td>

            </tr>

        `;

        return;
    }


    tbody.innerHTML =
        items.map(item => {

            const netProfit =
                Number(item.net_profit || 0);


            const profitClass =
                netProfit >= 0
                    ? 'positive'
                    : 'negative';


            const statusClass =
                item.engineering_category
                    ? (
                        STATUS_COLORS[
                            item.engineering_category
                        ] || 'status-none'
                    )
                    : 'status-none';


            const statusLabel =
                item.engineering_category || '—';


            return `

                <tr>

                    <td>

                        <div style="font-weight:500">

                            ${escapeHtml(
                                item.name || 'Unknown'
                            )}

                        </div>

                    </td>


                    <td>

                        <span class="item-category">

                            ${escapeHtml(
                                item.category ||
                                'Uncategorized'
                            )}

                        </span>

                    </td>


                    <td class="num">

                        ${formatNumber(
                            item.quantity_sold || 0
                        )}

                    </td>


                    <td class="num">

                        ${formatCurrency(
                            item.gross_revenue || 0
                        )}

                    </td>


                    <td class="num">

                        ${formatCurrency(
                            item.net_revenue || 0
                        )}

                    </td>


                    <td
                        class="num cell-profit ${profitClass}"
                    >

                        ${formatCurrency(
                            netProfit
                        )}

                    </td>


                    <td class="num">

                        ${Number(
                            item.profit_margin || 0
                        ).toFixed(1)}%

                    </td>


                    <td>

                        <span
                            class="status-badge ${statusClass}"
                        >

                            ${statusLabel}

                        </span>

                    </td>

                </tr>

            `;

        }).join('');

}


// ============================================================
// ITEM PERFORMANCE — EXPORT CSV
// ============================================================

async function exportCSV() {

    const days =
        document.getElementById('daysFilter')?.value ||
        '30';


    const token =
        localStorage.getItem('token');


    if (!token) {

        showAlert(
            'Please login again.',
            'error'
        );

        return;

    }


    try {

        const response =
            await fetch(
                `${API_URL}/api/items/export?days=${encodeURIComponent(days)}`,
                {
                    method: 'GET',

                    headers: {
                        Authorization: `Bearer ${token}`
                    }
                }
            );


        if (!response.ok) {

            let message =
                'Export failed';

            try {

                const data =
                    await response.json();

                message =
                    data.message ||
                    data.error ||
                    message;

            } catch (_) {}

            throw new Error(message);

        }


        const blob =
            await response.blob();


        const url =
            URL.createObjectURL(blob);


        const anchor =
            document.createElement('a');


        anchor.href = url;

        anchor.download =
            `item-performance-${Date.now()}.csv`;


        document.body.appendChild(anchor);

        anchor.click();

        document.body.removeChild(anchor);


        URL.revokeObjectURL(url);


        showAlert(
            'CSV downloaded successfully',
            'success'
        );


    } catch (error) {

        console.error(
            'Export error:',
            error
        );


        showAlert(
            'Export failed: ' +
            error.message,
            'error'
        );

    }

}


// ============================================================
// ============================================================
// DISHES PAGE
// ============================================================
// ============================================================


// ============================================================
// DISHES INITIALIZATION
// ============================================================

function initDishesPage() {

    setupDishSortHandlers();

    const daysFilter =
        document.getElementById(
            'daysFilterItems'
        );


    if (daysFilter) {

        daysFilter.addEventListener(
            'change',
            loadDishes
        );

    }


    const searchInput =
        document.getElementById('dishSearch');


    if (searchInput) {

        searchInput.addEventListener(
            'input',
            applyDishFilters
        );

    }


    const categoryFilter =
        document.getElementById(
            'categoryFilter'
        );


    if (categoryFilter) {

        categoryFilter.addEventListener(
            'change',
            applyDishFilters
        );

    }


    const statusFilter =
        document.getElementById(
            'statusFilter'
        );


    if (statusFilter) {

        statusFilter.addEventListener(
            'change',
            applyDishFilters
        );

    }


    loadDishes();

}


// ============================================================
// DISHES SORT HANDLERS
// ============================================================

function setupDishSortHandlers() {

    const tableBody =
        document.getElementById(
            'dishesTableBody'
        );


    if (!tableBody) {
        return;
    }


    const table =
        tableBody.closest('table');


    if (!table) {
        return;
    }


    table
        .querySelectorAll('th.sortable')
        .forEach(th => {

            th.addEventListener(
                'click',
                () => {

                    const key =
                        th.dataset.sort;


                    if (!key) {
                        return;
                    }


                    if (
                        dishSort.key === key
                    ) {

                        dishSort.dir =
                            dishSort.dir === 'asc'
                                ? 'desc'
                                : 'asc';

                    } else {

                        dishSort.key = key;

                        dishSort.dir =
                            'desc';

                    }


                    applyDishFilters();

                }
            );

        });

}


// ============================================================
// DISHES — LOAD
// ============================================================

async function loadDishes() {

    const days =
        document.getElementById(
            'daysFilterItems'
        )?.value || '30';


    try {

        const items =
            await apiFetch(
                `/api/items/performance?days=${encodeURIComponent(days)}`
            );


        allDishes =
            Array.isArray(items)
                ? items
                : [];


        populateDishCategories();

        applyDishFilters();


    } catch (error) {

        console.error(
            'Dishes error:',
            error
        );


        const tbody =
            document.getElementById(
                'dishesTableBody'
            );


        if (tbody) {

            tbody.innerHTML = `

                <tr>

                    <td
                        colspan="8"
                        style="
                            text-align:center;
                            color:var(--red-500);
                            padding:3rem
                        "
                    >

                        Failed to load dishes.
                        Try uploading data first.

                    </td>

                </tr>

            `;

        }


        const countEl =
            document.getElementById(
                'dishesCount'
            );


        if (countEl) {
            countEl.textContent =
                'Unable to load dishes';
        }

    }

}


// ============================================================
// DISHES — CATEGORY FILTER
// ============================================================

function populateDishCategories() {

    const select =
        document.getElementById(
            'categoryFilter'
        );


    if (!select) {
        return;
    }


    const categories =
        [
            ...new Set(
                allDishes
                    .map(dish => dish.category)
                    .filter(Boolean)
            )
        ].sort();


    select.innerHTML =
        '<option value="">All Categories</option>' +

        categories.map(category => `

            <option value="${escapeHtml(category)}">

                ${escapeHtml(category)}

            </option>

        `).join('');

}


// ============================================================
// DISHES — FILTER
// ============================================================

function applyDishFilters() {

    const search =
        (
            document.getElementById(
                'dishSearch'
            )?.value || ''
        )
            .toLowerCase()
            .trim();


    const category =
        document.getElementById(
            'categoryFilter'
        )?.value || '';


    const status =
        document.getElementById(
            'statusFilter'
        )?.value || '';


    const filtered =
        allDishes.filter(dish => {

            const name =
                String(
                    dish.name || ''
                ).toLowerCase();


            if (
                search &&
                !name.includes(search)
            ) {
                return false;
            }


            if (
                category &&
                dish.category !== category
            ) {
                return false;
            }


            if (
                status &&
                getRecommendation(dish).type !== status
            ) {
                return false;
            }


            return true;

        });


    renderDishes(filtered);

}


// ============================================================
// DISHES — RENDER
// ============================================================

function renderDishes(items = null) {

    if (items === null) {

        const search =
            (
                document.getElementById(
                    'dishSearch'
                )?.value || ''
            )
                .toLowerCase()
                .trim();


        const category =
            document.getElementById(
                'categoryFilter'
            )?.value || '';


        const status =
            document.getElementById(
                'statusFilter'
            )?.value || '';


        items =
            allDishes.filter(dish => {

                const name =
                    String(
                        dish.name || ''
                    ).toLowerCase();


                if (
                    search &&
                    !name.includes(search)
                ) {
                    return false;
                }


                if (
                    category &&
                    dish.category !== category
                ) {
                    return false;
                }


                if (
                    status &&
                    getRecommendation(dish).type !== status
                ) {
                    return false;
                }


                return true;

            });

    }


    // ========================================================
    // SORT
    // ========================================================

    const sorted =
        [...items].sort((a, b) => {

            let valueA =
                getDishSortValue(
                    a,
                    dishSort.key
                );


            let valueB =
                getDishSortValue(
                    b,
                    dishSort.key
                );


            if (
                typeof valueA === 'string'
            ) {

                valueA =
                    valueA.toLowerCase();

                valueB =
                    String(valueB || '')
                        .toLowerCase();


                if (valueA < valueB) {

                    return dishSort.dir === 'asc'
                        ? -1
                        : 1;

                }


                if (valueA > valueB) {

                    return dishSort.dir === 'asc'
                        ? 1
                        : -1;

                }


                return 0;

            }


            valueA =
                parseFloat(valueA) || 0;

            valueB =
                parseFloat(valueB) || 0;


            return dishSort.dir === 'asc'
                ? valueA - valueB
                : valueB - valueA;

        });


    updateDishSortIndicators();


    const tbody =
        document.getElementById(
            'dishesTableBody'
        );


    const countEl =
        document.getElementById(
            'dishesCount'
        );


    if (!tbody) {
        return;
    }


    if (countEl) {

        countEl.textContent =
            `Showing ${sorted.length} of ${allDishes.length} dishes`;

    }


    if (sorted.length === 0) {

        tbody.innerHTML = `

            <tr>

                <td
                    colspan="8"
                    style="
                        text-align:center;
                        color:var(--gray-500);
                        padding:3rem
                    "
                >

                    No dishes match your filters.

                </td>

            </tr>

        `;

        return;

    }


    tbody.innerHTML =
        sorted.map(dish => {

            const recommendation =
                getRecommendation(dish);


            const margin =
                Number(
                    dish.profit_margin || 0
                );


            const marginPct =
                Math.max(
                    0,
                    Math.min(100, margin)
                );


            const marginColor =
                marginPct >= 40
                    ? 'green'
                    : marginPct >= 30
                        ? 'blue'
                        : marginPct >= 20
                            ? 'amber'
                            : 'red';


            const foodCost =
                dish.food_cost_pct != null
                    ? Number(dish.food_cost_pct)
                    : Math.max(
                        0,
                        100 - marginPct
                    );


            // Do NOT use Math.random()
            // because UI would change every render.
            const rating =
                Number(dish.rating || 0);


            const ratingHtml =
                rating > 0
                    ? `
                        <span class="cell-rating">
                            <span class="star">★</span>
                            ${rating.toFixed(1)}
                        </span>
                    `
                    : `
                        <span class="muted">
                            —
                        </span>
                    `;


            return `

                <tr>

                    <td>

                        <div class="cell-dish">

                            <div class="cell-dish-thumb">
                                🍛
                            </div>

                            <div class="cell-dish-info">

                                <span class="cell-dish-name">

                                    ${escapeHtml(
                                        dish.name ||
                                        'Unknown'
                                    )}

                                </span>

                            </div>

                        </div>

                    </td>


                    <td>

                        ${escapeHtml(
                            dish.category ||
                            'Uncategorized'
                        )}

                    </td>


                    <td class="num">

                        ${formatNumber(
                            dish.quantity_sold || 0
                        )}

                    </td>


                    <td
                        class="num"
                        style="font-weight:600"
                    >

                        ${formatCurrency(
                            dish.net_revenue || 0
                        )}

                    </td>


                    <td
                        class="num hide-mobile"
                    >

                        ${foodCost.toFixed(1)}%

                    </td>


                    <td class="num">

                        <div class="cell-margin">

                            <span class="cell-margin-text">

                                ${marginPct.toFixed(1)}%

                            </span>


                            <div class="cell-margin-bar">

                                <div
                                    class="
                                        cell-margin-fill
                                        ${marginColor}
                                    "
                                    style="
                                        width:${marginPct}%
                                    "
                                ></div>

                            </div>

                        </div>

                    </td>


                    <td
                        class="num hide-mobile"
                    >

                        ${ratingHtml}

                    </td>


                    <td>

                        <span
                            class="
                                rec-badge
                                ${recommendation.type}
                            "
                        >

                            ${recommendation.icon}
                            ${recommendation.label}

                        </span>

                    </td>

                </tr>

            `;

        }).join('');

}


// ============================================================
// DISHES — SORT VALUE
// ============================================================

function getDishSortValue(dish, key) {

    switch (key) {

        case 'name':
            return dish.name || '';

        case 'category':
            return dish.category || '';

        case 'orders':
            return Number(
                dish.quantity_sold || 0
            );

        case 'revenue':
            return Number(
                dish.net_revenue || 0
            );

        case 'food_cost':
            return Number(
                dish.food_cost_pct ||
                0
            );

        case 'margin':
            return Number(
                dish.profit_margin ||
                0
            );

        case 'rating':
            return Number(
                dish.rating ||
                0
            );

        default:
            return Number(
                dish[key] ||
                0
            );

    }

}


// ============================================================
// DISHES — SORT INDICATORS
// ============================================================

function updateDishSortIndicators() {

    const tbody =
        document.getElementById(
            'dishesTableBody'
        );


    if (!tbody) {
        return;
    }


    const table =
        tbody.closest('table');


    if (!table) {
        return;
    }


    table
        .querySelectorAll('th.sortable')
        .forEach(th => {

            th.classList.remove(
                'sort-asc',
                'sort-desc'
            );


            if (
                th.dataset.sort === dishSort.key
            ) {

                th.classList.add(
                    dishSort.dir === 'asc'
                        ? 'sort-asc'
                        : 'sort-desc'
                );

            }

        });

}


// ============================================================
// DISHES — RECOMMENDATION
// ============================================================

function getRecommendation(dish) {

    const margin =
        Number(
            dish.profit_margin || 0
        );


    const orders =
        Number(
            dish.quantity_sold || 0
        );


    // --------------------------------------------------------
    // High margin + high volume
    // --------------------------------------------------------

    if (
        margin >= 40 &&
        orders >= 100
    ) {

        return {
            type: 'promote',
            label: 'Promote',
            icon: '🚀'
        };

    }


    // --------------------------------------------------------
    // High margin + low volume
    // --------------------------------------------------------

    if (
        margin >= 40 &&
        orders < 100
    ) {

        return {
            type: 'growth',
            label: 'Growth',
            icon: '📈'
        };

    }


    // --------------------------------------------------------
    // Low margin + high volume
    // --------------------------------------------------------

    if (
        margin < 30 &&
        orders >= 100
    ) {

        return {
            type: 'optimize',
            label: 'Optimize',
            icon: '⚙️'
        };

    }


    // --------------------------------------------------------
    // Low margin + low volume
    // --------------------------------------------------------

    return {
        type: 'review',
        label: 'Review',
        icon: '⚠️'
    };

}


// ============================================================
// DISHES — EXPORT
// ============================================================

async function exportDishes() {

    const days =
        document.getElementById(
            'daysFilterItems'
        )?.value || '30';


    const token =
        localStorage.getItem('token');


    if (!token) {

        showAlert(
            'Please login again.',
            'error'
        );

        return;

    }


    try {

        const response =
            await fetch(
                `${API_URL}/api/items/export?days=${encodeURIComponent(days)}`,
                {
                    method: 'GET',

                    headers: {
                        Authorization: `Bearer ${token}`
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                'Dishes export failed'
            );

        }


        const blob =
            await response.blob();


        const url =
            URL.createObjectURL(blob);


        const anchor =
            document.createElement('a');


        anchor.href = url;

        anchor.download =
            `dishes-${Date.now()}.csv`;


        document.body.appendChild(anchor);

        anchor.click();

        document.body.removeChild(anchor);


        URL.revokeObjectURL(url);


        showAlert(
            'Dishes CSV downloaded successfully',
            'success'
        );


    } catch (error) {

        console.error(
            'Dishes export error:',
            error
        );


        showAlert(
            'Export failed: ' +
            error.message,
            'error'
        );

    }

}


// ============================================================
// OPTIONAL BACKWARD-COMPATIBILITY ALIASES
// ============================================================

// If your HTML already calls filterTable()
window.filterTable = filterTable;

// If your HTML already calls exportCSV()
window.exportCSV = exportCSV;

// If your HTML already calls exportDishes()
window.exportDishes = exportDishes;

// If HTML manually calls applyFilters()
window.applyFilters = applyDishFilters;

// If HTML manually calls renderDishes()
window.renderDishes = renderDishes;


// ============================================================
// SAFETY HELPERS
// ============================================================

// These are only fallbacks.
// If your common.js already defines these functions,
// its versions will remain available.

if (typeof window.escapeHtml !== 'function') {

    window.escapeHtml = function(value) {

        const div =
            document.createElement('div');

        div.textContent =
            String(value ?? '');

        return div.innerHTML;

    };

}


// ============================================================
// END
// ============================================================


// ═══════════════════════════════════════════
// POPULATE CATEGORIES (from API)
// ═══════════════════════════════════════════
async function populateCategories() {
    const sel = document.getElementById('categoryFilter');
    if (!sel) return;

    try {
        // Try API first
        const categories = await apiFetch('/api/items/categories').catch(() => null);

        if (categories && categories.length > 0) {
            sel.innerHTML = '<option value="">All Categories</option>' +
                categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
            return;
        }
    } catch (e) {
        console.warn('Categories API failed, using local data');
    }

    // Fallback: derive from loaded dishes
    const cats = [...new Set(allDishes.map(d => d.category).filter(Boolean))].sort();
    sel.innerHTML = '<option value="">All Categories</option>' +
        cats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}