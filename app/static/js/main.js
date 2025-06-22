// This file will contain the logic for interactivity, such as:
// - Fetching offer data for a customer from the API
// - Handling the filtering of offers on the client-side
// - Powering the searchable customer dropdown
// - Managing the global configuration form

// Kavak Trade-Up Engine Dashboard JavaScript
let currentCustomer = null;
let allCustomers = [];

// Global flag to prevent unwanted modal display
let allowAmortizationModal = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log("🚗 Kavak Dashboard JS Loaded");
    
    // Page-specific initializers
    if (document.getElementById('customer-list-body')) {
        initializeCustomerListPage();
    }
    if (document.querySelector('.customer-view-container')) {
        // The customer ID is usually passed from the template
        // For this to work, ensure your customer_view.html has a data attribute
        const customerId = document.querySelector('.customer-view-container').dataset.customerId;
        if (customerId) {
            initializeCustomerView(customerId);
        }
    }
    if (document.getElementById('config-status-banner')) {
        initializeConfigPage();
    }
    if (document.getElementById('dashboard-scenario-summary')) {
        loadDashboardScenarioSummary();
    }

    // Generic modal setup
    setupModals();
});

function setupModals() {
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

    // Create generic breakdown modal if it doesn't exist
    if (!document.getElementById('generic-breakdown-modal')) {
        const modal = document.createElement('div');
        modal.id = 'generic-breakdown-modal';
        modal.className = 'modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="modal-close" id="generic-breakdown-close">&times;</span>
                <h3 id="generic-breakdown-title">Breakdown</h3>
                <div id="generic-breakdown-table"></div>
            </div>`;
        document.body.appendChild(modal);
        document.getElementById('generic-breakdown-close').addEventListener('click', () => modal.style.display = 'none');
        window.addEventListener('click', evt => { if (evt.target === modal) modal.style.display = 'none'; });
    }
}

// ---------------------
// Customer View Page
// ---------------------
function initializeCustomerView(customerId) {
    console.log('🏁 Initializing customer view for:', customerId);
    currentCustomer = customerId;
    allowAmortizationModal = false; // Reset flag
    loadCustomersList().then(() => {
        generateOffersForCustomer(customerId);
    });
}

async function loadCustomersList() {
    try {
        const response = await fetch('/api/customers?limit=5000');
        const data = await response.json();
        allCustomers = data.customers || data;
        
        const customerSelect = document.getElementById('customer-select');
        if (customerSelect && allCustomers.length > 0) {
            allCustomers.forEach(customer => {
                const option = document.createElement('option');
                option.value = customer.customer_id;
                option.textContent = `Customer ${customer.customer_id} (${customer.risk_profile_name})`;
                if (customer.customer_id == currentCustomer) {
                    option.selected = true;
                }
                customerSelect.appendChild(option);
            });
            customerSelect.addEventListener('change', () => {
                window.location.href = `/customer/${customerSelect.value}`;
            });
        }
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

async function generateOffersForCustomer(customerId) {
    showLoading();
    try {
        const customer = allCustomers.find(c => c.customer_id == customerId);
        if (!customer) throw new Error('Customer not found');
        
        const requestData = {
            customer_data: customer,
            inventory: await fetch('/api/inventory').then(r => r.json()),
            engine_config: {} // Use saved config on backend
        };
        
        const response = await fetch('/api/generate-offers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Failed to generate offers');
        
        displayOffers(result.offers, customer);
    } catch (error) {
        console.error('Error generating offers:', error);
        showError(error.message);
    } finally {
        hideLoading();
    }
}

function displayOffers(offersByTier, customer) {
    if (!offersByTier || Object.keys(offersByTier).length === 0) {
        showNoResults();
        return;
    }
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('results-container').style.display = 'block';
    
    updateOffersSummary(offersByTier, customer);
    displayOffersByTier(offersByTier);
}

function updateOffersSummary(offersByTier, customer) {
    const summaryContainer = document.getElementById('offers-summary');
    if (!summaryContainer) return;
    
    const allOffers = Object.values(offersByTier).flat();
    const totalOffers = allOffers.length;
    const avgNPV = totalOffers > 0 ? allOffers.reduce((sum, offer) => sum + (offer.npv || 0), 0) / totalOffers : 0;
    const bestOffer = allOffers.reduce((best, offer) => (!best || (offer.npv || 0) > (best.npv || 0) ? offer : best), null);
    
    summaryContainer.innerHTML = `
        <div class="kpi-card"><div class="kpi-value">${totalOffers}</div><div class="kpi-label">Total Offers</div></div>
        <div class="kpi-card"><div class="kpi-value">${Object.keys(offersByTier).length}</div><div class="kpi-label">Available Tiers</div></div>
        <div class="kpi-card"><div class="kpi-value">$${Math.round(avgNPV).toLocaleString()}</div><div class="kpi-label">Average NPV</div></div>
        <div class="kpi-card"><div class="kpi-value">${bestOffer ? '$' + Math.round(bestOffer.monthly_payment).toLocaleString() : 'N/A'}</div><div class="kpi-label">Best Payment</div></div>
    `;
}

function displayOffersByTier(offersByTier) {
    const container = document.getElementById('offers-by-tier');
    if (!container) return;
    container.innerHTML = '';
    const tierOrder = ['Refresh', 'Upgrade', 'Max Upgrade'];
    
    tierOrder.forEach(tier => {
        if (offersByTier[tier]) {
            container.appendChild(createTierSection(tier, offersByTier[tier]));
        }
    });
}

function createTierSection(tierName, offers) {
    const section = document.createElement('div');
    section.className = 'section-card tier-section';
    section.innerHTML = `<div class="tier-header"><h4>${tierName} Tier</h4><span class="tier-count">${offers.length} offers</span></div>`;
    
    const offersGrid = document.createElement('div');
    offersGrid.className = 'offers-grid';
    offers.forEach(offer => {
        offersGrid.appendChild(createOfferCard(offer));
    });
    section.appendChild(offersGrid);
    return section;
}

function createOfferCard(offer) {
    const card = document.createElement('div');
    card.className = 'offer-card';
    card.dataset.offer = JSON.stringify(offer);
    
    const paymentDelta = (offer.payment_delta || 0) * 100;
    const paymentDeltaClass = paymentDelta > 0 ? 'positive' : 'negative';
    const paymentDeltaColor = paymentDelta > 0 ? 'success' : 'danger';
    
    card.innerHTML = `
        <div class="offer-card-header"><h5>${offer.car_model}</h5></div>
        <div class="offer-details">
            <div class="detail-row"><span>Car Price</span><span class="detail-value">$${Math.round(offer.new_car_price).toLocaleString()}</span></div>
            <div class="detail-row"><span>New Payment</span><span class="detail-value primary">$${Math.round(offer.monthly_payment).toLocaleString()}</span></div>
            <div class="detail-row"><span>Payment Change</span><span class="detail-value ${paymentDeltaColor} ${paymentDeltaClass}">${Math.abs(paymentDelta).toFixed(1)}%</span></div>
            <div class="detail-row"><span>Term</span><span class="detail-value">${offer.term} months</span></div>
            <div class="detail-row"><span>Financed Balance</span><span class="detail-value clickable financed-balance">$${(offer.loan_amount || 0).toLocaleString()}</span></div>
            <div class="detail-row"><span>Effective Equity</span><span class="detail-value clickable vehicle-equity">$${Math.round(offer.effective_equity || 0).toLocaleString()}</span></div>
            <div class="detail-row"><span>NPV</span><span class="detail-value success">$${Math.round(offer.npv || 0).toLocaleString()}</span></div>
        </div>
    `;
    const amortBtn = document.createElement('button');
    amortBtn.className = 'btn-secondary';
    amortBtn.textContent = 'View Amortization';
    amortBtn.onclick = () => viewAmortizationTable(offer);
    card.appendChild(amortBtn);
    return card;
}

async function viewAmortizationTable(offer) {
    allowAmortizationModal = true;
    try {
        const response = await fetch('/api/amortization-table', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(offer)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        showAmortizationModal(data.table);
    } catch (err) {
        showAmortizationError(err.message);
    }
}

function showAmortizationModal(table) {
    if (!allowAmortizationModal) return;
    const modal = document.getElementById('amortization-modal');
    const container = document.getElementById('amortization-table');
    if (!table || table.length === 0) {
        container.innerHTML = '<p class="no-data">No amortization data available</p>';
    } else {
        let html = `
            <table class="amort-table">
                <thead><tr><th>Month</th><th>Beginning Balance</th><th>Payment</th><th>Principal</th><th>Interest</th><th>Ending Balance</th></tr></thead>
                <tbody>${table.map(row => `<tr>
                    <td>${row.month}</td>
                    <td>$${Math.round(row.beginning_balance || 0).toLocaleString()}</td>
                    <td>$${Math.round(row.payment || 0).toLocaleString()}</td>
                    <td>$${Math.round(row.principal || 0).toLocaleString()}</td>
                    <td>$${Math.round(row.interest || 0).toLocaleString()}</td>
                    <td>$${Math.round(row.ending_balance || 0).toLocaleString()}</td>
                </tr>`).join('')}</tbody>
            </table>`;
        container.innerHTML = html;
    }
    modal.style.display = 'block';
}

function showAmortizationError(message) {
    if (!allowAmortizationModal) return;
    const container = document.getElementById('amortization-table');
    container.innerHTML = `<div class="error-state"><h3>Error Loading Table</h3><p>${message}</p></div>`;
    document.getElementById('amortization-modal').style.display = 'block';
}

function closeAmortizationModal() {
    const modal = document.getElementById('amortization-modal');
    if (modal) modal.style.display = 'none';
    allowAmortizationModal = false;
}

function showLoading() {
    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('results-container').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loading-state').style.display = 'none';
}

function showNoResults() {
    hideLoading();
    document.getElementById('no-results').style.display = 'block';
}

function showError(message) {
    hideLoading();
    const noResultsDiv = document.getElementById('no-results');
    noResultsDiv.style.display = 'block';
    noResultsDiv.innerHTML = `<div class="section-card"><div class="no-offers-state"><h3>Error</h3><p>${message}</p></div></div>`;
}

// Delegated click listener for breakdown modals
document.addEventListener('click', function(evt){
    const target = evt.target;
    if (target.matches('.financed-balance, .vehicle-equity')) {
        const card = target.closest('.offer-card');
        if (!card) return;
        const offer = JSON.parse(card.dataset.offer);
        const isFinanced = target.classList.contains('financed-balance');
        const title = isFinanced ? 'Financed Balance Breakdown' : 'Effective Equity Breakdown';
        const breakdown = isFinanced ? 
            { "Loan Amount": offer.loan_amount || 0, "Service Fee": offer.service_fee_amount || 0, "Kavak Total": offer.kavak_total_amount || 0, "Insurance": offer.insurance_amount || 0 } : 
            { "Vehicle Equity": offer.vehicle_equity || 0, "+ CAC Bonus": offer.fees_applied?.cac_bonus || 0, "- CXA Fee": -(offer.cxa_amount || 0) };
        
        showGenericBreakdownModal(title, breakdown);
    }
});

function showGenericBreakdownModal(title, breakdown) {
    document.getElementById('generic-breakdown-title').textContent = title;
    const tableContainer = document.getElementById('generic-breakdown-table');
    const total = Object.values(breakdown).reduce((sum, val) => sum + val, 0);
    
    tableContainer.innerHTML = `
        <table class="breakdown-table">
            <tbody>
                ${Object.entries(breakdown).map(([key, value]) => `
                    <tr><td>${key}</td><td>$${Math.round(value).toLocaleString()}</td></tr>`).join('')}
            </tbody>
            <tfoot>
                <tr><td>Total</td><td>$${Math.round(total).toLocaleString()}</td></tr>
            </tfoot>
        </table>`;
    document.getElementById('generic-breakdown-modal').style.display = 'block';
}


// ---------------------
// Customer List Page
// ---------------------
let customerPage = 1;
const customerLimit = 100;
let customerTotal = null;
let loadingCustomers = false;

async function initializeCustomerListPage() {
    const tbody = document.getElementById('customer-list-body');
    const countSpan = document.getElementById('customer-count');
    if (!tbody) return;

    tbody.innerHTML = '';

    const renderRows = (custList) => {
        custList.forEach(cust => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><a href="/customer/${cust.customer_id}" class="id-link">${cust.customer_id}</a></td>
                <td>${cust.current_car_model || 'Unknown'}</td>
                <td><span class="risk-badge risk-${cust.risk_profile_name || 'default'}">${cust.risk_profile_name || 'N/A'}</span></td>
                <td>$${Math.round(cust.current_monthly_payment).toLocaleString()}</td>
                <td>$${Math.round(cust.vehicle_equity).toLocaleString()}</td>
                <td><a href="/customer/${cust.customer_id}" class="view-btn">Generate Offers →</a></td>`;
            tbody.appendChild(tr);
        });
    };

    const loadNextPage = async () => {
        if (loadingCustomers) return;
        if (customerTotal !== null && allCustomers.length >= customerTotal) return;
        loadingCustomers = true;
        try {
            const data = await fetch(`/api/customers?page=${customerPage}&limit=${customerLimit}`).then(r => r.json());
            const customers = data.customers || [];
            customerTotal = data.total;
            allCustomers = allCustomers.concat(customers);
            renderRows(customers);
            if (countSpan) {
                countSpan.textContent = `${allCustomers.length} / ${customerTotal} customers loaded`;
            }
            customerPage += 1;
        } catch (err) {
            tbody.innerHTML = '<tr><td colspan="6">Failed to load customer data.</td></tr>';
        } finally {
            loadingCustomers = false;
        }
    };

    await loadNextPage();

    window.addEventListener('scroll', () => {
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 100) {
            loadNextPage();
        }
    });
}

