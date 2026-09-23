// ==========================================
// UTILITY FUNCTIONS
// ==========================================

function formatCurrency(amount, currency = '₹') {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return currency + '0';
    }
    const num = parseFloat(amount);
    return currency + num.toLocaleString('en-IN', {
        maximumFractionDigits: 0
    });
}

function formatCurrencyDecimal(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '₹0.00';
    }
    return '₹' + parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return parseInt(num).toLocaleString('en-IN');
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    });
}

function formatPercent(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) return '0%';
    return parseFloat(value).toFixed(decimals) + '%';
}

function showAlert(message, type = 'info', autoHide = true) {
    const box = document.getElementById('alertBox');
    if (!box) return;

    box.className = `alert alert-${type}`;
    box.textContent = message;
    box.style.display = 'block';

    if (autoHide) {
        setTimeout(() => {
            box.style.display = 'none';
        }, 5000);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

