import json
import os

INPUT_FILE = "data/analysis_results.json"
OUTPUT_HTML = "data/visualization.html"

TRAIT_COLORS = {
    "Cult of Tradition": "#ffcccc",
    "Rejection of Modernism": "#ffe5cc",
    "Action for Action's Sake": "#ffffcc",
    "Disagreement is Treason": "#e5ffcc",
    "Fear of Difference": "#ccffcc",
    "Appeal to Social Frustration": "#ccffe5",
    "Obsession with a Plot": "#ccffff",
    "Enemy is Strong and Weak": "#cce5ff",
    "Pacifism is Trafficking with the Enemy": "#ccccff",
    "Contempt for the Weak": "#e5ccff",
    "Everybody is Educated to Become a Hero": "#ffccff",
    "Machismo and Weaponry": "#ffcce5",
    "Selective Populism": "#e0e0e0",
    "Ur-Fascism Speaks Newspeak": "#ff9999"
}

def generate_visualization():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    <div id="controls" style="text-align: center; margin-bottom: 2rem; position: sticky; top: 0; background: white; padding: 1rem; border-bottom: 1px solid #eee; z-index: 100;">
        <button onclick="filterTraits('all')" style="padding: 0.5rem 1rem; margin: 0.2rem; cursor: pointer;">Show All</button>
        {% for trait, color in TRAIT_COLORS.items() %}
        <button onclick="filterTraits('{{ trait }}')" style="padding: 0.5rem 1rem; margin: 0.2rem; cursor: pointer; background-color: {{ color }}; border: 1px solid #ccc;">{{ trait }}</button>
        {% endfor %}
    </div>

    <div id="content">
    """

    # We need to inject the buttons dynamically or just hardcode the logic since we are in Python generating HTML.
    # Let's generate the buttons in the python loop.
    
    # Reset html_content to include buttons properly
    # Calculate stats
    trait_counts = {}
    for chunk in data:
        for concept in chunk.get("concepts", []):
            t = concept["trait"]
            trait_counts[t] = trait_counts.get(t, 0) + 1
            
    # Sort by count
    sorted_traits = sorted(trait_counts.items(), key=lambda x: x[1], reverse=True)
    max_count = sorted_traits[0][1] if sorted_traits else 1

    MAX_CONCEPTS_FOR_COLOR = 5
    
    html_content = """
    <html>
    <head>
        <title>Fascist Language Analysis Results</title>
        <style>
            body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; line-height: 1.6; color: #333; }
            .header { text-align: center; padding: 2rem; background: #fafafa; border-bottom: 1px solid #eee; }
            
            .stats { max-width: 800px; margin: 0 auto 2rem auto; padding: 1rem; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .stat-row { display: flex; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem; }
            .stat-label { width: 250px; text-align: right; padding-right: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .stat-bar-container { flex-grow: 1; background: #eee; height: 1.2rem; border-radius: 4px; overflow: hidden; }
            .stat-bar { height: 100%; transition: width 0.5s; color: #fff; text-align: right; padding-right: 0.5rem; font-size: 0.8rem; line-height: 1.2rem; }
            
            .heatmap { display: grid; grid-template-columns: repeat(auto-fill, minmax(12px, 1fr)); gap: 2px; max-width: 1000px; margin: 0 auto 2rem auto; padding: 10px; background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .heatmap-cell { width: 100%; padding-top: 100%; position: relative; background: #eee; border-radius: 2px; cursor: pointer; }
            .heatmap-cell:hover { transform: scale(1.2); z-index: 10; border: 1px solid #333; }
            .heatmap-cell[title]:hover::after { content: attr(title); position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: #333; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 10px; white-space: nowrap; pointer-events: none; }
            
            .controls { text-align: center; margin-bottom: 2rem; position: sticky; top: 0; background: white; padding: 1rem; border-bottom: 1px solid #eee; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .btn { padding: 0.4rem 0.8rem; margin: 0.2rem; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9rem; transition: all 0.2s; }
            .btn:hover { opacity: 0.8; }
            .btn.active { outline: 2px solid #333; font-weight: bold; }
            
            .chunk { scroll-margin-top: 100px; border: 1px solid #eee; padding: 1.5rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: opacity 0.3s; }
            .chunk.hidden { display: none; }
            
            .summary { font-style: italic; color: #666; background: #f9f9f9; padding: 1rem; border-radius: 4px; margin-bottom: 1rem; }
            .quote-card { margin-top: 1rem; padding: 1rem; border-left: 4px solid #333; background: #fff; }
            .trait-tag { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: bold; font-size: 0.85em; margin-bottom: 0.5rem; }
            .confidence { margin-left: 0.5rem; font-size: 0.8em; color: #666; font-weight: normal; }
            .source-text { font-size: 0.8em; color: #999; margin-top: 0.5rem; display: block; }
        </style>
        <script>
            function filterTraits(trait) {
                const chunks = document.querySelectorAll('.chunk');
                const buttons = document.querySelectorAll('.btn');
                
                // Update active button
                buttons.forEach(b => b.classList.remove('active'));
                event.target.classList.add('active');
                
                chunks.forEach(chunk => {
                    if (trait === 'all') {
                        chunk.classList.remove('hidden');
                        return;
                    }
                    
                    const traitsInChunk = Array.from(chunk.querySelectorAll('.trait-tag')).map(t => t.dataset.trait);
                    if (traitsInChunk.includes(trait)) {
                        chunk.classList.remove('hidden');
                    } else {
                        chunk.classList.add('hidden');
                    }
                });
            }
            
            function scrollToChunk(id) {
                const el = document.getElementById('chunk-' + id);
                if (el) {
                    el.scrollIntoView({behavior: 'smooth'});
                    el.style.backgroundColor = '#fffbeb';
                    setTimeout(() => el.style.backgroundColor = '', 2000);
                }
            }
        </script>
    </head>
    <body>
        <div class="header">
            <h1>Project 2025: Ur-Fascism Analysis</h1>
            <p>Generated by LangChain + Gemini-3-Flash</p>
        </div>

        <div class="stats">
            <h3 style="text-align: center; margin-top: 0;">Prevalence of Fascist Traits</h3>
    """
    
    for trait, count in sorted_traits:
        color = TRAIT_COLORS.get(trait, "#ccc")
        percentage = (count / max_count) * 100
        html_content += f"""
            <div class="stat-row">
                <div class="stat-label">{trait}</div>
                <div class="stat-bar-container">
                    <div class="stat-bar" style="width: {percentage}%; background-color: {color}; color: #333;">{count}</div>
                </div>
            </div>
        """
        
    html_content += """
        </div>
        
        <div class="heatmap">
    """
    
    # Heatmap generation
    # Sort chunks by ID to ensure order in grid
    sorted_chunks = sorted(data, key=lambda x: x["chunk_id"])
    
    for chunk in sorted_chunks:
        concept_count = len(chunk.get("concepts", []))
        opacity = min(concept_count / MAX_CONCEPTS_FOR_COLOR, 1.0)
        # Use a red color scale: 255, 0, 0
        bg_color = f"rgba(255, 0, 0, {opacity})" if concept_count > 0 else "#eee"
        
        html_content += f'<div class="heatmap-cell" style="background-color: {bg_color};" title="Chunk {chunk["chunk_id"]}: {concept_count} concepts" onclick="scrollToChunk({chunk["chunk_id"]})"></div>'
        
    html_content += """
        </div>
        
        <div class="controls">
            <button class="btn active" onclick="filterTraits('all')">Show All</button>
    """
    
    for trait, color in TRAIT_COLORS.items():
        html_content += f'<button class="btn" onclick="filterTraits(\'{trait}\')" style="background-color: {color}">{trait}</button>\n'
        
    html_content += "</div>\n<div id='content'>"

    for chunk in data:
        html_content += f'<div id="chunk-{chunk["chunk_id"]}" class="chunk">'
        html_content += f'<h3>Chunk {chunk["chunk_id"]}</h3>'
        html_content += f'<div class="summary"><strong>Summary:</strong> {chunk.get("summary", "No summary available")}</div>'
        
        if "source_text" in chunk:
             html_content += f'<span class="source-text">Context: {chunk["source_text"]}</span>'
        
        for concept in chunk.get("concepts", []):
            trait = concept["trait"]
            color = TRAIT_COLORS.get(trait, "#f0f0f0")
            
            html_content += f'<div class="quote-card" style="border-left-color: {color}">'
            html_content += f'<span class="trait-tag" data-trait="{trait}" style="background-color: {color}">{trait} <span class="confidence">(Conf: {concept["confidence"]})</span></span>'
            html_content += f'<blockquote style="margin: 0.5rem 0 0.5rem 0;">"{concept["quote"]}"</blockquote>'
            html_content += f'<p style="margin: 0; font-size: 0.9rem;">{concept["explanation"]}</p>'
            html_content += '</div>'
            
        html_content += '</div>'

    html_content += """
    </div>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Visualization saved to {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_visualization()
