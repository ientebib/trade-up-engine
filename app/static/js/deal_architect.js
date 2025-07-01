const dataEl = document.getElementById("da-data");
const customerId = dataEl.dataset.customerId;
const currentPayment = parseFloat(dataEl.dataset.currentPayment);
const vehicleEquity = parseFloat(dataEl.dataset.vehicleEquity);
// State management
let currentOffers = [];
function escapeHtml(str){return str.replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c];});}
let allVehicles = [];
let currentSearchResults = [];
let activeFilters = {};
let comparisonSlots = [null, null, null];
let updateTimer = null;
let searchTimer = null;
let currentCategory = 'all';
let isSearching = false;
let isLoading = false;
let selectedVehicles = [];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Deal Architect initialized');
    showLoadingState('calculations');
    showLoadingState('inventory');
    showLoadingState('scenarios');
    document.getElementById('reset-btn').addEventListener('click', resetAll);
    document.getElementById('export-btn').addEventListener('click', exportComparison);
    document.getElementById('save-config-btn').addEventListener('click', saveCurrentConfig);
    document.getElementById('toggle-filters-btn').addEventListener('click', toggleAdvancedFilters);
    document.getElementById('clear-filters-btn').addEventListener('click', clearFilters);
    document.getElementById('apply-filters-btn').addEventListener('click', applyFilters);
    document.getElementById('clear-comparison-btn').addEventListener('click', clearComparison);
    document.getElementById('generate-report-btn').addEventListener('click', generateReport);
    document.getElementById('search-inventory').addEventListener('keyup', debounceSearch);
    document.getElementById('term-select').addEventListener('change', updateCalculations);
    ['interest-slider','service-fee-slider','cxa-slider','cac-slider','insurance-slider'].forEach(id => {
        const el = document.getElementById(id);
        el.addEventListener('input', () => {
            const displayId = id.replace('-slider','-value');
            const prefix = id.includes('cac') || id.includes('insurance') ? '$' : '%';
            updateSlider(el, displayId, prefix);
            updateCalculations();
        });
    });
    document.querySelectorAll('.quick-action[data-preset]').forEach(btn => {
        btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
    });
    document.querySelectorAll('[data-category]').forEach(btn => {
        btn.addEventListener('click', () => filterByCategory(btn.dataset.category));
    });

    loadInitialData();
    setupRealtimeUpdates();
});

function loadInitialData() {
    // Load initial calculations
    calculatePayments();
    
    // Load saved scenarios for this customer
    fetch(`/api/scenarios/customer/${customerId}`)
        .then(res => res.json())
        .then(data => {
            if (data.scenarios) {
                updateSavedScenarios(data.scenarios);
            }
        })
        .catch(err => console.error('Error loading scenarios:', err))
        .finally(() => hideLoadingState('scenarios'));
    
    // Initial inventory search
    performSearch('');
}

