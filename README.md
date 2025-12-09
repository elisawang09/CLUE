# CLUE
A dashboard-integrated provenance tool to explain SQL transformations for transparent metric understanding

## Key Features

- **SQL Provenance Tracking**: Complete traceability of data transformations and their sources
- **AI-generated Transformation Summary**: Provide human-readable summary of the transformation process
- **Neo4j Graph Database**: Leverage graph database capabilities for efficient relationship queries and visualization

## How to Run Locally

### Prerequisites
- Python 3.7+
- Node.js and npm
- Neo4j database (local or remote instance)
- OpenAI API key

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CLUE
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Neo4j connection**
   - Update Neo4j credentials in the configuration file or environment variables
   - Ensure your Neo4j database is running

4. **Build the data lineage graph**
   ```bash
   cd lineage
   python main.py
   ```

5. **Start the dashboard application**
   ```bash
   cd app
   npm install
   npm start
   ```

6. **Access the dashboard**
   - Open your browser and navigate to `http://localhost:3000` (or the configured port)
   - Use the dashboard to explore data lineage and metrics

### Note
Currently fixing bugs related to graph database queries. To explore the demo interface, navigate to the app directory and start a local HTTP server by running `python -m http.server 8080` in your terminal. Then, open a browser and visit http://localhost:8080.