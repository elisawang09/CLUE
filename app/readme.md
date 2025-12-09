# SQL Transformation Lineage Dashboard

A web application that visualizes SQL query transformations and column lineage using D3.js, with AI-generated summaries from OpenAI API and graph data from Neo4j.

## Project Structure

```
/app
├── index.html                 # Main HTML file
├── styles/
│   ├── main.css              # Global styles
│   ├── dashboard.css         # Dashboard-specific styles
│   └── modal.css             # Modal-specific styles
├── js/
│   ├── main.js               # Application entry point
│   ├── charts/               # D3.js chart implementations
│   │   ├── revenueChart.js
│   │   ├── userTierChart.js
│   │   ├── adoptionChart.js
│   │   └── sessionsChart.js
│   ├── modal/                # Modal-related logic
│   │   ├── modalController.js
│   │   └── dagRenderer.js
│   └── api/                  # API service layers
│       ├── openaiService.js  # OpenAI API integration (mock)
│       └── neo4jService.js   # Neo4j API integration (mock)
└── data/                     # CSV data files
    ├── revenue.csv
    ├── user_tiers.csv
    ├── adoption.csv
    └── sessions.csv
```

## Features

### 1. Dashboard View
- Four interactive D3.js charts displaying metrics
- Info icons on each chart to view transformation details
- Responsive grid layout

### 2. Transformation Modal
- **AI-Generated Summary**: Displays human-readable transformation explanation from OpenAI API
- **DAG Visualization**: Shows column lineage from Neo4j as a directed acyclic graph using D3.js
- Separate layers showing data flow: Source → Transformation → Output

### 3. Data Integration
- **CSV Data**: Charts load data from CSV files using D3.js
- **OpenAI API**: Fetches transformation summaries (currently mocked)
- **Neo4j Graph DB**: Queries lineage data with node types (DataModel, Column, Op) and relationships

## Neo4j Graph Schema

### Node Types
- **DataModel**: Represents tables or data sources
- **Column**: Represents columns at each transformation stage
- **Op**: Represents operations (JOIN, WHERE, aggregations, arithmetic)

### Relationships
- `(:DataModel)-[:HAS_COLUMN]->(:Column)`
- `(:DataModel)-[:HAS_OP]->(:Op)`
- `(:DataModel)-[:DEPENDS_ON_MODEL]->(:DataModel)`
- `(:Column)-[:DERIVES_FROM {mode: "passthrough"}]->(:Column)`
- `(:Column)-[:FEEDS]->(:Op)`
- `(:Op)-[:OUTPUTS]->(:Column)`

## Setup and Installation

1. **Clone or download the project**

2. **Serve the files using a local web server** (required for ES6 modules and D3.js CSV loading):
   ```bash
   # Using Python 3
   python -m http.server 8000

   # Using Node.js http-server
   npx http-server -p 8000
   ```

3. **Open in browser**: Navigate to `http://localhost:8000`

## Production Integration

### OpenAI API Integration
Replace the mock in `js/api/openaiService.js`:

```javascript
export async function fetchTransformationSummary(metricName) {
    const response = await fetch('/api/transformation-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric: metricName })
    });
    return await response.json();
}
```

### Neo4j Integration
Replace the mock in `js/api/neo4jService.js`:

```javascript
export async function fetchLineageData(metricName) {
    const response = await fetch('/api/lineage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric: metricName })
    });
    return await response.json();
}
```

## Tech Stack

- **D3.js v7**: Data visualization and chart rendering
- **Vanilla JavaScript (ES6 modules)**: No framework dependencies
- **CSS3**: Modern styling with Grid and Flexbox
- **OpenAI API**: AI-generated transformation summaries
- **Neo4j**: Graph database for lineage tracking

## Browser Compatibility

- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅
- Requires ES6 module support

## License

MIT