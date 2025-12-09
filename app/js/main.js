import { renderRevenueChart } from './charts/revenue_chart.js';
import { renderOrderChart } from './charts/new_customer_order_chart.js';
import { renderLargeNumber } from './charts/large_number.js';
import { renderStoreRevenueChart } from './charts/store_revenue_chart.js';
import { openModal, closeModal } from './modal/modal_controller.js';

// Initialize application
async function init() {
    try {
        // Render all charts
        await renderRevenueChart();
        await renderOrderChart();
        await renderLargeNumber();
        await renderStoreRevenueChart();

        // Set up modal event listeners
        setupModalListeners();
    } catch (error) {
        console.error('Error initializing dashboard:', error);
    }
}

// Set up modal event listeners
function setupModalListeners() {
    // Info icon click handlers
    const infoButtons = document.querySelectorAll('.info-icon');
    infoButtons.forEach(button => {
        button.addEventListener('click', async (e) => {
            const metricName = e.currentTarget.dataset.metric;
            await openModal(metricName);
        });
    });

    // Close button handler
    const closeButton = document.querySelector('.close-button');
    closeButton.addEventListener('click', closeModal);

    // Close on overlay click
    const modal = document.getElementById('transformation-modal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
}

// Start the application
init();