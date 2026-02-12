# Project Goals: Fascist Language Identification & Visualization

## Mission
To build an automated system using LangChain that analyzes political communications (e.g., Project 2025 documents) to identify, classify, and visualize language patterns associated with fascist ideology.

## Work Styles ("Ralph Style")
1. **Iterative Goal-Driven**: Define goal -> Build Model -> Update Doc -> Repeat.
2. **Context First**: Maintain clear context throughout the process.

## Domain Concepts
We will map LangChain representations to defined fascist traits. A starting framework is Umberto Eco's "Ur-Fascism" (14 properties):
1.  **Cult of Tradition**
2.  **Rejection of Modernism**
3.  **Action for Action's Sake**
4.  **Disagreement is Treason**
5.  **Fear of Difference**
6.  **Appeal to Social Frustration**
7.  **Obsession with a Plot**
8.  **Enemy is both Strong and Weak**
9.  **Pacifism is Trafficking with the Enemy**
10. **Contempt for the Weak**
11. **Everybody is Educated to Become a Hero**
12. **Machismo and Weaponry**
13. **Selective Populism**
14. **Ur-Fascism Speaks Newspeak**

## Technical Objectives (LangChain Learning)
- **Chains**: Build sequential chains to process text.
- **Retrieval**: Use RAG to query the document against the definitions.
- **Agents**: Potentially use agents to explore the text autonomously.
- **Output Parsers**: Structured output for the visualization layer.

## Visualization
- **Heatmaps**: Density of fascist rhetoric in document sections.
- **Classification**: Tagging specific quotes with the Ur-Fascism trait.
