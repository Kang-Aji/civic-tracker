// Initialize Google Places Autocomplete
let autocomplete;
let allOfficials = [];
const DEBUG = document.body.getAttribute('data-debug') === 'true';

function log(...args) {
    if (DEBUG) {
        console.log(...args);
    }
}

// Load all officials when the page loads
document.addEventListener('DOMContentLoaded', async function() {
    const addressInput = document.getElementById('address');
    const resultsDiv = document.getElementById('results');
    
    try {
        // Initialize the autocomplete object
        log('Initializing Places Autocomplete...');
        autocomplete = new google.maps.places.Autocomplete(addressInput, {
            componentRestrictions: { country: 'us' },
            fields: ['formatted_address', 'address_components'],
            types: ['address']
        });

        // Handle place selection
        autocomplete.addListener('place_changed', function() {
            const place = autocomplete.getPlace();
            log('Place selected:', place);
            if (place.formatted_address) {
                addressInput.value = place.formatted_address;
                searchRepresentatives();
            }
        });

        log('Places Autocomplete initialized successfully');
        
        // Load all officials
        await loadAllOfficials();
        
        // Initialize search functionality
        initAutocomplete();
        
        // Add event listener for the search button
        document.querySelector('button').addEventListener('click', function() {
            const address = document.getElementById('address').value;
            if (address) {
                searchRepresentatives(address);
            }
        });
        
        // Add event listener for Enter key in address input
        document.getElementById('address').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const address = this.value;
                if (address) {
                    searchRepresentatives(address);
                }
            }
        });
    } catch (error) {
        console.error('Error initializing:', error);
        addressInput.placeholder = 'Enter address (Places API not available)';
    }
});

async function loadAllOfficials() {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch('/all_officials');
        const data = await response.json();
        
        if (data.error) {
            resultsDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        displayResults({
            officials: data,
            counts: {
                federal: data.filter(o => o.offices.some(office => 
                    office.includes('United States') || office.includes('President') || office.includes('Congress')
                )).length,
                state: data.filter(o => o.offices.some(office => 
                    office.includes('State') || office.includes('Governor') || office.includes('Senator') || office.includes('Assembly')
                )).length,
                local: data.filter(o => o.offices.every(office => 
                    !office.includes('United States') && !office.includes('President') && !office.includes('Congress') &&
                    !office.includes('State') && !office.includes('Governor') && !office.includes('Senator') && !office.includes('Assembly')
                )).length
            }
        });
        
    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = '<div class="error">Error loading officials. Please try again.</div>';
    }
}

