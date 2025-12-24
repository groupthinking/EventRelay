import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# Load the data
data = {"components": [{"layer": "Input", "items": ["Video URLs", "Live Streams", "File Uploads", "Multi-Video Collections"]}, {"layer": "Video Processing", "items": ["Frame Extraction", "OCR Engine", "Audio Transcription", "UI Detection", "Temporal Analysis"]}, {"layer": "Multi-Modal AI", "items": ["Vision Transformers", "Speech-to-Text", "Language Models", "Cross-Modal Fusion"]}, {"layer": "Knowledge Extraction", "items": ["Code Reconstruction", "Intent Recognition", "Parameter Extraction", "Logic Flow Mapping"]}, {"layer": "Semantic Synthesis", "items": ["Knowledge Graph", "Context Fusion", "Temporal Mapping", "Pattern Recognition"]}, {"layer": "System Generation", "items": ["IR Generation", "Platform Adaptation", "Blueprint Creation", "Security Management"]}, {"layer": "Output", "items": ["n8n Workflows", "Trading Systems", "Marketing Funnels", "API Configurations"]}]}

# Define colors for each layer
colors = ['#1FB8CD', '#FFC185', '#ECEBD5', '#5D878F', '#D2BA4C', '#B4413C', '#964325']

# Create the figure
fig = go.Figure()

# Layer positions (y-coordinates)
layer_positions = {
    'Input': 6,
    'Video Processing': 5,
    'Multi-Modal AI': 4,
    'Knowledge Extraction': 3,
    'Semantic Synthesis': 2,
    'System Generation': 1,
    'Output': 0
}

# Process each layer and create component boxes
for layer_idx, layer_data in enumerate(data['components']):
    layer_name = layer_data['layer']
    items = layer_data['items']
    y_pos = layer_positions[layer_name]
    
    # Calculate x positions for components in this layer
    num_items = len(items)
    x_positions = np.linspace(1, 9, num_items)
    
    for i, item in enumerate(items):
        # Abbreviate component names to fit 15 char limit
        short_name = item if len(item) <= 15 else item[:12] + "..."
        
        # Create component box as scatter point
        fig.add_trace(go.Scatter(
            x=[x_positions[i]],
            y=[y_pos],
            mode='markers+text',
            marker=dict(
                size=80,
                color=colors[layer_idx],
                symbol='square',
                line=dict(width=2, color='white')
            ),
            text=short_name,
            textposition='middle center',
            textfont=dict(size=8, color='black'),
            hovertemplate=f'<b>{item}</b><br>Layer: {layer_name}<extra></extra>',
            showlegend=False,
            name=short_name
        ))

# Add flow arrows between layers
for i in range(len(layer_positions) - 1):
    current_layer = list(layer_positions.keys())[i]
    next_layer = list(layer_positions.keys())[i + 1]
    
    # Add arrows from current layer to next layer
    fig.add_annotation(
        x=5,
        y=layer_positions[current_layer] - 0.3,
        ax=5,
        ay=layer_positions[next_layer] + 0.3,
        arrowhead=2,
        arrowsize=1.5,
        arrowwidth=3,
        arrowcolor='gray',
        showarrow=True
    )

# Add layer labels on the left
for layer_name, y_pos in layer_positions.items():
    fig.add_trace(go.Scatter(
        x=[0],
        y=[y_pos],
        mode='text',
        text=layer_name,
        textposition='middle right',
        textfont=dict(size=12, color='black'),
        showlegend=False,
        hoverinfo='skip'
    ))

# Add multi-modal convergence arrows
fig.add_annotation(
    x=2,
    y=5.5,
    text="Multi-Modal<br>Convergence",
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowwidth=2,
    arrowcolor='#1FB8CD',
    ax=3,
    ay=4.5,
    font=dict(size=9)
)

# Add synthesis branching arrows
fig.add_annotation(
    x=7,
    y=1.5,
    text="System<br>Branching",
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowwidth=2,
    arrowcolor='#964325',
    ax=6,
    ay=0.5,
    font=dict(size=9)
)

# Update layout
fig.update_layout(
    title='Multi-Modal Knowledge Engine',
    xaxis=dict(
        range=[-0.5, 10],
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        title=''
    ),
    yaxis=dict(
        range=[-0.5, 6.5],
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        title=''
    ),
    showlegend=False,
    plot_bgcolor='white'
)

# Save the chart
fig.write_image('architecture_diagram.png')