/**
 * The browser's own form checks (a required field left empty, an e-mail
 * address without "@"…) speak the language of the system, not of the
 * application. Their message is replaced here by an English one, for every
 * form at once; the bubble itself stays the browser's.
 */

const messageFor = field => {
  const { validity } = field;
  if (validity.valueMissing) {
    return field.type === 'file' ? 'Please choose a file.' : 'Please fill in this field.';
  }
  if (validity.typeMismatch) {
    if (field.type === 'email') return 'Please enter a valid e-mail address.';
    if (field.type === 'url')
      return 'Please enter a web address starting with http:// or https://.';
    return 'Please enter a valid value.';
  }
  if (validity.rangeUnderflow || validity.rangeOverflow) {
    if (field.min && field.max) return `Please enter a number from ${field.min} to ${field.max}.`;
    if (field.min) return `Please enter ${field.min} or more.`;
    return `Please enter ${field.max} or less.`;
  }
  if (validity.stepMismatch) return 'Please enter a whole number.';
  if (validity.badInput) return 'Please enter a number.';
  if (validity.tooShort) return `Please use at least ${field.minLength} characters.`;
  if (validity.tooLong) return `Please use at most ${field.maxLength} characters.`;
  if (validity.patternMismatch) return field.title || 'Please match the requested format.';
  return '';
};

const isField = target =>
  target instanceof HTMLInputElement ||
  target instanceof HTMLTextAreaElement ||
  target instanceof HTMLSelectElement;

const onInvalid = event => {
  const field = event.target;
  if (!isField(field)) return;
  // Clear first: a custom message makes the field invalid by itself.
  field.setCustomValidity('');
  if (!field.validity.valid) field.setCustomValidity(messageFor(field));
};

// A message set above would keep the field invalid: it goes as soon as the
// value changes, and the browser checks again on the next submit.
const onEdit = event => {
  if (isField(event.target)) event.target.setCustomValidity('');
};

let installed = false;

/** Install once, for the whole application (app/App.jsx). */
export const installEnglishValidity = () => {
  if (installed || typeof document === 'undefined') return;
  installed = true;
  document.addEventListener('invalid', onInvalid, true);
  document.addEventListener('input', onEdit, true);
  document.addEventListener('change', onEdit, true);
};
