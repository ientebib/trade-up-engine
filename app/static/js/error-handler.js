/**
 * Global Error Handler and Loading State Manager
 * Provides consistent error handling and loading states across the application
 */

// Loading state manager
const LoadingManager = {
    activeLoaders: new Set(),
    
    show(elementId, message = 'Loading...') {
        this.activeLoaders.add(elementId);
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.dataset.originalContent = element.innerHTML;
        element.innerHTML = `
            <div class="loading-state" style="text-align: center; padding: 2rem;">
                <i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: #1451EC;"></i>
                <p style="margin-top: 1rem; color: #666;">${message}</p>
            </div>
        `;
    },
    
    hide(elementId) {
        this.activeLoaders.delete(elementId);
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // If there's original content, restore it
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
            delete element.dataset.originalContent;
        }
    },
    
    showProgress(elementId, progress, message = 'Processing...') {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.innerHTML = `
            <div class="loading-state" style="text-align: center; padding: 2rem;">
                <i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: #1451EC;"></i>
                <p style="margin-top: 1rem; color: #666;">${message}</p>
                <div style="width: 80%; margin: 1rem auto; background: #e0e0e0; border-radius: 10px; overflow: hidden;">
                    <div style="width: ${progress}%; background: #1451EC; height: 10px; transition: width 0.3s;"></div>
                </div>
                <p style="font-size: 0.9rem; color: #999;">${progress}% complete</p>
            </div>
        `;
    }
};

// Error handler
const ErrorHandler = {
    show(elementId, error, retry = null) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        let errorMessage = 'An unexpected error occurred';
        
        if (typeof error === 'string') {
            errorMessage = error;
        } else if (error.message) {
            errorMessage = error.message;
        } else if (error.detail) {
            errorMessage = error.detail;
        }
        
        let html = `
            <div class="error-state" style="text-align: center; padding: 2rem; background: #fee; border-radius: 8px; border: 1px solid #fcc;">
                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #f44336;"></i>
                <p style="margin-top: 1rem; color: #d32f2f; font-weight: 500;">${errorMessage}</p>
        `;
        
        if (retry && typeof retry === 'function') {
            html += `
                <button onclick="${retry.name}()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #1451EC; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    <i class="fas fa-redo"></i> Try Again
                </button>
            `;
        }
        
        html += '</div>';
        element.innerHTML = html;
    },
    
    handleApiError(error, defaultMessage = 'Failed to load data') {
        if (error.status === 404) {
            return 'Resource not found';
        } else if (error.status === 403) {
            return 'Access denied';
        } else if (error.status === 500) {
            return 'Server error - please try again later';
        } else if (error.status === 503) {
            return 'Service temporarily unavailable';
        } else if (error.message && error.message.includes('fetch')) {
            return 'Network error - please check your connection';
        }
        return defaultMessage;
    }
};

// Global fetch wrapper with timeout and error handling
async function fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        
        clearTimeout(timeout);
        
        if (!response.ok) {
            const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
            error.status = response.status;
            throw error;
        }
        
        return response;
    } catch (error) {
        clearTimeout(timeout);
        
        if (error.name === 'AbortError') {
            throw new Error('Request timed out');
        }
        throw error;
    }
}

// Auto-retry wrapper for flaky endpoints
async function fetchWithRetry(url, options = {}, maxRetries = 3, delay = 1000) {
    let lastError;
    
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fetchWithTimeout(url, options);
        } catch (error) {
            lastError = error;
            
            // Don't retry on client errors (4xx)
            if (error.status && error.status >= 400 && error.status < 500) {
                throw error;
            }
            
            // Wait before retrying
            if (i < maxRetries - 1) {
                await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
            }
        }
    }
    
    throw lastError;
}

// Export for use in other scripts
window.LoadingManager = LoadingManager;
window.ErrorHandler = ErrorHandler;
window.fetchWithTimeout = fetchWithTimeout;
window.fetchWithRetry = fetchWithRetry;