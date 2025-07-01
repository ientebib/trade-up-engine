// Global variables - will be initialized after DOM loads
let customerId = null;
let currentPayment = 0;
let vehicleEquity = 0;

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
let backendConfig = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Deal Architect Initializing ===');
    console.log('DOM state:', document.readyState);
    
    try {
        // Get customer data from DOM
        const dataEl = document.getElementById("da-data");
        if (!dataEl) {
            console.error('FATAL: da-data element not found!');
            document.body.innerHTML += '<div style="position:fixed;top:0;left:0;right:0;background:red;color:white;padding:20px;z-index:9999;">ERROR: Missing da-data element</div>';
            return;
        }
        
        console.log('Found da-data element:', dataEl);
        customerId = dataEl.dataset.customerId;
        currentPayment = parseFloat(dataEl.dataset.currentPayment) || 0;
        vehicleEquity = parseFloat(dataEl.dataset.vehicleEquity) || 0;
        
        console.log('Customer data loaded:', {
            customerId: customerId,
            currentPayment: currentPayment,
            vehicleEquity: vehicleEquity
        });
    
        // Show loading states
        console.log('Setting loading states...');
        showLoadingState('calculations');
        showLoadingState('inventory');
        showLoadingState('scenarios');
        
        // Safely attach event listeners
        console.log('Attaching event listeners...');
        const attachListener = (id, event, handler) => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener(event, handler);
                console.log(`✓ Attached ${event} to #${id}`);
            } else {
                console.warn(`✗ Element #${id} not found`);
            }
        };
        
        attachListener('reset-btn', 'click', resetAll);
        attachListener('export-btn', 'click', exportComparison);
        attachListener('save-config-btn', 'click', saveCurrentConfig);
        attachListener('recalculate-btn', 'click', recalculateOffers);
        attachListener('toggle-filters-btn', 'click', toggleAdvancedFilters);
        attachListener('clear-filters-btn', 'click', clearFilters);
        attachListener('apply-filters-btn', 'click', applyFilters);
        attachListener('clear-comparison-btn', 'click', clearComparison);
        attachListener('generate-report-btn', 'click', generateReport);
        attachListener('search-inventory', 'keyup', debounceSearch);
        // Attach slider listeners
        console.log('Attaching slider listeners...');
        ['interest-slider','service-fee-slider','cxa-slider','cac-slider','insurance-slider'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => {
                    const displayId = id.replace('-slider','-value');
                    const prefix = id.includes('cac') || id.includes('insurance') ? '$' : '%';
                    updateSlider(el, displayId, prefix);
                });
                console.log(`✓ Attached input to #${id}`);
            } else {
                console.warn(`✗ Slider #${id} not found`);
            }
        });
        // Attach preset and category listeners
        console.log('Attaching preset listeners...');
        document.querySelectorAll('.quick-action[data-preset]').forEach(btn => {
            btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
        });
        
        console.log('Attaching category listeners...');
        document.querySelectorAll('[data-category]').forEach(btn => {
            btn.addEventListener('click', () => filterByCategory(btn.dataset.category));
        });

        console.log('Loading backend configuration...');
        loadBackendConfig().then(() => {
            console.log('Calling loadInitialData...');
            loadInitialData();
            setupRealtimeUpdates();
        });
        
    } catch (error) {
        console.error('FATAL ERROR during initialization:', error);
        console.error('Stack trace:', error.stack);
        document.body.innerHTML += `<div style="position:fixed;top:0;left:0;right:0;background:red;color:white;padding:20px;z-index:9999;">ERROR: ${error.message}</div>`;
    }
});

async function loadBackendConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        backendConfig = config;
        console.log('Backend config loaded:', config);
        
        // Update UI with backend values
        if (config.fees) {
            // Update sliders with backend values
            document.getElementById('cxa-slider').value = config.fees.cxa_pct * 100;
            document.getElementById('cxa-value').textContent = (config.fees.cxa_pct * 100).toFixed(2) + '%';
            
            document.getElementById('service-fee-slider').value = config.fees.service_fee_pct * 100;
            document.getElementById('service-fee-value').textContent = (config.fees.service_fee_pct * 100).toFixed(1) + '%';
            
            // Update insurance slider based on default
            if (config.fees.insurance_annual) {
                document.getElementById('insurance-slider').value = config.fees.insurance_annual;
                document.getElementById('insurance-value').textContent = '$' + Math.round(config.fees.insurance_annual).toLocaleString();
            }
            
            // Update Kavak Total display if it exists
            const kavakTotalDisplay = document.querySelector('#kavak-total-toggle + span');
            if (kavakTotalDisplay && config.fees.kavak_total_amount) {
                kavakTotalDisplay.textContent = `$${Math.round(config.fees.kavak_total_amount).toLocaleString()} MXN (One-time)`;
            }
        }
    } catch (error) {
        console.error('Failed to load backend config:', error);
        // Continue with defaults if config fails to load
    }
}

