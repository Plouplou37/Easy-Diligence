// A DD type's category, guessed from its name, for the filter of the picker.
const CATEGORIES = [
  ['financial', /financial/],
  ['operational', /operation/],
  ['legal', /legal|compliance|sanity/],
  ['esg', /esg|environmental|sustainability/],
  // \bit\b: "it" alone, not inside "credit" or "equity".
  ['technical', /technical|technology|\bit\b/],
];

export const ddTypeCategory = (name = '') => {
  const lower = name.toLowerCase();
  const found = CATEGORIES.find(([, pattern]) => pattern.test(lower));
  return found ? found[0] : 'other';
};

/** The categories present among `ddTypes`, with how many each holds. */
export const categoriesOf = ddTypes => {
  const counts = new Map();
  ddTypes.forEach(ddType => {
    const category = ddTypeCategory(ddType.name);
    counts.set(category, (counts.get(category) || 0) + 1);
  });
  return [...counts].map(([key, count]) => ({
    key,
    count,
    label: key.charAt(0).toUpperCase() + key.slice(1),
  }));
};
