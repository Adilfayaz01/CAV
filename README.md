# Cloud Visualizer (CAV)

Visualize your Azure cloud from a CSV export. This tool generates a single, interactive HTML file to map resource relationships and dependencies. Features an "Internet Exposure" view for quick security analysis of public-facing NSGs and Storage Accounts. Stack: Python, Pandas, NetworkX, JS.

---

## ✨ Key Features

- **🌐 Interactive Graph:** Drag, zoom, and explore your Azure resources and their relationships.
    
- **🔍 Dynamic Filtering:** Instantly filter the visible graph by Resource Type or Resource Group.
    
- **🛡️ Internet Exposure View:** A security-focused view to immediately identify publicly accessible resources.
    
- **📄 Property Inspector:** Click any resource to view all its properties from the source CSV.
    
- **🟢 VM Power State Coloring:** Running VMs are automatically colored green for at-a-glance status.
    
- **📦 Single HTML Output:** Generates a portable, self-contained HTML file that can be easily shared.
    

## 🚀 Getting Started

Follow these steps to generate your own visualization in minutes.

### 1. Prerequisites

Ensure you have Python 3 and install the required packages:

Bash

```
pip install pandas networkx pyvis
```

### 2. Export Azure Data

The input is a CSV file generated from the **Azure Resource Graph Explorer**.

1. In the Azure Portal, navigate to **Resource Graph Explorer**.
    
2. Run the following query (replace with your Subscription ID):
    
    Code snippet
    
    ```
    resources
    | where subscriptionId == "<Your Subscription ID Here>"
    ```
    
3. Click **"Download as CSV"** and save the file to `Test_data/Azure/`.
    

### 3. Generate the Visualization

Run the main Python script from the `data_transformation` directory.

Bash

```
python visualize_azure_graph.py
```

This will create `azure_graph.html` in the project's root directory.

### 4. Explore!

Open `azure_graph.html` in any modern web browser to begin exploring your cloud infrastructure.

## 🛠️ How It Works

1. The **Python script** (`visualize_azure_graph.py`) reads the CSV, builds a graph using `NetworkX`, infers relationships, and performs security analysis.
    
2. It uses `Pyvis` to export a basic HTML file, then injects a sophisticated **Vanilla JS frontend** (`template.html`) to create the rich, interactive UI.
    

## 💻 Technology Stack

- **Backend:** Python, Pandas, NetworkX, Pyvis
    
- **Frontend:** Vanilla JavaScript, HTML5, CSS3
