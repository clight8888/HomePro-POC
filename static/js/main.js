// HomePro Main JavaScript

// Global variables
let currentUser = null;
let csrfToken = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    preventAutoTooltips();
    initializeApp();
    setupEventListeners();
    setupFormValidation();
});

function preventAutoTooltips() {
    // Prevent automatic tooltip creation from title attributes
    // Only allow tooltips that are explicitly defined with data-bs-toggle="tooltip"
    const elementsWithTitle = document.querySelectorAll('[title]:not([data-bs-toggle="tooltip"])');
    elementsWithTitle.forEach(function(element) {
        // Store the title in a data attribute and remove the title to prevent auto-tooltips
        const title = element.getAttribute('title');
        if (title && title.trim()) {
            element.setAttribute('data-original-title', title);
            element.removeAttribute('title');
        }
    });
}

function initializeApp() {
    // Get CSRF token if available
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        csrfToken = csrfMeta.getAttribute('content');
    }
    
    // Initialize tooltips only for elements that explicitly have data-bs-toggle="tooltip"
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        try {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                boundary: 'viewport',
                placement: 'auto'
            });
        } catch (error) {
            console.warn('Failed to initialize tooltip:', error, tooltipTriggerEl);
        }
    });
    
    // Initialize popovers only for elements that explicitly have data-bs-toggle="popover"
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        try {
            return new bootstrap.Popover(popoverTriggerEl, {
                boundary: 'viewport',
                placement: 'auto'
            });
        } catch (error) {
            console.warn('Failed to initialize popover:', error, popoverTriggerEl);
        }
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (error) {
                console.warn('Failed to close alert:', error);
            }
        });
    }, 5000);
}

function setupEventListeners() {
    // File upload handling
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(setupFileUpload);
    
    // Form submission handling
    const forms = document.querySelectorAll('form[data-ajax="true"]');
    forms.forEach(setupAjaxForm);
    
    // Search functionality
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(setupSearch);
    
    // Filter functionality
    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(setupFilter);
}

// File Upload Functionality
function setupFileUpload(fileInput) {
    const uploadArea = fileInput.closest('.file-upload-area');
    if (!uploadArea) return;
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelection(fileInput, files[0]);
        }
    });
    
    // Click to upload
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    // File selection change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFileSelection(this, this.files[0]);
        }
    });
}

function handleFileSelection(input, file) {
    const uploadArea = input.closest('.file-upload-area');
    const maxSize = parseInt(input.getAttribute('data-max-size')) || 50 * 1024 * 1024; // 50MB default
    const allowedTypes = input.getAttribute('data-allowed-types')?.split(',') || [];
    
    // Validate file size
    if (file.size > maxSize) {
        showAlert('File size exceeds the maximum limit of ' + formatFileSize(maxSize), 'danger');
        input.value = '';
        return;
    }
    
    // Validate file type
    if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
        showAlert('File type not supported. Allowed types: ' + allowedTypes.join(', '), 'danger');
        input.value = '';
        return;
    }
    
    // Update UI
    const fileName = uploadArea.querySelector('.file-name');
    const fileSize = uploadArea.querySelector('.file-size');
    const uploadIcon = uploadArea.querySelector('.file-upload-icon');
    
    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = formatFileSize(file.size);
    if (uploadIcon) {
        uploadIcon.className = 'file-upload-icon fas fa-check-circle text-success';
    }
    
    uploadArea.classList.add('file-selected');
    
    // Show preview for images
    if (file.type.startsWith('image/')) {
        showImagePreview(file, uploadArea);
    }
}

function showImagePreview(file, container) {
    const reader = new FileReader();
    reader.onload = function(e) {
        let preview = container.querySelector('.image-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.className = 'image-preview mt-3';
            container.appendChild(preview);
        }
        
        preview.innerHTML = `
            <img src="${e.target.result}" alt="Preview" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">
        `;
    };
    reader.readAsDataURL(file);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// AJAX Form Handling
function setupAjaxForm(form) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitFormAjax(this);
    });
}

function submitFormAjax(form) {
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    submitBtn.disabled = true;
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message || 'Operation completed successfully', 'success');
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
        } else {
            showAlert(data.message || 'An error occurred', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An unexpected error occurred', 'danger');
    })
    .finally(() => {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// Search Functionality
function setupSearch(searchInput) {
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(this.value, this.getAttribute('data-target'));
        }, 300);
    });
}

function performSearch(query, target) {
    const targetElement = document.querySelector(target);
    if (!targetElement) return;
    
    const items = targetElement.querySelectorAll('.searchable-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        const matches = text.includes(query.toLowerCase());
        item.style.display = matches ? '' : 'none';
    });
    
    // Update results count
    const visibleItems = targetElement.querySelectorAll('.searchable-item:not([style*="display: none"])');
    const countElement = document.querySelector('.search-results-count');
    if (countElement) {
        countElement.textContent = `${visibleItems.length} result${visibleItems.length !== 1 ? 's' : ''}`;
    }
}