function loadInitialData() {
    console.log('loadInitialData called, customerId:', customerId);
    
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
    console.log('Calling performSearch from loadInitialData');
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
        // DON'T refresh all offers when config changes - that's insane!
        // Just update the display with current data
        displayVehicles();
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
    const paymentEl = document.getElementById('calculated-payment');
    const deltaEl = document.getElementById('payment-delta');
    
    if (!paymentEl || !deltaEl) {
        console.error('Payment display elements not found');
        return;
    }
    
    if (data && data.viable) {
        paymentEl.textContent = Math.round(data.monthly_payment).toLocaleString();
        const delta = ((data.monthly_payment / currentPayment) - 1) * 100;
        deltaEl.innerHTML = `
            ${delta > 0 ? '+' : ''}${delta.toFixed(1)}% vs current
            <br>
            <span style="font-size: 0.875rem; opacity: 0.8;">
                Without fees: $${Math.round(data.payment_without_fees || 0).toLocaleString()}
            </span>
        `;
    } else if (data && data.error) {
        paymentEl.textContent = 'Error';
        deltaEl.innerHTML = `<span style="color: #f44336;">${data.error}</span>`;
    } else {
        paymentEl.textContent = 'Calculating';
        deltaEl.textContent = 'Configuration not viable';
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
    const toggle = document.getElementById('kavak-total-toggle');
    const isActive = toggle.classList.contains('active');
    
    if (isActive) {
        toggle.classList.remove('active');
        toggle.style.background = '#ccc';
        toggle.querySelector('span').style.transform = 'translateX(2px)';
    } else {
        toggle.classList.add('active');
        toggle.style.background = '#1451EC';
        toggle.querySelector('span').style.transform = 'translateX(26px)';
    }
    
    // Update calculations
    updateCalculations();
}

// Make function global
window.toggleKavakTotal = toggleKavakTotal;

function togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.classList.toggle('collapsed');
        
        // Adjust grid when panels are collapsed
        const workspace = document.querySelector('.workspace-body');
        const configCollapsed = document.getElementById('config-panel')?.classList.contains('collapsed');
        const comparisonCollapsed = document.getElementById('comparison-panel')?.classList.contains('collapsed');
        
        if (configCollapsed && comparisonCollapsed) {
            workspace.style.gridTemplateColumns = '60px 1fr 60px';
        } else if (configCollapsed) {
            workspace.style.gridTemplateColumns = '60px 1fr 350px';
        } else if (comparisonCollapsed) {
            workspace.style.gridTemplateColumns = '350px 1fr 60px';
        } else {
            workspace.style.gridTemplateColumns = '350px 1fr 350px';
        }
    }
}

// Make function global
window.togglePanel = togglePanel;


