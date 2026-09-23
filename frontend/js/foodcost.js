// ==========================================
// FOOD COST ANALYSIS LOGIC
// ==========================================

let foodCostChart = null;
let marginChart = null;
let trueProfitItems = [];

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadFoodCost();
});

async function loadFoodCost() {
    const days = document.getElementById('daysFilter').value;

    try {
        const [summary, profitability, alerts, missing] = await Promise.all([
            apiFetch('/api/foodcost/summary'),
            apiFetch(`/api/foodcost/true-profitability?days=${days}`),
            apiFetch('/api/foodcost/stock-alerts'),
            apiFetch('/api/foodcost/missing-recipes')
        ]);

        renderSummary(summary);
        renderStockAlerts(alerts);
        renderTrueProfitability(profitability);
        renderMissingRecipes(missing);
        renderCharts(profitability);

    } catch (err) {
        showAlert('Failed to load food cost data: ' + err.message, 'error');
    }
}

function renderSummary(s) {
    document.getElementById('kpiIngredients').textContent =
        formatNumber(s.total_ingredients);
    document.getElementById('kpiStockValue').textContent =
        formatCurrency(s.stock_value);
    document.getElementById('kpiLowStock').textContent =
        formatNumber(s.low_stock_count);
    document.getElementById('kpiCoverage').textContent =
        s.recipe_coverage + '%';
    document.getElementById('kpiCoverageSub').textContent =
        `${s.items_with_recipe} of ${s.total_items} items`;
}

function renderStockAlerts(alerts) {
    const card = document.getElementById('stockAlertsCard');
    const list = document.getElementById('stockAlertsList');

    if (!alerts || alerts.length === 0) {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';
    list.innerHTML = alerts.map(a => `
        <div class="alert-item">
            <div>
                <strong>${escapeHtml(a.name)}</strong>
                <div class="alert-meta">
                    Current: ${a.current_stock} ${a.unit} • 
                    Reorder at: ${a.reorder_threshold} ${a.unit} • 
                    Shortage: <strong>${a.shortage} ${a.unit}</strong>
                </div>
            </div>
            <div class="alert-action">
                Order Now
            </div>
        </div>
    `).join('');
}

function renderTrueProfitability(items) {
    trueProfitItems = items;
    const tbody = document.getElementById('trueProfitBody');

    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="muted center">No items with recipes yet. Add recipes to see true profitability.</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(i => {
        const varianceClass = i.cost_variance > 0 ? 'negative' : 'positive';
        const marginClass = i.true_margin >= 40 ? 'positive' : (i.true_margin >= 20 ? '' : 'negative');
        const foodCostClass = i.food_cost_pct <= 35 ? 'positive' : (i.food_cost_pct <= 50 ? '' : 'negative');

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(i.name)}</strong>
                    <button onclick="viewRecipe(${i.id}, '${escapeHtml(i.name)}')" class="btn-link">View Recipe</button>
                </td>
                <td class="num">${i.quantity_sold}</td>
                <td class="num">${formatCurrency(i.selling_price)}</td>
                <td class="num">${formatCurrencyDecimal(i.estimated_cost)}</td>
                <td class="num">${formatCurrencyDecimal(i.actual_cost)}</td>
                <td class="num cell-profit ${varianceClass}">
                    ${i.cost_variance > 0 ? '+' : ''}${formatCurrencyDecimal(i.cost_variance)}
                </td>
                <td class="num cell-profit ${marginClass}">${i.true_margin}%</td>
                <td class="num cell-profit ${foodCostClass}">${i.food_cost_pct}%</td>
            </tr>
        `;
    }).join('');
}

function renderMissingRecipes(items) {
    const card = document.getElementById('missingCard');
    const list = document.getElementById('missingList');

    if (!items || items.length === 0) {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';
    list.innerHTML = items.map(i => `
        <div class="missing-item">
            <div>
                <strong>${escapeHtml(i.name)}</strong>
                <div class="alert-meta">
                    Selling: ${formatCurrency(i.selling_price)} • 
                    Est. Cost: ${formatCurrencyDecimal(i.estimated_cost)}
                </div>
            </div>
            <button onclick="viewRecipe(${i.id}, '${escapeHtml(i.name)}')" class="btn btn-secondary btn-sm">
                ➕ Add Recipe
            </button>
        </div>
    `).join('');
}

function renderCharts(items) {
    if (!items || items.length === 0) return;

    // Food Cost % chart
    const sorted = [...items].sort((a, b) => b.food_cost_pct - a.food_cost_pct).slice(0, 10);

    const ctx1 = document.getElementById('foodCostChart').getContext('2d');
    if (foodCostChart) foodCostChart.destroy();

    foodCostChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: sorted.map(i => i.name.length > 15 ? i.name.slice(0, 13) + '…' : i.name),
            datasets: [{
                label: 'Food Cost %',
                data: sorted.map(i => i.food_cost_pct),
                backgroundColor: sorted.map(i => {
                    if (i.food_cost_pct <= 35) return 'rgba(34, 197, 94, 0.7)';
                    if (i.food_cost_pct <= 50) return 'rgba(245, 158, 11, 0.7)';
                    return 'rgba(239, 68, 68, 0.7)';
                }),
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
                        label: (ctx) => `Food Cost: ${ctx.parsed.y}%`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: (v) => v + '%' },
                    grid: { color: '#f3f4f6' }
                },
                x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 45, font: { size: 10 } } }
            }
        }
    });

    // Margin chart
    const topMargin = [...items].sort((a, b) => b.true_margin - a.true_margin).slice(0, 8);

    const ctx2 = document.getElementById('marginChart').getContext('2d');
    if (marginChart) marginChart.destroy();

    marginChart = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels: topMargin.map(i => i.name.length > 15 ? i.name.slice(0, 13) + '…' : i.name),
            datasets: [{
                label: 'True Margin %',
                data: topMargin.map(i => i.true_margin),
                backgroundColor: 'rgba(34, 197, 94, 0.7)',
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Margin: ${ctx.parsed.x}%`
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { callback: (v) => v + '%' },
                    grid: { color: '#f3f4f6' }
                },
                y: { grid: { display: false } }
            }
        }
    });
}

