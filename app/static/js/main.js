// This file will contain the logic for interactivity, such as:
// - Fetching offer data for a customer from the API
// - Handling the filtering of offers on the client-side
// - Powering the searchable customer dropdown
// - Managing the global configuration form

// Kavak Trade-Up Engine Dashboard JavaScript
let currentCustomer = null;
let allCustomers = [];

document.addEventListener('DOMContentLoaded', function() {
    console.log("🚗 Kavak Dashboard JS Loaded");
    loadCustomersList();
    updateConfigStatusBadge();

    // If dashboard summary container exists, populate scenario results
    if (document.getElementById('dashboard-scenario-summary')) {
        loadDashboardScenarioSummary();
    }

    // Create amortization modal if it doesn't exist
    if (!document.getElementById('amortization-modal')) {
        const modal = document.createElement('div');
        modal.id = 'amortization-modal';
        modal.className = 'modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="modal-close" id="amortization-close">&times;</span>
                <div id="amortization-table"></div>
            </div>`;
        document.body.appendChild(modal);
        document.getElementById('amortization-close').addEventListener('click', closeAmortizationModal);
        window.addEventListener('click', function(evt) { if (evt.target === modal) closeAmortizationModal(); });
    }

    // Create financed balance breakdown modal if it doesn't exist
    if (!document.getElementById('balance-breakdown-modal')) {
        const modal = document.createElement('div');
        modal.id = 'balance-breakdown-modal';
        modal.className = 'modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="modal-close" id="balance-breakdown-close">&times;</span>
                <h3>Financed Balance Breakdown</h3>
                <div id="balance-breakdown-table"></div>
            </div>`;
        document.body.appendChild(modal);
        document.getElementById('balance-breakdown-close').addEventListener('click', () => modal.style.display = 'none');
        window.addEventListener('click', evt => { if (evt.target === modal) modal.style.display = 'none'; });
    }

    // Create equity breakdown modal
    if (!document.getElementById('equity-breakdown-modal')) {
        const modal = document.createElement('div');
        modal.id = 'equity-breakdown-modal';
        modal.className = 'modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="modal-close" id="equity-breakdown-close">&times;</span>
                <h3>Vehicle Equity Breakdown</h3>
                <div id="equity-breakdown-table"></div>
            </div>`;
        document.body.appendChild(modal);
        document.getElementById('equity-breakdown-close').addEventListener('click', ()=> modal.style.display='none');
        window.addEventListener('click', evt=>{ if(evt.target===modal) modal.style.display='none';});
    }
});

// Initialize customer view page
function initializeCustomerView(customerId) {
    currentCustomer = customerId;
    updateConfigStatusBadge();
    loadCustomersList().then(() => {
        // Auto-generate offers for the current customer
        generateOffersForCustomer(customerId);
    });
}

// Load all customers from API
async function loadCustomersList() {
    try {
        const response = await fetch('/api/customers');
        allCustomers = await response.json();
        
        // Populate customer dropdown if it exists
        const customerSelect = document.getElementById('customer-select');
        if (customerSelect && allCustomers.length > 0) {
            customerSelect.innerHTML = '';
            allCustomers.forEach(customer => {
                const option = document.createElement('option');
                option.value = customer.customer_id;
                option.textContent = `Customer ${customer.customer_id} (${customer.risk_profile_name})`;
                if (customer.customer_id == currentCustomer) {
                    option.selected = true;
                }
                customerSelect.appendChild(option);
            });
            
            // Add event listener for dropdown changes
            customerSelect.addEventListener('change', function() {
                const newCustomerId = this.value;
                if (newCustomerId && newCustomerId !== currentCustomer) {
                    window.location.href = `/customer/${newCustomerId}`;
                }
            });
        }
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

// Generate offers for a specific customer
async function generateOffersForCustomer(customerId) {
    showLoading();
    
    try {
        // Find customer data
        const customer = allCustomers.find(c => c.customer_id == customerId);
        if (!customer) {
            console.error('Customer not found');
            showNoResults();
            return;
        }
        
        // Prepare request data
        const requestData = {
            customer_data: {
                customer_id: customer.customer_id,
                current_monthly_payment: customer.current_monthly_payment,
                vehicle_equity: customer.vehicle_equity,
                current_car_price: customer.current_car_price,
                risk_profile_name: customer.risk_profile_name,
                risk_profile_index: customer.risk_profile_index
            },
            inventory: await loadInventory(),
            engine_config: buildEngineConfigForRequest()
        };
        
        const response = await fetch('/api/generate-offers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || 'Failed to generate offers');
        }
        
        displayOffers(result.offers, customer);
        
    } catch (error) {
        console.error('Error generating offers:', error);
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// Load inventory data
async function loadInventory() {
    try {
        const response = await fetch('/api/inventory');
        const inventory = await response.json();
        return inventory;
    } catch (error) {
        console.error('Error loading inventory from API:', error);
        // Fallback to CSV approach
        return loadInventoryFromCSV();
    }
}

// Fallback CSV loading method
async function loadInventoryFromCSV() {
    try {
        const response = await fetch('/sample_inventory_data.csv');
        const csvText = await response.text();
        
        const lines = csvText.split('\n').slice(1);
        const inventory = [];
        
        lines.forEach(line => {
            if (line.trim()) {
                const [car_id, model, sales_price] = line.split(',');
                inventory.push({
                    car_id: parseInt(car_id),
                    model: model,
                    sales_price: parseFloat(sales_price)
                });
            }
        });
        
        return inventory;
    } catch (error) {
        console.error('Error loading inventory from CSV:', error);
        return [];
    }
}

// Display offers in the UI
function displayOffers(offersByTier, customer) {
    const resultsContainer = document.getElementById('results-container');
    const noResultsDiv = document.getElementById('no-results');
    
    if (!offersByTier || Object.keys(offersByTier).length === 0) {
        showNoResults();
        return;
    }
    
    // Hide no results and show results container
    if (noResultsDiv) noResultsDiv.style.display = 'none';
    if (resultsContainer) resultsContainer.style.display = 'block';
    
    // Update offers summary
    updateOffersSummary(offersByTier, customer);
    
    // Display offers by tier
    displayOffersByTier(offersByTier);
}

// Update the offers summary KPIs
function updateOffersSummary(offersByTier, customer) {
    const summaryContainer = document.getElementById('offers-summary');
    if (!summaryContainer) return;
    
    const totalOffers = Object.values(offersByTier).reduce((sum, offers) => sum + offers.length, 0);
    const tierCount = Object.keys(offersByTier).length;
    
    // Calculate average NPV
    let totalNPV = 0;
    let offerCount = 0;
    Object.values(offersByTier).forEach(offers => {
        offers.forEach(offer => {
            totalNPV += offer.npv || 0;
            offerCount++;
        });
    });
    const avgNPV = offerCount > 0 ? totalNPV / offerCount : 0;
    
    // Get best offer (highest NPV)
    let bestOffer = null;
    Object.values(offersByTier).forEach(offers => {
        offers.forEach(offer => {
            if (!bestOffer || (offer.npv || 0) > (bestOffer.npv || 0)) {
                bestOffer = offer;
            }
        });
    });
    
    summaryContainer.innerHTML = `
        <div class="kpi-card">
            <div class="kpi-value">${totalOffers}</div>
            <div class="kpi-label">Total Offers</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">${tierCount}</div>
            <div class="kpi-label">Available Tiers</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">$${Math.round(avgNPV).toLocaleString()}</div>
            <div class="kpi-label">Average NPV</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">${bestOffer ? '$' + Math.round(bestOffer.monthly_payment).toLocaleString() : 'N/A'}</div>
            <div class="kpi-label">Best Payment</div>
        </div>
    `;
}

// Display offers organized by tier
function displayOffersByTier(offersByTier) {
    const container = document.getElementById('offers-by-tier');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Define tier order for consistent display
    const tierOrder = ['Refresh', 'Upgrade', 'Max Upgrade'];
    
    tierOrder.forEach(tier => {
        if (offersByTier[tier] && offersByTier[tier].length > 0) {
            const tierSection = createTierSection(tier, offersByTier[tier]);
            container.appendChild(tierSection);
        }
    });
    
    // Handle any additional tiers not in the standard order
    Object.keys(offersByTier).forEach(tier => {
        if (!tierOrder.includes(tier) && offersByTier[tier].length > 0) {
            const tierSection = createTierSection(tier, offersByTier[tier]);
            container.appendChild(tierSection);
        }
    });
}

// Create a tier section element
function createTierSection(tierName, offers) {
    const section = document.createElement('div');
    section.className = 'section-card tier-section';
    
    const header = document.createElement('div');
    header.className = 'tier-header';
    header.innerHTML = `
        <h4>${tierName} Tier</h4>
        <span class="tier-count">${offers.length} offers</span>
    `;
    
    const offersGrid = document.createElement('div');
    offersGrid.className = 'offers-grid';
    
    offers.forEach(offer => {
        const offerCard = createOfferCard(offer);
        // Store offer JSON for later breakdown click
        offerCard.dataset.offer = JSON.stringify(offer);
        offersGrid.appendChild(offerCard);
    });
    
    section.appendChild(header);
    section.appendChild(offersGrid);
    
    return section;
}

// Create an individual offer card
function createOfferCard(offer) {
    const card = document.createElement('div');
    card.className = 'offer-card';
    
    // Use the payment_delta that's already calculated in the offer (as percentage)
    const paymentDelta = offer.payment_delta * 100; // Convert from decimal to percentage
    const paymentDeltaClass = paymentDelta > 0 ? 'positive' : 'negative';
    const paymentDeltaColor = paymentDelta > 0 ? 'success' : 'danger';
    
    card.innerHTML = `
        <div class="offer-card-header">
            <h5>${offer.car_model}</h5>
        </div>
        <div class="offer-details">
            <div class="detail-row">
                <span class="detail-label">Car Price</span>
                <span class="detail-value">$${Math.round(offer.new_car_price).toLocaleString()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">New Payment</span>
                <span class="detail-value primary">$${Math.round(offer.monthly_payment).toLocaleString()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Payment Change</span>
                <span class="detail-value ${paymentDeltaColor} ${paymentDeltaClass}">${Math.abs(paymentDelta).toFixed(1)}%</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Loan Term</span>
                <span class="detail-value">${offer.term} months</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Financed Balance</span>
                <span class="detail-value clickable financed-balance">$${calculateFinancedBalance(offer).total.toLocaleString()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Vehicle Equity</span>
                <span class="detail-value clickable vehicle-equity">$${Math.round(offer.effective_equity || 0).toLocaleString()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">NPV</span>
                <span class="detail-value success">$${Math.round(offer.npv || 0).toLocaleString()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Interest Rate (APR)</span>
                <span class="detail-value">${(offer.interest_rate*100).toFixed(2)} %</span>
            </div>
            <hr class="offer-divider">
            <div class="fee-components">
                ${renderFeeComponent('Service Fee',
                    offer.fees_applied?.service_fee_pct ?? 0,
                    true)}
                ${renderFeeComponent('CXA Fee',
                    offer.fees_applied?.cxa_pct ?? 0,
                    true)}
                ${renderFeeComponent('CAC Bonus',
                    offer.fees_applied?.cac_bonus ?? 0,
                    false,
                    true)}
                ${renderFeeComponent('Insurance',
                    offer.insurance_amount ?? 0,
                    false)}
                ${renderFeeComponent('Kavak Total',
                    offer.kavak_total_amount ?? 0,
                    false)}
                ${renderFeeComponent('GPS Instalación',
                    offer.gps_install_fee ?? 0,
                    false)}
                ${renderFeeComponent('GPS Mensual',
                    offer.gps_monthly_fee ?? 0,
                    false)}
            </div>
        </div>
    `;

    const amortBtn = document.createElement('button');
    amortBtn.className = 'btn-secondary';
    amortBtn.textContent = 'View Amortization';
    amortBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        viewAmortizationTable(offer);
    });
    card.appendChild(amortBtn);

    return card;
}

// Helper: Render a single fee component row with checkmark / cross
function renderFeeComponent(label, rawValue, isPercent=false, treatZeroAsCross=false) {
    const isApplied = rawValue && rawValue !== 0;
    const checkSymbol = isApplied ? '✅' : '❌';

    if (!isApplied && treatZeroAsCross) {
        return `<div class="fee-row"><span>${checkSymbol} ${label}</span><span>$0</span></div>`;
    }

    let displayValue;
    if (isPercent) {
        displayValue = `${(rawValue * 100).toFixed(1)} %`;
    } else {
        displayValue = `$${Math.round(rawValue).toLocaleString()}`;
    }

    return `<div class="fee-row"><span>${checkSymbol} ${label}</span><span>${displayValue}</span></div>`;
}

// Fetch amortization table and display in modal
async function viewAmortizationTable(offer) {
    try {
        const response = await fetch('/api/amortization-table', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(offer)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to get table');
        showAmortizationModal(data.table);
    } catch (err) {
        console.error('Amortization error', err);
    }
}

function showAmortizationModal(table) {
    const modal = document.getElementById('amortization-modal');
    const container = document.getElementById('amortization-table');
    if (!modal || !container) return;
    let html = '<table class="amort-table"><tr><th>Month</th><th>Beginning Balance</th><th>Payment</th><th>Principal</th><th>Interest</th><th>Ending Balance</th></tr>';
    table.forEach(row => {
        html += `<tr><td>${row.month}</td><td>$${Math.round(row.beginning_balance).toLocaleString()}</td><td>$${Math.round(row.payment).toLocaleString()}</td><td>$${Math.round(row.principal).toLocaleString()}</td><td>$${Math.round(row.interest).toLocaleString()}</td><td>$${Math.round(row.ending_balance).toLocaleString()}</td></tr>`;
    });
    html += '</table>';
    container.innerHTML = html;
    modal.style.display = 'block';
}

function closeAmortizationModal() {
    const modal = document.getElementById('amortization-modal');
    if (modal) modal.style.display = 'none';
}

// Show loading state
function showLoading() {
    const loadingDiv = document.getElementById('loading-state');
    const resultsDiv = document.getElementById('results-container');
    const noResultsDiv = document.getElementById('no-results');
    
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (resultsDiv) resultsDiv.style.display = 'none';
    if (noResultsDiv) noResultsDiv.style.display = 'none';
}

// Hide loading state
function hideLoading() {
    const loadingDiv = document.getElementById('loading-state');
    if (loadingDiv) loadingDiv.style.display = 'none';
}

// Show no results state
function showNoResults() {
    const loadingDiv = document.getElementById('loading-state');
    const resultsDiv = document.getElementById('results-container');
    const noResultsDiv = document.getElementById('no-results');
    
    if (loadingDiv) loadingDiv.style.display = 'none';
    if (resultsDiv) resultsDiv.style.display = 'none';
    if (noResultsDiv) noResultsDiv.style.display = 'block';
}

// Show error state
function showError(message) {
    const loadingDiv = document.getElementById('loading-state');
    const resultsDiv = document.getElementById('results-container');
    const noResultsDiv = document.getElementById('no-results');
    
    if (loadingDiv) loadingDiv.style.display = 'none';
    if (resultsDiv) resultsDiv.style.display = 'none';
    if (noResultsDiv) {
        noResultsDiv.style.display = 'block';
        noResultsDiv.innerHTML = `
            <div class="section-card">
                <div class="no-offers-state">
                    <h3>Error Generating Offers</h3>
                    <p>${message}</p>
                    <button class="btn-primary" onclick="generateOffersForCustomer(currentCustomer)">Try Again</button>
                </div>
            </div>
        `;
    }
}

// Add event listener for generate offers button
document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-offers-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', function() {
            if (currentCustomer) {
                generateOffersForCustomer(currentCustomer);
            }
        });
    }
});

// Initialize configuration page
function initializeConfigPage() {
    console.log("🔧 Initializing Configuration Page");
    
    // Set up range slider value displays
    const sliders = [
        { id: 'service-fee', suffix: '%' },
        { id: 'cxa-fee', suffix: '%' },
        { id: 'cac-bonus', prefix: '$', suffix: '', format: 'currency' }
    ];
    
    sliders.forEach(slider => {
        const element = document.getElementById(slider.id);
        const valueDisplay = element?.parentElement.querySelector('.range-value');
        
        if (element && valueDisplay) {
            element.addEventListener('input', function() {
                let displayValue = this.value;
                if (slider.format === 'currency') {
                    displayValue = '$' + parseInt(this.value).toLocaleString();
                } else {
                    displayValue = (slider.prefix || '') + this.value + (slider.suffix || '');
                }
                valueDisplay.textContent = displayValue;
            });
        }
    });
    
    // Set up engine mode radio buttons
    const engineModeRadios = document.querySelectorAll('input[name="engine-mode"]');
    engineModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            toggleEngineMode(this.value);
        });
    });
    
    // Set up range optimization inputs with live calculation
    const rangeOptInputs = document.querySelectorAll('#range-config input[type="number"]');
    rangeOptInputs.forEach(input => {
        input.addEventListener('input', updateRangeSummary);
    });
    
    // Set up form buttons
    const runScenarioBtn = document.getElementById('run-scenario');
    const resetConfigBtn = document.getElementById('reset-config');
    
    if (runScenarioBtn) {
        runScenarioBtn.addEventListener('click', runScenarioAnalysis);
    }
    
    if (resetConfigBtn) {
        resetConfigBtn.addEventListener('click', resetConfiguration);
    }
    
    // Initialize engine mode
    toggleEngineMode('default');
    // Initialize range summary
    updateRangeSummary();

    // Show current configuration status
    updateConfigStatusBadge();
}

// Toggle engine mode visibility and behavior
function toggleEngineMode(mode) {
    // This function is now primarily handled in the global_config.html selectMode() function
    // We just need to update the range summary if in range mode
    if (mode === 'range') {
        updateRangeSummary();
    }
    
    // Update any additional UI elements based on mode if needed
    console.log(`Engine mode changed to: ${mode}`);
}

// Update range summary calculations
function updateRangeSummary() {
    const serviceFeeMin = parseFloat(document.getElementById('service-fee-min')?.value || 0);
    const serviceFeeMax = parseFloat(document.getElementById('service-fee-max')?.value || 5);
    const serviceFeeStep = parseFloat(document.getElementById('service-fee-step')?.value || 0.01);
    
    const cxaMin = parseFloat(document.getElementById('cxa-min')?.value || 0);
    const cxaMax = parseFloat(document.getElementById('cxa-max')?.value || 4);
    const cxaStep = parseFloat(document.getElementById('cxa-step')?.value || 0.01);
    
    const cacBonusMin = parseFloat(document.getElementById('cac-bonus-min')?.value || 0);
    const cacBonusMax = parseFloat(document.getElementById('cac-bonus-max')?.value || 10000);
    const cacBonusStep = parseFloat(document.getElementById('cac-bonus-step')?.value || 100);
    
    // Calculate number of values for each parameter
    const serviceFeeCount = Math.floor((serviceFeeMax - serviceFeeMin) / serviceFeeStep) + 1;
    const cxaCount = Math.floor((cxaMax - cxaMin) / cxaStep) + 1;
    const cacBonusCount = Math.floor((cacBonusMax - cacBonusMin) / cacBonusStep) + 1;
    
    const totalCombinations = serviceFeeCount * cxaCount * cacBonusCount;
    
    // Update display
    const serviceFeeCountEl = document.getElementById('service-fee-count');
    const cxaCountEl = document.getElementById('cxa-count');
    const cacBonusCountEl = document.getElementById('cac-bonus-count');
    const totalCombinationsEl = document.getElementById('total-combinations');
    const performanceWarning = document.getElementById('performance-warning');
    
    if (serviceFeeCountEl) serviceFeeCountEl.textContent = serviceFeeCount.toLocaleString();
    if (cxaCountEl) cxaCountEl.textContent = cxaCount.toLocaleString();
    if (cacBonusCountEl) cacBonusCountEl.textContent = cacBonusCount.toLocaleString();
    if (totalCombinationsEl) totalCombinationsEl.textContent = totalCombinations.toLocaleString();
    
    // Show/hide performance warning based on combination count
    if (performanceWarning) {
        if (totalCombinations > 1000000) {
            performanceWarning.style.display = 'block';
            performanceWarning.innerHTML = `⚠️ <strong>High computation load:</strong> This configuration will test over ${(totalCombinations / 1000000).toFixed(1)}M parameter combinations. Consider reducing ranges or increasing step sizes for faster results.`;
        } else if (totalCombinations > 100000) {
            performanceWarning.style.display = 'block';
            performanceWarning.innerHTML = `⚠️ <strong>Moderate computation load:</strong> This configuration will test ${totalCombinations.toLocaleString()} parameter combinations. Execution may take several minutes.`;
        } else {
            performanceWarning.style.display = 'none';
        }
    }
}

// Fetch and display current configuration status
async function updateConfigStatusBadge(){
    try{
        const res = await fetch('/api/config-status');
        const status = await res.json();
        const badge = document.getElementById('config-status-badge');
        if(badge){
            badge.style.display = 'inline-block';
            badge.textContent = `${status.mode} • ${status.last_updated}`;
        }
    }catch(_){ }
}

// Load scenario results summary on dashboard
async function loadDashboardScenarioSummary(){
    const container = document.getElementById('dashboard-scenario-summary');
    if(!container) return;
    try{
        const result = await fetch('/api/scenario-results').then(r=>r.json());
        if(result && result.actual_metrics){
            const m = result.actual_metrics;
            const mode = result.mode_info?.mode || '';
            const last = result.scenario_config?.last_updated || '';
            container.innerHTML = `
                <div class="kpi-card">
                    <div class="kpi-value">${mode}</div>
                    <div class="kpi-label">Mode</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">${last}</div>
                    <div class="kpi-label">Last Run</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">${m.total_offers.toLocaleString()}</div>
                    <div class="kpi-label">Total Offers</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">$${Math.round(m.average_npv_per_offer).toLocaleString()}</div>
                    <div class="kpi-label">Avg. Offer NPV</div>
                </div>`;
            container.style.display = 'grid';
        }
    }catch(_){ }
}

// Run scenario analysis
async function runScenarioAnalysis() {
    const loadingModal = document.getElementById('loading-modal');
    const progressBar = document.getElementById('progress-bar') || document.querySelector('#loading-modal .progress-bar');
    const status = document.getElementById('loading-status') || document.getElementById('status');
    const configButton = document.getElementById('run-scenario');

    if (loadingModal) loadingModal.style.display = 'block';
    if (status) status.textContent = 'Initializing analysis...';
    if (configButton){
        configButton.disabled = true;
        configButton.dataset.originalText = configButton.textContent;
        configButton.textContent = 'Running...';
    }

    // TODO: collect actual form data for scenario config
    const configData = typeof getConfigFormData === 'function' ? getConfigFormData() : {};

    // Attempt to fetch customer count for better progress estimation
    let totalCustomers = 0;
    try {
        const allCustomers = await fetch('/api/customers').then(res => res.json());
        totalCustomers = Array.isArray(allCustomers) ? allCustomers.length : 0;
    } catch (_) {
        totalCustomers = 0;
    }

    let processedTicks = 0;
    const estimatedDuration = totalCustomers > 0 ? Math.min(totalCustomers * 150, 60000) : 30000; // fallback 30s
    const interval = setInterval(() => {
        processedTicks += 100;
        const percentage = Math.min(Math.round((processedTicks / estimatedDuration) * 100), 95);
        if (progressBar) progressBar.style.width = percentage + '%';
        if (status) status.textContent = `Processing... ${percentage}%`;
    }, 100);

    try {
        // First save config so backend knows what to run
        await fetch('/api/save-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });

        const es = new EventSource('/api/scenario-analysis-stream');
        clearInterval(interval);

        es.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data);
            const percent = data.percent || 0;
            if (progressBar) progressBar.style.width = `${percent}%`;
            if (status) status.textContent = `Processing ${data.processed} of ${data.total} customers... (${percent}%)`;
        });

        es.addEventListener('finished', (e) => {
            const data = JSON.parse(e.data);
            if (progressBar) progressBar.style.width = '100%';
            if (status) status.textContent = 'Analysis complete!';
            es.close();
            if(configButton){
                configButton.disabled=false;
                configButton.textContent=configButton.dataset.originalText||'Run Analysis';
            }
            setTimeout(() => {
                window.location.href = '/customers';
            }, 1000);
        });

        es.addEventListener('error', (e) => {
            console.error('SSE error', e);
            es.close();
            if(configButton){configButton.disabled=false;configButton.textContent=configButton.dataset.originalText||'Run Analysis';}
            showConfigError(e.message || 'Unknown error');
        });

    } catch (err) {
        showConfigError(err.message || 'Unknown error');
    } finally {
        if (loadingModal) loadingModal.style.display = 'none';
    }
}

// Display scenario results
function displayScenarioResults(result) {
    const resultsDiv = document.getElementById('scenario-results');
    const impactSummary = document.getElementById('impact-summary');
    const currentMetrics = document.getElementById('current-metrics');
    const newMetrics = document.getElementById('new-metrics');
    
    if (!resultsDiv || !impactSummary) return;
    
    // Show results section
    resultsDiv.style.display = 'block';
    
    // Extract metrics from real engine run
    const metrics = result.actual_metrics;
    const execDetails = result.execution_details;
    const modeInfo = result.mode_info;
    const tierDist = metrics.tier_distribution;
    
    // Calculate tier distribution percentages
    const totalTierOffers = Object.values(tierDist).reduce((a, b) => a + b, 0);
    
    impactSummary.innerHTML = `
        <div class="kpi-card">
            <div class="kpi-value">${metrics.total_offers.toLocaleString()}</div>
            <div class="kpi-label">Total Portfolio Offers</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">$${metrics.average_npv_per_offer.toLocaleString()}</div>
            <div class="kpi-label">Average NPV per Offer</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">${metrics.offers_per_customer}</div>
            <div class="kpi-label">Offers per Customer</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">$${(metrics.total_portfolio_npv / 1000000).toFixed(1)}M</div>
            <div class="kpi-label">Total Portfolio NPV</div>
        </div>
    `;
    
    // Update execution details
    if (currentMetrics) {
        currentMetrics.innerHTML = `
            <h4>🔬 Execution Details</h4>
            <div class="metric-item">
                <span class="metric-label">Mode</span>
                <span class="metric-value">${modeInfo.mode}</span>
            </div>
            ${modeInfo.parameter_combinations > 0 ? `
            <div class="metric-item">
                <span class="metric-label">Parameter Combinations</span>
                <span class="metric-value">${modeInfo.parameter_combinations.toLocaleString()}</span>
            </div>
            ` : ''}
            <div class="metric-item">
                <span class="metric-label">Customers Processed</span>
                <span class="metric-value">${execDetails.processed_customers} of ${execDetails.sample_size}</span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Execution Time</span>
                <span class="metric-value">${execDetails.execution_time_seconds}s</span>
            </div>
            ${execDetails.processing_errors > 0 ? `
            <div class="metric-item">
                <span class="metric-label">Processing Errors</span>
                <span class="metric-value" style="color: #ef4444;">${execDetails.processing_errors}</span>
            </div>
            ` : ''}
        `;
    }
    
    // Update tier distribution
    if (newMetrics) {
        newMetrics.innerHTML = `
            <h4>📊 Tier Distribution</h4>
            <div class="metric-item">
                <span class="metric-label">Refresh Tier</span>
                <span class="metric-value">
                    ${tierDist.Refresh.toLocaleString()}
                    <span class="metric-subtitle">(${totalTierOffers > 0 ? ((tierDist.Refresh / totalTierOffers) * 100).toFixed(1) : 0}%)</span>
                </span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Upgrade Tier</span>
                <span class="metric-value">
                    ${tierDist.Upgrade.toLocaleString()}
                    <span class="metric-subtitle">(${totalTierOffers > 0 ? ((tierDist.Upgrade / totalTierOffers) * 100).toFixed(1) : 0}%)</span>
                </span>
            </div>
            <div class="metric-item">
                <span class="metric-label">Max Upgrade Tier</span>
                <span class="metric-value">
                    ${tierDist['Max Upgrade'].toLocaleString()}
                    <span class="metric-subtitle">(${totalTierOffers > 0 ? ((tierDist['Max Upgrade'] / totalTierOffers) * 100).toFixed(1) : 0}%)</span>
                </span>
            </div>
            <div class="metric-item" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e5e7eb;">
                <span class="metric-label"><strong>Total Offers</strong></span>
                <span class="metric-value"><strong>${totalTierOffers.toLocaleString()}</strong></span>
            </div>
        `;
    }
    
    // Add note about extrapolation
    const noteDiv = document.createElement('div');
    noteDiv.className = 'alert alert-info';
    noteDiv.style.marginTop = '20px';
    noteDiv.innerHTML = `
        <strong>📌 Note:</strong> Results are based on a sample of ${execDetails.sample_size} customers 
        ${execDetails.total_customers > execDetails.sample_size ? `and extrapolated to the full portfolio of ${execDetails.total_customers.toLocaleString()} customers` : ''}.
        The configuration has been saved and will be used for future offer generation.
    `;
    resultsDiv.appendChild(noteDiv);
}

// Reset configuration to defaults
function resetConfiguration() {
    // Engine Mode - reset to default
    const defaultModeRadio = document.getElementById('default-mode');
    if (defaultModeRadio) {
        defaultModeRadio.checked = true;
        toggleEngineMode('default');
    }
    
    // Fee Structure defaults
    const serviceFee = document.getElementById('service-fee');
    const cxaFee = document.getElementById('cxa-fee');
    const cacBonus = document.getElementById('cac-bonus');
    const kavakToggle = document.getElementById('kavak-total-toggle');
    const insuranceAmount = document.getElementById('insurance-amount');
    const gpsFee = document.getElementById('gps-fee');
    
    // Payment Delta Thresholds defaults
    const refreshMin = document.getElementById('refresh-min');
    const refreshMax = document.getElementById('refresh-max');
    const upgradeMin = document.getElementById('upgrade-min');
    const upgradeMax = document.getElementById('upgrade-max');
    const maxUpgradeMin = document.getElementById('max-upgrade-min');
    const maxUpgradeMax = document.getElementById('max-upgrade-max');
    
    // Engine Behavior defaults
    const termPriority = document.getElementById('term-priority');
    const minNPV = document.getElementById('min-npv');
    
    // Reset Range Optimization inputs
    const serviceFeeMin = document.getElementById('service-fee-min');
    const serviceFeeMax = document.getElementById('service-fee-max');
    const serviceFeeStep = document.getElementById('service-fee-step');
    const cxaMin = document.getElementById('cxa-min');
    const cxaMax = document.getElementById('cxa-max');
    const cxaStep = document.getElementById('cxa-step');
    const cacBonusMin = document.getElementById('cac-bonus-min');
    const cacBonusMax = document.getElementById('cac-bonus-max');
    const cacBonusStep = document.getElementById('cac-bonus-step');
    const maxOffersPerTier = document.getElementById('max-offers-per-tier');
    
    if (serviceFeeMin) serviceFeeMin.value = 0;
    if (serviceFeeMax) serviceFeeMax.value = 5;
    if (serviceFeeStep) serviceFeeStep.value = 0.01;
    if (cxaMin) cxaMin.value = 0;
    if (cxaMax) cxaMax.value = 4;
    if (cxaStep) cxaStep.value = 0.01;
    if (cacBonusMin) cacBonusMin.value = 0;
    if (cacBonusMax) cacBonusMax.value = 10000;
    if (cacBonusStep) cacBonusStep.value = 100;
    if (maxOffersPerTier) maxOffersPerTier.value = 50;
    
    // Reset Fee Structure
    if (serviceFee) {
        serviceFee.value = 5;
        serviceFee.parentElement.querySelector('.range-value').textContent = '5%';
    }
    if (cxaFee) {
        cxaFee.value = 4;
        cxaFee.parentElement.querySelector('.range-value').textContent = '4%';
    }
    if (cacBonus) {
        cacBonus.value = 5000;
        cacBonus.parentElement.querySelector('.range-value').textContent = '$5,000';
    }
    if (kavakToggle) kavakToggle.checked = true;
    if (insuranceAmount) insuranceAmount.value = 10999;
    if (gpsFee) gpsFee.value = 350;
    
    // Reset Payment Delta Thresholds
    if (refreshMin) refreshMin.value = -5;
    if (refreshMax) refreshMax.value = 5;
    if (upgradeMin) upgradeMin.value = 5.01;
    if (upgradeMax) upgradeMax.value = 25;
    if (maxUpgradeMin) maxUpgradeMin.value = 25.01;
    if (maxUpgradeMax) maxUpgradeMax.value = 100;
    
    // Reset Engine Behavior
    if (termPriority) termPriority.value = 'standard';
    if (minNPV) minNPV.value = 5000;
    
    // Hide results section
    const resultsDiv = document.getElementById('scenario-results');
    if (resultsDiv) resultsDiv.style.display = 'none';
    
    // Update range summary with reset values
    updateRangeSummary();
}

// Show configuration loading state
function showConfigLoading() {
    const loadingDiv = document.getElementById('config-loading');
    const resultsDiv = document.getElementById('scenario-results');
    
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (resultsDiv) resultsDiv.style.display = 'none';
}

// Hide configuration loading state
function hideConfigLoading() {
    const loadingDiv = document.getElementById('config-loading');
    if (loadingDiv) loadingDiv.style.display = 'none';
}

// Show configuration error
function showConfigError(message) {
    const loadingDiv = document.getElementById('config-loading');
    if (loadingDiv) {
        loadingDiv.innerHTML = `
            <div class="no-offers-state">
                <h3>Error Running Analysis</h3>
                <p>${message}</p>
                <button class="btn-primary" onclick="runScenarioAnalysis()">Try Again</button>
            </div>
        `;
    }
}

// ---------------------
// Customer List Page
// ---------------------

async function initializeCustomerListPage() {
    const tbody = document.getElementById('customer-list-body');
    const summaryContainer = document.getElementById('scenario-summary');
    updateConfigStatusBadge();
    if (!tbody) return;

    try {
        const [customers, scenarioResults] = await Promise.all([
            fetch('/api/customers').then(r => r.json()),
            fetch('/api/scenario-results').then(r => r.json()).catch(() => ({}))
        ]);

        // Populate summary if available
        if (summaryContainer && scenarioResults && scenarioResults.actual_metrics) {
            const metrics = scenarioResults.actual_metrics;
            summaryContainer.innerHTML = `
                <div class="kpi-card">
                    <div class="kpi-value">${metrics.total_offers.toLocaleString()}</div>
                    <div class="kpi-label">Total Offers</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">$${Math.round(metrics.average_npv_per_offer).toLocaleString()}</div>
                    <div class="kpi-label">Avg. Offer NPV</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">${metrics.offers_per_customer}</div>
                    <div class="kpi-label">Offers / Customer</div>
                </div>`;
            summaryContainer.style.display = 'grid';
        }

        // Clear body
        tbody.innerHTML = '';
        customers.slice(0, 200).forEach(cust => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><a href="/customer/${cust.customer_id}" class="id-link">${cust.customer_id}</a></td>
                <td>${cust.current_car_model || 'Unknown'}</td>
                <td><span class="risk-badge risk-${cust.risk_profile_name || 'default'}">${cust.risk_profile_name || 'N/A'}</span></td>
                <td>N/A</td>
                <td>N/A</td>
                <td><a href="/customer/${cust.customer_id}" class="view-btn">Generate Offers →</a></td>`;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error('Failed to load customer list page', err);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#ef4444;">Failed to load customer data</td></tr>';
        }
    }
}

// Tier filter logic (customer view)
document.addEventListener('DOMContentLoaded', () => {
  const tierSelect = document.getElementById('tier-select');
  if (tierSelect) {
      tierSelect.addEventListener('change', () => {
          const selected = tierSelect.value;
          document.querySelectorAll('.offers-section').forEach(sec => {
              if (selected === 'all') {
                  sec.style.display = 'block';
              } else {
                  if (sec.querySelector('h4')?.textContent?.startsWith(selected)) {
                      sec.style.display = 'block';
                  } else {
                      sec.style.display = 'none';
                  }
              }
          });
      });
  }
});

function buildEngineConfigForRequest(){
    const modeSel=document.getElementById('mode-select');
    const mode=modeSel?modeSel.value:'current';
    if(mode==='current') return {}; // rely on saved config
    if(mode==='default') return {use_custom_params:false,use_range_optimization:false,include_kavak_total:true};
    if(mode==='custom'){
        // For demo we pull values from the global config form if present else defaults
        return {
            use_custom_params:true,
            use_range_optimization:false,
            include_kavak_total:true,
            service_fee_pct:parseFloat(document.getElementById('service-fee')?.value||5)/100,
            cxa_pct:parseFloat(document.getElementById('cxa-fee')?.value||4)/100,
            cac_bonus:parseFloat(document.getElementById('cac-bonus')?.value||5000),
            insurance_amount:parseFloat(document.getElementById('insurance-amount')?.value||10999),
            gps_fee:parseFloat(document.getElementById('gps-fee')?.value||350)
        };
    }
    if(mode==='range'){
        return {use_custom_params:false,use_range_optimization:true,include_kavak_total:true};
    }
    return {};
}

// calculateFinancedBalance moved above with breakdown capability
function calculateFinancedBalance(offer){
    const breakdown = {
        "Loan Amount": offer.loan_amount || 0,
        "Service Fee": offer.service_fee_amount || 0,
        "Kavak Total": offer.kavak_total_amount || 0,
        "Insurance (first cycle)": offer.insurance_amount || 0,
        // GPS installation is paid upfront, not financed
    };
    const total = Object.values(breakdown).reduce((a,b)=>a+b,0);
    return {total, breakdown};
}

// calculateEquityBreakdown moved above with breakdown capability
function calculateEquityBreakdown(offer){
    // Reverse-engineer the original vehicle equity:
    // effective_equity = vehicle_equity + CAC - CXA - GPS_install
    const startingEquity = (offer.effective_equity || 0)
        - (offer.fees_applied?.cac_bonus || 0)
        + (offer.cxa_amount || 0)
        + (offer.gps_install_fee || 0);
    const breakdown = {
        "Starting Vehicle Equity": startingEquity,
        "+ CAC Bonus": offer.fees_applied?.cac_bonus || 0,
        "- CXA Fee": -(offer.cxa_amount || 0),
        "- GPS Installation": -(offer.gps_install_fee || 0)
    };
    const total = offer.effective_equity || 0;
    return {total, breakdown};
}

// Attach delegated click listener once
document.addEventListener('click', function(evt){
    const target = evt.target;
    if(target && target.classList.contains('financed-balance')){
        const card = target.closest('.offer-card');
        if(!card) return;
        const offerStr = card.dataset.offer;
        if(!offerStr) return;
        const offer = JSON.parse(offerStr);
        const {total, breakdown} = calculateFinancedBalance(offer);
        showBalanceBreakdownModal(total, breakdown);
    }
    if(target && target.classList.contains('vehicle-equity')){
        const card = target.closest('.offer-card');
        if(!card) return;
        const offerStr = card.dataset.offer;
        if(!offerStr) return;
        const offer = JSON.parse(offerStr);
        const {total, breakdown} = calculateEquityBreakdown(offer);
        showGenericBreakdownModal('equity', total, breakdown);
    }
});

function showBalanceBreakdownModal(total, breakdown){
    showGenericBreakdownModal('balance', total, breakdown);
}

function showGenericBreakdownModal(type, total, breakdown){
    const modalId = type==='equity' ? 'equity-breakdown-modal' : 'balance-breakdown-modal';
    const tableId = type==='equity' ? 'equity-breakdown-table' : 'balance-breakdown-table';
    const modal = document.getElementById(modalId);
    const container = document.getElementById(tableId);
    if(!modal||!container) return;
    let html='<table class="amort-table"><tr><th>Component</th><th>Amount</th></tr>';
    for(const [label, val] of Object.entries(breakdown)){
        html += `<tr><td>${label}</td><td>$${Math.round(val).toLocaleString()}</td></tr>`;
    }
    html += `<tr><th>Total</th><th>$${Math.round(total).toLocaleString()}</th></tr></table>`;
    container.innerHTML = html;
    modal.style.display = 'block';
} 