async function searchRepresentatives() {
    const addressInput = document.getElementById('address');
    const resultsDiv = document.getElementById('results');
    const address = addressInput.value.trim();

    if (!address) {
        // If address is cleared, show all officials
        displayResults({
            officials: allOfficials,
            counts: {
                federal: allOfficials.filter(o => o.offices.some(office => 
                    office.includes('United States') || office.includes('President') || office.includes('Congress')
                )).length,
                state: allOfficials.filter(o => o.offices.some(office => 
                    office.includes('State') || office.includes('Governor') || office.includes('Senator') || office.includes('Assembly')
                )).length,
                local: allOfficials.filter(o => o.offices.every(office => 
                    !office.includes('United States') && !office.includes('President') && !office.includes('Congress') &&
                    !office.includes('State') && !office.includes('Governor') && !office.includes('Senator') && !office.includes('Assembly')
                )).length
            }
        });
        return;
    }

    try {
        resultsDiv.innerHTML = '<div class="loading-spinner"></div>';
        log('Searching representatives for address:', address);

        const response = await fetch(`/search?address=${encodeURIComponent(address)}`);
        const data = await response.json();

        log('API Response:', data);

        if (data.error) {
            resultsDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        displayResults(data);
        
    } catch (error) {
        console.error('Error fetching data:', error);
        resultsDiv.innerHTML = '<div class="error">An error occurred while fetching the data</div>';
    }
}

function normalizeOfficeName(name) {
    return name.toLowerCase().trim();
}

function findMatchingOffices(official1, official2) {
    const offices1 = official1.offices || [];
    const offices2 = official2.offices || [];
    
    return offices1.some(office1 => 
        offices2.some(office2 => 
            normalizeOfficeName(office1) === normalizeOfficeName(office2)
        )
    );
}

function filterAndDisplayResults(addressData) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    if (!addressData.officials || !addressData.offices) {
        resultsDiv.innerHTML = '<div class="error-message">No officials found for this address</div>';
        return;
    }

    log('Processing address data:', {
        officialsCount: addressData.officials.length,
        officesCount: addressData.offices.length
    });

    // Create a map of officials from the address search with their offices
    const addressOfficials = addressData.officials.map((official, index) => {
        const offices = addressData.offices
            .filter(office => office.officialIndices.includes(index))
            .map(office => office.name);
        return { ...official, offices };
    });

    log('Processed address officials:', {
        count: addressOfficials.length,
        sample: addressOfficials.slice(0, 2)
    });

    // Filter and mark all officials
    const filteredOfficials = allOfficials.map(official => {
        // Check if this official is in the address results
        const matchingOfficial = addressOfficials.find(addressOfficial => 
            official.name === addressOfficial.name && 
            findMatchingOffices(official, addressOfficial)
        );

        const isLocal = !!matchingOfficial;
        
        if (DEBUG && isLocal) {
            log('Found local official:', {
                name: official.name,
                offices: official.offices
            });
        }

        return {
            ...official,
            isLocal
        };
    });

    // Sort officials: local ones first, then by level
    filteredOfficials.sort((a, b) => {
        if (a.isLocal !== b.isLocal) {
            return a.isLocal ? -1 : 1;
        }

        // Secondary sort by office level (federal > state > local)
        const getOfficeLevel = (official) => {
            const offices = official.offices || [];
            const officesStr = offices.join(' ').toLowerCase();
            if (officesStr.includes('united states') || officesStr.includes('president')) return 0;
            if (officesStr.includes('state')) return 1;
            return 2;
        };

        return getOfficeLevel(a) - getOfficeLevel(b);
    });

    // Count officials by level
    const counts = {
        local: filteredOfficials.filter(o => o.isLocal).length,
        total: filteredOfficials.length,
        federal: filteredOfficials.filter(o => {
            const offices = (o.offices || []).join(' ').toLowerCase();
            return offices.includes('united states') || offices.includes('president');
        }).length,
        state: filteredOfficials.filter(o => {
            const offices = (o.offices || []).join(' ').toLowerCase();
            return offices.includes('state');
        }).length
    };

    log('Officials counts:', counts);

    // Display results with a summary
    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'results-summary';
    summaryDiv.innerHTML = `
        <p>Found ${counts.local} representative${counts.local !== 1 ? 's' : ''} for your area</p>
        <p>Showing all ${counts.total} officials:</p>
        <ul>
            <li>${counts.federal} Federal Officials</li>
            <li>${counts.state} State Officials</li>
            <li>${counts.total - counts.federal - counts.state} Local Officials</li>
        </ul>
        <p class="note">Your local representatives are highlighted in green</p>
    `;
    resultsDiv.appendChild(summaryDiv);

    const fragment = document.createDocumentFragment();
    filteredOfficials.forEach(official => {
        const card = createOfficialCard(official);
        fragment.appendChild(card);
    });
    resultsDiv.appendChild(fragment);
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';
    
    if (!data.officials || data.officials.length === 0) {
        resultsDiv.innerHTML = '<div class="error-message">No officials found</div>';
        return;
    }

    // Count officials by level
    const counts = {
        total: data.officials.length,
        federal: data.officials.filter(o => {
            const offices = (o.offices || []).join(' ').toLowerCase();
            return offices.includes('united states') || offices.includes('president');
        }).length,
        state: data.officials.filter(o => {
            const offices = (o.offices || []).join(' ').toLowerCase();
            return offices.includes('state');
        }).length
    };

    log('Displaying all officials:', counts);

    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'results-summary';
    summaryDiv.innerHTML = `
        <p>Showing all ${counts.total} US elected officials:</p>
        <ul>
            <li>${counts.federal} Federal Officials</li>
            <li>${counts.state} State Officials</li>
            <li>${counts.total - counts.federal - counts.state} Local Officials</li>
        </ul>
    `;
    resultsDiv.appendChild(summaryDiv);

    const fragment = document.createDocumentFragment();
    data.officials.forEach(official => {
        const card = createOfficialCard(official);
        fragment.appendChild(card);
    });
    resultsDiv.appendChild(fragment);
}