function updateSavedScenarios(scenarios) {
    const container = document.getElementById('saved-scenarios');
    if (scenarios.length === 0) {
        container.innerHTML = '<p style="color: #999; font-size: 0.875rem;">No saved scenarios yet</p>';
        return;
    }

    container.innerHTML = scenarios.map(scenario => `
        <div class="quick-action scenario-item" data-scenario-id="${escapeHtml(String(scenario.id))}" style="margin-bottom: 0.5rem;">
            <div style="font-weight: 500;">${escapeHtml(scenario.name)}</div>
            <div style="font-size: 0.75rem; color: #666;">
                $${Math.round(scenario.configuration.monthly_payment || 0).toLocaleString()}/mo
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.scenario-item').forEach(el => {
        el.addEventListener('click', () => loadScenario(el.dataset.scenarioId));
    });
}

// Real-time calculation updates
function updateCalculations() {
    // Debounce updates
    clearTimeout(updateTimer);
    updateTimer = setTimeout(() => {
        calculatePayments();
    }, 300);
}

function calculatePayments() {
    // Get current configuration
    const config = getCurrentConfig();
    
    // Show loading state
    if (window.LoadingManager) {
        LoadingManager.show('calculated-payment', 'Calculating payment...');
    } else {
        showLoadingState('calculations');
    }
    
    // Make real-time calculation request
    // For now, use a default car ID or the first selected vehicle
    const carId = selectedVehicles.length > 0 ? selectedVehicles[0].car_id : (allVehicles.length > 0 ? allVehicles[0].car_id : null);
    
    if (!carId) {
        hideLoadingState('calculations');
        return; // No cars available yet
    }
    
    fetch('/api/calculate-payment', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            customer_id: customerId,
            car_id: String(carId), // Ensure it's a string
            term: parseInt(config.term),
            service_fee_pct: config.service_fee_pct,
            cxa_pct: config.cxa_pct,
            cac_bonus: config.cac_bonus,
            kavak_total_enabled: config.kavak_total_enabled,
            insurance_amount: config.insurance_amount,
            interest_rate: config.interest_rate
        })
    })
    .then(res => res.json())
    .then(data => {
        updatePaymentDisplay(data);
        refreshOffers();
    })
    .catch(err => {
        console.error('Calculation error:', err);
        if (window.ErrorHandler) {
            ErrorHandler.show('calculated-payment', 'Failed to calculate payment: ' + err.message);
        }
    })
    .finally(() => {
        if (window.LoadingManager) {
            LoadingManager.hide('calculated-payment');
        } else {
            hideLoadingState('calculations');
        }
    });
}

function getCurrentConfig() {
    return {
        term: document.getElementById('term-select').value,
        interest_rate: parseFloat(document.getElementById('interest-slider').value) / 100,
        service_fee_pct: parseFloat(document.getElementById('service-fee-slider').value) / 100,
        cxa_pct: parseFloat(document.getElementById('cxa-slider').value) / 100,
        cac_bonus: parseInt(document.getElementById('cac-slider').value),
        kavak_total_enabled: document.getElementById('kavak-total-toggle').classList.contains('active'),
        insurance_amount: parseInt(document.getElementById('insurance-slider').value)
    };
}

function updatePaymentDisplay(data) {
    if (data.viable) {
        document.getElementById('calculated-payment').textContent = Math.round(data.monthly_payment).toLocaleString();
        const delta = ((data.monthly_payment / currentPayment) - 1) * 100;
        document.getElementById('payment-delta').innerHTML = `
            ${delta > 0 ? '+' : ''}${delta.toFixed(1)}% vs current
            <br>
            <span style="font-size: 0.875rem; opacity: 0.8;">
                Without fees: $${Math.round(data.payment_without_fees).toLocaleString()}
            </span>
        `;
    } else {
        document.getElementById('payment-delta').textContent = 'Configuration not viable';
    }
}

function updateSlider(slider, displayId, prefix) {
    const value = slider.value;
    const display = document.getElementById(displayId);
    if (prefix === '$') {
        display.textContent = '$' + parseInt(value).toLocaleString();
    } else {
        display.textContent = value + prefix;
    }
}

function toggleKavakTotal() {
    document.getElementById('kavak-total-toggle').classList.toggle('active');
}


function performSearch(searchTerm = '') {
    if (isSearching) return;  // Prevent concurrent searches
    
    isSearching = true;
    const config = getCurrentConfig();
    
    // Show loading
    document.getElementById('results-container').innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #999;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
            <p>Searching inventory...</p>
        </div>
    `;
    
    // Use live search API for real-time NPV calculations
    fetch('/api/search-inventory-live', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            customer_id: customerId,
            search_term: searchTerm,
            config: config,
            limit: 50
        })
    })
    .then(res => res.json())
    .then(data => {
        allVehicles = data.vehicles || [];
        currentSearchResults = allVehicles;
        displayVehicles();
    })
    .catch(err => {
        console.error('Error searching inventory:', err);
        document.getElementById('results-container').innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #f44336;">
                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                <p>Error loading inventory. Please try again.</p>
            </div>
        `;
    })
    .finally(() => {
        isSearching = false;  // Reset flag
    });
}

function refreshOffers() {
    // This is now an alias for performSearch
    performSearch(document.getElementById('search-inventory').value);
}

function displayVehicles() {
    let vehicles = currentCategory === 'all' ? currentSearchResults : filterVehiclesByCategory(currentCategory);
    
    let html = '';
    let totalNPV = 0;
    let categories = {
        perfect_match: 0,
        slight_increase: 0,
        moderate_increase: 0,
        stretch: 0
    };
    
    vehicles.forEach(vehicle => {
        const delta = vehicle.payment_delta || 0;
        totalNPV += vehicle.npv || 0;
        
        // Categorize
        if (delta >= -0.05 && delta <= 0.05) {
            categories.perfect_match++;
        } else if (delta > 0.05 && delta <= 0.15) {
            categories.slight_increase++;
        } else if (delta > 0.15 && delta <= 0.25) {
            categories.moderate_increase++;
        } else {
            categories.stretch++;
        }
        
        html += createVehicleCard(vehicle);
    });
    
    // Update stats
    document.getElementById('total-offers').textContent = currentSearchResults.length;
    document.getElementById('viable-offers').textContent = vehicles.length;
    document.getElementById('avg-npv').textContent = vehicles.length > 0 ? 
        '$' + Math.round(totalNPV / vehicles.length).toLocaleString() : '$0';
    
    // Update category counts
    document.getElementById('count-perfect').textContent = `(${categories.perfect_match})`;
    document.getElementById('count-slight').textContent = `(${categories.slight_increase})`;
    document.getElementById('count-moderate').textContent = `(${categories.moderate_increase})`;
    
    // Display vehicles
    const container = document.getElementById('results-container');
    if (isLoading) {
        container.innerHTML = createLoadingState();
    } else {
        container.innerHTML = html ||
            '<p style="text-align: center; color: #999; padding: 3rem;">No vehicles found. Try adjusting your search or filters.</p>';

        container.querySelectorAll('.vehicle-card').forEach(card => {
            card.addEventListener('click', () => {
                const vehicle = JSON.parse(decodeURIComponent(card.dataset.vehicle));
                selectVehicle(vehicle);
            });
        });
    }
}

function createVehicleCard(vehicle) {
    const delta = vehicle.payment_delta || 0;
    let paymentClass = 'payment-match';
    if (delta > 0.15) paymentClass = 'payment-high';
    else if (delta > 0.05) paymentClass = 'payment-increase';
    
    const deltaPercent = (delta * 100).toFixed(1);
    const deltaDisplay = delta > 0 ? `+${deltaPercent}%` : `${deltaPercent}%`;
    
    const data = encodeURIComponent(JSON.stringify(vehicle));
    return `
        <div class="vehicle-card" data-vehicle="${data}">
            <span class="payment-indicator ${paymentClass}">${deltaDisplay}</span>
            
            <div class="vehicle-header">
                <div>
                    <div class="vehicle-title">${vehicle.car_model || vehicle.model}</div>
                    <div class="vehicle-subtitle">${vehicle.year} • ${Math.round((vehicle.kilometers || 0) / 1000)}k km</div>
                </div>
                <div class="vehicle-price">
                    <div class="vehicle-price-value">$${Math.round(vehicle.car_price).toLocaleString()}</div>
                    <div class="vehicle-price-label">Vehicle Price</div>
                </div>
            </div>
            
            <div class="vehicle-stats">
                <div class="vehicle-stat">
                    <div class="vehicle-stat-value">$${Math.round(vehicle.monthly_payment).toLocaleString()}</div>
                    <div class="vehicle-stat-label">Monthly</div>
                </div>
                <div class="vehicle-stat">
                    <div class="vehicle-stat-value">${vehicle.term}mo</div>
                    <div class="vehicle-stat-label">Term</div>
                </div>
                <div class="vehicle-stat">
                    <div class="vehicle-stat-value" style="color: #4caf50;">$${Math.round(vehicle.npv).toLocaleString()}</div>
                    <div class="vehicle-stat-label">NPV</div>
                </div>
                <div class="vehicle-stat">
                    <div class="vehicle-stat-value">${Math.round(vehicle.down_payment_pct * 100)}%</div>
                    <div class="vehicle-stat-label">Down</div>
                </div>
            </div>
        </div>
    `;
}

function selectVehicle(vehicle) {
    // Add to selected vehicles list
    if (!selectedVehicles.find(v => v.car_id === vehicle.car_id)) {
        selectedVehicles.push(vehicle);
    }
    
    // Find first empty slot
    for (let i = 0; i < 3; i++) {
        if (!comparisonSlots[i]) {
            addToComparison(vehicle, i);
            break;
        }
    }
}

// Smart Inventory Browser Functions
function toggleAdvancedFilters() {
    const filtersDiv = document.getElementById('advanced-filters');
    filtersDiv.style.display = filtersDiv.style.display === 'none' ? 'block' : 'none';
}

function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        const searchTerm = document.getElementById('search-inventory').value;
        if (!isSearching) {  // Prevent multiple simultaneous searches
            performSearch(searchTerm);
        }
    }, 800);  // Increased from 500ms to 800ms
}

function applyFilters() {
    // Collect all filter values
    activeFilters = {
        payment_delta_min: parseFloat(document.getElementById('payment-min').value) / 100 || -0.1,
        payment_delta_max: parseFloat(document.getElementById('payment-max').value) / 100 || 0.25,
        min_price: parseFloat(document.getElementById('price-min').value) || null,
        max_price: parseFloat(document.getElementById('price-max').value) || null,
        min_year: parseInt(document.getElementById('year-min').value) || null,
        max_year: parseInt(document.getElementById('year-max').value) || null,
        max_km: parseFloat(document.getElementById('max-km').value) || null
    };
    
    // Get selected vehicle types
    const vehicleTypesSelect = document.getElementById('vehicle-types');
    const selectedTypes = Array.from(vehicleTypesSelect.selectedOptions).map(opt => opt.value);
    if (selectedTypes.length > 0) {
        activeFilters.vehicle_types = selectedTypes;
    }
    
    // Get sort options
    const sortBy = document.getElementById('sort-by').value;
    
    // Show loading
    document.getElementById('results-container').innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #999;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
            <p>Applying filters...</p>
        </div>
    `;
    
    // Make filtered search request
    fetch('/api/search-inventory', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            customer_id: customerId,
            filters: activeFilters,
            sort_by: sortBy,
            sort_order: 'asc',
            limit: 100
        })
    })
    .then(res => res.json())
    .then(data => {
        // Update vehicles with quick calculations
        allVehicles = data.vehicles || [];
        currentSearchResults = allVehicles;
        
        // Now get full NPV calculations for visible vehicles
        const config = getCurrentConfig();
        return fetch('/api/search-inventory-live', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                customer_id: customerId,
                search_term: document.getElementById('search-inventory').value,
                config: config,
                limit: 50
            })
        });
    })
    .then(res => res.json())
    .then(data => {
        allVehicles = data.vehicles || [];
        currentSearchResults = allVehicles;
        displayVehicles();
        
        // Hide filters after applying
        toggleAdvancedFilters();
    })
    .catch(err => {
        console.error('Error applying filters:', err);
    });
}

