// Imported question codes embed the reviewer's reference: "A.01-_96323997".
// The digits after it are a timestamp plus a random suffix, generated at import
// to keep codes unique -- meaningless to a reader. Since the reference no longer
// opens the question text, the badge is where people read it, so it shows
// "A.01" alone. Same pattern as CODE_REFERENCE on the backend
// (scripts/update_questionnaire.py, core/exporters.py).
//
// Codes that do not follow that shape -- questions created in the UI get
// "WHATIS_12345678" -- are returned untouched: there is no reference to show.
const CODE_REFERENCE = /^([A-Za-z]{1,3}\.?\d{1,3})-_/;

export const displayQuestionCode = (code) => {
  if (!code) return code;
  const match = CODE_REFERENCE.exec(code);
  return match ? match[1] : code;
};