function createOfficialCard(official) {
    console.log('Creating card for official:', official);
    const card = document.createElement('div');
    card.className = `official-card${official.isLocal ? ' local-official' : ''}`;

    // Determine official level
    const officesStr = (official.offices || []).join(' ').toLowerCase();
    let level = 'Local';
    if (officesStr.includes('united states') || officesStr.includes('president')) {
        level = 'Federal';
    } else if (officesStr.includes('state')) {
        level = 'State';
    }

    // Create action button
    const actionButton = document.createElement('button');
    actionButton.className = 'view-actions-btn';
    actionButton.textContent = 'View Actions';
    actionButton.onclick = () => showActionTracker(official);

    const content = `
        ${official.photoUrl ? `<img src="${official.photoUrl}" alt="${official.name}" class="official-photo" onerror="this.style.display='none'">` : ''}
        <h3>${official.name}</h3>
        <p class="official-level ${level.toLowerCase()}-level">${level} Official</p>
        <p><strong>Offices:</strong> ${official.offices ? official.offices.join(', ') : 'Not specified'}</p>
        ${official.party ? `<p><strong>Party:</strong> ${official.party}</p>` : ''}
        ${official.phones ? `<p><strong>Phone:</strong> ${official.phones[0]}</p>` : ''}
        ${official.emails ? `<p><strong>Email:</strong> ${official.emails[0]}</p>` : ''}
        ${official.urls ? `<p><a href="${official.urls[0]}" target="_blank" rel="noopener">Official Website</a></p>` : ''}
        ${official.isLocal ? '<div class="local-badge">Your Representative</div>' : ''}
        <div class="action-buttons"></div>
    `;

    card.innerHTML = content;
    
    // Add button to the action-buttons div after setting innerHTML
    const actionButtons = card.querySelector('.action-buttons');
    actionButtons.appendChild(actionButton);

    console.log('Created card HTML:', card.outerHTML);
    return card;
}

let currentOfficialTracker = null;
let isRefreshingTracker = false;

// Initialize UI elements when the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    // Hide the action tracker section initially
    const actionTrackerSection = document.getElementById('action-tracker');
    console.log('Action Tracker Section:', actionTrackerSection);
    if (actionTrackerSection) {
        actionTrackerSection.style.display = 'none';
    }
});

function showActionTracker(official) {
    console.log('showActionTracker called with:', official);
    
    if (!official || !official.name) {
        console.error('Invalid official data:', official);
        return;
    }
    
    // Get or create the action tracker section
    let actionTrackerSection = document.getElementById('action-tracker');
    console.log('Looking for action tracker section...');
    if (!actionTrackerSection) {
        console.log('Creating action tracker section...');
        actionTrackerSection = document.createElement('div');
        actionTrackerSection.id = 'action-tracker';
        actionTrackerSection.className = 'action-tracker-section';
        document.querySelector('.container').appendChild(actionTrackerSection);
    }
    console.log('Found/created action tracker section:', actionTrackerSection);
    
    // Hide the results section
    const resultsSection = document.getElementById('results');
    if (!resultsSection) {
        console.error('Results section not found in DOM');
        return;
    }
    console.log('Found results section:', resultsSection);
    
    // Show action tracker and hide results
    actionTrackerSection.style.display = 'block';
    resultsSection.style.display = 'none';
    
    // Update action tracker content
    actionTrackerSection.innerHTML = `
        <div class="action-tracker-header">
            <div class="header-top">
                <button class="back-button" onclick="hideActionTracker()">← Back to Results</button>
                <h2>Actions - ${official.name}</h2>
            </div>
            <div class="action-tracker-controls">
                <div class="filter-group">
                    <label class="filter-label">Time Period:</label>
                    <select class="filter-select" id="time-filter-tracker" onchange="filterActionsTracker()">
                        <option value="7">Last 7 days</option>
                        <option value="30" selected>Last 30 days</option>
                        <option value="90">Last 90 days</option>
                        <option value="180">Last 6 months</option>
                        <option value="365">Last year</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">Action Type:</label>
                    <select class="filter-select" id="type-filter-tracker" onchange="filterActionsTracker()">
                        <option value="all" selected>All Actions</option>
                        <option value="bill">Bills</option>
                        <option value="press-release">Press Releases</option>
                        <option value="news">News</option>
                    </select>
                </div>
                <button class="refresh-button" onclick="refreshActionsTracker()" id="refresh-button-tracker">
                    <span>Refresh</span>
                    <span class="loading-spinner" style="display: none;"></span>
                </button>
            </div>
        </div>
        <div id="actions-container-tracker">
            <div class="loading-spinner"></div>
        </div>
    `;
    
    // Store the current official
    currentOfficialTracker = official;
    console.log('Set currentOfficialTracker:', currentOfficialTracker);
    
    // Load initial actions
    loadActionsTracker();
}