function clearFilters() {
    // Reset all filter inputs
    document.getElementById('payment-min').value = '-10';
    document.getElementById('payment-max').value = '25';
    document.getElementById('price-min').value = '';
    document.getElementById('price-max').value = '';
    document.getElementById('year-min').value = '';
    document.getElementById('year-max').value = '';
    document.getElementById('max-km').value = '';
    document.getElementById('vehicle-types').selectedIndex = -1;
    document.getElementById('sort-by').value = 'payment_delta';
    
    // Clear active filters
    activeFilters = {};
    
    // Refresh with no filters
    performSearch(document.getElementById('search-inventory').value);
}

function filterByCategory(category) {
    currentCategory = category;
    
    // Update active button
    document.querySelectorAll('[data-category]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-category') === category);
    });
    
    // Redisplay vehicles
    displayVehicles();
}

function filterVehiclesByCategory(category) {
    return currentSearchResults.filter(vehicle => {
        const delta = vehicle.payment_delta || 0;
        switch(category) {
            case 'perfect_match':
                return delta >= -0.05 && delta <= 0.05;
            case 'slight_increase':
                return delta > 0.05 && delta <= 0.15;
            case 'moderate_increase':
                return delta > 0.15 && delta <= 0.25;
            default:
                return true;
        }
    });
}

