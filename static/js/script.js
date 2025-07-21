// Global variables
let isSearching = false;
let selectedExcelFile = null;

// DOM elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('resultsContainer');
const resultsMeta = document.getElementById('resultsMeta');
const emptyState = document.getElementById('emptyState');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const resultsCount = document.getElementById('resultsCount');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    setupTabSwitching();
    
    // Search button click
    searchBtn.addEventListener('click', performSearch);
    
    // Enter key in search input
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    // Example query buttons
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const query = this.getAttribute('data-query');
            searchInput.value = query;
            performSearch();
        });
    });
    
    // Focus search input on page load
    searchInput.focus();
});

// Main search function
async function performSearch() {
    const query = searchInput.value.trim();
    const topK = parseInt(resultsCount.value);
    
    if (!query) {
        showError('Please enter a search query');
        return;
    }
    
    if (isSearching) {
        return;
    }
    
    // Show loading state
    setLoadingState(true);
    hideAllSections();
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                top_k: topK
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data);
        } else {
            showError(data.error || 'Search failed');
        }
        
    } catch (error) {
        console.error('Search error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        setLoadingState(false);
    }
}

// Display search results
function displayResults(data) {
    hideAllSections();
    
    if (data.results.length === 0) {
        showError('No results found for your query. Try different keywords or check spelling.');
        return;
    }
    
    // Update results metadata
    resultsMeta.innerHTML = `
        <div>
            <strong>${data.total_results}</strong> results found in <strong>${data.search_time}s</strong>
        </div>
        <div class="query-display">
            Query: "<em>${escapeHtml(data.query)}</em>"
        </div>
    `;
    
    // Clear and populate results container
    resultsContainer.innerHTML = '';
    
    data.results.forEach((result, index) => {
        const resultElement = createResultElement(result, index + 1);
        resultsContainer.appendChild(resultElement);
    });
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Fetch probability scores asynchronously
    fetchProbabilityScores(data.query, data.results);
}

// Create individual result element
function createResultElement(result, rank) {
    const div = document.createElement('div');
    const matchTypeClass = result.match_type === 'exact' ? 'exact-match' : 'fuzzy-match';
    const matchIcon = result.match_type === 'exact' ? 'fas fa-star' : 'fas fa-chart-line';
    const matchLabel = result.match_type === 'exact' ? 'EXACT MATCH' : 'FUZZY MATCH';
    
    div.className = `result-item ${matchTypeClass}`;
    div.innerHTML = `
        <div class="result-header">
            <div>
                <div class="result-code">${rank}. [${escapeHtml(result.order_code)}] - ${escapeHtml(result.description)}</div>
            </div>
            <div class="result-actions">
                <div class="result-score">
                    <i class="${matchIcon}"></i>
                    ${matchLabel} (${result.probability})
                </div>
                ${result.match_type !== 'exact' ? `
                    <button class="train-btn" onclick="addToTraining('${escapeHtml(result.order_code)}', '${escapeHtml(result.description)}')">
                        <i class="fas fa-plus"></i>
                        Add to Training
                    </button>
                ` : ''}
            </div>
        </div>
        
        <div class="result-details">
            ${result.training_query ? `
                <div class="detail-item">
                    <span class="detail-label">Training Query</span>
                    <span class="detail-value training-query">${escapeHtml(result.training_query)}</span>
                </div>
            ` : ''}
            
            <div class="detail-item">
                <span class="detail-label">Scores</span>
                <span class="detail-value">
                    TF-IDF: ${result.tfidf_score} | Fuzzy: ${result.fuzzy_score} | Model: <span class="prob-score" data-order-code="${escapeHtml(result.order_code)}"><i class="fas fa-spinner fa-spin"></i></span>
                </span>
            </div>
        </div>
    `;
    
    return div;
}

// Set loading state
function setLoadingState(loading) {
    isSearching = loading;
    
    if (loading) {
        searchBtn.disabled = true;
        searchBtn.querySelector('.btn-text').style.display = 'none';
        searchBtn.querySelector('.btn-spinner').style.display = 'inline-block';
    } else {
        searchBtn.disabled = false;
        searchBtn.querySelector('.btn-text').style.display = 'inline';
        searchBtn.querySelector('.btn-spinner').style.display = 'none';
    }
}

// Show error message
function showError(message) {
    hideAllSections();
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
}

// Clear error and show empty state
function clearError() {
    hideAllSections();
    emptyState.style.display = 'block';
    searchInput.focus();
}

// Hide all sections
function hideAllSections() {
    resultsSection.style.display = 'none';
    emptyState.style.display = 'none';
    errorSection.style.display = 'none';
}

