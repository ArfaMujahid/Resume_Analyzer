/**
 * JavaScript for recruiter results display
 * Handles filtering, sorting, and dynamic updates of analysis results
 */

class ResultsDisplay {
    constructor(options = {}) {
        this.options = {
            resultsUrl: options.resultsUrl || '/recruiter/api/results/',
            filterUrl: options.filterUrl || '/recruiter/api/filter-results/',
            sortUrl: options.sortUrl || '/recruiter/api/sort-results/',
            ...options
        };

        this.results = [];
        this.filteredResults = [];
        this.currentSort = { field: 'score', direction: 'desc' };
        this.currentFilters = {};

        this.initializeElements();
        this.bindEvents();
        this.loadResults();
    }

    initializeElements() {
        // Results containers
        this.tableView = document.getElementById('tableView');
        this.cardView = document.getElementById('cardView');
        this.resultsTableBody = document.getElementById('resultsTableBody');
        this.resultsCardContainer = document.getElementById('resultsCardContainer');

        // View toggle buttons
        this.tableViewBtn = document.getElementById('tableViewBtn');
        this.cardViewBtn = document.getElementById('cardViewBtn');

        // Filter controls
        this.scoreFilter = document.getElementById('scoreFilter');
        this.sortBy = document.getElementById('sortBy');
        this.searchInput = document.getElementById('searchInput');

        // Statistics
        this.totalCandidates = document.getElementById('totalCandidates');
        this.averageScore = document.getElementById('averageScore');
        this.shortlistedCount = document.getElementById('shortlistedCount');

        // Charts
        this.scoreDistributionChart = document.getElementById('scoreDistributionChart');
        this.skillsChart = document.getElementById('skillsChart');

        // Export buttons
        this.exportCsvBtn = document.getElementById('exportCsvBtn');
        this.exportPdfBtn = document.getElementById('exportPdfBtn');
    }