// ---------------------
// Dashboard Page
// ---------------------
async function loadDashboardScenarioSummary() {
    const container = document.getElementById('dashboard-scenario-summary');
    if (!container) return;
    try {
        const results = await fetch('/api/scenario-results').then(res => res.json());
        if (!results || !results.actual_metrics) {
            container.innerHTML = '<p>No scenario has been run yet. <a href="/config">Configure and run one</a>.</p>';
            return;
        }
        const metrics = results.actual_metrics;
        const details = results.execution_details;
        const config = results.scenario_config;
        
        container.innerHTML = `
            <div class="summary-header">
                <h3>Latest Scenario: ${results.mode_info.mode}</h3>
                <p>Ran at ${new Date(config.last_updated).toLocaleString()}</p>
            </div>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-value">${metrics.total_offers.toLocaleString()}</div>
                    <div class="kpi-label">Total Offers</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">$${Math.round(metrics.average_npv_per_offer).toLocaleString()}</div>
                    <div class="kpi-label">Average Offer NPV</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">${metrics.offers_per_customer}</div>
                    <div class="kpi-label">Offers / Customer</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">${details.processed_customers} / ${details.total_customers}</div>
                    <div class="kpi-label">Customers Processed</div>
                </div>
            </div>
        `;
    } catch (err) {
        container.innerHTML = '<p>Could not load scenario results.</p>';
    }
}

