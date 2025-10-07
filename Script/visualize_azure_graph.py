#!/usr/bin/env python3
"""
visualize_azure_graph.py

Read Test_data/Azure/Azure_Arm.csv, build a graph where nodes are values
from the `name` column and edges are inferred when one resource's fields
reference another resource's `id`. Saves `azure_graph.png` and shows the plot.

Usage:
    python visualize_azure_graph.py [path/to/Azure_Arm.csv]

If required packages are missing the script will print installation instructions.
"""
from __future__ import annotations
import sys
import json
import os
from pathlib import Path
from urllib.parse import quote
try:
    import pandas as pd
    import networkx as nx
    import matplotlib.pyplot as plt
    # pyvis is optional; used for interactive HTML export
    try:
        from pyvis.network import Network
        _HAS_PYVIS = True
    except Exception:
        _HAS_PYVIS = False
except Exception as e:
    print("Missing required packages. Install with:")
    print("\n    pip install -r requirements.txt\n")
    raise


def build_graph_from_csv(csv_path: Path) -> nx.DiGraph:
    df = pd.read_csv(csv_path, dtype=str).fillna("")

    # ensure the columns exist
    if 'id' not in df.columns or 'name' not in df.columns:
        raise SystemExit("CSV must contain 'id' and 'name' columns")

    # map id -> name
    id_to_name = {row['id']: row['name'] for _, row in df.iterrows() if row['id']}
    id_to_row = {row['id']: row for _, row in df.iterrows() if row['id']}

    # create graph
    G = nx.DiGraph()

    # add all names as nodes
    for _, row in df.iterrows():
        name = row['name']
        if not name:
            continue
        # attach attributes if available
        # attach all CSV columns (non-empty) as node attributes so the interactive
        # properties panel can show original CSV fields
        attrs = {}
        for key in df.columns:
            val = row.get(key)
            if val is not None and val != "":
                # store as string
                attrs[key] = str(val)
        G.add_node(name, **attrs)

    # For each row, search its string fields for any known ids and add edges
    # from this resource -> referenced resource
    candidate_ids = list(id_to_name.keys())

    # small optimization: only search in a subset of columns that typically contain references
    search_columns = [c for c in df.columns if c in ('properties', 'tags', 'identity', 'managedBy', 'resourceGroup', 'type')]
    # if properties column missing, fall back to all string columns
    if not search_columns:
        search_columns = [c for c in df.columns if df[c].dtype == object]

    for _, row in df.iterrows():
        src_name = row['name']
        if not src_name:
            continue

        hay = " ".join(str(row.get(c, "")) for c in search_columns)
        # naive substring match: many resource ids are long and unique
        for cid in candidate_ids:
            if cid == row['id']:
                continue
            if cid in hay:
                tgt_name = id_to_name.get(cid)
                if tgt_name:
                    G.add_node(tgt_name)
                    # preserve reference info on edges
                    G.add_edge(src_name, tgt_name)

    # --- Add Internet node for exposed NSGs ---
    internet_node_name = "Internet"
    internet_sources = {'*', 'internet', '0.0.0.0/0'}
    has_internet_node = False

    for _, row in df.iterrows():
        node_type = row.get('type', '').lower()
        node_name = row['name']
        properties_str = row.get('properties', '{}')
        is_exposed = False

        try:
            properties = json.loads(properties_str)
            # Check for exposed NSGs
            if node_type == 'microsoft.network/networksecuritygroups':
                rules = properties.get('securityRules', [])
                for rule in rules:
                    rule_props = rule.get('properties', {})
                    if (rule_props.get('direction', '').lower() == 'inbound' and
                        rule_props.get('access', '').lower() == 'allow' and
                        rule_props.get('sourceAddressPrefix', '').lower() in internet_sources):
                        is_exposed = True
                        break # Found one open rule, no need to check others
            
            # Check for exposed Storage Accounts
            elif node_type == 'microsoft.storage/storageaccounts':
                network_acls = properties.get('networkAcls', {})
                if network_acls.get('defaultAction', '').lower() == 'allow':
                    is_exposed = True

        except (json.JSONDecodeError, AttributeError):
            continue

        if is_exposed:
            if not has_internet_node:
                G.add_node(internet_node_name, type='Internet', group='Internet', size=40)
                has_internet_node = True
            G.add_edge(internet_node_name, node_name)

    return G


