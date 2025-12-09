export class LineChart {
    constructor(containerId, data_path, useKFormat) {
        this.container = d3.select(`#${containerId}`);
        this.data_path = data_path
        this.useKFormat = useKFormat || false;
    }

    async loadData() {
        const raw = await d3.csv(this.data_path);

        // Detect metric name from header (second column after "month")
        const columns = raw.columns;
        const metricName = columns[1];   // e.g. "revenue", "new_customer_orders", etc.
        this.metricName = metricName;

        // Parse dataset
        return raw.map(d => ({
            month: d3.timeParse('%Y-%m')(d.month),
            value: +d[metricName]       // store under a generic field
        }));
    }


    async renderChart() {
        const data = await this.loadData();
        this.render(data);
    }


    render(data) {
        const width = this.container.node().offsetWidth;
        const height = this.container.node().offsetHeight;
        const margin = { top: 20, right: 20, bottom: 40, left: 60 };

        // Tooltip functions
        function showTooltip(event, text) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'tooltip visible')
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .text(text);
        }

        function hideTooltip() {
            d3.selectAll('.tooltip').remove();
        }

        // Create SVG
        const svg = this.container.append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        // Scales
        const xScale = d3.scaleTime()
            .domain(d3.extent(data, d => d.month))
            .range([0, chartWidth]);

        const yScale = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.value) * 1.1])
            .range([chartHeight, 0]);

        // Axes
        const xAxis = d3.axisBottom(xScale)
            .ticks(6)
            .tickFormat(d3.timeFormat('%Y-%m'));

        const yAxis = d3.axisLeft(yScale)
            .ticks(5)
            .tickFormat(d => {
            if (this.useKFormat) {
                return `$${d / 1000}K`;   // revenue-style
            }
            return d;                     // raw value (e.g., num of orders)
        });

        g.append('g')
            .attr('class', 'axis')
            .attr('transform', `translate(0,${chartHeight})`)
            .call(xAxis);

        g.append('g')
            .attr('class', 'axis')
            .call(yAxis);

        // Line generator
        const line = d3.line()
            .x(d => xScale(d.month))
            .y(d => yScale(d.value))
            .curve(d3.curveMonotoneX);

        // Draw line
        g.append('path')
            .datum(data)
            .attr('class', 'line')
            .attr('d', line)
            .attr('stroke', '#3498db')
            .attr('stroke-width', 3);

        // Add dots
        g.selectAll('.dot')
            .data(data)
            .enter()
            .append('circle')
            .attr('class', 'dot')
            .attr('cx', d => xScale(d.month))
            .attr('cy', d => yScale(d.value))
            .attr('r', 4)
            .attr('fill', '#3498db')
            .on('mouseover', function(event, d) {
                d3.select(this).attr('r', 6);

                const timeText = d3.timeFormat('%Y-%m')(d.month);
                let valueText;

                if (this.useKFormat) {
                    valueText = `$${(d.value / 1000).toFixed(1)}K`;
                } else {
                    valueText = d.value;
                }

                showTooltip(event, `${timeText}: ${valueText}`);
            })
            .on('mouseout', function() {
                d3.select(this).attr('r', 4);
                hideTooltip();
            });

    }

}