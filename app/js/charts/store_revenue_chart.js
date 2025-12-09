export async function renderStoreRevenueChart() {
    const container = d3.select('#chart-store-revenue');
    const width = container.node().offsetWidth;
    const height = container.node().offsetHeight;
    const margin = { top: 20, right: 20, bottom: 60, left: 60 };

    // Load data from CSV
    const data = await d3.csv('data/month_revenue_by_location.csv', d => ({
        location: d.location,
        revenue: +d.revenue
    }));

    // Create SVG
    const svg = container.append('svg')
        .attr('width', width)
        .attr('height', height);

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Scales
    const xScale = d3.scaleBand()
        .domain(data.map(d => d.location))
        .range([0, chartWidth])
        .padding(0.3);

    const yScale = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.revenue) * 1.1])
        .range([chartHeight, 0]);

    // Color scale
    const colorScale = d3.scaleOrdinal()
        .domain(['Philadelphia', 'Brooklyn', 'Chicago', 'San Francisco'])
        .range(['#2ecc71', '#3498db', '#f39c12', '#e74c3c']);

    // Axes
    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale).ticks(5);

    g.append('g')
        .attr('class', 'axis')
        .attr('transform', `translate(0,${chartHeight})`)
        .call(xAxis);

    g.append('g')
        .attr('class', 'axis')
        .call(yAxis);

    // Draw bars
    g.selectAll('.bar')
        .data(data)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', d => xScale(d.location))
        .attr('y', d => yScale(d.revenue))
        .attr('width', xScale.bandwidth())
        .attr('height', d => chartHeight - yScale(d.revenue))
        .attr('fill', d => colorScale(d.location))
        .on('mouseover', function(event, d) {
            d3.select(this).style('opacity', 0.8);
            showTooltip(event, `${d.location}: $${d.revenue}`);
        })
        .on('mouseout', function() {
            d3.select(this).style('opacity', 1);
            hideTooltip();
        });
}

function showTooltip(event, text) {
    d3.select('body').append('div')
        .attr('class', 'tooltip visible')
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px')
        .text(text);
}

function hideTooltip() {
    d3.selectAll('.tooltip').remove();
}