def plot_graph(G: nx.Graph, out_path: Path):
    plt.figure(figsize=(12, 9))
    # layout
    try:
        pos = nx.spring_layout(G, seed=42)
    except Exception:
        pos = nx.random_layout(G)

    # draw nodes and edges
    nx.draw_networkx_edges(G, pos, alpha=0.3)
    nx.draw_networkx_nodes(G, pos, node_size=300, node_color='#1f78b4')
    nx.draw_networkx_labels(G, pos, font_size=8)

    plt.title('Azure resources (nodes = name)')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved graph image to: {out_path}")
    try:
        plt.show()
    except Exception:
        # running headless - ignore
        pass

def _get_node_style(node_type: str) -> dict:
    """Return pyvis style options for a given Azure resource type."""
    tlow = (node_type or '').lower()

    # SVG icon for network resources
    net_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="16" r="6" fill="#ff7f00"/><circle cx="16" cy="48" r="6" fill="#6a3d9a"/><circle cx="48" cy="48" r="6" fill="#b15928"/><path d="M32 22 L32 42" stroke="#555" stroke-width="2" stroke-linecap="round"/><path d="M32 42 L18 48" stroke="#555" stroke-width="2" stroke-linecap="round"/><path d="M32 42 L46 48" stroke="#555" stroke-width="2" stroke-linecap="round"/></svg>'''
    net_data_url = 'data:image/svg+xml;utf8,' + quote(net_svg)

    # External PNG icons
    ip_data_url = 'https://cdn-icons-png.flaticon.com/512/6726/6726855.png'
    nic_data_url = 'https://cdn-icons-png.flaticon.com/512/969/969430.png'
    nsg_data_url = 'https://cdn-icons-png.flaticon.com/512/9378/9378191.png'
    disk_data_url = 'https://cdn-icons-png.flaticon.com/512/2493/2493389.png'
    routetable_data_url = 'https://cdn-icons-png.flaticon.com/512/2923/2923498.png'
    internet_data_url = 'https://cdn-icons-png.flaticon.com/512/1011/1011373.png'
    storage_data_url = 'https://cdn-icons-png.flaticon.com/512/1975/1975643.png'
    default_data_url = 'https://cdn-icons-png.flaticon.com/512/15549/15549062.png'

    # Define styles based on type keywords
    vm_data_url = 'https://cdn-icons-png.flaticon.com/512/8036/8036436.png'
    extension_data_url = 'https://cdn-icons-png.flaticon.com/512/11821/11821370.png'
    style = {'size': 30, 'shapeProperties': {'useImageSize': False}}
    # Check for extensions first as its type string also contains 'virtualmachine'
    if 'extensions' in tlow:
        style.update({'shape': 'image', 'image': extension_data_url})
        return style
    if 'internet' in tlow:
        style.update({'shape': 'image', 'image': internet_data_url, 'size': 40})
        return style
    if 'virtualmachine' in tlow:
        style.update({'shape': 'image', 'image': vm_data_url})
        return style
    if 'disks' in tlow:
        style.update({'shape': 'image', 'image': disk_data_url})
        return style
    if 'storageaccounts' in tlow:
        style.update({'shape': 'image', 'image': storage_data_url})
        return style
    if 'networkinterface' in tlow:
        style.update({'shape': 'image', 'image': nic_data_url})
        return style
    if 'publicipaddress' in tlow:
        style.update({'shape': 'image', 'image': ip_data_url})
        return style
    if 'networksecuritygroup' in tlow:
        style.update({'shape': 'image', 'image': nsg_data_url})
        return style
    if 'routetable' in tlow:
        style.update({'shape': 'image', 'image': routetable_data_url})
        return style
    if 'virtualnetworks' in tlow:
        style.update({'shape': 'image', 'image': net_data_url})
        return style

    # Default style
    return {'shape': 'image', 'image': default_data_url, 'size': 25}

def export_interactive(G: nx.Graph, out_path: Path):
    """Export an interactive HTML using pyvis. If pyvis is not installed, print
    an instruction and skip export.
    """
    if not _HAS_PYVIS:
        print("pyvis not installed. Install with: pip install pyvis")
        return

    net = Network(height='800px', width='100%', directed=True)
    net.force_atlas_2based()

    # Default vis.js options to avoid huge gaps between nodes
    net.set_options("""
    var options = {
        "physics": {
            "enabled": true,
            "solver": "barnesHut",
            "barnesHut": {"gravitationalConstant": -10000, "centralGravity": 0.3, "springLength": 120, "springConstant": 0.05, "damping": 0.09},
            "minVelocity": 0.75
        },
        "edges": {"smooth": {"enabled": true, "type": "dynamic"}}
    }
    """)

    # collect node types for coloring
    type_to_color = {}
    palette = ["#1f78b4", "#33a02c", "#e31a1c", "#ff7f00", "#6a3d9a", "#b15928"]

    for i, n in enumerate(G.nodes(data=True)):
        name, data = n
        ntype = data.get('type', 'unknown') if isinstance(data, dict) else 'unknown'
        if ntype not in type_to_color:
            type_to_color[ntype] = palette[len(type_to_color) % len(palette)]

    for name, data in G.nodes(data=True):
        title_lines = [f"<b>{name}</b>"]
        rg = None
        if isinstance(data, dict):
            for k in ('type', 'resourceGroup', 'location', 'id'):
                if data.get(k):
                    title_lines.append(f"{k}: {data.get(k)}")
            rg = data.get('resourceGroup')
        title = '<br>'.join(title_lines)
        ntype = data.get('type', 'unknown') if isinstance(data, dict) else 'unknown'
        color = type_to_color.get(ntype, '#888')
        # build node attributes from CSV-derived data so the client can access original fields
        node_attrs = {}
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    node_attrs[k] = str(v)
                except Exception:
                    node_attrs[k] = v
        # ensure UI-related fields are set/overridden

        # --- Extract nested VM powerState and add as a top-level attribute ---
        if ntype.lower() == 'microsoft.compute/virtualmachines':
            try:
                props = json.loads(data.get('properties', '{}'))
                power_state = props.get('extended', {}).get('instanceView', {}).get('powerState', {}).get('displayStatus')
                if power_state:
                    node_attrs['powerState'] = power_state
            except (json.JSONDecodeError, AttributeError):
                pass # Ignore if properties are malformed
        # ---

        # avoid passing 'title' to pyvis nodes (it becomes a hover tooltip); use
        # a separate 'details' attribute that our properties panel will read.
        node_attrs.update({
            'label': name,
            'details': title,
            'color': color,
            'group': ntype,
            'resourceGroup': rg,
        })
        node_attrs.update(_get_node_style(ntype))
        net.add_node(name, **node_attrs)

    for src, dst in G.edges():
        net.add_edge(src, dst)

    out_path = str(out_path)
    # write_html is more reliable in non-notebook environments
    net.write_html(out_path)
    print(f"Saved interactive graph to: {out_path}")

    # Post-process the generated HTML to inject a small control panel (filters, physics toggle,
    # save/load positions). We append a script before </body> that hooks into the vis Network instance.
    _inject_interactive_controls(out_path)


def _inject_interactive_controls(out_path: str):
    """Injects JS and HTML for filters and other controls into the pyvis output file."""
    try:
        html = Path(out_path).read_text(encoding='utf-8')
        template_path = Path(__file__).resolve().parents[1] / 'lib' / 'bindings' / 'template.html'
        inject_html = template_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f'Warning: could not read generated HTML or template: {e}')
        return

    if '</body>' in html:
        html = html.replace('</body>', inject_html + '\n</body>')
        Path(out_path).write_text(html, encoding='utf-8')


def main(argv):
    """Main execution function."""
    # Set default path relative to the script's location
    azure_data_dir = Path(__file__).resolve().parents[1] / 'Test_data' / 'Azure'
    
    # Find the first CSV file in the directory
    try:
        default = next(azure_data_dir.glob('*.csv'))
    except StopIteration:
        print(f"No CSV files found in {azure_data_dir}.")
        raise SystemExit(1)

    csv_path = Path(argv[1]) if len(argv) > 1 else default
    if not csv_path.exists():
        print(f"CSV not found at {csv_path}. Provide path as first argument.")
        raise SystemExit(1)

    print(f"Loading CSV from: {csv_path}")
    G = build_graph_from_csv(csv_path)
    print(f"Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Generate the interactive HTML output
    html_out = Path.cwd() / 'azure_graph.html'
    export_interactive(G, html_out)


if __name__ == '__main__':
    main(sys.argv)