function addToComparison(vehicle, slotIndex) {
    comparisonSlots[slotIndex] = vehicle;
    
    const slot = document.querySelector(`[data-slot="${slotIndex + 1}"]`);
    slot.classList.add('filled');
    slot.innerHTML = `
        <div style="position: relative;">
            <button class="remove-comp" data-slot-index="${slotIndex}" style="position: absolute; top: -0.5rem; right: -0.5rem; background: #f44336; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer;">
                <i class="fas fa-times"></i>
            </button>
            <h5 style="margin: 0 0 0.5rem 0;">${vehicle.car_model || vehicle.model}</h5>
            <div style="font-size: 0.875rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span>Monthly:</span>
                    <strong>$${Math.round(vehicle.monthly_payment).toLocaleString()}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span>Change:</span>
                    <strong style="color: ${vehicle.payment_delta > 0 ? '#f44336' : '#4caf50'};">
                        ${vehicle.payment_delta > 0 ? '+' : ''}${(vehicle.payment_delta * 100).toFixed(1)}%
                    </strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>NPV:</span>
                    <strong style="color: #4caf50;">$${Math.round(vehicle.npv).toLocaleString()}</strong>
                </div>
            </div>
        </div>
    `;

    slot.querySelector('.remove-comp').addEventListener('click', () => removeFromComparison(slotIndex));
}

