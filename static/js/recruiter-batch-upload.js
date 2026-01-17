/**
 * JavaScript for recruiter batch upload functionality
 * Handles file uploads, progress tracking, and UI updates
 */

class BatchUploader {
    constructor(options = {}) {
        this.options = {
            maxFileSize: options.maxFileSize || 10 * 1024 * 1024, // 10MB
            maxFiles: options.maxFiles || 50,
            allowedTypes: options.allowedTypes || [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain'
            ],
            uploadUrl: options.uploadUrl || '/recruiter/api/batch-upload/',
            progressUrl: options.progressUrl || '/recruiter/api/upload-progress/',
            ...options
        };

        this.files = [];
        this.uploadQueue = [];
        this.currentUpload = null;
        this.progressCallbacks = [];

        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        // File input
        this.fileInput = document.getElementById('resumeFiles');

        // Drop zone
        this.dropZone = document.getElementById('dropZone');

        // Upload button
        this.uploadBtn = document.getElementById('uploadBtn');

        // Progress container
        this.progressContainer = document.getElementById('uploadProgress');

        // File list
        this.fileList = document.getElementById('fileList');

        // Progress bar
        this.progressBar = document.getElementById('progressBar');
        this.progressText = document.getElementById('progressText');

        // Status messages
        this.statusMessage = document.getElementById('statusMessage');
    }

