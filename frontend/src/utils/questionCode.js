// A question code is its reference: "A.01" (backend/app/services/question_codes.py),
// shown as is. Older codes carried a timestamp and a random suffix after it,
// "A.01-_96323997", meaningless to a reader: the badge shows "A.01" alone.
// Any other code is returned untouched.
const CODE_REFERENCE = /^([A-Za-z]{1,3}\.?\d{1,3})-_/;

export const displayQuestionCode = (code) => {
  if (!code) return code;
  const match = CODE_REFERENCE.exec(code);
  return match ? match[1] : code;
};
