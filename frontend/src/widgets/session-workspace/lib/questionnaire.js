import { getSourceContent, parseSourcesFromString } from '@/entities/answer';
import { displayQuestionCode } from '@/entities/dd-type';

/**
 * Where a question stands for the reviewer. A freshly generated answer is
 * stored as `completed`, not `needs_review`: every answer with a text that is
 * not approved is "to review".
 */
export const STATES = {
  review: { label: 'To review', tone: 'warning' },
  approved: { label: 'Approved', tone: 'success' },
  none: { label: 'Not answered', tone: 'neutral' },
  failed: { label: 'Failed', tone: 'error' },
};

// The order of the status filter.
export const STATE_ORDER = ['review', 'approved', 'none', 'failed'];

export const answerState = answer => {
  if (!answer) return 'none';
  if (answer.status === 'failed') return 'failed';
  if (!answer.text) return 'none';
  return answer.status === 'approved' ? 'approved' : 'review';
};

// Answered, as the run's progress counts it: an answer with a text.
export const isAnswered = state => state === 'review' || state === 'approved';

/** The start of an answer as plain text, for the list: the markdown marks left out. */
const snippetOf = text =>
  (text || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+/gm, '')
    .replace(/[*_`~|]/g, ' ')
    .replace(/^[\s:-]+$/gm, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 240);

const sourceCount = answer =>
  answer
    ? parseSourcesFromString(answer.sources).filter(source => getSourceContent(source) !== null)
        .length
    : 0;

const makeRow = (key, code, text, group, answer) => {
  const state = answerState(answer);
  return {
    key,
    code,
    displayCode: displayQuestionCode(code) || '—',
    text: text || '',
    sectionKey: group.key,
    sectionTitle: group.title,
    answer,
    state,
    snippet: snippetOf(answer?.text),
    sources: sourceCount(answer),
    // What the search box looks through.
    haystack: `${code || ''} ${text || ''} ${answer?.text || ''}`.toLowerCase(),
  };
};

/**
 * The questions of a questionnaire, by section, each with its current answer.
 *
 * `structure`: the DD type with its sections and questions, in their order;
 * null when it could not be loaded, and only the answered questions are known.
 * `answers`: the current answers of the run, matched by question code (unique
 * within a questionnaire). An answer whose question is gone or was recoded is
 * still listed, in its section or under "Other answers": nothing is hidden.
 */
export const buildQuestionnaire = (structure, answers) => {
  const groups = [];
  const groupsByKey = new Map();
  const addGroup = (key, code, title) => {
    const group = {
      key,
      code,
      title,
      label: code && code !== title ? `${code}. ${title}` : title,
      rows: [],
    };
    groups.push(group);
    groupsByKey.set(key, group);
    return group;
  };

  // The latest answer of each code (the server lists them oldest first).
  const byCode = new Map();
  answers.forEach(answer => {
    if (answer.question_code) byCode.set(answer.question_code, answer);
  });
  const matched = new Set();

  (structure?.sections || []).forEach(section => {
    const group = addGroup(`s-${section.id}`, section.section_code, section.title || 'Section');
    (section.questions || []).forEach(question => {
      const answer = byCode.get(question.question_code) || null;
      if (answer) matched.add(answer.id);
      group.rows.push(
        makeRow(`q-${question.id}`, question.question_code, question.question_text, group, answer)
      );
    });
  });

  answers
    .filter(answer => !matched.has(answer.id))
    .forEach(answer => {
      let group = groups.find(item => item.code && item.code === answer.section_code);
      if (!group) {
        const key = structure ? 'other' : `n-${answer.section_code || answer.section_name || ''}`;
        group =
          groupsByKey.get(key) ||
          (structure
            ? addGroup(key, '', 'Other answers')
            : addGroup(key, answer.section_code, answer.section_name || 'Uncategorized'));
      }
      group.rows.push(
        makeRow(`a-${answer.id}`, answer.question_code, answer.question_text, group, answer)
      );
    });

  const rows = groups.flatMap(group => group.rows);
  const sections = groups.map(group => ({
    key: group.key,
    label: group.label,
    total: group.rows.length,
    done: group.rows.filter(row => isAnswered(row.state)).length,
  }));
  return {
    rows,
    sections,
    total: rows.length,
    done: rows.filter(row => isAnswered(row.state)).length,
  };
};

/**
 * A line about the answer's version. A regeneration leaves no editor (the
 * engine stores it as the AI's); an edit, a revert or a review records who.
 */
export const versionNote = answer => {
  if (!answer?.text) return null;
  const version = answer.version || 1;
  if (version === 1) return 'Version 1 · written by the AI';
  return answer.editor_name
    ? `Version ${version} · last change by ${answer.editor_name}`
    : `Version ${version} · regenerated by the AI`;
};
