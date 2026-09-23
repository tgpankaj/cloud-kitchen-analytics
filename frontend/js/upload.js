// ==========================================
// CSV UPLOAD LOGIC
// ==========================================

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

let currentFile = null;

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    const session = requireAuth();
    if (!session) return;

    setupDropzone();
    loadUploadHistory();
});

// ── Dropzone setup ──
function setupDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');

    if (!dropzone) return;

    // Click to browse
    dropzone.addEventListener('click', (e) => {
        // Ignore clicks on buttons/links inside
        if (e.target.closest('button') || e.target.closest('a')) return;
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag events
    ['dragenter', 'dragover'].forEach(evt => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
}

// ── File validation ──
function handleFile(file) {
    // Check extension
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showAlert('Only .csv files are allowed', 'error');
        return;
    }

    // Check size
    if (file.size > MAX_FILE_SIZE) {
        showAlert(`File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max 10MB.`, 'error');
        return;
    }

    if (file.size === 0) {
        showAlert('File is empty', 'error');
        return;
    }

    currentFile = file;
    uploadFile(file);
}

// ── Upload to backend ──
async function uploadFile(file) {
    // Switch UI state
    showState('progress');
    updateProgress(0, `Reading ${file.name}...`);

    // Build FormData
    const formData = new FormData();
    formData.append('file', file);

    const kitchen = JSON.parse(localStorage.getItem('kitchen') || '{}');
    if (kitchen.id) {
        formData.append('kitchen_id', kitchen.id);
    }

    // Upload with XMLHttpRequest for progress tracking
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const pct = (e.loaded / e.total) * 100;
                updateProgress(pct, `Uploading... ${pct.toFixed(0)}%`);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const result = JSON.parse(xhr.responseText);
                    onUploadSuccess(result);
                    resolve(result);
                } catch (err) {
                    onUploadError('Invalid server response');
                    reject(err);
                }
            } else {
                let errorMsg = `Upload failed (${xhr.status})`;
                try {
                    const err = JSON.parse(xhr.responseText);
                    errorMsg = err.error || errorMsg;
                } catch (e) { /* ignore */ }
                onUploadError(errorMsg);
                reject(new Error(errorMsg));
            }
        });

        xhr.addEventListener('error', () => {
            onUploadError('Network error. Please check your connection.');
            reject(new Error('Network error'));
        });

        xhr.addEventListener('abort', () => {
            onUploadError('Upload cancelled');
            reject(new Error('Aborted'));
        });

        const token = localStorage.getItem('token');
        xhr.open('POST', `${API_URL}/api/upload/csv`);
        if (token) {
            xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }
        xhr.send(formData);
    });
}

// ── UI state management ──
function showState(state) {
    ['dropzoneContent', 'progressState', 'successState'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    const map = {
        'idle': 'dropzoneContent',
        'progress': 'progressState',
        'success': 'successState'
    };

    const target = document.getElementById(map[state]);
    if (target) target.style.display = 'block';
}

function updateProgress(pct, text) {
    const fill = document.getElementById('progressFill');
    const textEl = document.getElementById('progressText');
    if (fill) fill.style.width = `${pct}%`;
    if (textEl) textEl.textContent = text;
}

function onUploadSuccess(result) {
    updateProgress(100, 'Complete!');

    setTimeout(() => {
        const stats = result.stats || {};

        const statsDisplay = document.getElementById('statsDisplay');
        statsDisplay.innerHTML = `
            <div class="stat-box">
                <span class="stat-value">${stats.inserted || 0}</span>
                <span class="stat-label">Orders Imported</span>
            </div>
            <div class="stat-box">
                <span class="stat-value">${stats.new_items || 0}</span>
                <span class="stat-label">New Items</span>
            </div>
            <div class="stat-box">
                <span class="stat-value">${stats.new_customers || 0}</span>
                <span class="stat-label">New Customers</span>
            </div>
            <div class="stat-box ${stats.failed > 0 ? 'warning' : ''}">
                <span class="stat-value">${stats.failed || 0}</span>
                <span class="stat-label">Failed Rows</span>
            </div>
        `;

        showState('success');
        loadUploadHistory();
    }, 400);
}

function onUploadError(message) {
    showAlert(message, 'error');
    showState('idle');
    currentFile = null;

    // Reset file input
    const input = document.getElementById('fileInput');
    if (input) input.value = '';
}

function resetUpload() {
    currentFile = null;
    const input = document.getElementById('fileInput');
    if (input) input.value = '';
    showState('idle');
    document.getElementById('alertBox').style.display = 'none';
}

// ── Upload history ──
async function loadUploadHistory() {
    const container = document.getElementById('historyList');
    if (!container) return;

    try {
        const history = await apiFetch('/api/upload/history');

        if (!history || history.length === 0) {
            container.innerHTML = '<p class="muted small">No uploads yet. Upload your first CSV above.</p>';
            return;
        }

        container.innerHTML = history.slice(0, 5).map(h => {
            const hasErrors = h.rows_failed > 0;
            const date = new Date(h.uploaded_at).toLocaleString('en-IN', {
                day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
            });

            return `
                <div class="history-item">
                    <div><strong>${escapeHtml(h.filename || 'upload.csv')}</strong></div>
                    <div class="history-meta">${date} • ${escapeHtml(h.kitchen_name || '')}</div>
                    <div class="history-stats ${hasErrors ? 'has-errors' : ''}">
                        ✅ ${h.rows_inserted} inserted${hasErrors ? ` • ⚠️ ${h.rows_failed} failed` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        container.innerHTML = '<p class="muted small">Could not load history.</p>';
    }
}

// ── Download template ──
async function downloadTemplate() {
    try {
        const data = await apiFetch('/api/upload/template');
        const blob = new Blob([data.template], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'kitchen-analytics-template.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showAlert('Template downloaded!', 'success');
    } catch (err) {
        showAlert('Could not download template', 'error');
    }
}