// Filter Functionality
function setupFilter(filterSelect) {
    filterSelect.addEventListener('change', function() {
        applyFilter(this.value, this.getAttribute('data-target'), this.getAttribute('data-filter-type'));
    });
}

function applyFilter(value, target, filterType) {
    const targetElement = document.querySelector(target);
    if (!targetElement) return;
    
    const items = targetElement.querySelectorAll('.filterable-item');
    
    items.forEach(item => {
        if (value === '' || value === 'all') {
            item.style.display = '';
        } else {
            const itemValue = item.getAttribute(`data-${filterType}`);
            item.style.display = itemValue === value ? '' : 'none';
        }
    });
}

// Form Validation
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Real-time validation
    const inputs = document.querySelectorAll('.form-control[required]');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            if (this.classList.contains('is-invalid')) {
                validateField(this);
            }
        });
    });
}

function validateField(field) {
    const isValid = field.checkValidity();
    field.classList.toggle('is-valid', isValid);
    field.classList.toggle('is-invalid', !isValid);
    
    // Show/hide custom error message
    const errorElement = field.parentNode.querySelector('.invalid-feedback');
    if (errorElement) {
        errorElement.style.display = isValid ? 'none' : 'block';
    }
}

// Utility Functions
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.querySelector('.alert-container') || document.body;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, duration);
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }).format(new Date(date));
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Project-specific functions
function toggleContractorFields() {
    const userType = document.querySelector('input[name="user_type"]:checked')?.value;
    const contractorFields = document.querySelector('.contractor-fields');
    
    if (contractorFields) {
        contractorFields.style.display = userType === 'contractor' ? 'block' : 'none';
        
        // Toggle required attributes
        const contractorInputs = contractorFields.querySelectorAll('input, select, textarea');
        contractorInputs.forEach(input => {
            if (userType === 'contractor') {
                input.setAttribute('required', 'required');
            } else {
                input.removeAttribute('required');
            }
        });
    }
}

function updateProjectType() {
    const description = document.querySelector('#description')?.value || '';
    const projectTypeSelect = document.querySelector('#project_type');
    
    if (!projectTypeSelect || !description) return;
    
    // Simple keyword-based project type detection
    const keywords = {
        'plumbing': ['plumb', 'pipe', 'leak', 'faucet', 'toilet', 'drain', 'water'],
        'electrical': ['electric', 'wire', 'outlet', 'switch', 'light', 'circuit', 'power'],
        'hvac': ['heat', 'cool', 'air', 'hvac', 'furnace', 'ac', 'ventilation'],
        'roofing': ['roof', 'shingle', 'gutter', 'leak', 'tile'],
        'flooring': ['floor', 'carpet', 'tile', 'hardwood', 'laminate'],
        'painting': ['paint', 'color', 'wall', 'interior', 'exterior'],
        'landscaping': ['garden', 'lawn', 'tree', 'plant', 'landscape', 'yard']
    };
    
    const lowerDescription = description.toLowerCase();
    
    for (const [type, words] of Object.entries(keywords)) {
        if (words.some(word => lowerDescription.includes(word))) {
            projectTypeSelect.value = type;
            break;
        }
    }
}

function estimateBudget() {
    const description = document.querySelector('#description')?.value || '';
    const projectType = document.querySelector('#project_type')?.value;
    const budgetMinInput = document.querySelector('#budget_min');
    const budgetMaxInput = document.querySelector('#budget_max');
    
    if (!description || !projectType || !budgetMinInput || !budgetMaxInput) return;
    
    // Simple budget estimation based on project type and description length
    const baseBudgets = {
        'plumbing': { min: 150, max: 800 },
        'electrical': { min: 200, max: 1200 },
        'hvac': { min: 300, max: 2000 },
        'roofing': { min: 500, max: 5000 },
        'flooring': { min: 300, max: 3000 },
        'painting': { min: 200, max: 1500 },
        'landscaping': { min: 100, max: 2000 },
        'other': { min: 100, max: 1000 }
    };
    
    const budget = baseBudgets[projectType] || baseBudgets['other'];
    const complexity = Math.min(description.length / 100, 3); // 1-3 complexity multiplier
    
    const estimatedMin = Math.round(budget.min * complexity);
    const estimatedMax = Math.round(budget.max * complexity);
    
    if (!budgetMinInput.value) budgetMinInput.value = estimatedMin;
    if (!budgetMaxInput.value) budgetMaxInput.value = estimatedMax;
}

// Export functions for global use
window.HomePro = {
    showAlert,
    formatCurrency,
    formatDate,
    toggleContractorFields,
    updateProjectType,
    estimateBudget,
    debounce
};