// Fetch probability scores asynchronously
async function fetchProbabilityScores(query, results) {
    try {
        const response = await fetch('/api/probability_score', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                results: results
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update each result with its probability score
            data.scores.forEach(scoreData => {
                const orderCode = scoreData.order_code;
                const probScore = scoreData.probability_score;
                const scoreElement = document.querySelector(`[data-order-code="${orderCode}"]`);
                
                if (scoreElement) {
                    if (probScore !== null) {
                        scoreElement.innerHTML = `${probScore}`;
                    } else {
                        scoreElement.innerHTML = `<span style="color: #d13438;">Error</span>`;
                    }
                }
            });
        } else {
            // Show error for all probability score elements
            document.querySelectorAll('.prob-score').forEach(element => {
                element.innerHTML = `<span style="color: #d13438;">N/A</span>`;
            });
        }
        
    } catch (error) {
        console.error('Probability scoring error:', error);
        // Show error for all probability score elements
        document.querySelectorAll('.prob-score').forEach(element => {
            element.innerHTML = `<span style="color: #d13438;">N/A</span>`;
        });
    }
}

// Add training example
async function addToTraining(orderCode, description) {
    const query = searchInput.value.trim();
    
    if (!query) {
        alert('No search query available to add to training');
        return;
    }
    
    if (confirm(`Add this training example?\n\nQuery: "${query}"\nResult: ${orderCode}\n\nThis will help improve future search results.`)) {
        try {
            const response = await fetch('/api/add_training', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    order_code: orderCode,
                    description: description
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('Training example added successfully! The model has been updated.');
            } else {
                alert(`Failed to add training example: ${data.error}`);
            }
            
        } catch (error) {
            console.error('Training error:', error);
            alert('Network error. Could not add training example.');
        }
    }
}

// Setup tab switching functionality
function setupTabSwitching() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and contents
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Show corresponding content
            const targetContent = targetTab === 'search' ? 
                document.getElementById('searchTab') : 
                document.getElementById('bulkTab');
            
            if (targetContent) {
                targetContent.classList.add('active');
            }
            
            // Focus search input when switching to search tab
            if (targetTab === 'search') {
                setTimeout(() => searchInput.focus(), 100);
            }
        });
    });
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Excel Upload Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Show empty state initially
    emptyState.style.display = 'block';
    
    // Check if search service is available
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'healthy') {
                showError('Search service is currently unavailable. Please try again later.');
            }
        })
        .catch(error => {
            console.warn('Health check failed:', error);
        });
    
    // Excel upload functionality
    setupExcelUpload();
});

function setupExcelUpload() {
    const uploadArea = document.getElementById('excelUploadArea');
    const fileInput = document.getElementById('excelFileInput');
    const selectedFile = document.getElementById('selectedFile');
    const fileName = document.getElementById('fileName');
    const processBtn = document.getElementById('processBtn');
    
    // Drag and drop handlers
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
            handleFileSelection(files[0]);
        }
    });
    
    // File input change
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });
}

function handleFileSelection(file) {
    if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
        showExcelStatus('Only Excel files (.xlsx, .xls) are supported.', 'error');
        return;
    }
    
    selectedExcelFile = file;
    
    // Update UI
    document.querySelector('.upload-content').style.display = 'none';
    document.getElementById('selectedFile').style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('processBtn').disabled = false;
    
    // Clear any previous status
    showExcelStatus('');
}

function clearSelectedFile() {
    selectedExcelFile = null;
    document.querySelector('.upload-content').style.display = 'block';
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('processBtn').disabled = true;
    document.getElementById('excelFileInput').value = '';
    showExcelStatus('');
}

async function processExcel() {
    if (!selectedExcelFile) {
        showExcelStatus('Please select an Excel file first.', 'error');
        return;
    }
    
    const processBtn = document.getElementById('processBtn');
    const btnText = processBtn.querySelector('.btn-text');
    const btnSpinner = processBtn.querySelector('.btn-spinner');
    
    // Show loading state
    processBtn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'inline-block';
    showExcelStatus('Processing your Excel file...', 'processing');
    
    try {
        const formData = new FormData();
        formData.append('file', selectedExcelFile);
        
        const response = await fetch('/api/process_excel', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showExcelStatus(
                `✅ ${data.message}. Processed ${data.sheets_processed.join(', ')}.`, 
                'success'
            );
            
            // Trigger download
            downloadExcelFile(data.file_data, selectedExcelFile.name);
        } else {
            showExcelStatus(`❌ ${data.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Excel processing error:', error);
        showExcelStatus('❌ Failed to process Excel file. Please try again.', 'error');
    } finally {
        // Reset button state
        processBtn.disabled = false;
        btnText.style.display = 'inline';
        btnSpinner.style.display = 'none';
    }
}

function downloadExcelFile(hexData, originalFileName) {
    try {
        // Convert hex string back to bytes
        const bytes = new Uint8Array(hexData.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
        const blob = new Blob([bytes], { 
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
        });
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // Generate filename
        const name = originalFileName.replace(/\.[^/.]+$/, '');
        a.download = `${name}_processed.xlsx`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Download error:', error);
        showExcelStatus('❌ Failed to download processed file.', 'error');
    }
}

function showExcelStatus(message, type = '') {
    const status = document.getElementById('excelStatus');
    status.textContent = message;
    status.className = `excel-status ${type}`;
    
    if (message && type !== 'processing') {
        setTimeout(() => {
            if (status.textContent === message) {
                status.textContent = '';
                status.className = 'excel-status';
            }
        }, 5000);
    }
}