function removeFromComparison(slotIndex) {
    comparisonSlots[slotIndex] = null;
    const slot = document.querySelector(`[data-slot="${slotIndex + 1}"]`);
    slot.classList.remove('filled');
    slot.innerHTML = `
        <div style="color: #999;">
            <i class="fas fa-plus-circle" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
            <p>Click a vehicle to compare</p>
        </div>
    `;
}

function clearComparison() {
    for (let i = 0; i < 3; i++) {
        removeFromComparison(i);
    }
}

function applyPreset(preset) {
    switch(preset) {
        case 'conservative':
            document.getElementById('service-fee-slider').value = 4;
            document.getElementById('cxa-slider').value = 4;
            document.getElementById('cac-slider').value = 0;
            document.getElementById('term-select').value = '48';
            break;
        case 'aggressive':
            document.getElementById('service-fee-slider').value = 2;
            document.getElementById('cxa-slider').value = 2;
            document.getElementById('cac-slider').value = 5000;
            document.getElementById('term-select').value = '60';
            break;
        case 'no-fees':
            document.getElementById('service-fee-slider').value = 0;
            document.getElementById('cxa-slider').value = 0;
            document.getElementById('cac-slider').value = 0;
            document.getElementById('kavak-total-toggle').classList.remove('active');
            break;
        case 'max-term':
            document.getElementById('term-select').value = '72';
            break;
    }
    
    // Update displays
    updateSlider(document.getElementById('service-fee-slider'), 'service-fee-value', '%');
    updateSlider(document.getElementById('cxa-slider'), 'cxa-value', '%');
    updateSlider(document.getElementById('cac-slider'), 'cac-value', '$');
    
    // Recalculate
    updateCalculations();
}