// ==========================================
// RECIPE MODAL
// ==========================================
async function viewRecipe(itemId, itemName) {
    document.getElementById('recipeModalTitle').textContent = `Recipe: ${itemName}`;
    document.getElementById('recipeModalBody').innerHTML = '<p class="muted">Loading...</p>';
    document.getElementById('recipeModal').style.display = 'flex';

    try {
        const [recipe, ingredients] = await Promise.all([
            apiFetch(`/api/foodcost/recipes/${itemId}`),
            apiFetch('/api/foodcost/ingredients')
        ]);

        renderRecipeModal(recipe, ingredients);
    } catch (err) {
        document.getElementById('recipeModalBody').innerHTML =
            `<p class="alert-error" style="padding:1rem;border-radius:8px">${err.message}</p>`;
    }
}

function renderRecipeModal(recipe, ingredients) {
    const body = document.getElementById('recipeModalBody');

    const recipeRows = recipe.ingredients.map(ri => `
        <tr>
            <td>${escapeHtml(ri.ingredient_name)}</td>
            <td class="num">${ri.quantity_required} ${ri.unit}</td>
            <td class="num">${formatCurrencyDecimal(ri.cost_per_unit)}</td>
            <td class="num">${formatCurrencyDecimal(ri.line_cost)}</td>
            <td>
                <button onclick="removeRecipeIngredient(${ri.recipe_id})" class="btn-icon" title="Remove">🗑️</button>
            </td>
        </tr>
    `).join('');

    const availableIngredients = ingredients.filter(ing =>
        !recipe.ingredients.some(ri => ri.ingredient_id === ing.id)
    );

    const addOptions = availableIngredients.map(i =>
        `<option value="${i.id}">${escapeHtml(i.name)} (${formatCurrencyDecimal(i.cost_per_unit)}/${i.unit})</option>`
    ).join('');

    body.innerHTML = `
        <div class="recipe-summary">
            <div class="recipe-stat">
                <span class="recipe-stat-label">Selling Price</span>
                <span class="recipe-stat-value">${formatCurrency(recipe.menu_item.selling_price)}</span>
            </div>
            <div class="recipe-stat">
                <span class="recipe-stat-label">Recipe Cost</span>
                <span class="recipe-stat-value">${formatCurrencyDecimal(recipe.total_recipe_cost)}</span>
            </div>
            <div class="recipe-stat">
                <span class="recipe-stat-label">True Margin</span>
                <span class="recipe-stat-value positive">
                    ${recipe.menu_item.selling_price > 0 
                        ? (((recipe.menu_item.selling_price - recipe.total_recipe_cost) / recipe.menu_item.selling_price) * 100).toFixed(1)
                        : 0}%
                </span>
            </div>
        </div>

        <h4 style="margin:1.5rem 0 0.75rem">Ingredients</h4>
        ${recipe.ingredients.length > 0 ? `
            <table class="data-table" style="margin-bottom:1rem">
                <thead>
                    <tr>
                        <th>Ingredient</th>
                        <th class="num">Quantity</th>
                        <th class="num">Cost / Unit</th>
                        <th class="num">Line Cost</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>${recipeRows}</tbody>
            </table>
        ` : '<p class="muted">No ingredients yet. Add the first one below.</p>'}

        ${availableIngredients.length > 0 ? `
            <div class="add-ingredient-form">
                <h4 style="margin-bottom:0.75rem">Add Ingredient</h4>
                <div class="form-row">
                    <select id="newIngredientSelect" class="form-select">
                        <option value="">Select ingredient...</option>
                        ${addOptions}
                    </select>
                    <input type="number" id="newIngredientQty" step="0.01" min="0.01" placeholder="Quantity" class="form-input">
                    <button onclick="addRecipeIngredient(${recipe.menu_item.id})" class="btn btn-primary btn-sm">
                        ➕ Add
                    </button>
                </div>
            </div>
        ` : '<p class="muted small" style="margin-top:1rem">All ingredients already in recipe. Add more in Ingredients page.</p>'}
    `;
}

