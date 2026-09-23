// ==========================================
// INGREDIENTS MANAGEMENT
// ==========================================

let allIngredients = [];

document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;
    loadIngredients();
});

async function loadIngredients() {
    try {
        const ingredients = await apiFetch('/api/foodcost/ingredients');
        allIngredients = ingredients;
        renderIngredients(ingredients);
        renderSummary(ingredients);
    } catch (err) {
        showAlert('Failed to load ingredients: ' + err.message, 'error');
    }
}

function renderSummary(ingredients) {
    const total = ingredients.length;
    const stockValue = ingredients.reduce((s, i) => s + i.stock_value, 0);
    const lowStock = ingredients.filter(i => i.needs_reorder).length;

    document.getElementById('kpiTotal').textContent = formatNumber(total);
    document.getElementById('kpiStockValue').textContent = formatCurrency(stockValue);
    document.getElementById('kpiLowStock').textContent = formatNumber(lowStock);
}

function filterIngredients() {
    const search = document.getElementById('searchInput').value.toLowerCase().trim();
    const filtered = allIngredients.filter(i =>
        i.name.toLowerCase().includes(search)
    );
    renderIngredients(filtered);
}

function renderIngredients(ingredients) {
    const tbody = document.getElementById('ingredientsBody');

    if (!ingredients || ingredients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="muted center">No ingredients yet. Click "Add Ingredient" to start.</td></tr>';
        return;
    }

    tbody.innerHTML = ingredients.map(i => {
        const statusBadge = i.needs_reorder
            ? '<span class="rate-badge bad">⚠️ Low</span>'
            : '<span class="rate-badge good">✅ OK</span>';

        return `
            <tr>
                <td><strong>${escapeHtml(i.name)}</strong></td>
                <td>${escapeHtml(i.unit)}</td>
                <td class="num">${formatCurrencyDecimal(i.cost_per_unit)}</td>
                <td class="num">${i.current_stock}</td>
                <td class="num">${i.reorder_threshold}</td>
                <td class="num">${formatCurrency(i.stock_value)}</td>
                <td>${statusBadge}</td>
                <td>
                    <button onclick="editIngredient(${i.id})" class="btn-icon" title="Edit">✏️</button>
                    <button onclick="deleteIngredient(${i.id}, '${escapeHtml(i.name)}')" class="btn-icon" title="Delete">🗑️</button>
                </td>
            </tr>
        `;
    }).join('');
}

function openAddModal() {
    document.getElementById('modalTitle').textContent = 'Add Ingredient';
    document.getElementById('ingredientForm').reset();
    document.getElementById('ingredientId').value = '';
    document.getElementById('ingredientModal').style.display = 'flex';
}

function editIngredient(id) {
    const ing = allIngredients.find(i => i.id === id);
    if (!ing) return;

    document.getElementById('modalTitle').textContent = 'Edit Ingredient';
    document.getElementById('ingredientId').value = id;
    document.getElementById('ingName').value = ing.name;
    document.getElementById('ingUnit').value = ing.unit;
    document.getElementById('ingCost').value = ing.cost_per_unit;
    document.getElementById('ingStock').value = ing.current_stock;
    document.getElementById('ingReorder').value = ing.reorder_threshold;
    document.getElementById('ingredientModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('ingredientModal').style.display = 'none';
}

async function saveIngredient(e) {
    e.preventDefault();

    const id = document.getElementById('ingredientId').value;
    const data = {
        name: document.getElementById('ingName').value.trim(),
        unit: document.getElementById('ingUnit').value,
        cost_per_unit: parseFloat(document.getElementById('ingCost').value) || 0,
        current_stock: parseFloat(document.getElementById('ingStock').value) || 0,
        reorder_threshold: parseFloat(document.getElementById('ingReorder').value) || 0
    };

    const btn = document.getElementById('saveBtn');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        if (id) {
            await apiFetch(`/api/foodcost/ingredients/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            showAlert('Ingredient updated', 'success');
        } else {
            await apiFetch('/api/foodcost/ingredients', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showAlert('Ingredient added', 'success');
        }
        closeModal();
        loadIngredients();
    } catch (err) {
        showAlert(err.message || 'Failed to save', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save';
    }
}

async function deleteIngredient(id, name) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;

    try {
        await apiFetch(`/api/foodcost/ingredients/${id}`, { method: 'DELETE' });
        showAlert('Ingredient deleted', 'success');
        loadIngredients();
    } catch (err) {
        showAlert(err.message || 'Delete failed', 'error');
    }
}

