// Main JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // File upload handling
    initializeFileUpload();

    // Form validation
    initializeFormValidation();

    // Auto-hide alerts
    initializeAlerts();
});

// File Upload Functions
function initializeFileUpload() {
    const uploadAreas = document.querySelectorAll('.upload-area');

    uploadAreas.forEach(area => {
        const fileInput = area.querySelector('input[type="file"]');

        if (!fileInput) return;

        // Click to upload
        area.addEventListener('click', () => fileInput.click());

        // Drag and drop
        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });

        area.addEventListener('dragleave', () => {
            area.classList.remove('dragover');
        });

        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');

            const files = e.dataTransfer.files;
            handleFileSelect(files, fileInput);
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            handleFileSelect(e.target.files, fileInput);
        });
    });
}

function handleFileSelect(files, fileInput) {
    if (files.length === 0) return;

    const file = files[0];
    const maxSize = 20 * 1024 * 1024; // 20MB
    const allowedTypes = ['application/pdf', 'application/msword',
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                         'text/plain'];

    // Validate file size
    if (file.size > maxSize) {
        showAlert('File size must be less than 20MB', 'danger');
        return;
    }

    // Validate file type
    if (!allowedTypes.includes(file.type)) {
        showAlert('Please upload a PDF, DOC, DOCX, or TXT file', 'danger');
        return;
    }

    // Update UI
    const uploadArea = fileInput.closest('.upload-area');
    if (uploadArea) {
        uploadArea.querySelector('.upload-text').textContent = file.name;
        uploadArea.classList.add('file-selected');
    }

    // Trigger form submission if needed
    const form = fileInput.closest('form');
    if (form && form.dataset.autoSubmit === 'true') {
        form.submit();
    }
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');

    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Alert Management
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');

    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.3s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
}

function showErrorModal(message, title = 'Something went wrong') {
    const modalElement = document.getElementById('appErrorModal');
    if (!modalElement) {
        console.error('Error modal not found:', message);
        return;
    }

    const modalTitle = document.getElementById('appErrorModalLabel');
    const modalBody = document.getElementById('appErrorModalBody');

    if (modalTitle) {
        modalTitle.textContent = title;
    }
    if (modalBody) {
        modalBody.textContent = message || 'An unexpected error occurred.';
    }

    const modalInstance = bootstrap.Modal.getOrCreateInstance(modalElement);
    modalInstance.show();
}

function showAlert(message, type = 'info') {
    if (type === 'danger') {
        showErrorModal(message);
        return;
    }

    const alertContainer = document.querySelector('.alert-container') || document.querySelector('main');

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.appendChild(alertDiv);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertDiv.style.transition = 'opacity 0.3s';
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

// Loading States
function showLoading(element) {
    element.classList.add('loading');
    const originalText = element.textContent;
    element.dataset.originalText = originalText;
    element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    element.disabled = true;
}

function hideLoading(element) {
    element.classList.remove('loading');
    element.textContent = element.dataset.originalText || 'Submit';
    element.disabled = false;
}

// API Helper Functions
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    const finalOptions = { ...defaultOptions, ...options };

    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }

        return data;
    } catch (error) {
        showAlert(error.message, 'danger');
        throw error;
    }
}

// Utility Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Score Visualization
function createScoreChart(elementId, score, maxScore = 100) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 40;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#e9ecef';
    ctx.lineWidth = 8;
    ctx.stroke();

    // Progress arc
    const progress = (score / maxScore) * 2 * Math.PI;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + progress);

    // Color based on score
    if (score >= 80) ctx.strokeStyle = '#28a745';
    else if (score >= 60) ctx.strokeStyle = '#17a2b8';
    else if (score >= 40) ctx.strokeStyle = '#ffc107';
    else ctx.strokeStyle = '#dc3545';

    ctx.lineWidth = 8;
    ctx.stroke();

    // Score text
    ctx.fillStyle = '#212529';
    ctx.font = 'bold 24px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(score, centerX, centerY);
}

// Export Functions
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';

    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');

    const csvRows = data.map(row => {
        return headers.map(header => {
            const value = row[header];
            return typeof value === 'string' ? `"${value}"` : value;
        }).join(',');
    });

    return [csvHeaders, ...csvRows].join('\n');
}
