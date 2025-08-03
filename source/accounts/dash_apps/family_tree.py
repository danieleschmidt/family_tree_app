import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from django_plotly_dash import DjangoDash
import plotly.graph_objs as go
import plotly.express as px
import networkx as nx
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from ..models import Person, FamilyTree
from ..services import RelationshipCalculator, FamilyTreeSearchService

app_name = 'family_tree'

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'
]

app = DjangoDash(
    name=app_name,
    external_stylesheets=external_stylesheets,
    add_bootstrap_links=True
)


class FamilyTreeVisualizer:
    """
    Advanced family tree visualization system with multiple layout options
    and interactive features.
    """
    
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree
        self.relationship_calculator = RelationshipCalculator(family_tree)
        
    def generate_interactive_tree(self, layout_type: str = 'hierarchical', 
                                focus_person: Optional[Person] = None) -> go.Figure:
        """
        Generate an interactive family tree visualization.
        
        Args:
            layout_type: Type of layout ('hierarchical', 'circular', 'force')
            focus_person: Person to center the view on
            
        Returns:
            Plotly figure object
        """
        people = Person.objects.filter(family_tree=self.family_tree)
        
        if not people.exists():
            return self._create_empty_tree_figure()
        
        # Build graph structure
        graph = self._build_family_graph(people)
        
        # Calculate layout positions
        if layout_type == 'hierarchical':
            pos = self._hierarchical_layout(graph, focus_person)
        elif layout_type == 'circular':
            pos = self._circular_layout(graph)
        elif layout_type == 'force':
            pos = self._force_directed_layout(graph)
        else:
            pos = self._hierarchical_layout(graph, focus_person)
        
        # Create the visualization
        return self._create_plotly_figure(graph, pos, focus_person)
    
    def _build_family_graph(self, people) -> nx.Graph:
        """Build a NetworkX graph from family relationships."""
        G = nx.Graph()
        
        # Add nodes for each person
        for person in people:
            G.add_node(person.id, 
                      person=person,
                      name=f"{person.first_name} {person.last_name}",
                      birth_year=person.birth_date.year if person.birth_date else None,
                      death_year=person.death_date.year if person.death_date else None,
                      gender=getattr(person, 'gender', 'unknown'))
        
        # Add edges for relationships
        for person in people:
            # Parent-child relationships
            if person.father_id:
                G.add_edge(person.id, person.father_id, 
                          relationship='parent-child', color='blue')
            if person.mother_id:
                G.add_edge(person.id, person.mother_id, 
                          relationship='parent-child', color='blue')
            
            # Spouse relationships
            if person.spouse_id:
                G.add_edge(person.id, person.spouse_id, 
                          relationship='spouse', color='red')
        
        return G
    
    def _hierarchical_layout(self, graph: nx.Graph, 
                           focus_person: Optional[Person] = None) -> Dict[int, Tuple[float, float]]:
        """Create a hierarchical layout with generations as levels."""
        generations = self._calculate_generations(graph)
        
        pos = {}
        generation_widths = {}
        
        # Calculate positions for each generation
        for generation, people in generations.items():
            y = -generation * 100  # Negative to have oldest at top
            generation_widths[generation] = len(people)
            
            # Distribute people horizontally within generation
            if len(people) == 1:
                x_positions = [0]
            else:
                x_positions = [i * 150 - (len(people) - 1) * 75 for i in range(len(people))]
            
            for i, person_id in enumerate(people):
                pos[person_id] = (x_positions[i], y)
        
        return pos
    
    def _circular_layout(self, graph: nx.Graph) -> Dict[int, Tuple[float, float]]:
        """Create a circular layout for the family tree."""
        return nx.circular_layout(graph, scale=200)
    
    def _force_directed_layout(self, graph: nx.Graph) -> Dict[int, Tuple[float, float]]:
        """Create a force-directed layout."""
        return nx.spring_layout(graph, k=100, iterations=50, scale=200)
    
    def _calculate_generations(self, graph: nx.Graph) -> Dict[int, List[int]]:
        """Calculate generational levels for hierarchical layout."""
        generations = {}
        visited = set()
        
        # Find root nodes (people with no parents in the tree)
        roots = []
        for node in graph.nodes():
            person = graph.nodes[node]['person']
            has_parent_in_tree = any(
                neighbor for neighbor in graph.neighbors(node)
                if graph.edges[node, neighbor].get('relationship') == 'parent-child'
                and self._is_parent_relationship(node, neighbor, graph)
            )
            if not has_parent_in_tree:
                roots.append(node)
        
        # BFS to assign generations
        if not roots:
            # If no clear roots, pick the oldest person
            oldest_person = min(graph.nodes(), 
                              key=lambda x: graph.nodes[x]['birth_year'] or 9999)
            roots = [oldest_person]
        
        queue = [(root, 0) for root in roots]
        
        while queue:
            node, generation = queue.pop(0)
            
            if node in visited:
                continue
            
            visited.add(node)
            
            if generation not in generations:
                generations[generation] = []
            generations[generation].append(node)
            
            # Add children to next generation
            for neighbor in graph.neighbors(node):
                if neighbor not in visited:
                    edge_data = graph.edges[node, neighbor]
                    if (edge_data.get('relationship') == 'parent-child' and 
                        self._is_child_relationship(node, neighbor, graph)):
                        queue.append((neighbor, generation + 1))
        
        return generations
    
    def _is_parent_relationship(self, node1: int, node2: int, graph: nx.Graph) -> bool:
        """Check if node1 is parent of node2."""
        person1 = graph.nodes[node1]['person']
        person2 = graph.nodes[node2]['person']
        return person2.father_id == person1.id or person2.mother_id == person1.id
    
    def _is_child_relationship(self, node1: int, node2: int, graph: nx.Graph) -> bool:
        """Check if node1 is child of node2."""
        return self._is_parent_relationship(node2, node1, graph)
    
    def _create_plotly_figure(self, graph: nx.Graph, pos: Dict[int, Tuple[float, float]], 
                            focus_person: Optional[Person] = None) -> go.Figure:
        """Create the Plotly figure from graph and positions."""
        
        # Extract edge coordinates
        edge_x, edge_y = [], []
        edge_info = []
        
        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            relationship = graph.edges[edge]['relationship']
            edge_info.append(f"{relationship}")
        
        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Extract node coordinates and information
        node_x, node_y = [], []
        node_text, node_info = [], []
        node_colors = []
        
        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            person = graph.nodes[node]['person']
            name = graph.nodes[node]['name']
            birth_year = graph.nodes[node]['birth_year']
            death_year = graph.nodes[node]['death_year']
            
            # Create hover text
            hover_text = f"<b>{name}</b><br>"
            if birth_year:
                hover_text += f"Born: {birth_year}<br>"
            if death_year:
                hover_text += f"Died: {death_year}<br>"
            else:
                hover_text += "Living<br>"
            
            # Add relationship to focus person if specified
            if focus_person and person.id != focus_person.id:
                relationship_info = self.relationship_calculator.calculate_relationship(
                    focus_person, person
                )
                hover_text += f"Relationship: {relationship_info['relationship']}"
            
            node_info.append(hover_text)
            node_text.append(name)
            
            # Color coding based on gender or generation
            if hasattr(person, 'gender'):
                if person.gender == 'M':
                    node_colors.append('lightblue')
                elif person.gender == 'F':
                    node_colors.append('pink')
                else:
                    node_colors.append('lightgray')
            else:
                node_colors.append('lightgray')
        
        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            hovertext=node_info,
            marker=dict(
                size=30,
                color=node_colors,
                line=dict(width=2, color='black')
            )
        )
        
        # Create the figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title='Interactive Family Tree',
                titlefont_size=16,
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=40),
                annotations=[
                    dict(
                        text="Click and drag to pan, scroll to zoom",
                        showarrow=False,
                        xref="paper", yref="paper",
                        x=0.005, y=-0.002,
                        xanchor='left', yanchor='bottom',
                        font=dict(size=12)
                    )
                ],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='white'
            )
        )
        
        return fig
    
    def _create_empty_tree_figure(self) -> go.Figure:
        """Create an empty tree figure when no people exist."""
        fig = go.Figure()
        fig.add_annotation(
            text="No people in this family tree yet.<br>Start by adding family members!",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )
        return fig


