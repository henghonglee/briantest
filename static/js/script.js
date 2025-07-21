// Global variables
let isSearching = false;

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

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize page
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
});