function hideActionTracker() {
    // Hide the action tracker section
    const actionTrackerSection = document.getElementById('action-tracker');
    if (actionTrackerSection) {
        actionTrackerSection.style.display = 'none';
    }
    
    // Show the results section
    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        resultsSection.style.display = 'block';
    }
}

async function loadActionsTracker() {
    if (!currentOfficialTracker) return;
    
    const actionsContainer = document.getElementById('actions-container-tracker');
    const timeFilter = document.getElementById('time-filter-tracker').value;
    const typeFilter = document.getElementById('type-filter-tracker').value;
    
    try {
        // Show loading state
        actionsContainer.innerHTML = '<div class="loading-spinner"></div>';
        
        // Properly encode the name for URL usage
        const encodedName = encodeURIComponent(currentOfficialTracker.name)
            .replace(/'/g, '%27')  // Ensure single quotes are properly encoded
            .replace(/\(/g, '%28') // Ensure parentheses are properly encoded
            .replace(/\)/g, '%29')
            .replace(/\./g, '%2E'); // Ensure periods are properly encoded
        
        const response = await fetch(`/api/officials/${encodedName}/actions?days=${timeFilter}&type=${typeFilter}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load actions');
        }
        
        if (!data.actions || data.actions.length === 0) {
            actionsContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <h3>No Actions Found</h3>
                    <p>No recent actions found for this time period and filter.</p>
                    <button class="refresh-button" onclick="refreshActionsTracker()">
                        Refresh Actions
                    </button>
                </div>
            `;
            return;
        }
        
        actionsContainer.innerHTML = data.actions.map(action => `
            <div class="action-card">
                <div class="action-date">${formatDate(action.date)}</div>
                <div class="action-type ${getActionTypeClass(action.type)}">${formatActionType(action.type)}</div>
                <div class="action-content">${action.description}</div>
                ${action.source ? `
                    <div class="action-source">
                        Source: <a href="${action.source}" target="_blank" rel="noopener noreferrer">View Details</a>
                    </div>
                ` : ''}
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading actions:', error);
        actionsContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h3>Error Loading Actions</h3>
                <p>There was an error loading the actions. Please try again later.</p>
                <p class="error-details">${error.message}</p>
                <button class="refresh-button" onclick="refreshActionsTracker()">
                    Try Again
                </button>
            </div>
        `;
    }
}

function getActionTypeClass(type) {
    const typeMap = {
        'bill_introduced': 'bill',
        'bill_action': 'bill',
        'vote': 'bill',
        'press_release': 'press-release',
        'news_mention': 'news'
    };
    return typeMap[type] || type;
}

function formatActionType(type) {
    const typeMap = {
        'bill_introduced': 'Bill Introduced',
        'bill_action': 'Bill Action',
        'vote': 'Vote',
        'press_release': 'Press Release',
        'news_mention': 'News'
    };
    return typeMap[type] || type.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

async function refreshActionsTracker() {
    if (isRefreshingTracker) return;
    
    const refreshButton = document.getElementById('refresh-button-tracker');
    const spinner = refreshButton.querySelector('.loading-spinner');
    
    try {
        isRefreshingTracker = true;
        refreshButton.disabled = true;
        spinner.style.display = 'inline-block';
        
        // Call API to refresh actions
        const response = await fetch(`/api/officials/${encodeURIComponent(currentOfficialTracker.name)}/actions/refresh`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to refresh actions');
        }
        
        // Show success message
        const actionsContainer = document.getElementById('actions-container-tracker');
        actionsContainer.innerHTML = `
            <div class="success-message">
                <p>Successfully refreshed actions!</p>
                <p>Found ${data.count} new actions.</p>
            </div>
        `;
        
        // Reload actions after a short delay
        setTimeout(() => loadActionsTracker(), 2000);
        
    } catch (error) {
        console.error('Error refreshing actions:', error);
        alert(`Error refreshing actions: ${error.message}`);
    } finally {
        isRefreshingTracker = false;
        refreshButton.disabled = false;
        spinner.style.display = 'none';
    }
}

function filterActionsTracker() {
    loadActionsTracker();
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

// Initialize Google Places Autocomplete
function initAutocomplete() {
    const addressInput = document.getElementById('address');
    const autocomplete = new google.maps.places.Autocomplete(addressInput, {
        types: ['address'],
        componentRestrictions: { country: 'us' }
    });
    
    autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (place.formatted_address) {
            searchRepresentatives(place.formatted_address);
        }
    });
}