# Initialize the visualizer (will be set dynamically)
visualizer = None

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Family Tree Visualization", className="text-center mb-4"),
        
        # Controls
        html.Div([
            html.Div([
                html.Label("Layout Type:", className="form-label"),
                dcc.Dropdown(
                    id='layout-dropdown',
                    options=[
                        {'label': 'Hierarchical (Generations)', 'value': 'hierarchical'},
                        {'label': 'Circular', 'value': 'circular'},
                        {'label': 'Force Directed', 'value': 'force'}
                    ],
                    value='hierarchical',
                    className="form-control"
                )
            ], className="col-md-4"),
            
            html.Div([
                html.Label("Focus Person:", className="form-label"),
                dcc.Dropdown(
                    id='focus-person-dropdown',
                    placeholder="Select a person to focus on...",
                    className="form-control"
                )
            ], className="col-md-4"),
            
            html.Div([
                html.Label("Search:", className="form-label"),
                dcc.Input(
                    id='search-input',
                    type='text',
                    placeholder="Search family members...",
                    className="form-control"
                )
            ], className="col-md-4")
        ], className="row mb-4")
    ], className="container-fluid"),
    
    # Family Tree Visualization
    html.Div([
        dcc.Graph(
            id='family-tree-plot',
            style={'height': '80vh'},
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['select2d', 'lasso2d']
            }
        )
    ]),
    
    # Person Details Panel
    html.Div([
        html.Div(id='person-details', className="card")
    ], className="container-fluid mt-4"),
    
    # Hidden div to store family tree ID
    html.Div(id='family-tree-id', style={'display': 'none'})
])


