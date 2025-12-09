import { fetchTransformationSummary } from '../api/openai_service.js';
import { fetchLineageData } from '../api/neo4j_service.js';
import { renderDAG } from './dag_renderer.js';

export async function openModal(metricName) {
    const modal = document.getElementById('transformation-modal');
    const modalTitle = document.getElementById('modal-title');
    const summaryContent = document.getElementById('summary-content');
    const dagContainer = document.getElementById('dag-container');

    // Update title
    modalTitle.textContent = `Metric Transformation: ${metricName}`;

    // Show loading state
    summaryContent.innerHTML = '<p>Loading transformation summary...</p>';
    dagContainer.innerHTML = '<p style="padding: 2rem; text-align: center;">Loading lineage diagram...</p>';

    // Show modal
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    try {
        // Fetch data in parallel
        const [summary, lineageData] = await Promise.all([
            fetchTransformationSummary(metricName),
            fetchLineageData(metricName)
        ]);

        // Render summary
        console.log('Fetched summary:', summary);
        summaryContent.innerHTML = formatSummary(summary);

        // Clear and render DAG
        dagContainer.innerHTML = '';
        renderDAG(dagContainer, lineageData);
    } catch (error) {
        console.error('Error loading modal data:', error);
        summaryContent.innerHTML = '<p style="color: #e74c3c;">Error loading transformation summary.</p>';
        dagContainer.innerHTML = '<p style="padding: 2rem; text-align: center; color: #e74c3c;">Error loading lineage diagram.</p>';
    }
}

export function closeModal() {
    const modal = document.getElementById('transformation-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = 'auto';

    // Clear DAG to free memory
    const dagContainer = document.getElementById('dag-container');
    dagContainer.innerHTML = '';
}

function formatSummary(summary) {
    // Format the AI-generated summary with proper HTML structure
    let html = `<p>${summary.description}</p>`;

    // TODO: Add example and data flow if available
    if (summary.steps && summary.steps.length > 0) {
        html += '<p><strong>Calculation Steps:</strong></p><ul>';
        summary.steps.forEach((step, index) => {
            html += `<li><strong>${index + 1}. ${step.title}:</strong> ${step.description}</li>`;
        });
        html += '</ul>';
    }

    if (summary.businessContext) {
        html += `<p style="font-style: italic; color: #6c757d; margin-top: 1rem;">${summary.businessContext}</p>`;
    }

    return html;
}