export async function renderSessionsChart() {
    const container = d3.select('#chart-sessions');
    const width = container.node().offsetWidth;
    const height = container.node().offsetHeight;
    const margin = { top: 20, right: 20, bottom: 40, left: 50 };

    // Load data from CSV
    const data = await d3.csv('data/sessions.csv', d => ({
        hour: +d.hour,
        sessions: +d.sessions
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
    const xScale = d3.scaleLinear()
        .domain([0, 23])
        .range([0, chartWidth]);

    const yScale = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.sessions) * 1.1])
        .range([chartHeight, 0]);

    // Axes
    const xAxis = d3.axisBottom(xScale)
        .ticks(12)
        .tickFormat(d => `${d}h`);

    const yAxis = d3.axisLeft(yScale).ticks(5);

    g.append('g')
        .attr('class', 'axis')
        .attr('transform', `translate(0,${chartHeight})`)
        .call(xAxis);

    g.append('g')
        .attr('class', 'axis')
        .call(yAxis);

    // Area generator
    const area = d3.area()
        .x(d => xScale(d.hour))
        .y0(chartHeight)
        .y1(d => yScale(d.sessions))
        .curve(d3.curveMonotoneX);

    // Draw area
    g.append('path')
        .datum(data)
        .attr('d', area)
        .attr('fill', '#3498db')
        .attr('opacity', 0.3);

    // Line generator
    const line = d3.line()
        .x(d => xScale(d.hour))
        .y(d => yScale(d.sessions))
        .curve(d3.curveMonotoneX);

    // Draw line
    g.append('path')
        .datum(data)
        .attr('class', 'line')
        .attr('d', line)
        .attr('stroke', '#3498db')
        .attr('stroke-width', 2);
}