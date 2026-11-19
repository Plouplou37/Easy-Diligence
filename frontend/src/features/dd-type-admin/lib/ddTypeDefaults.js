// The emoji stored in a DD type's `icon` column, guessed from its name. The
// screens draw an outline icon instead (getDdTypeIcon); the column is kept
// filled for the data's sake.
const ICONS = [
  [['technical', 'tech', 'software', ' it '], '🔧'],
  [['legal', 'law', 'compliance'], '⚖️'],
  [['financial', 'finance', 'accounting'], '💰'],
  [['commercial', 'business', 'sales'], '💼'],
  [['market', 'data'], '📊'],
  [['hr', 'human', 'people'], '👥'],
  [['environmental', 'esg', 'sustainability'], '🌱'],
  [['security', 'cyber'], '🔒'],
  [['operational', 'operations'], '⚙️'],
  [['supply', 'logistics'], '📦'],
  [['risk'], '⚠️'],
  [['tax'], '📑'],
  [['property', 'real estate'], '🏢'],
];

export const guessIcon = (name = '') => {
  const lower = ` ${name.toLowerCase()} `;
  const found = ICONS.find(([keywords]) => keywords.some((keyword) => lower.includes(keyword)));
  return found ? found[1] : '📋';
};

/** A code for a new DD type: its name's first words, and a suffix to keep it unique. */
export const generateCode = (name) => {
  const base = name
    .split(' ')
    .slice(0, 3)
    .map((word) => word.toUpperCase())
    .join('_')
    .replace(/[^A-Z0-9_]/g, '')
    .substring(0, 20);
  const suffix = Date.now().toString(36).toUpperCase().slice(-4);
  return `${base}_${suffix}`;
};

/** A readable name from a questionnaire's file name ("fund_review.xlsx" -> "Fund Review"). */
export const nameFromFile = (filename) =>
  filename
    .replace(/\.[^/.]+$/, '')
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export const IMPORT_EXTENSIONS = ['.xlsx', '.xls', '.csv', '.json'];