    bindEvents() {
        // View toggle
        if (this.tableViewBtn) {
            this.tableViewBtn.addEventListener('click', () => this.showTableView());
        }
        if (this.cardViewBtn) {
            this.cardViewBtn.addEventListener('click', () => this.showCardView());
        }

        // Filters
        if (this.scoreFilter) {
            this.scoreFilter.addEventListener('change', () => this.applyFilters());
        }
        if (this.sortBy) {
            this.sortBy.addEventListener('change', () => this.applySorting());
        }
        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.debounce(() => this.applySearch(), 300));
        }

        // Export
        if (this.exportCsvBtn) {
            this.exportCsvBtn.addEventListener('click', () => this.exportToCSV());
        }
        if (this.exportPdfBtn) {
            this.exportPdfBtn.addEventListener('click', () => this.exportToPDF());
        }

        // Real-time updates (if supported)
        this.startRealTimeUpdates();
    }

    async loadResults() {
        try {
            const response = await fetch(this.options.resultsUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load results');
            }

            const data = await response.json();
            this.results = data.results || [];
            this.filteredResults = [...this.results];

            this.updateDisplay();
            this.updateStatistics();
            this.updateCharts();

        } catch (error) {
            console.error('Error loading results:', error);
            this.showError('Failed to load results. Please refresh the page.');
        }
    }

    updateDisplay() {
        this.renderTableView();
        this.renderCardView();
    }

    renderTableView() {
        if (!this.resultsTableBody) return;

        this.resultsTableBody.innerHTML = '';

        this.filteredResults.forEach((result, index) => {
            const row = document.createElement('tr');
            row.dataset.score = result.overall_score;
            row.dataset.resultId = result.id;

            const scoreClass = this.getScoreClass(result.overall_score);
            const rank = index + 1;

            row.innerHTML = `
                <td>${rank}</td>
                <td>
                    <strong>${result.filename}</strong>
                    <br>
                    <small class="text-muted">
                        ${this.formatFileSize(result.file_size)} •
                        ${this.formatDate(result.created_at)}
                    </small>
                </td>
                <td>
                    <span class="score-badge ${scoreClass}">
                        ${result.overall_score}%
                    </span>
                </td>
                <td>${result.component_scores.skills_match}/25</td>
                <td>${result.component_scores.experience_seniority}/20</td>
                <td>${result.component_scores.education_certs}/10</td>
                <td>${result.confidence}%</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary" onclick="resultsDisplay.viewDetails('${result.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="resultsDisplay.shortlist('${result.id}')">
                            <i class="fas fa-star"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="resultsDisplay.downloadResume('${result.id}')">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </td>
            `;

            this.resultsTableBody.appendChild(row);
        });
    }

    renderCardView() {
        if (!this.resultsCardContainer) return;

        this.resultsCardContainer.innerHTML = '';

        this.filteredResults.forEach((result, index) => {
            const card = document.createElement('div');
            card.className = 'candidate-card';
            card.dataset.score = result.overall_score;
            card.dataset.resultId = result.id;

            const scoreClass = this.getScoreClass(result.overall_score);
            const rank = index + 1;

            card.innerHTML = `
                <div class="candidate-header">
                    <div>
                        <div class="candidate-rank">#${rank}</div>
                        <div class="candidate-name">${result.filename}</div>
                        <small class="text-muted">
                            ${this.formatDate(result.created_at)} •
                            ${this.formatFileSize(result.file_size)}
                        </small>
                    </div>
                    <div class="candidate-score score-badge ${scoreClass}">
                        ${result.overall_score}%
                    </div>
                </div>

                <div class="score-breakdown">
                    <div class="breakdown-item">
                        <div class="breakdown-label">Skills</div>
                        <div class="breakdown-value">${result.component_scores.skills_match}/25</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Experience</div>
                        <div class="breakdown-value">${result.component_scores.experience_seniority}/20</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Education</div>
                        <div class="breakdown-value">${result.component_scores.education_certs}/10</div>
                    </div>
                    <div class="breakdown-item">
                        <div class="breakdown-label">Confidence</div>
                        <div class="breakdown-value">${result.confidence}%</div>
                    </div>
                </div>

                ${result.evidence?.matched_requirements ? `
                <div class="evidence-preview">
                    <h6>Top Matches</h6>
                    ${result.evidence.matched_requirements.slice(0, 2).map(match =>
                        `<p>${match.jd_text}</p>`
                    ).join('')}
                </div>
                ` : ''}

                <div class="action-buttons mt-3">
                    <button class="btn btn-sm btn-outline-primary" onclick="resultsDisplay.viewDetails('${result.id}')">
                        View Details
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="resultsDisplay.shortlist('${result.id}')">
                        Shortlist
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="resultsDisplay.downloadResume('${result.id}')">
                        Download
                    </button>
                </div>
            `;

            this.resultsCardContainer.appendChild(card);
        });
    }

    showTableView() {
        if (this.tableView) {
            this.tableView.style.display = 'block';
        }
        if (this.cardView) {
            this.cardView.style.display = 'none';
        }
        if (this.tableViewBtn) {
            this.tableViewBtn.classList.add('active');
        }
        if (this.cardViewBtn) {
            this.cardViewBtn.classList.remove('active');
        }
    }

    showCardView() {
        if (this.tableView) {
            this.tableView.style.display = 'none';
        }
        if (this.cardView) {
            this.cardView.style.display = 'block';
        }
        if (this.tableViewBtn) {
            this.tableViewBtn.classList.remove('active');
        }
        if (this.cardViewBtn) {
            this.cardViewBtn.classList.add('active');
        }
    }

    applyFilters() {
        const scoreThreshold = this.scoreFilter ? parseInt(this.scoreFilter.value) : 0;

        this.filteredResults = this.results.filter(result => {
            // Score filter
            if (scoreThreshold > 0 && result.overall_score < scoreThreshold) {
                return false;
            }

            // Search filter
            if (this.currentFilters.search) {
                const searchTerm = this.currentFilters.search.toLowerCase();
                if (!result.filename.toLowerCase().includes(searchTerm)) {
                    return false;
                }
            }

            return true;
        });

        // Apply current sorting
        this.applySorting();
    }

    applySorting() {
        const sortBy = this.sortBy ? this.sortBy.value : 'score';

        this.currentSort = {
            field: sortBy,
            direction: sortBy === 'score' ? 'desc' : 'asc'
        };

        this.filteredResults.sort((a, b) => {
            let valueA, valueB;

            switch (sortBy) {
                case 'score':
                    valueA = a.overall_score;
                    valueB = b.overall_score;
                    break;
                case 'skills':
                    valueA = a.component_scores.skills_match;
                    valueB = b.component_scores.skills_match;
                    break;
                case 'experience':
                    valueA = a.component_scores.experience_seniority;
                    valueB = b.component_scores.experience_seniority;
                    break;
                case 'education':
                    valueA = a.component_scores.education_certs;
                    valueB = b.component_scores.education_certs;
                    break;
                default:
                    valueA = a.overall_score;
                    valueB = b.overall_score;
            }

            if (this.currentSort.direction === 'desc') {
                return valueB - valueA;
            } else {
                return valueA - valueB;
            }
        });

        this.updateDisplay();
    }

    applySearch() {
        const searchTerm = this.searchInput ? this.searchInput.value : '';
        this.currentFilters.search = searchTerm;
        this.applyFilters();
    }

    updateStatistics() {
        if (!this.filteredResults.length) return;

        // Total candidates
        if (this.totalCandidates) {
            this.totalCandidates.textContent = this.filteredResults.length;
        }

        // Average score
        const avgScore = this.filteredResults.reduce((sum, r) => sum + r.overall_score, 0) / this.filteredResults.length;
        if (this.averageScore) {
            this.averageScore.textContent = `${Math.round(avgScore)}%`;
        }

        // Shortlisted count (80% and above)
        const shortlisted = this.filteredResults.filter(r => r.overall_score >= 80).length;
        if (this.shortlistedCount) {
            this.shortlistedCount.textContent = shortlisted;
        }
    }

    updateCharts() {
        this.updateScoreDistributionChart();
        this.updateSkillsChart();
    }

    updateScoreDistributionChart() {
        if (!this.scoreDistributionChart) return;

        const distribution = [0, 0, 0, 0, 0]; // 0-20, 21-40, 41-60, 61-80, 81-100

        this.filteredResults.forEach(result => {
            const score = result.overall_score;
            if (score <= 20) distribution[0]++;
            else if (score <= 40) distribution[1]++;
            else if (score <= 60) distribution[2]++;
            else if (score <= 80) distribution[3]++;
            else distribution[4]++;
        });

        // Update or create chart
        if (window.scoreDistChart) {
            window.scoreDistChart.data.datasets[0].data = distribution;
            window.scoreDistChart.update();
        } else {
            const ctx = this.scoreDistributionChart.getContext('2d');
            window.scoreDistChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'],
                    datasets: [{
                        label: 'Number of Candidates',
                        data: distribution,
                        backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#28a745']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        }
    }

    updateSkillsChart() {
        if (!this.skillsChart) return;

        // Aggregate skills data
        const skillsCount = {};
        this.filteredResults.forEach(result => {
            if (result.evidence?.matched_skills) {
                result.evidence.matched_skills.forEach(skill => {
                    skillsCount[skill] = (skillsCount[skill] || 0) + 1;
                });
            }
        });

        // Get top 10 skills
        const topSkills = Object.entries(skillsCount)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10);

        // Update or create chart
        if (window.skillsChart) {
            window.skillsChart.data.labels = topSkills.map(([skill]) => skill);
            window.skillsChart.data.datasets[0].data = topSkills.map(([, count]) => count);
            window.skillsChart.update();
        } else {
            const ctx = this.skillsChart.getContext('2d');
            window.skillsChart = new Chart(ctx, {
                type: 'horizontalBar',
                data: {
                    labels: topSkills.map(([skill]) => skill),
                    datasets: [{
                        label: 'Count',
                        data: topSkills.map(([, count]) => count),
                        backgroundColor: '#007bff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        }
    }

    async viewDetails(resultId) {
        try {
            const response = await fetch(`/recruiter/api/candidate/${resultId}/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load candidate details');
            }

            const data = await response.json();
            this.showCandidateModal(data);

        } catch (error) {
            console.error('Error loading candidate details:', error);
            this.showError('Failed to load candidate details');
        }
    }

    showCandidateModal(candidate) {
        const modal = document.getElementById('candidateModal');
        if (!modal) return;

        const modalBody = modal.querySelector('#candidateModalBody');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="candidate-details">
                    <h5>${candidate.filename}</h5>
                    <div class="mb-3">
                        <strong>Overall Score:</strong>
                        <span class="score-badge ${this.getScoreClass(candidate.overall_score)}">
                            ${candidate.overall_score}%
                        </span>
                    </div>

                    <div class="score-breakdown-details mb-3">
                        <h6>Score Breakdown:</h6>
                        <div class="row">
                            <div class="col-6">
                                <div class="detail-item">
                                    <span>Skills Match:</span>
                                    <strong>${candidate.component_scores.skills_match}/25</strong>
                                </div>
                                <div class="detail-item">
                                    <span>Experience:</span>
                                    <strong>${candidate.component_scores.experience_seniority}/20</strong>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="detail-item">
                                    <span>Education:</span>
                                    <strong>${candidate.component_scores.education_certs}/10</strong>
                                </div>
                                <div class="detail-item">
                                    <span>Confidence:</span>
                                    <strong>${candidate.confidence}%</strong>
                                </div>
                            </div>
                        </div>
                    </div>

                    ${candidate.evidence?.matched_requirements ? `
                    <div class="matched-requirements mb-3">
                        <h6>Matched Requirements:</h6>
                        <ul>
                            ${candidate.evidence.matched_requirements.map(req =>
                                `<li>${req.jd_text}</li>`
                            ).join('')}
                        </ul>
                    </div>
                    ` : ''}

                    ${candidate.evidence?.missing_requirements ? `
                    <div class="missing-requirements">
                        <h6>Missing Requirements:</h6>
                        <ul>
                            ${candidate.evidence.missing_requirements.map(req =>
                                `<li>${req.jd_text}</li>`
                            ).join('')}
                        </ul>
                    </div>
                    ` : ''}
                </div>
            `;
        }

        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    async shortlist(resultId) {
        try {
            const response = await fetch(`/recruiter/api/shortlist/${resultId}/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to shortlist candidate');
            }

            const data = await response.json();
            if (data.success) {
                this.showSuccess('Candidate shortlisted successfully!');
                // Update UI
                const resultElement = document.querySelector(`[data-result-id="${resultId}"]`);
                if (resultElement) {
                    resultElement.classList.add('shortlisted');
                }
            } else {
                throw new Error(data.error || 'Failed to shortlist');
            }

        } catch (error) {
            console.error('Error shortlisting candidate:', error);
            this.showError('Failed to shortlist candidate');
        }
    }

    downloadResume(resultId) {
        window.open(`/recruiter/download/${resultId}/`, '_blank');
    }

    exportToCSV() {
        const csv = this.generateCSV();
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `candidate_results_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    generateCSV() {
        const headers = [
            'Rank', 'Filename', 'Overall Score', 'Skills Match',
            'Experience', 'Education', 'Confidence', 'Created At'
        ];

        const rows = this.filteredResults.map((result, index) => [
            index + 1,
            result.filename,
            result.overall_score,
            result.component_scores.skills_match,
            result.component_scores.experience_seniority,
            result.component_scores.education_certs,
            result.confidence,
            this.formatDate(result.created_at)
        ]);

        return [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');
    }

    exportToPDF() {
        // This would require a PDF library like jsPDF
        // For now, just show a message
        this.showInfo('PDF export will be available soon');
    }

    startRealTimeUpdates() {
        // Check for updates every 30 seconds
        setInterval(() => {
            this.checkForUpdates();
        }, 30000);
    }

    async checkForUpdates() {
        try {
            const response = await fetch('/recruiter/api/results-updates/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.has_updates) {
                    this.loadResults();
                    this.showInfo('Results have been updated');
                }
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
    }

    // Utility methods
    getScoreClass(score) {
        if (score >= 80) return 'score-excellent';
        if (score >= 60) return 'score-good';
        if (score >= 40) return 'score-fair';
        return 'score-poor';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
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

    debounce(func, wait) {
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

    showError(message) {
        this.showMessage(message, 'error');
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showInfo(message) {
        this.showMessage(message, 'info');
    }

    showMessage(message, type) {
        // Create or update message container
        let messageContainer = document.getElementById('resultsMessage');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.id = 'resultsMessage';
            messageContainer.className = 'alert';
            const resultsContainer = document.querySelector('.results-table') || document.body;
            resultsContainer.insertBefore(messageContainer, resultsContainer.firstChild);
        }

        messageContainer.textContent = message;
        messageContainer.className = `alert alert-${type}`;
        messageContainer.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageContainer.style.display = 'none';
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.resultsDisplay = new ResultsDisplay();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ResultsDisplay;
}