function saveCurrentConfig() {
    const name = prompt('Enter a name for this configuration:');
    if (!name) return;
    
    const config = getCurrentConfig();
    
    // Save scenario
    fetch('/api/scenarios/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            customer_id: customerId,
            car_id: 'config_only',
            name: name,
            configuration: config,
            notes: 'Deal Architect configuration'
        })
    })
    .then(res => res.json())
    .then(data => {
        alert('Configuration saved!');
        location.reload(); // Refresh to show new scenario
    })
    .catch(err => {
        alert('Error saving configuration: ' + err.message);
    });
}

function filterOffers(tier) {
    // Update active button
    document.querySelectorAll('.btn-sm').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Filter display
    // Implementation depends on how you want to filter
}

function setupRealtimeUpdates() {
    // Could use WebSockets here for true real-time
    // For now, using debounced updates
}

function resetAll() {
    // Reset all sliders to defaults
    document.getElementById('service-fee-slider').value = 4;
    document.getElementById('cxa-slider').value = 4;
    document.getElementById('cac-slider').value = 0;
    document.getElementById('insurance-slider').value = 10999;
    document.getElementById('interest-slider').value = 18;
    document.getElementById('term-select').value = '48';
    document.getElementById('kavak-total-toggle').classList.add('active');
    
    // Update displays
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        const displayId = slider.id.replace('-slider', '-value');
        const prefix = slider.id.includes('cac') || slider.id.includes('insurance') ? '$' : '%';
        updateSlider(slider, displayId, prefix);
    });
    
    // Clear comparison
    clearComparison();
    
    // Recalculate
    updateCalculations();
}

