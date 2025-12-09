export function renderDAG(container, data) {
    const width = container.offsetWidth;
    const height = 700;

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    // Legend height
    const legendHeight = 100;

    // Content group (all DAG nodes + edges move down together)
    const contentGroup = svg.append('g')
        .attr('class', 'dag-content')
        .attr('transform', `translate(0, ${legendHeight})`);

    // Define arrow marker
    contentGroup.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 0 10 10')
        .attr('refX', 9)
        .attr('refY', 5)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M 0 0 L 10 5 L 0 10 z')
        .attr('class', 'link-arrow');

    // Calculate layer positions
    const layerCount = data.layers.length;
    const layerWidth = (width - 60) / layerCount;
    const layerPositions = {};

    data.layers.forEach((layer, i) => {
        layerPositions[layer.index] = 30 + i * layerWidth + layerWidth / 2;
    });

    // Group nodes by layer
    const nodesByLayer = {};
    data.nodes.forEach(node => {
        if (!nodesByLayer[node.layer]) {
            nodesByLayer[node.layer] = [];
        }
        nodesByLayer[node.layer].push(node);
    });

    // Filter to only visible nodes (Column and Op types)
    const visibleNodes = data.nodes.filter(n => n.type === 'Column' || n.type === 'Op');

    // Build adjacency information
    const nodeConnections = {};
    visibleNodes.forEach(node => {
        nodeConnections[node.id] = {
            sources: [],
            targets: []
        };
    });

    data.links.forEach(link => {
        if (nodeConnections[link.source] && nodeConnections[link.target]) {
            nodeConnections[link.source].targets.push(link.target);
            nodeConnections[link.target].sources.push(link.source);
        }
    });

    // Calculate node positions with smart vertical positioning
    const nodePositions = {};
    const nodeHeight = 60;
    const nodeSpacing = 60;
    const minNodeSpacing = 70; // Minimum space between nodes

    // Initial positioning: distribute evenly within each layer
    Object.keys(nodesByLayer).forEach(layer => {
        const nodes = nodesByLayer[layer].filter(n => n.type === 'Column' || n.type === 'Op');
        const totalHeight = nodes.length * (nodeHeight + nodeSpacing);
        const startY = (height - totalHeight) / 2;

        nodes.forEach((node, i) => {
            nodePositions[node.id] = {
                x: layerPositions[layer],
                y: startY + i * (nodeHeight + nodeSpacing) + nodeHeight / 2,
                node: node
            };
        });
    });

    // Iterative refinement to minimize edge crossings
    const iterations = 8;
    const damping = 0.3; // How much to move towards target (0-1)

    for (let iter = 0; iter < iterations; iter++) {
        // Process layers left to right, then right to left alternately
        const layerOrder = iter % 2 === 0
            ? Object.keys(nodesByLayer).sort((a, b) => a - b)
            : Object.keys(nodesByLayer).sort((a, b) => b - a);

        layerOrder.forEach(layer => {
            const nodes = nodesByLayer[layer].filter(n => n.type === 'Column' || n.type === 'Op');

            nodes.forEach(node => {
                const pos = nodePositions[node.id];
                if (!pos) return;

                // Calculate target Y based on connected nodes
                const connections = nodeConnections[node.id];
                const connectedYs = [];

                // Get Y positions of source nodes
                connections.sources.forEach(sourceId => {
                    if (nodePositions[sourceId]) {
                        connectedYs.push(nodePositions[sourceId].y);
                    }
                });

                // Get Y positions of target nodes
                connections.targets.forEach(targetId => {
                    if (nodePositions[targetId]) {
                        connectedYs.push(nodePositions[targetId].y);
                    }
                });

                // If node has connections, move towards their average Y
                if (connectedYs.length > 0) {
                    const targetY = connectedYs.reduce((sum, y) => sum + y, 0) / connectedYs.length;
                    pos.y = pos.y + (targetY - pos.y) * damping;
                }
            });

            // Resolve collisions within this layer
            const sortedNodes = nodes
                .map(n => nodePositions[n.id])
                .filter(p => p)
                .sort((a, b) => a.y - b.y);

            for (let i = 1; i < sortedNodes.length; i++) {
                const prev = sortedNodes[i - 1];
                const curr = sortedNodes[i];
                const minDistance = nodeHeight + minNodeSpacing;

                if (curr.y - prev.y < minDistance) {
                    const overlap = minDistance - (curr.y - prev.y);
                    curr.y += overlap / 2;
                    prev.y -= overlap / 2;
                }
            }

            // Keep nodes within bounds
            sortedNodes.forEach(pos => {
                pos.y = Math.max(nodeHeight / 2 + 40, Math.min(height - nodeHeight / 2 - 20, pos.y));
            });
        });
    }

    // Draw layer labels
    const layerLabels = contentGroup.append('g').attr('class', 'layer-labels');
    data.layers.forEach(layer => {
        layerLabels.append('text')
            .attr('class', 'layer-label')
            .attr('x', layerPositions[layer.index])
            .attr('y', 30)
            .attr('text-anchor', 'middle')
            .text(layer.label);
    });

    function computeTrimmedLine(source, target, targetNode) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx*dx + dy*dy);

        if (dist === 0) return { x2: target.x, y2: target.y };

        // Normalize direction
        const ux = dx / dist;
        const uy = dy / dist;

        let offset = 0;

        if (targetNode.type === "Op") {
            if (["÷", "−", "+", "×"].includes(targetNode.label)) {
                offset = 25;   // circle radius
            } else {
                offset = 70;   // ellipse rx (approx)
            }
        } else if (targetNode.type === "Column") {
            // Rectangles: use half width or half height depending on direction
            const rectWidth = 140;
            const rectHeight = 60;
            const halfW = rectWidth / 2;
            const halfH = rectHeight / 2;

            // If the link is more horizontal than vertical, hit the side;
            // otherwise, hit the top/bottom.
            const isHorizontal = Math.abs(dx) >= Math.abs(dy);
            offset = isHorizontal ? halfW : halfH;
        }

        // Small gap so the arrowhead is not covered by the node’s stroke
        const gap = 4;

        // Make sure we never trim more than the actual distance between nodes,
        // otherwise the endpoint can end up behind the source.
        const maxOffset = Math.max(0, dist - gap);
        offset = Math.min(offset + gap, maxOffset);

        const x2 = target.x - ux * offset;
        const y2 = target.y - uy * offset;

        return { x2, y2 };
    }


    // Draw links
    const links = contentGroup.append('g').attr('class', 'links');
    data.links.forEach(link => {
        const source = nodePositions[link.source];
        const target = nodePositions[link.target];
        const trimmed = computeTrimmedLine(source, target, target.node);

        if (source && target) {
            links.append('line')
                .attr('class', 'link')
                .attr('x1', source.x)
                .attr('y1', source.y)
                .attr('x2', trimmed.x2)
                .attr('y2', trimmed.y2)
                .attr('marker-end', 'url(#arrowhead)');

            // ---- Edge label (relationship) ----
            const label =
                link.relationship || link.edge_type || link.label || link.description;

            if (!label) return;

            // Midpoint of the visible segment
            const mx = (source.x + trimmed.x2) / 2;
            const my = (source.y + trimmed.y2 + 30) / 2;

            // Optional: small offset perpendicular to the line
            const dx = trimmed.x2 - source.x;
            const dy = trimmed.y2 - source.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const nx = -dy / dist;   // unit normal x
            const ny = dx / dist;    // unit normal y
            const offset = -30;       // how far away from the line

            links.append('text')
                .attr('class', 'link-label')
                .attr('x', mx + nx * offset)
                .attr('y', my + ny * offset)
                .attr('text-anchor', 'middle')
                .text(label);
        }
    });

    // Helper function to truncate text
    function truncateText(text, maxLength = 20) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    // Draw nodes
    const nodes = contentGroup.append('g').attr('class', 'nodes');

    data.nodes.forEach(node => {
        const pos = nodePositions[node.id];
        if (!pos || node.type === 'DataModel') return;

        const nodeGroup = nodes.append('g')
            .attr('transform', `translate(${pos.x}, ${pos.y})`);

        if (node.type === 'Op') {
            // Operations are circles/ellipses
            if (node.label === '÷' || node.label === '−' || node.label === '+' || node.label === '×') {
                // Simple operators: circle
                nodeGroup.append('circle')
                    .attr('class', 'operation-node')
                    .attr('r', 25);

                nodeGroup.append('text')
                    .attr('class', 'operation-text')
                    .text(node.label);

                // Tooltip for description if exists
                if (node.description) {
                    nodeGroup.append('title')
                        .text(node.description);
                }
            } else {
                // Complex operations: ellipse
                const labelWidth = node.label.length * 8;
                const ellipseRx = Math.max(labelWidth / 2, 70);

                nodeGroup.append('ellipse')
                    .attr('class', 'node-rect')
                    .attr('rx', ellipseRx)
                    .attr('ry', 30)
                    .attr('fill', '#fdedec')
                    .attr('stroke', '#e74c3c');

                nodeGroup.append('text')
                    .attr('class', 'node-text')
                    .attr('text-anchor', 'middle')
                    .attr('y', node.description ? -5 : 5)
                    .text(node.label);

                if (node.description) {
                    const truncated = truncateText(node.description, 25);
                    nodeGroup.append('text')
                        .attr('class', 'node-subtext')
                        .attr('text-anchor', 'middle')
                        .attr('y', 10)
                        .text(truncated);

                    // Add tooltip with full text
                    nodeGroup.append('title')
                        .text(`${node.description}`);
                }
            }
        } else if (node.type === 'Column') {
            // Columns are rectangles
            const rectWidth = 140;
            const rectHeight = 60;

            // Determine color based on layer
            let fillColor = '#e8f4f8';
            let strokeColor = '#3498db';

            if (node.layer >= 3) {
                fillColor = '#eafaf1';
                strokeColor = '#27ae60';
            } else if (node.layer === 2) {
                fillColor = '#fef5e7';
                strokeColor = '#f39c12';
            }

            // Special styling for output column
            if (node.label.includes('adoption_rate') ||
                node.label.includes('net_revenue') ||
                node.label.includes('total_revenue')) {
                fillColor = '#d5f4e6';
                strokeColor = '#16a085';
            }

            nodeGroup.append('rect')
                .attr('class', 'node-rect')
                .attr('x', -rectWidth / 2)
                .attr('y', -rectHeight / 2)
                .attr('width', rectWidth)
                .attr('height', rectHeight)
                .attr('rx', 6)
                .attr('fill', fillColor)
                .attr('stroke', strokeColor);

            // Column label
            const hasParent = node.parent && data.nodes.find(n => n.id === node.parent);
            nodeGroup.append('text')
                .attr('class', 'node-text')
                .attr('text-anchor', 'middle')
                .attr('y', hasParent ? -8 : 5)
                .text(node.label);

            // Parent (table) label if exists
            if (hasParent) {
                const parentNode = data.nodes.find(n => n.id === node.parent);
                const parentText = `from ${parentNode.label}`;
                const truncatedParent = truncateText(parentText, 18);

                nodeGroup.append('text')
                    .attr('class', 'node-subtext')
                    .attr('text-anchor', 'middle')
                    .attr('y', 8)
                    .text(truncatedParent);

                // Add tooltip if truncated
                if (parentText !== truncatedParent) {
                    nodeGroup.append('title')
                        .text(`${node.label}\n${parentText}`);
                }
            }
        }
    });

    // Legend
    const legend = svg.append('g')
    .attr('class', 'legend')
    .attr('transform', 'translate(50, 30)');

    // Title
    legend.append('text')
    .attr('x', 0)
    .attr('y', 0)
    .attr('font-family', 'Arial')
    .attr('font-size', 10)
    .attr('fill', '#6c757d')
    .attr('font-weight', 'bold')
    .text('Legend:');

    // Common text style helper
    function applyLegendTextStyle(sel) {
    return sel
        .attr('font-family', 'Arial')
        .attr('font-size', 9)
        .attr('fill', '#495057');
    }

    const opLegend = legend.append('g')
                            .attr('transform', 'translate(50, 0)');

    opLegend.append('ellipse')
    .attr('cx', 20)   // center x
    .attr('cy', 10)   // center y
    .attr('rx', 20)   // radius x
    .attr('ry', 10)   // radius y
    .attr('fill', '#fdedec')
    .attr('stroke', '#e74c3c')
    .attr('stroke-width', 2);

    applyLegendTextStyle(
    opLegend.append('text')
        .attr('x', 50)  // to the right of ellipse
        .attr('y', 14)
    ).text('Operations');

    // ---- Box legends (Raw / Staging / Mart / Output) ----
    const boxLegendItems = [
    {
        offsetX: 170,
        fill: '#e8f4f8',
        stroke: '#3498db',
        strokeWidth: 1,
        label: 'Raw Source'
    },
    {
        offsetX: 310,
        fill: '#fef5e7',
        stroke: '#f39c12',
        strokeWidth: 1,
        label: 'Staging'
    },
    {
        offsetX: 470,
        fill: '#eafaf1',
        stroke: '#27ae60',
        strokeWidth: 1,
        label: 'Mart'
    },
    {
        offsetX: 630,
        fill: '#d5f4e6',
        stroke: '#16a085',
        strokeWidth: 2,
        label: 'Final Output'
    }
    ];

    boxLegendItems.forEach(item => {
        const g = legend.append('g')
            .attr('transform', `translate(${item.offsetX}, 0)`);

        g.append('rect')
            .attr('width', 40)
            .attr('height', 20)
            .attr('rx', 3)
            .attr('fill', item.fill)
            .attr('stroke', item.stroke)
            .attr('stroke-width', item.strokeWidth);

        applyLegendTextStyle(
            g.append('text')
            .attr('x', 45)
            .attr('y', 14) // 24 (original) - 10 (group translate)
        ).text(item.label);
    });


}