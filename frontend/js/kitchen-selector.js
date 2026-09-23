// ==========================================
// GLOBAL KITCHEN SELECTOR
// ==========================================

async function initKitchenSelector() {
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks) return;

    // Check if already exists
    if (document.getElementById('kitchenSelector')) return;

    try {
        const kitchens = await apiFetch('/api/branches/list');
        if (!kitchens || kitchens.length === 0) return;

        const activeId = getActiveKitchenId(kitchens);

        const select = document.createElement('select');
        select.id = 'kitchenSelector';
        select.className = 'kitchen-selector';
        select.onchange = (e) => switchKitchen(e.target.value);

        select.innerHTML = kitchens.map(k =>
            `<option value="${k.id}" ${k.id === activeId ? 'selected' : ''}>
                ${escapeHtml(k.name)}${k.city ? ' — ' + escapeHtml(k.city) : ''}
            </option>`
        ).join('');

        // Insert before user info / logout
        const firstBtn = navLinks.querySelector('.btn');
        if (firstBtn) {
            navLinks.insertBefore(select, firstBtn);
        } else {
            navLinks.appendChild(select);
        }

    } catch (err) {
        console.warn('Kitchen selector failed:', err.message);
    }
}

function getActiveKitchenId(kitchens) {
    const stored = parseInt(localStorage.getItem('active_kitchen_id') || '0');
    if (stored && kitchens.some(k => k.id === stored)) {
        return stored;
    }
    // Fallback to session kitchen or first
    const session = JSON.parse(localStorage.getItem('kitchen') || '{}');
    if (session.id && kitchens.some(k => k.id === session.id)) {
        return session.id;
    }
    if (kitchens.length > 0) {
        localStorage.setItem('active_kitchen_id', kitchens[0].id);
        return kitchens[0].id;
    }
    return null;
}

function getActiveKitchen() {
    return parseInt(localStorage.getItem('active_kitchen_id') || '0') || null;
}

function switchKitchen(kitchenId) {
    localStorage.setItem('active_kitchen_id', kitchenId);
    // Reload current page with new kitchen
    window.location.reload();
}

// Auto-run when DOM is ready (only on authenticated pages)
document.addEventListener('DOMContentLoaded', () => {
    if (typeof requireAuth === 'function' && localStorage.getItem('token')) {
        setTimeout(initKitchenSelector, 100);
    }
});