/**
 * =================================================================================
 * CONFIGURATION PAGE (/config)
 * =================================================================================
 */
function initializeConfigPage() {
    // --- DOM Elements ---
    const elements = {
        modeRadios: document.querySelectorAll('input[name="engine-mode"]'),
        customSection: document.getElementById('custom-config-section'),
        rangeSection: document.getElementById('range-config-section'),
        saveBtn: document.getElementById('save-config-btn'),
        runBtn: document.getElementById('run-analysis-btn'),
        resetBtn: document.getElementById('reset-config-btn'),
        modal: document.getElementById('config-loading-modal'),
        modalTitle: document.getElementById('loading-modal-title'),
        modalMessage: document.getElementById('loading-modal-message'),
        statusBanner: document.getElementById('config-status-banner'),
        statusTitle: document.getElementById('config-status-title'),
        statusMessage: document.getElementById('config-status-message'),
        rangeSummary: {
            serviceFee: { min: document.getElementById('range-service-fee-min'), max: document.getElementById('range-service-fee-max'), step: document.getElementById('range-service-fee-step'), count: document.getElementById('service-fee-count') },
            cxaFee: { min: document.getElementById('range-cxa-fee-min'), max: document.getElementById('range-cxa-fee-max'), step: document.getElementById('range-cxa-fee-step'), count: document.getElementById('cxa-fee-count') },
            cacBonus: { min: document.getElementById('range-cac-bonus-min'), max: document.getElementById('range-cac-bonus-max'), step: document.getElementById('range-cac-bonus-step'), count: document.getElementById('cac-bonus-count') },
            total: document.getElementById('total-combinations'),
            warning: document.getElementById('performance-warning')
        },
        searchMethod: document.getElementById('range-search-method')
    };

    // --- State & Logic ---
    const showLoadingModal = (title, message) => {
        elements.modalTitle.textContent = title;
        elements.modalMessage.textContent = message;
        elements.modal.style.display = 'flex';
    };

    const hideLoadingModal = () => {
        elements.modal.style.display = 'none';
    };

    const updateStatusBanner = (mode, lastUpdated) => {
        elements.statusTitle.textContent = `Current Mode: ${mode}`;
        elements.statusMessage.textContent = `Last saved: ${lastUpdated || 'Never'}`;
        elements.statusBanner.style.borderColor = '#4ade80'; // Success color
        elements.statusBanner.querySelector('.status-icon').style.backgroundColor = '#4ade80';
    };
    
    const getFormData = () => {
        const mode = document.querySelector('input[name="engine-mode"]:checked').value;
        const data = {
            use_custom_params: mode === 'custom',
            use_range_optimization: mode === 'range'
        };

        if (mode === 'custom') {
            data.service_fee_pct = parseFloat(document.getElementById('custom-service-fee').value) / 100;
            data.cxa_pct = parseFloat(document.getElementById('custom-cxa-fee').value) / 100;
            data.cac_bonus = parseFloat(document.getElementById('custom-cac-bonus').value);
            data.insurance_amount = parseFloat(document.getElementById('custom-insurance').value);
            data.gps_installation_fee = parseFloat(document.getElementById('custom-gps-install').value);
            data.gps_monthly_fee = parseFloat(document.getElementById('custom-gps-monthly').value);
        } else if (mode === 'range') {
            data.service_fee_range = [parseFloat(elements.rangeSummary.serviceFee.min.value), parseFloat(elements.rangeSummary.serviceFee.max.value)];
            data.cxa_range = [parseFloat(elements.rangeSummary.cxaFee.min.value), parseFloat(elements.rangeSummary.cxaFee.max.value)];
            data.cac_bonus_range = [parseFloat(elements.rangeSummary.cacBonus.min.value), parseFloat(elements.rangeSummary.cacBonus.max.value)];
            data.service_fee_step = parseFloat(elements.rangeSummary.serviceFee.step.value);
            data.cxa_step = parseFloat(elements.rangeSummary.cxaFee.step.value);
            data.cac_bonus_step = parseFloat(elements.rangeSummary.cacBonus.step.value);
            data.range_search_method = elements.searchMethod.value;
        }
        return data;
    };

    const saveConfig = async () => {
        showLoadingModal('Saving Configuration...', 'Sending new parameters to the server.');
        try {
            const response = await fetch('/api/save-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getFormData())
            });
            if (!response.ok) throw new Error(`Server responded with ${response.status}`);
            const result = await response.json();
            const newMode = result.config.use_range_optimization ? 'Range Optimization' : (result.config.use_custom_params ? 'Custom Parameters' : 'Default');
            updateStatusBanner(newMode, result.config.last_updated);
            alert('Configuration saved successfully!');
        } catch (error) {
            alert(`Error saving configuration: ${error.message}`);
        } finally {
            hideLoadingModal();
        }
    };

    const runAnalysis = async () => {
        if (!confirm('This will save the current configuration and run a full analysis, which may take time. Are you sure you want to proceed?')) return;
        showLoadingModal('Running Full Analysis...', 'This might take a moment. The page will redirect to the dashboard when complete.');
        try {
            await fetch('/api/scenario-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getFormData())
            });
            window.location.href = '/'; 
        } catch (error) {
            hideLoadingModal();
            alert(`Error running analysis: ${error.message}`);
        }
    };
    
    const resetToDefaults = () => {
        if (!confirm('Are you sure you want to reset all settings to their defaults?')) return;
        
        document.getElementById('mode-default').checked = true;
        elements.customSection.style.display = 'none';
        elements.rangeSection.style.display = 'none';
        
        document.getElementById('custom-service-fee').value = 5;
        document.getElementById('custom-cxa-fee').value = 4;
        document.getElementById('custom-cac-bonus').value = 5000;
        document.getElementById('custom-insurance').value = 10999;
        document.getElementById('custom-gps-install').value = 750;
        document.getElementById('custom-gps-monthly').value = 350;
        document.querySelectorAll('.range-slider input').forEach(updateSliderDisplay);

        elements.rangeSummary.serviceFee.min.value = 0;
        elements.rangeSummary.serviceFee.max.value = 5;
        elements.rangeSummary.serviceFee.step.value = 0.5;
        elements.rangeSummary.cxaFee.min.value = 0;
        elements.rangeSummary.cxaFee.max.value = 4;
        elements.rangeSummary.cxaFee.step.value = 0.5;
        elements.rangeSummary.cacBonus.min.value = 0;
        elements.rangeSummary.cacBonus.max.value = 10000;
        elements.rangeSummary.cacBonus.step.value = 1000;
        elements.searchMethod.value = 'exhaustive';
        updateAllRangeCounts();
    };

    const updateSliderDisplay = (slider) => {
        const display = slider.nextElementSibling;
        let value = parseFloat(slider.value);
        if (slider.id.includes('cac')) {
            display.textContent = `$${value.toLocaleString()}`;
        } else {
            display.textContent = `${value.toFixed(1)}%`;
        }
    };

    const updateAllRangeCounts = () => {
        const calc = (min, max, step) => step > 0 ? Math.floor((max - min) / step) + 1 : 0;
        
        const counts = {
            service: calc(parseFloat(elements.rangeSummary.serviceFee.min.value), parseFloat(elements.rangeSummary.serviceFee.max.value), parseFloat(elements.rangeSummary.serviceFee.step.value)),
            cxa: calc(parseFloat(elements.rangeSummary.cxaFee.min.value), parseFloat(elements.rangeSummary.cxaFee.max.value), parseFloat(elements.rangeSummary.cxaFee.step.value)),
            cac: calc(parseFloat(elements.rangeSummary.cacBonus.min.value), parseFloat(elements.rangeSummary.cacBonus.max.value), parseFloat(elements.rangeSummary.cacBonus.step.value))
        };
        
        elements.rangeSummary.serviceFee.count.textContent = counts.service;
        elements.rangeSummary.cxaFee.count.textContent = counts.cxa;
        elements.rangeSummary.cacBonus.count.textContent = counts.cac;
        
        const total = counts.service * counts.cxa * counts.cac;
        elements.rangeSummary.total.textContent = total.toLocaleString();

        if (total > 100000) {
            elements.rangeSummary.warning.textContent = '⚠️ High number of combinations may impact performance.';
            elements.rangeSummary.warning.style.display = 'block';
        } else {
            elements.rangeSummary.warning.style.display = 'none';
        }
    };

    // --- Initial Setup ---
    elements.modeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            elements.customSection.style.display = e.target.value === 'custom' ? 'block' : 'none';
            elements.rangeSection.style.display = e.target.value === 'range' ? 'block' : 'none';
        });
    });

    elements.saveBtn.addEventListener('click', saveConfig);
    elements.runBtn.addEventListener('click', runAnalysis);
    elements.resetBtn.addEventListener('click', resetToDefaults);

    document.querySelectorAll('.range-slider input').forEach(slider => {
        slider.addEventListener('input', () => updateSliderDisplay(slider));
        updateSliderDisplay(slider);
    });
    
    ['serviceFee', 'cxaFee', 'cacBonus'].forEach(key => {
        const group = elements.rangeSummary[key];
        group.min.addEventListener('input', updateAllRangeCounts);
        group.max.addEventListener('input', updateAllRangeCounts);
        group.step.addEventListener('input', updateAllRangeCounts);
    });

    fetch('/api/config-status')
        .then(res => res.json())
        .then(data => updateStatusBanner(data.mode, data.last_updated))
        .catch(err => {
            console.error("Failed to load config status:", err);
            updateStatusBanner('Error', 'Could not connect to server');
            elements.statusBanner.style.borderColor = '#f43f5e'; // Error color
        });

    updateAllRangeCounts();
}