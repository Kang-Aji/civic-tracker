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
    } catch (error) {
        console.error('Error initializing:', error);
        addressInput.placeholder = 'Enter address (Places API not available)';
    }
});

async function loadAllOfficials() {
    const resultsDiv = document.getElementById('results');
    try {
        resultsDiv.innerHTML = '<p class="loading">Loading all US elected officials...</p>';
        const response = await fetch('/all_officials');
        const data = await response.json();
        
        if (response.ok) {
            allOfficials = data.officials;
            log('Loaded all officials:', {
                count: allOfficials.length,
                sample: allOfficials.slice(0, 3)
            });
            displayResults({ officials: allOfficials });
        } else {
            resultsDiv.innerHTML = `<p class="error-message">${data.error}</p>`;
            log('Error loading officials:', data.error);
        }
    } catch (error) {
        console.error('Error loading all officials:', error);
        resultsDiv.innerHTML = '<p class="error-message">Error loading officials list</p>';
    }
}

async function searchRepresentatives() {
    const addressInput = document.getElementById('address');
    const resultsDiv = document.getElementById('results');
    const address = addressInput.value.trim();

    if (!address) {
        // If address is cleared, show all officials
        displayResults({ officials: allOfficials });
        return;
    }

    try {
        resultsDiv.innerHTML = '<p class="loading">Searching representatives for your area...</p>';
        log('Searching representatives for address:', address);

        const response = await fetch(`/search_representatives?address=${encodeURIComponent(address)}`);
        const data = await response.json();

        log('API Response:', data);

        if (response.ok) {
            // Filter the display to show only officials for this address
            filterAndDisplayResults(data);
        } else {
            resultsDiv.innerHTML = `<p class="error-message">${data.error}</p>`;
            log('API Error:', data.error);
        }
    } catch (error) {
        console.error('Error fetching data:', error);
        resultsDiv.innerHTML = '<p class="error-message">An error occurred while fetching the data</p>';
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
        resultsDiv.innerHTML = '<p class="error-message">No officials found for this address</p>';
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

    filteredOfficials.forEach(official => {
        const card = createOfficialCard(official);
        resultsDiv.appendChild(card);
    });
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    if (!data.officials || data.officials.length === 0) {
        resultsDiv.innerHTML = '<p class="error-message">No officials found</p>';
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

    data.officials.forEach(official => {
        const card = createOfficialCard(official);
        resultsDiv.appendChild(card);
    });
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
    `;

    card.innerHTML = content;
    return card;
}
