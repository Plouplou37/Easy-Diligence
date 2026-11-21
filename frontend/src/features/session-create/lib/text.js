/** "1 question", "18 questions": a count with its noun. */
export const plural = (count, word, many = `${word}s`) =>
  `${Number(count).toLocaleString('en-US')} ${count === 1 ? word : many}`;

/** A list of names, readable: "A", "A and B", "A, B and C". */
export const joinNames = names => {
  if (names.length <= 1) return names.join('');
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
};
