export async function renderLargeNumber() {
    const container = d3.select('#chart-large-number');
    const width = container.node().offsetWidth;
    const height = container.node().offsetHeight;

    // Load data from CSV (keep both month + pct_large_orders just in case)
    const data = await d3.csv('data/monthly_pct_large_orders.csv', d => ({
        month: d.month,
        pct_large_orders: +d.pct_large_orders
    }));

    // Guard: need at least 1 row
    if (data.length < 1) {
        return;
    }

    // Latest record = last row
    const latest = data[data.length - 1];
    const latest_pct = latest.pct_large_orders;
    console.log('Latest large order pct:', latest_pct);

    // Previous record = second-to-last row (if exists)
    const previous = data.length > 1 ? data[data.length - 2] : null;
    const previous_pct = previous ? previous.pct_large_orders : null;
    console.log('Previous large order pct:', previous_pct);

    // Change between last two values
    const change = previous_pct !== null ? (latest_pct - previous_pct) : null;
    console.log('Change in large order pct:', change);

    // Create SVG
    const svg = container.append('svg')
        .attr('width', width)
        .attr('height', height);

    const centerX = width / 2;
    const centerY = height / 2;

    // Display large latest percentage
    svg.append('text')
        .attr('x', centerX)
        .attr('y', centerY - 10)
        .attr('text-anchor', 'middle')
        .attr('font-size', '48px')
        .attr('font-weight', 'bold')
        .attr('fill', '#2c3e50')
        .text(`${(latest_pct * 100).toFixed(1)}%`);

    // Build subtitle text for change (if we have at least 2 rows)
    let subtitleText = 'Latest value';
    if (change !== null) {
        const sign = change > 0 ? '+' : (change < 0 ? '−' : '');
        const absChange = Math.abs(change) * 100; // convert to percentage points
        subtitleText = `${sign}${absChange.toFixed(1)} vs previous month`;
    }

    // Display subtitle (change)
    svg.append('text')
        .attr('x', centerX)
        .attr('y', centerY + 30)
        .attr('text-anchor', 'middle')
        .attr('font-size', '14px')
        .attr('fill', '#7f8c8d')
        .text(subtitleText);
}
