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
});

// Initialize customer view page
function initializeCustomerView(customerId) {
    currentCustomer = customerId;
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
            engine_config: {
                include_kavak_total: true
            }
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
                <span class="detail-label">Loan Amount</span>
                <span class="detail-value">$${Math.round(offer.loan_amount).toLocaleString()}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">NPV</span>
                <span class="detail-value success">$${Math.round(offer.npv || 0).toLocaleString()}</span>
            </div>
        </div>
    `;
    
    return card;
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

// Run scenario analysis
async function runScenarioAnalysis() {
    showConfigLoading();
    
    try {
        // Collect form data
        const formData = getConfigFormData();
        
        // First save the configuration
        const saveResponse = await fetch('/api/save-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!saveResponse.ok) {
            throw new Error('Failed to save configuration');
        }
        
        // Show progress message
        const loadingDiv = document.getElementById('config-loading');
        if (loadingDiv) {
            loadingDiv.innerHTML = `
                <div class="loading-animation"></div>
                <h3>🎯 Running Real Engine Analysis...</h3>
                <p>Processing customers with ${formData.use_range_optimization ? 'Range Optimization' : (formData.use_custom_params ? 'Custom Parameters' : 'Default Hierarchical')} mode...</p>
                <p><small>This may take a moment as we're actually running the engine for each customer.</small></p>
            `;
        }
        
        // Call scenario analysis API
        const response = await fetch('/api/scenario-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Scenario analysis failed');
        }
        
        const result = await response.json();
        displayScenarioResults(result);
        
    } catch (error) {
        console.error('Error running scenario analysis:', error);
        showConfigError(error.message);
    } finally {
        hideConfigLoading();
    }
}

// Get configuration form data
function getConfigFormData() {
    const engineMode = document.querySelector('input[name="engine-mode"]:checked')?.value || 'default';
    
    const baseConfig = {
        use_custom_params: engineMode === 'custom',
        use_range_optimization: engineMode === 'range',
        include_kavak_total: document.getElementById('kavak-total-toggle')?.checked !== false,
        min_npv_threshold: parseFloat(document.getElementById('min-npv')?.value || 5000)
    };
    
    // If using range optimization mode
    if (engineMode === 'range') {
        return {
            ...baseConfig,
            // Range parameters
            service_fee_range: [
                parseFloat(document.getElementById('service-fee-min')?.value || 0),
                parseFloat(document.getElementById('service-fee-max')?.value || 5)
            ],
            service_fee_step: parseFloat(document.getElementById('service-fee-step')?.value || 0.01),
            cxa_range: [
                parseFloat(document.getElementById('cxa-min')?.value || 0),
                parseFloat(document.getElementById('cxa-max')?.value || 4)
            ],
            cxa_step: parseFloat(document.getElementById('cxa-step')?.value || 0.01),
            cac_bonus_range: [
                parseFloat(document.getElementById('cac-bonus-min')?.value || 0),
                parseFloat(document.getElementById('cac-bonus-max')?.value || 10000)
            ],
            cac_bonus_step: parseFloat(document.getElementById('cac-bonus-step')?.value || 100),
            max_offers_per_tier: parseFloat(document.getElementById('max-offers-per-tier')?.value || 50),
            
            // Include other configuration if needed
            insurance_amount: parseFloat(document.getElementById('insurance-amount')?.value || 10999),
            gps_fee: parseFloat(document.getElementById('gps-fee')?.value || 350),
            
            // Payment Delta Thresholds
            payment_delta_tiers: {
                refresh: [
                    parseFloat(document.getElementById('refresh-min')?.value || -5) / 100,
                    parseFloat(document.getElementById('refresh-max')?.value || 5) / 100
                ],
                upgrade: [
                    parseFloat(document.getElementById('upgrade-min')?.value || 5.01) / 100,
                    parseFloat(document.getElementById('upgrade-max')?.value || 25) / 100
                ],
                max_upgrade: [
                    parseFloat(document.getElementById('max-upgrade-min')?.value || 25.01) / 100,
                    parseFloat(document.getElementById('max-upgrade-max')?.value || 100) / 100
                ]
            }
        };
    }
    
    // If using custom parameters mode
    if (engineMode === 'custom') {
        return {
            ...baseConfig,
            // Fee Structure
            service_fee_pct: parseFloat(document.getElementById('service-fee')?.value || 5) / 100,
            cxa_pct: parseFloat(document.getElementById('cxa-fee')?.value || 4) / 100,
            cac_bonus: parseFloat(document.getElementById('cac-bonus')?.value || 5000),
            insurance_amount: parseFloat(document.getElementById('insurance-amount')?.value || 10999),
            gps_fee: parseFloat(document.getElementById('gps-fee')?.value || 350),
            
            // Payment Delta Thresholds
            payment_delta_tiers: {
                refresh: [
                    parseFloat(document.getElementById('refresh-min')?.value || -5) / 100,
                    parseFloat(document.getElementById('refresh-max')?.value || 5) / 100
                ],
                upgrade: [
                    parseFloat(document.getElementById('upgrade-min')?.value || 5.01) / 100,
                    parseFloat(document.getElementById('upgrade-max')?.value || 25) / 100
                ],
                max_upgrade: [
                    parseFloat(document.getElementById('max-upgrade-min')?.value || 25.01) / 100,
                    parseFloat(document.getElementById('max-upgrade-max')?.value || 100) / 100
                ]
            },
            
            // Engine Behavior
            term_priority: document.getElementById('term-priority')?.value || 'standard'
        };
    }
    
    // If using default mode, only return basic config
    return baseConfig;
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