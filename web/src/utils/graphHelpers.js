// Shared constants and helpers for graph visualization

export const TRAIT_COLORS = {
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
};

export const ENTITY_CLASS_COLORS = {
  government_agency: '#4a90d9',
  organization:      '#e67e22',
  person:            '#27ae60',
  policy_program:    '#8e44ad',
  legal_reference:   '#c0392b',
  location:          '#16a085',
};

export const ENTITY_CLASS_LABELS = {
  government_agency: 'Gov. Agencies',
  organization:      'Organizations',
  person:            'People',
  policy_program:    'Programs',
  legal_reference:   'Legal Refs',
  location:          'Locations',
};

export const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : null;
};

export const interpolateColor = (color1, color2, factor = 0.5) => {
  const result = color1.slice();
  for (let i = 0; i < 3; i++) {
    result[i] = Math.round(result[i] + factor * (color2[i] - color1[i]));
  }
  return `rgb(${result[0]}, ${result[1]}, ${result[2]})`;
};

// Look up the trait color for a theme node. Theme IDs often have a numeric
// prefix like "1. Cult of Tradition" — strip it to match TRAIT_COLORS keys.
export const traitColorForTheme = (themeId) => {
  if (TRAIT_COLORS[themeId]) return TRAIT_COLORS[themeId];
  const stripped = themeId.replace(/^\d+\.\s*/, '');
  return TRAIT_COLORS[stripped] || '#ddd';
};
