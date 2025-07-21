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
        // Perform both searches simultaneously
        const [trainingResponse, catalogResponse] = await Promise.all([
            fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    top_k: topK
                })
            }),
            fetch('/api/catalog_search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    top_k: topK
                })
            })
        ]);
        
        const trainingData = await trainingResponse.json();
        const catalogData = await catalogResponse.json();
        
        // Display results with both training and catalog data
        displayCombinedResults(trainingData, catalogData, query);
        
    } catch (error) {
        console.error('Search error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        setLoadingState(false);
    }
}

// Display combined search results from training and catalog
function displayCombinedResults(trainingData, catalogData, query) {
    hideAllSections();
    
    const hasTrainingResults = trainingData.success && trainingData.results.length > 0;
    const hasCatalogResults = catalogData.success && catalogData.results.length > 0;
    
    if (!hasTrainingResults && !hasCatalogResults) {
        showError('No results found for your query. Try different keywords or check spelling.');
        return;
    }
    
    // Update results metadata
    const totalTime = Math.max(
        trainingData.success ? trainingData.search_time : 0,
        catalogData.success ? catalogData.search_time : 0
    );
    
    resultsMeta.innerHTML = `
        <div>
            Search completed in <strong>${totalTime.toFixed(3)}s</strong>
        </div>
        <div class="query-display">
            Query: "<em>${escapeHtml(query)}</em>"
        </div>
    `;
    
    // Update tab counts
    document.getElementById('trainingCount').textContent = hasTrainingResults ? trainingData.results.length : 0;
    document.getElementById('catalogCount').textContent = hasCatalogResults ? catalogData.results.length : 0;
    
    // Clear and populate training results
    resultsContainer.innerHTML = '';
    if (hasTrainingResults) {
        trainingData.results.forEach((result, index) => {
            const resultElement = createResultElement(result, index + 1, 'training');
            resultsContainer.appendChild(resultElement);
        });
        
        // Fetch probability scores for training results
        fetchProbabilityScores(query, trainingData.results);
    } else {
        resultsContainer.innerHTML = '<div class="no-results">No training matches found</div>';
    }
    
    // Clear and populate catalog results
    const catalogContainer = document.getElementById('catalogContainer');
    catalogContainer.innerHTML = '';
    if (hasCatalogResults) {
        catalogData.results.forEach((result, index) => {
            const resultElement = createResultElement(result, index + 1, 'catalog');
            catalogContainer.appendChild(resultElement);
        });
    } else {
        catalogContainer.innerHTML = '<div class="no-results">No catalog matches found</div>';
    }
    
    // Setup results tab switching
    setupResultsTabSwitching();
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Create individual result element
function createResultElement(result, rank, type = 'training') {
    const div = document.createElement('div');
    
    let matchTypeClass, matchIcon, matchLabel, scoreDisplay;
    
    if (type === 'catalog') {
        // Catalog results
        matchTypeClass = 'catalog-match';
        matchIcon = 'fas fa-database';
        matchLabel = 'CATALOG MATCH';
        scoreDisplay = `Fuzzy: ${result.fuzzy_score} | Field: ${result.match_field}`;
    } else {
        // Training results
        matchTypeClass = result.match_type === 'exact' ? 'exact-match' : 'fuzzy-match';
        matchIcon = result.match_type === 'exact' ? 'fas fa-star' : 'fas fa-chart-line';
        matchLabel = result.match_type === 'exact' ? 'EXACT MATCH' : 'FUZZY MATCH';
        scoreDisplay = `TF-IDF: ${result.tfidf_score} | Fuzzy: ${result.fuzzy_score} | Model: <span class="prob-score" data-order-code="${escapeHtml(result.order_code)}"><i class="fas fa-spinner fa-spin"></i></span>`;
    }
    
    div.className = `result-item ${matchTypeClass}`;
    div.innerHTML = `
        <div class="result-header">
            <div>
                <div class="result-code">${rank}. [${escapeHtml(result.order_code)}] - ${escapeHtml(result.description)}</div>
            </div>
            <div class="result-actions">
                <div class="result-score">
                    <i class="${matchIcon}"></i>
                    ${matchLabel} (${type === 'catalog' ? result.fuzzy_score : result.probability})
                </div>
                ${type === 'training' && result.match_type !== 'exact' ? `
                    <button class="train-btn" onclick="addToTraining('${escapeHtml(result.order_code)}', '${escapeHtml(result.description)}')">
                        <i class="fas fa-plus"></i>
                        Add to Training
                    </button>
                ` : ''}
                ${type === 'catalog' ? `
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
                    ${scoreDisplay}
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

// Setup results tab switching functionality
function setupResultsTabSwitching() {
    const resultsTabBtns = document.querySelectorAll('.results-tab-btn');
    const resultsTabContents = document.querySelectorAll('.results-tab-content');
    
    resultsTabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and contents
            resultsTabBtns.forEach(b => b.classList.remove('active'));
            resultsTabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Show corresponding content
            const targetContent = targetTab === 'training' ? 
                document.getElementById('trainingResults') : 
                document.getElementById('catalogResults');
            
            if (targetContent) {
                targetContent.classList.add('active');
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