@app.callback(
    Output('family-tree-plot', 'figure'),
    [Input('layout-dropdown', 'value'),
     Input('focus-person-dropdown', 'value')],
    [State('family-tree-id', 'children')]
)
def update_tree_layout(layout_type, focus_person_id, family_tree_id):
    """Update the family tree visualization when layout or focus changes."""
    if not family_tree_id:
        return go.Figure()
    
    try:
        family_tree = FamilyTree.objects.get(id=family_tree_id)
        visualizer = FamilyTreeVisualizer(family_tree)
        
        focus_person = None
        if focus_person_id:
            focus_person = Person.objects.get(id=focus_person_id)
        
        return visualizer.generate_interactive_tree(layout_type, focus_person)
    except Exception:
        return go.Figure()


@app.callback(
    Output('focus-person-dropdown', 'options'),
    [Input('family-tree-id', 'children')]
)
def update_person_options(family_tree_id):
    """Update the focus person dropdown options."""
    if not family_tree_id:
        return []
    
    try:
        people = Person.objects.filter(family_tree_id=family_tree_id)
        return [
            {'label': f"{p.first_name} {p.last_name}", 'value': p.id}
            for p in people
        ]
    except Exception:
        return []


@app.callback(
    Output('person-details', 'children'),
    [Input('family-tree-plot', 'clickData')],
    [State('family-tree-id', 'children')]
)
def display_person_details(click_data, family_tree_id):
    """Display detailed information when a person is clicked."""
    if not click_data or not family_tree_id:
        return ""
    
    try:
        # Extract person information from click data
        point_index = click_data['points'][0]['pointIndex']
        
        family_tree = FamilyTree.objects.get(id=family_tree_id)
        people = Person.objects.filter(family_tree=family_tree)
        person = list(people)[point_index]
        
        return html.Div([
            html.Div([
                html.H4(f"{person.first_name} {person.last_name}", className="card-title"),
                html.P([
                    html.Strong("Born: "), 
                    person.birth_date.strftime("%B %d, %Y") if person.birth_date else "Unknown"
                ], className="card-text"),
                html.P([
                    html.Strong("Died: "), 
                    person.death_date.strftime("%B %d, %Y") if person.death_date else "Living"
                ], className="card-text"),
                html.P([
                    html.Strong("Father: "), 
                    f"{person.father.first_name} {person.father.last_name}" if person.father else "Unknown"
                ], className="card-text"),
                html.P([
                    html.Strong("Mother: "), 
                    f"{person.mother.first_name} {person.mother.last_name}" if person.mother else "Unknown"
                ], className="card-text"),
                html.P([
                    html.Strong("Spouse: "), 
                    f"{person.spouse.first_name} {person.spouse.last_name}" if person.spouse else "None"
                ], className="card-text"),
            ], className="card-body")
        ], className="card")
    except Exception:
        return ""


def set_family_tree_context(family_tree_id: int):
    """Set the family tree context for the visualization."""
    global visualizer
    try:
        family_tree = FamilyTree.objects.get(id=family_tree_id)
        visualizer = FamilyTreeVisualizer(family_tree)
    except FamilyTree.DoesNotExist:
        visualizer = None
