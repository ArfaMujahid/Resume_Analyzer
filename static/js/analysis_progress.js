/**
 * Analysis Progress Tracker
 * Handles real-time progress updates for resume analysis
 */

class AnalysisProgressTracker {
    constructor(options = {}) {
        this.options = {
            checkInterval: 3000, // 3 seconds
            maxRetries: 100,
            loadingSelector: '#loadingOverlay',
            progressBarSelector: '#progressBar',
            statusTextSelector: '#statusText',
            ...options
        };

        this.retryCount = 0;
        this.isRunning = false;
        this.statusCheckInterval = null;
    }

    /**
     * Start tracking analysis progress
     * @param {string} statusUrl - URL to check status
     * @param {Function} onComplete - Callback when analysis is complete
     * @param {Function} onError - Callback when analysis fails
     */
    startTracking(statusUrl, onComplete, onError) {
        if (this.isRunning) {
            console.warn('Analysis tracking is already running');
            return;
        }

        this.isRunning = true;
        this.retryCount = 0;
        this.statusUrl = statusUrl;
        this.onComplete = onComplete || (() => window.location.reload());
        this.onError = onError || ((error) => console.error('Analysis failed:', error));

        // Show loading overlay
        this.showLoading();

        // Start periodic status checks
        this.statusCheckInterval = setInterval(() => {
            this.checkStatus();
        }, this.options.checkInterval);

        // Initial status check
        this.checkStatus();
    }

    /**
     * Stop tracking analysis progress
     */
    stopTracking() {
        this.isRunning = false;

        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }

        this.hideLoading();
    }

    /**
     * Check analysis status
     */
    async checkStatus() {
        if (!this.isRunning || this.retryCount >= this.options.maxRetries) {
            this.stopTracking();
            if (this.retryCount >= this.options.maxRetries) {
                this.onError('Maximum retries reached');
            }
            return;
        }

        try {
            const response = await fetch(this.statusUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.handleStatusResponse(data);

        } catch (error) {
            console.error('Error checking analysis status:', error);
            this.retryCount++;

            // Don't stop on first error, might be temporary
            if (this.retryCount >= 3) {
                this.stopTracking();
                this.onError(error);
            }
        }
    }

    /**
     * Handle status response
     * @param {Object} data - Status response data
     */
    handleStatusResponse(data) {
        switch (data.status) {
            case 'complete':
                this.stopTracking();
                this.onComplete(data);
                break;

            case 'failed':
                this.stopTracking();
                this.onError('Analysis failed');
                break;

            case 'running':
            case 'processing':
                this.updateProgress(data);
                break;

            default:
                console.warn('Unknown status:', data.status);
        }
    }

    /**
     * Update progress display
     * @param {Object} data - Status data
     */
    updateProgress(data) {
        // Update progress bar if we have progress information
        if (data.progress !== undefined) {
            this.updateProgressBar(data.progress);
        } else if (data.current && data.total) {
            const progress = Math.round((data.current / data.total) * 100);
            this.updateProgressBar(progress);
        } else {
            // Simulate progress if we don't have actual data
            const simulatedProgress = Math.min(90, (this.retryCount * 10));
            this.updateProgressBar(simulatedProgress);
        }

        // Update status text
        if (data.message) {
            this.updateStatusText(data.message);
        }
    }

    /**
     * Update progress bar
     * @param {number} percent - Progress percentage (0-100)
     */
    updateProgressBar(percent) {
        const progressBar = document.querySelector(this.options.progressBarSelector);
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${percent}%`;
        }
    }

    /**
     * Update status text
     * @param {string} text - Status text
     */
    updateStatusText(text) {
        const statusElement = document.querySelector(this.options.statusTextSelector);
        if (statusElement) {
            statusElement.textContent = text;
        }
    }

    /**
     * Show loading overlay
     */
    showLoading() {
        const loadingOverlay = document.querySelector(this.options.loadingSelector);
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        const loadingOverlay = document.querySelector(this.options.loadingSelector);
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }
}

// Talent Analysis Progress Handler
class TalentAnalysisProgress extends AnalysisProgressTracker {
    constructor() {
        super({
            loadingSelector: '#loadingOverlay',
            progressBarSelector: '#progressBar',
            statusTextSelector: '#statusText'
        });
    }

    init(resumeId, jobDescriptionId) {
        const statusUrl = `${window.location.pathname}?resume_id=${resumeId}&job_description_id=${jobDescriptionId}`;

        this.startTracking(
            statusUrl,
            (data) => {
                // On complete, show success message
                this.showSuccessMessage();
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            },
            (error) => {
                // On error, show error message
                this.showErrorMessage(error);
            }
        );
    }

    showSuccessMessage() {
        const statusText = document.querySelector(this.options.statusTextSelector);
        if (statusText) {
            statusText.textContent = 'Analysis completed successfully!';
            statusText.className = 'text-success';
        }
    }

    showErrorMessage(error) {
        const statusText = document.querySelector(this.options.statusTextSelector);
        if (statusText) {
            statusText.textContent = 'Analysis failed. Please try again.';
            statusText.className = 'text-danger';
        }

        setTimeout(() => {
            window.location.href = '/talent/analysis/';
        }, 3000);
    }
}

// Recruiter Batch Progress Handler
class RecruiterBatchProgress extends AnalysisProgressTracker {
    constructor() {
        super({
            loadingSelector: '#loadingOverlay',
            progressBarSelector: '#progressBar',
            statusTextSelector: '#statusText'
        });
    }

    init(batchId) {
        const statusUrl = `/recruiter/batches/${batchId}/rank/`;

        this.startTracking(
            statusUrl,
            (data) => {
                // On complete, show success message with results count
                this.showSuccessMessage(data.resume_count);
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            },
            (error) => {
                // On error, show error message
                this.showErrorMessage(error);
            }
        );
    }

    showSuccessMessage(resumeCount) {
        const statusText = document.querySelector(this.options.statusTextSelector);
        if (statusText) {
            statusText.textContent = `Successfully analyzed ${resumeCount} resumes!`;
            statusText.className = 'text-success';
        }
    }

    showErrorMessage(error) {
        const statusText = document.querySelector(this.options.statusTextSelector);
        if (statusText) {
            statusText.textContent = 'Batch analysis failed. Please try again.';
            statusText.className = 'text-danger';
        }

        setTimeout(() => {
            window.history.back();
        }, 3000);
    }
}

// Initialize progress trackers when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on talent analysis page
    if (window.location.pathname.startsWith('/talent/analyze/')) {
        const urlParams = new URLSearchParams(window.location.search);
        const resumeId = urlParams.get('resume_id');
        const jobDescriptionId = urlParams.get('job_description_id');

        if (resumeId && jobDescriptionId) {
            const talentProgress = new TalentAnalysisProgress();
            talentProgress.init(resumeId, jobDescriptionId);
        }
    }

    // Check if we're on recruiter batch rank page
    if (window.location.pathname.includes('/batches/') && window.location.pathname.includes('/rank/')) {
        const batchId = window.location.pathname.split('/')[3]; // Extract batch ID from URL
        if (batchId) {
            const recruiterProgress = new RecruiterBatchProgress();
            recruiterProgress.init(batchId);
        }
    }
});

// Export for use in other scripts
window.AnalysisProgressTracker = AnalysisProgressTracker;
window.TalentAnalysisProgress = TalentAnalysisProgress;
window.RecruiterBatchProgress = RecruiterBatchProgress;