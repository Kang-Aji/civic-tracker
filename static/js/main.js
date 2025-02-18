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
        <button class="view-actions-btn" onclick="showActionsModal(${JSON.stringify(official)})">
            View Actions
        </button>
    `;

    card.innerHTML = content;
    return card;
}

// Debounce function to limit API calls
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

// Cache DOM elements
const resultsContainer = document.getElementById('results');
const actionsModal = document.getElementById('actionsModal');
const modalClose = document.querySelector('.close');
const timeFilter = document.getElementById('timeFilter');
const actionTypeFilter = document.getElementById('actionTypeFilter');
const actionsContent = document.getElementById('actionsContent');
const loadingSpinner = document.getElementById('actionsLoading');
const errorMessage = document.getElementById('actionsError');

let currentOfficial = null;
let actionsData = null;

// Create a document fragment for better performance
function createOfficialCards(officials) {
    const fragment = document.createDocumentFragment();
    
    officials.forEach(official => {
        const card = document.createElement('div');
        card.className = 'official-card';
        
        const content = `
            <h3>${official.name}</h3>
            <p class="office">${official.office}</p>
            ${official.party ? `<p class="party">${official.party}</p>` : ''}
            <div class="contact-info">
                ${official.phones ? `<p>📞 ${official.phones[0]}</p>` : ''}
                ${official.emails ? `<p>✉️ <a href="mailto:${official.emails[0]}">${official.emails[0]}</a></p>` : ''}
                ${official.urls ? `<p>🌐 <a href="${official.urls[0]}" target="_blank">Official Website</a></p>` : ''}
            </div>
            <button class="view-actions-btn" onclick="showActionsModal(${JSON.stringify(official)})">
                View Actions
            </button>
        `;
        
        card.innerHTML = content;
        fragment.appendChild(card);
    });
    
    return fragment;
}

// Optimize the display of actions
function displayActions(actions) {
    actionsData = actions;
    
    const timeline = actionsContent.querySelector('.actions-timeline');
    const summaryCards = {
        votes: actionsContent.querySelector('.summary-card.votes .count'),
        press_releases: actionsContent.querySelector('.summary-card.press-releases .count'),
        news: actionsContent.querySelector('.summary-card.news .count')
    };
    
    // Reset counts using a single loop
    Object.values(summaryCards).forEach(card => card.textContent = '0');
    
    // Create action counts and timeline items in a single pass
    const actionsByType = {};
    const timelineFragment = document.createDocumentFragment();
    
    actions.forEach(action => {
        // Update counts
        actionsByType[action.action_type] = (actionsByType[action.action_type] || 0) + 1;
        
        // Create timeline item
        const item = document.createElement('div');
        item.className = `timeline-item ${action.action_type}`;
        item.dataset.type = action.action_type;
        
        const date = new Date(action.date);
        item.innerHTML = `
            <div class="date">${date.toLocaleDateString()}</div>
            <div class="title">${action.action_type.replace('_', ' ').toUpperCase()}</div>
            <div class="description">${action.description}</div>
            ${action.source_url ? `
                <div class="source">
                    <a href="${action.source_url}" target="_blank" rel="noopener noreferrer">View Source</a>
                </div>
            ` : ''}
        `;
        
        timelineFragment.appendChild(item);
    });
    
    // Update summary cards
    Object.entries(actionsByType).forEach(([type, count]) => {
        if (summaryCards[type]) {
            summaryCards[type].textContent = count;
        }
    });
    
    // Clear and update timeline in a single operation
    timeline.innerHTML = '';
    timeline.appendChild(timelineFragment);
    
    actionsContent.style.display = 'block';
    filterActions();
}

// Optimize filtering
function filterActions() {
    const selectedType = actionTypeFilter.value;
    const timelineItems = document.querySelectorAll('.timeline-item');
    
    // Use classList for better performance
    timelineItems.forEach(item => {
        item.classList.toggle('hidden', selectedType !== 'all' && item.dataset.type !== selectedType);
    });
}

// Debounced search function
const debouncedSearch = debounce(() => {
    const address = document.getElementById('address').value;
    if (address) {
        searchRepresentatives(address);
    }
}, 300);

// Event listeners
modalClose.onclick = () => {
    actionsModal.style.display = 'none';
    currentOfficial = null;
    actionsData = null;
};

window.onclick = (event) => {
    if (event.target === actionsModal) {
        actionsModal.style.display = 'none';
        currentOfficial = null;
        actionsData = null;
    }
};

timeFilter.onchange = () => {
    if (currentOfficial) {
        fetchOfficialActions(currentOfficial);
    }
};

actionTypeFilter.onchange = filterActions;

// Actions Modal
function showActionsModal(official) {
    currentOfficial = official;
    document.getElementById('modalTitle').textContent = `${official.name}'s Actions`;
    actionsModal.style.display = 'block';
    fetchOfficialActions(official);
}

async function fetchOfficialActions(official) {
    const actionsContent = document.getElementById('actionsContent');
    const loadingSpinner = document.getElementById('actionsLoading');
    const errorMessage = document.getElementById('actionsError');
    
    try {
        actionsContent.style.display = 'none';
        loadingSpinner.style.display = 'block';
        errorMessage.style.display = 'none';
        
        const days = timeFilter.value;
        const response = await fetch(`/official/actions/${encodeURIComponent(official.name)}?days=${days}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch actions');
        }
        
        displayActions(data.actions);
        
    } catch (error) {
        console.error('Error fetching actions:', error);
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
        actionsContent.style.display = 'none';
    } finally {
        loadingSpinner.style.display = 'none';
    }
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