function exportComparison() {
    // Export comparison data to CSV
    const config = getCurrentConfig();
    const csvData = generateComparisonCSV(config);
    
    // Create download link
    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deal_comparison_${customerId}_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function generateReport() {
    // Generate detailed report with current configuration
    const config = getCurrentConfig();
    const reportData = {
        customer_id: customerId,
        configuration: config,
        timestamp: new Date().toISOString(),
        selected_vehicles: selectedVehicles || []
    };
    
    // Open report in new window
    const reportWindow = window.open('', '_blank');
    reportWindow.document.write(generateHTMLReport(reportData));
}

function generateComparisonCSV(config) {
    let csv = 'Parameter,Value\n';
    csv += `Service Fee,${config.service_fee_pct * 100}%\n`;
    csv += `CXA Fee,${config.cxa_pct * 100}%\n`;
    csv += `CAC Bonus,$${config.cac_bonus}\n`;
    csv += `Kavak Total,$${config.kavak_total_amount}\n`;
    csv += `Insurance,$${config.insurance_amount}\n`;
    csv += `Term,${config.term_months} months\n`;
    return csv;
}

function generateHTMLReport(data) {
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Deal Report - ${data.customer_id}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #1451EC; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f5f7fa; }
                .timestamp { color: #666; font-size: 14px; }
            </style>
        </head>
        <body>
            <h1>Deal Configuration Report</h1>
            <p class="timestamp">Generated: ${new Date(data.timestamp).toLocaleString()}</p>
            <h2>Customer: ${data.customer_id}</h2>
            
            <h3>Configuration Parameters</h3>
            <table>
                <tr><th>Parameter</th><th>Value</th></tr>
                <tr><td>Service Fee</td><td>${(data.configuration.service_fee_pct * 100).toFixed(2)}%</td></tr>
                <tr><td>CXA Fee</td><td>${(data.configuration.cxa_pct * 100).toFixed(2)}%</td></tr>
                <tr><td>CAC Bonus</td><td>$${data.configuration.cac_bonus.toLocaleString()}</td></tr>
                <tr><td>Kavak Total</td><td>$${data.configuration.kavak_total_amount.toLocaleString()}</td></tr>
                <tr><td>Insurance</td><td>$${data.configuration.insurance_amount.toLocaleString()}</td></tr>
                <tr><td>Term</td><td>${data.configuration.term_months} months</td></tr>
            </table>
            
            <h3>Selected Vehicles</h3>
            ${data.selected_vehicles.length > 0 ? 
                '<p>' + data.selected_vehicles.length + ' vehicles selected for comparison</p>' :
                '<p>No vehicles selected yet</p>'
            }
            
            <button id="print-report">Print Report</button>
            <script>document.getElementById('print-report').addEventListener('click', () => window.print());</script>
        </body>
        </html>
    `;
}

// Loading state helper functions
function showLoadingState(section) {
    if (section === 'inventory') {
        document.getElementById('results-container').innerHTML = `
            <div class="loading-overlay">
                <div>
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Loading inventory...</div>
                </div>
            </div>`;
    } else if (section === 'calculations') {
        document.querySelectorAll('.stat-value').forEach(el => {
            el.classList.add('skeleton', 'skeleton-text');
        });
        document.getElementById('calculated-payment').classList.add('skeleton', 'skeleton-text');
        document.getElementById('payment-delta').classList.add('skeleton', 'skeleton-text');
    } else if (section === 'search') {
        document.getElementById('results-container').innerHTML = `
            <div class="skeleton skeleton-box"></div>
            <div class="skeleton skeleton-box"></div>
            <div class="skeleton skeleton-box"></div>`;
    } else if (section === 'scenarios') {
        document.getElementById('saved-scenarios').innerHTML = `
            <div class="skeleton skeleton-box"></div>
            <div class="skeleton skeleton-box"></div>`;
    }
}

function hideLoadingState(section) {
    if (section === 'calculations') {
        document.querySelectorAll('.stat-value').forEach(el => {
            el.classList.remove('skeleton', 'skeleton-text');
        });
        document.getElementById('calculated-payment').classList.remove('skeleton', 'skeleton-text');
        document.getElementById('payment-delta').classList.remove('skeleton', 'skeleton-text');
    }
}

function createLoadingState() {
    return `
        <div style="text-align: center; padding: 3rem; color: #999;">
            <div class="loading-spinner" style="margin: 0 auto 1rem;"></div>
            <p>Loading...</p>
        </div>
    `;
}

// Search functionality
document.getElementById('search-inventory').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    
    // Filter inventory cards
    const inventoryCards = document.querySelectorAll('.inventory-card');
    let visibleCount = 0;
    
    inventoryCards.forEach(card => {
        const brand = card.querySelector('.car-title')?.textContent.toLowerCase() || '';
        const model = card.querySelector('.car-details')?.textContent.toLowerCase() || '';
        const price = card.querySelector('.car-price')?.textContent.toLowerCase() || '';
        
        const matches = brand.includes(searchTerm) || 
                       model.includes(searchTerm) || 
                       price.includes(searchTerm);
        
        if (matches) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    // Update results count
    const resultsInfo = document.querySelector('.results-info');
    if (resultsInfo) {
        resultsInfo.textContent = `Showing ${visibleCount} vehicles`;
    }
    
    // Show no results message if needed
    if (visibleCount === 0 && searchTerm) {
        const noResults = document.getElementById('no-results') || createNoResultsMessage();
        noResults.style.display = 'block';
    } else {
        const noResults = document.getElementById('no-results');
        if (noResults) noResults.style.display = 'none';
    }
});

function createNoResultsMessage() {
    const div = document.createElement('div');
    div.id = 'no-results';
    div.className = 'text-center p-4';
    div.innerHTML = '<p class="text-muted">No vehicles match your search</p>';
    document.getElementById('inventory-results').appendChild(div);
    return div;
}