async function pollForTaskCompletion(taskId, maxAttempts = 30) {
    console.log(`Starting to poll task ${taskId}, max attempts: ${maxAttempts}`);
    
    for (let i = 0; i < maxAttempts; i++) {
        try {
            console.log(`Poll attempt ${i + 1}/${maxAttempts} for task ${taskId}`);
            const response = await fetch(`/api/offers/status/${taskId}`);
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.status}`);
            }
            
            const status = await response.json();
            console.log(`Task status:`, status);
            
            if (status.status === 'completed') {
                console.log('Task completed, fetching full result...');
                // Get the full result
                const resultResponse = await fetch(`/api/offers/result/${taskId}`);
                
                if (!resultResponse.ok) {
                    throw new Error(`Result fetch failed: ${resultResponse.status}`);
                }
                
                const result = await resultResponse.json();
                console.log('Got result with offers:', Object.keys(result.offers || {}));
                return result;
            } else if (status.status === 'failed') {
                throw new Error(status.error || 'Task failed');
            }
            
            // Wait before next poll
            await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (error) {
            console.error('Polling error:', error);
            throw error;
        }
    }
    throw new Error('Timeout waiting for results');
}

function processOffersData(data) {
    console.log('processOffersData called with:', data);
    
    // Convert offers to vehicle format for Deal Architect
    allVehicles = [];
    if (data.offers) {
        console.log('Processing offers:', Object.keys(data.offers));
        // Flatten all offers from all tiers
        Object.values(data.offers).forEach(tierOffers => {
            if (Array.isArray(tierOffers)) {
                console.log(`Adding ${tierOffers.length} offers to allVehicles`);
                allVehicles = allVehicles.concat(tierOffers);
            }
        });
    } else {
        console.warn('No offers in data!');
    }
    
    console.log(`Total vehicles after processing: ${allVehicles.length}`);
    currentSearchResults = allVehicles;
    displayVehicles();
    hideLoadingState('inventory');
}

function performSearch(searchTerm = '') {
    console.log('performSearch called with:', searchTerm, 'customerId:', customerId);
    if (isSearching) {
        console.log('Already searching, skipping');
        return;  // Prevent concurrent searches
    }
    
    isSearching = true;
    const config = getCurrentConfig();
    
    // Show loading
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) {
        console.error('results-container element not found!');
        isSearching = false;
        return;
    }
    
    resultsContainer.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #999;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
            <p>Searching inventory...</p>
        </div>
    `;
    
    console.log('Making API call with config:', config);
    
    // Use the basic endpoint to get initial offers WITH CUSTOM CONFIG
    fetch('/api/generate-offers-basic', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            customer_id: customerId,
            custom_config: {
                service_fee_pct: config.service_fee_pct,
                cxa_pct: config.cxa_pct,
                cac_bonus: config.cac_bonus,
                kavak_total_enabled: config.kavak_total_enabled,
                insurance_amount: config.insurance_amount,
                interest_rate_override: config.interest_rate
            }
        })
    })
    .then(res => {
        console.log('API Response status:', res.status);
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(async (data) => {
        console.log('API Response data:', data);
        
        // Handle async task response
        if (data.task_id) {
            console.log('Got task ID, polling for completion:', data.task_id);
            // Poll for completion
            const result = await pollForTaskCompletion(data.task_id);
            console.log('Poll result:', result);
            if (result && result.offers) {
                processOffersData(result);
            } else {
                console.error('No offers in poll result');
                throw new Error('No offers returned from task');
            }
        } else if (data.offers) {
            console.log('Got direct offers response');
            // Direct response
            processOffersData(data);
        } else {
            console.error('Unexpected response format:', data);
            throw new Error('Invalid response format - no task_id or offers');
        }
    })
    .catch(err => {
        console.error('Error searching inventory:', err);
        console.error('Stack trace:', err.stack);
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: #f44336;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>Error: ${err.message}</p>
                    <p style="font-size: 0.875rem; margin-top: 1rem;">Check console for details</p>
                </div>
            `;
        }
    })
    .finally(() => {
        console.log('performSearch completed, resetting flag');
        isSearching = false;  // Reset flag
    });
}

function refreshOffers() {
    // This is now an alias for performSearch
    performSearch(document.getElementById('search-inventory').value);
}

function displayVehicles() {
    console.log('displayVehicles called');
    console.log('currentSearchResults:', currentSearchResults.length);
    console.log('currentCategory:', currentCategory);
    
    try {
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
        const updateElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
            } else {
                console.warn(`Element #${id} not found`);
            }
        };
        
        updateElement('total-offers', currentSearchResults.length);
        updateElement('viable-offers', vehicles.length);
        updateElement('avg-npv', vehicles.length > 0 ? 
            '$' + Math.round(totalNPV / vehicles.length).toLocaleString() : '$0');
        
        // Update category counts
        updateElement('count-perfect', `(${categories.perfect_match})`);
        updateElement('count-slight', `(${categories.slight_increase})`);
        updateElement('count-moderate', `(${categories.moderate_increase})`);
        
        // Display vehicles
        const container = document.getElementById('results-container');
        if (!container) {
            console.error('results-container not found!');
            return;
        }
        
        if (isLoading) {
            container.innerHTML = createLoadingState();
        } else {
            container.innerHTML = html ||
                '<p style="text-align: center; color: #999; padding: 3rem;">No vehicles found. Try adjusting your search or filters.</p>';

            container.querySelectorAll('.vehicle-card').forEach(card => {
                card.addEventListener('click', () => {
                    try {
                        const vehicle = JSON.parse(decodeURIComponent(card.dataset.vehicle));
                        selectVehicle(vehicle);
                    } catch (e) {
                        console.error('Error parsing vehicle data:', e);
                    }
                });
            });
        }
        
        console.log('displayVehicles completed successfully');
    } catch (error) {
        console.error('Error in displayVehicles:', error);
        console.error('Stack trace:', error.stack);
    }
}