    bindEvents() {
        // File input change
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        // Drag and drop
        if (this.dropZone) {
            this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
            this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            this.dropZone.addEventListener('drop', (e) => this.handleFileDrop(e));
        }

        // Upload button
        if (this.uploadBtn) {
            this.uploadBtn.addEventListener('click', () => this.startUpload());
        }

        // Prevent default drag behaviors
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('drop', (e) => e.preventDefault());
    }

    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        this.addFiles(files);
    }

    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dropZone.classList.add('drag-over');
    }

    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dropZone.classList.remove('drag-over');
    }

    handleFileDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.dropZone.classList.remove('drag-over');

        const files = Array.from(event.dataTransfer.files);
        this.addFiles(files);
    }

    addFiles(files) {
        const validFiles = [];
        const errors = [];

        files.forEach(file => {
            // Check file type
            if (!this.options.allowedTypes.includes(file.type)) {
                errors.push(`${file.name}: Invalid file type`);
                return;
            }

            // Check file size
            if (file.size > this.options.maxFileSize) {
                errors.push(`${file.name}: File too large (max ${this.formatFileSize(this.options.maxFileSize)})`);
                return;
            }

            // Check for duplicates
            if (this.files.some(f => f.name === file.name && f.size === file.size)) {
                errors.push(`${file.name}: Duplicate file`);
                return;
            }

            validFiles.push(file);
        });

        // Check total file count
        if (this.files.length + validFiles.length > this.options.maxFiles) {
            errors.push(`Too many files (max ${this.options.maxFiles})`);
            return;
        }

        // Add valid files
        validFiles.forEach(file => {
            this.files.push({
                file: file,
                id: Date.now() + Math.random(),
                status: 'pending',
                progress: 0,
                error: null
            });
        });

        // Update UI
        this.updateFileList();
        this.showErrors(errors);

        // Enable upload button if we have files
        if (this.uploadBtn && this.files.length > 0) {
            this.uploadBtn.disabled = false;
        }
    }

    updateFileList() {
        if (!this.fileList) return;

        this.fileList.innerHTML = '';

        this.files.forEach(fileObj => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.dataset.fileId = fileObj.id;

            const statusIcon = this.getStatusIcon(fileObj.status);
            const fileSize = this.formatFileSize(fileObj.file.size);

            fileItem.innerHTML = `
                <div class="file-info">
                    <span class="file-name">${fileObj.file.name}</span>
                    <span class="file-size">${fileSize}</span>
                </div>
                <div class="file-status">
                    ${statusIcon}
                    ${fileObj.error ? `<span class="error-text">${fileObj.error}</span>` : ''}
                </div>
                <div class="file-progress" style="display: ${fileObj.status === 'uploading' ? 'block' : 'none'}">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${fileObj.progress}%"></div>
                    </div>
                    <span class="progress-text">${fileObj.progress}%</span>
                </div>
                <button class="remove-file" onclick="batchUploader.removeFile('${fileObj.id}')">×</button>
            `;

            this.fileList.appendChild(fileItem);
        });
    }

    getStatusIcon(status) {
        const icons = {
            'pending': '<i class="fas fa-clock text-muted"></i>',
            'uploading': '<i class="fas fa-spinner fa-spin text-primary"></i>',
            'completed': '<i class="fas fa-check text-success"></i>',
            'error': '<i class="fas fa-exclamation-triangle text-danger"></i>'
        };
        return icons[status] || '';
    }

    removeFile(fileId) {
        this.files = this.files.filter(f => f.id !== fileId);
        this.updateFileList();

        // Disable upload button if no files
        if (this.uploadBtn && this.files.length === 0) {
            this.uploadBtn.disabled = true;
        }
    }

    async startUpload() {
        if (this.files.length === 0) {
            this.showStatus('No files to upload', 'warning');
            return;
        }

        // Show progress container
        if (this.progressContainer) {
            this.progressContainer.style.display = 'block';
        }

        // Disable upload button
        if (this.uploadBtn) {
            this.uploadBtn.disabled = true;
        }

        // Reset file statuses
        this.files.forEach(f => {
            f.status = 'pending';
            f.progress = 0;
            f.error = null;
        });

        this.updateFileList();

        try {
            // Create batch
            const batchData = await this.createBatch();
            const batchId = batchData.batch_id;

            // Upload files sequentially
            for (const fileObj of this.files) {
                await this.uploadFile(fileObj, batchId);
            }

            // Complete batch
            await this.completeBatch(batchId);

            this.showStatus('All files uploaded successfully!', 'success');

            // Redirect to batch detail after a delay
            setTimeout(() => {
                window.location.href = `/recruiter/batch/${batchId}/`;
            }, 2000);

        } catch (error) {
            console.error('Upload error:', error);
            this.showStatus(`Upload failed: ${error.message}`, 'error');
        } finally {
            // Re-enable upload button
            if (this.uploadBtn) {
                this.uploadBtn.disabled = false;
            }
        }
    }

    async createBatch() {
        const formData = new FormData();

        // Add job description if selected
        const jobDescriptionSelect = document.getElementById('jobDescription');
        if (jobDescriptionSelect && jobDescriptionSelect.value) {
            formData.append('job_description_id', jobDescriptionSelect.value);
        }

        // Add custom job title if provided
        const jobTitleInput = document.getElementById('customJobTitle');
        if (jobTitleInput && jobTitleInput.value) {
            formData.append('job_title', jobTitleInput.value);
        }

        const response = await fetch(this.options.uploadUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to create batch');
        }

        return await response.json();
    }

    async uploadFile(fileObj, batchId) {
        fileObj.status = 'uploading';
        this.updateFileList();

        const formData = new FormData();
        formData.append('file', fileObj.file);
        formData.append('batch_id', batchId);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Progress tracking
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const progress = Math.round((e.loaded / e.total) * 100);
                    fileObj.progress = progress;
                    this.updateFileList();
                    this.updateOverallProgress();
                }
            });

            // Completion
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    fileObj.status = 'completed';
                    fileObj.progress = 100;
                    this.updateFileList();
                    this.updateOverallProgress();
                    resolve();
                } else {
                    fileObj.status = 'error';
                    fileObj.error = 'Upload failed';
                    this.updateFileList();
                    reject(new Error('File upload failed'));
                }
            });

            // Error handling
            xhr.addEventListener('error', () => {
                fileObj.status = 'error';
                fileObj.error = 'Network error';
                this.updateFileList();
                reject(new Error('Network error'));
            });

            // Send request
            xhr.open('POST', this.options.uploadUrl);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.setRequestHeader('X-CSRFToken', this.getCSRFToken());
            xhr.send(formData);
        });
    }

    async completeBatch(batchId) {
        const response = await fetch(`${this.options.uploadUrl}complete/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                batch_id: batchId
            })
        });

        if (!response.ok) {
            throw new Error('Failed to complete batch');
        }

        return await response.json();
    }

    updateOverallProgress() {
        if (!this.progressBar || !this.progressText) return;

        const totalFiles = this.files.length;
        const completedFiles = this.files.filter(f => f.status === 'completed').length;
        const totalProgress = this.files.reduce((sum, f) => sum + f.progress, 0);
        const averageProgress = totalFiles > 0 ? Math.round(totalProgress / totalFiles) : 0;

        this.progressBar.style.width = `${averageProgress}%`;
        this.progressText.textContent = `${completedFiles}/${totalFiles} files (${averageProgress}%)`;
    }

    showStatus(message, type = 'info') {
        if (!this.statusMessage) return;

        this.statusMessage.textContent = message;
        this.statusMessage.className = `alert alert-${type}`;
        this.statusMessage.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.statusMessage.style.display = 'none';
        }, 5000);
    }

    showErrors(errors) {
        if (errors.length === 0) return;

        const errorList = errors.join('\n');
        this.showStatus(errorList, 'warning');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    getCSRFToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');

        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) {
                return decodeURIComponent(value);
            }
        }

        return '';
    }
}

// Initialize the batch uploader when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.batchUploader = new BatchUploader();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BatchUploader;
}