async function addRecipeIngredient(itemId) {
    const ingId = document.getElementById('newIngredientSelect').value;
    const qty = parseFloat(document.getElementById('newIngredientQty').value);

    if (!ingId || !qty || qty <= 0) {
        showAlert('Select ingredient and enter quantity', 'error');
        return;
    }

    try {
        await apiFetch(`/api/foodcost/recipes/${itemId}`, {
            method: 'POST',
            body: JSON.stringify({
                ingredient_id: parseInt(ingId),
                quantity_required: qty
            })
        });
        showAlert('Ingredient added to recipe', 'success');
        viewRecipe(itemId, document.getElementById('recipeModalTitle').textContent.replace('Recipe: ', ''));
        loadFoodCost();
    } catch (err) {
        showAlert(err.message || 'Failed to add', 'error');
    }
}

async function removeRecipeIngredient(recipeId) {
    if (!confirm('Remove this ingredient from recipe?')) return;

    try {
        await apiFetch(`/api/foodcost/recipes/${recipeId}`, { method: 'DELETE' });
        showAlert('Removed from recipe', 'success');
        // Reload by finding the item id from current modal title
        loadFoodCost();
        closeRecipeModal();
    } catch (err) {
        showAlert(err.message || 'Failed to remove', 'error');
    }
}

function closeRecipeModal() {
    document.getElementById('recipeModal').style.display = 'none';
}