function createVehicleCard(vehicle) {
    try {
        const delta = vehicle.payment_delta || 0;
        let paymentClass = 'payment-match';
        if (delta > 0.15) paymentClass = 'payment-high';
        else if (delta > 0.05) paymentClass = 'payment-increase';
        
        const deltaPercent = (delta * 100).toFixed(1);
        const deltaDisplay = delta > 0 ? `+${deltaPercent}%` : `${deltaPercent}%`;
        
        // Get vehicle price (handle different field names)
        const carPrice = vehicle.car_price || vehicle.new_car_price || 0;
        
        // Handle missing fields with defaults - look at the actual data structure
        const model = vehicle.car_model || vehicle.model || 'Unknown Model';
        const year = vehicle.year || new Date().getFullYear();
        const kilometers = vehicle.kilometers || vehicle.km || 0;
        const monthlyPayment = vehicle.monthly_payment || 0;
        const term = vehicle.term || 48;
        const npv = vehicle.npv || 0;
        
        // Calculate down payment percentage properly
        // down_payment = effective_equity, so down_payment_pct = effective_equity / car_price
        let downPaymentPct = 0;
        if (vehicle.effective_equity && carPrice > 0) {
            downPaymentPct = vehicle.effective_equity / carPrice;
        } else if (vehicle.vehicle_equity && carPrice > 0) {
            // Fallback calculation
            downPaymentPct = vehicle.vehicle_equity / carPrice;
        }
        
        const cxaAmount = vehicle.cxa_amount !== undefined ? vehicle.cxa_amount : 0;
        const baseLoanBeforeFees = vehicle.new_car_price - vehicleEquity; // preliminary base loan
        const cxaPercentOfBase = baseLoanBeforeFees > 0 ? (cxaAmount / baseLoanBeforeFees * 100) : 0;
        
        const data = encodeURIComponent(JSON.stringify(vehicle));
        return `
            <div class="vehicle-card" data-vehicle="${data}">
                <div class="vehicle-header">
                    <div style="flex: 1;">
                        <div class="vehicle-title">${escapeHtml(model)}</div>
                        <div class="vehicle-subtitle">${year} • ${kilometers > 0 ? Math.round(kilometers / 1000) + 'k km' : '0k km'}</div>
                    </div>
                    <div class="vehicle-price" style="text-align: right; flex-shrink: 0;">
                        <div class="vehicle-price-value">$${Math.round(carPrice).toLocaleString()}</div>
                        <div class="vehicle-price-label">Vehicle Price</div>
                    </div>
                </div>
                <div style="margin-top: 0.5rem;">
                    <span class="payment-indicator ${paymentClass}" style="position: static; display: inline-block; margin-bottom: 0.5rem;">${deltaDisplay}</span>
                </div>
                
                <div class="vehicle-stats">
                    <div class="vehicle-stat">
                        <div class="vehicle-stat-value">$${Math.round(monthlyPayment).toLocaleString()}</div>
                        <div class="vehicle-stat-label">Monthly</div>
                    </div>
                    <div class="vehicle-stat">
                        <div class="vehicle-stat-value">${term}mo</div>
                        <div class="vehicle-stat-label">Term</div>
                    </div>
                    <div class="vehicle-stat">
                        <div class="vehicle-stat-value" style="color: #2e7d32;">$${Math.round(npv).toLocaleString()}</div>
                        <div class="vehicle-stat-label">NPV</div>
                    </div>
                    <div class="vehicle-stat">
                        <div class="vehicle-stat-value">$${Math.round(vehicle.loan_amount).toLocaleString()}</div>
                        <div class="vehicle-stat-label">Loan</div>
                    </div>
                    <div class="vehicle-stat">
                        <div class="vehicle-stat-value" style="${downPaymentPct > 0.5 ? 'color: #ef6c00;' : ''}">${downPaymentPct > 0 ? Math.round(downPaymentPct * 100) + '%' : '0%'}</div>
                        <div class="vehicle-stat-label">Down</div>
                    </div>
                    <div class="vehicle-stat">
                        <div class="vehicle-stat-value" style="${cxaPercentOfBase > 0 ? 'color: #1451EC;' : ''}">${cxaPercentOfBase.toFixed(1)}% of base loan</div>
                        <div class="vehicle-stat-label">CXA Fee</div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error creating vehicle card:', error, vehicle);
        return '';
    }
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
        // Use local search for immediate filtering
        performLocalSearch(searchTerm);
    }, 300);  // Reduced to 300ms for faster local search
}

function applyFilters() {
    console.log('Applying filters...');
    
    // Collect all filter values
    const filters = {
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
    
    // Get sort options
    const sortBy = document.getElementById('sort-by').value;
    
    // Apply filters locally to current results
    let filtered = allVehicles.filter(vehicle => {
        const delta = vehicle.payment_delta || 0;
        const price = vehicle.car_price || vehicle.new_car_price || 0;
        const year = vehicle.year || 0;
        const km = vehicle.kilometers || vehicle.km || 0;
        
        // Apply payment delta filter
        if (delta < filters.payment_delta_min || delta > filters.payment_delta_max) return false;
        
        // Apply price filter
        if (filters.min_price && price < filters.min_price) return false;
        if (filters.max_price && price > filters.max_price) return false;
        
        // Apply year filter
        if (filters.min_year && year < filters.min_year) return false;
        if (filters.max_year && year > filters.max_year) return false;
        
        // Apply km filter
        if (filters.max_km && km > filters.max_km) return false;
        
        // Apply vehicle type filter
        if (selectedTypes.length > 0) {
            // Try to match vehicle type from model name
            const model = (vehicle.car_model || '').toLowerCase();
            const matchesType = selectedTypes.some(type => {
                if (type === 'SUV') return model.includes('suv') || model.includes('cherokee') || model.includes('x1');
                if (type === 'Sedan') return model.includes('sedan') || model.includes('corolla') || model.includes('civic');
                if (type === 'Truck') return model.includes('truck') || model.includes('ram') || model.includes('f-150');
                if (type === 'Hatchback') return model.includes('hatch') || model.includes('golf') || model.includes('swift');
                return false;
            });
            if (!matchesType) return false;
        }
        
        return true;
    });
    
    // Sort results
    if (sortBy === 'payment_delta') {
        filtered.sort((a, b) => (a.payment_delta || 0) - (b.payment_delta || 0));
    } else if (sortBy === 'npv') {
        filtered.sort((a, b) => (b.npv || 0) - (a.npv || 0));
    } else if (sortBy === 'payment') {
        filtered.sort((a, b) => (a.monthly_payment || 0) - (b.monthly_payment || 0));
    } else if (sortBy === 'price') {
        filtered.sort((a, b) => (a.car_price || a.new_car_price || 0) - (b.car_price || b.new_car_price || 0));
    } else if (sortBy === 'year') {
        filtered.sort((a, b) => (b.year || 0) - (a.year || 0));
    } else if (sortBy === 'km') {
        filtered.sort((a, b) => (a.kilometers || a.km || 0) - (b.kilometers || b.km || 0));
    }
    
    console.log(`Filtered from ${allVehicles.length} to ${filtered.length} vehicles`);
    currentSearchResults = filtered;
    displayVehicles();
    
    // Hide filters after applying
    toggleAdvancedFilters();
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
    if (!slot) {
        console.error(`Comparison slot ${slotIndex + 1} not found`);
        return;
    }
    
    slot.classList.add('filled');
    slot.innerHTML = `
        <div style="position: relative; padding: 1rem;">
            <button class="remove-comp" data-slot-index="${slotIndex}" style="position: absolute; top: 0; right: 0; background: #f44336; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; font-size: 0.75rem;">
                ×
            </button>
            <h5 style="margin: 0 0 0.75rem 0; font-size: 0.875rem; font-weight: 600;">${escapeHtml(vehicle.car_model || vehicle.model || 'Unknown')}</h5>
            <div style="font-size: 0.8125rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.375rem;">
                    <span style="color: #666;">Monthly:</span>
                    <strong>$${Math.round(vehicle.monthly_payment).toLocaleString()}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.375rem;">
                    <span style="color: #666;">Change:</span>
                    <strong style="color: ${vehicle.payment_delta > 0 ? '#ef6c00' : '#2e7d32'};">
                        ${vehicle.payment_delta > 0 ? '+' : ''}${(vehicle.payment_delta * 100).toFixed(1)}%
                    </strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #666;">NPV:</span>
                    <strong style="color: #2e7d32;">$${Math.round(vehicle.npv).toLocaleString()}</strong>
                </div>
            </div>
        </div>
    `;

    const removeBtn = slot.querySelector('.remove-comp');
    if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeFromComparison(slotIndex);
        });
    }
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
    // Use backend config if available, otherwise use defaults
    const defaultCxa = backendConfig?.fees?.cxa_pct ? backendConfig.fees.cxa_pct * 100 : 3.99;
    const defaultServiceFee = backendConfig?.fees?.service_fee_pct ? backendConfig.fees.service_fee_pct * 100 : 4;
    
    switch(preset) {
        case 'conservative':
            document.getElementById('service-fee-slider').value = defaultServiceFee;
            document.getElementById('cxa-slider').value = defaultCxa;
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

function recalculateOffers() {
    console.log('Recalculating offers with new configuration...');
    
    // Clear current results
    currentSearchResults = [];
    allVehicles = [];
    
    // Show loading state
    showLoadingState('inventory');
    
    // Perform new search with updated config
    performSearch(document.getElementById('search-inventory').value || '');
}

function resetAll() {
    // Reset all sliders to backend defaults or fallback values
    const config = backendConfig?.fees || {};
    document.getElementById('service-fee-slider').value = (config.service_fee_pct || 0.04) * 100;
    document.getElementById('cxa-slider').value = (config.cxa_pct || 0.0399) * 100;
    document.getElementById('cac-slider').value = config.cac_bonus || 0;
    document.getElementById('insurance-slider').value = config.insurance_annual || 10999;
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
    console.log(`showLoadingState called for section: ${section}`);
    
    if (section === 'inventory') {
        const container = document.getElementById('results-container');
        if (container) {
            container.innerHTML = `
                <div class="loading-overlay">
                    <div>
                        <div class="loading-spinner"></div>
                        <div class="loading-text">Loading inventory...</div>
                    </div>
                </div>`;
        } else {
            console.error('results-container not found!');
        }
    } else if (section === 'calculations') {
        document.querySelectorAll('.stat-value').forEach(el => {
            el.classList.add('skeleton', 'skeleton-text');
        });
        const calcPayment = document.getElementById('calculated-payment');
        const paymentDelta = document.getElementById('payment-delta');
        if (calcPayment) calcPayment.classList.add('skeleton', 'skeleton-text');
        if (paymentDelta) paymentDelta.classList.add('skeleton', 'skeleton-text');
    } else if (section === 'search') {
        const container = document.getElementById('results-container');
        if (container) {
            container.innerHTML = `
                <div class="skeleton skeleton-box"></div>
                <div class="skeleton skeleton-box"></div>
                <div class="skeleton skeleton-box"></div>`;
        }
    } else if (section === 'scenarios') {
        const container = document.getElementById('saved-scenarios');
        if (container) {
            container.innerHTML = `
                <div class="skeleton skeleton-box"></div>
                <div class="skeleton skeleton-box"></div>`;
        }
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

// Local search functionality
function performLocalSearch(searchTerm) {
    console.log('Performing local search for:', searchTerm);
    const term = searchTerm.toLowerCase();
    
    if (!term) {
        // Show all vehicles if no search term
        displayVehicles();
        return;
    }
    
    // Filter current results
    const filtered = allVehicles.filter(vehicle => {
        const model = (vehicle.car_model || '').toLowerCase();
        const year = String(vehicle.year || '');
        const carId = String(vehicle.car_id || '');
        
        return model.includes(term) || 
               year.includes(term) || 
               carId.includes(term);
    });
    
    console.log(`Found ${filtered.length} vehicles matching "${searchTerm}"`);
    currentSearchResults = filtered;
    displayVehicles();
}

function createNoResultsMessage() {
    const div = document.createElement('div');
    div.id = 'no-results';
    div.className = 'text-center p-4';
    div.innerHTML = '<p class="text-muted">No vehicles match your search</p>';
    document.getElementById('inventory-results').appendChild(div);
    return div;
}
