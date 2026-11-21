// What the model reads, rebuilt in the browser from the draft. Mirrors the
// backend: keep it in step with engine/openai_client._build_system_prompt and
// engine/processor.compose_question_text.

/** The first line of the system prompt. */
export const ROLE_LINE =
  'You are a due diligence expert analyzing company information and documents.';

/** engine/processor.EARLIER_ANSWERS_MAX_CHARS */
export const EARLIER_ANSWERS_MAX_CHARS = 30_000;

/**
 * The lines of the system prompt that describe the fund, as
 * _build_system_prompt writes them: the fund (with its website), the
 * management company only when it is known, the overview only when there is
 * one. `value` is empty when the fund has no name yet: the form requires one.
 */
export const promptHeader = fields => {
  const read = key => (fields?.[key] || '').trim();
  const site = url => (url ? ` (${url})` : '');
  const lines = [
    {
      key: 'fund',
      prefix: 'FUND UNDER REVIEW: ',
      value: read('name'),
      placeholder: '[fund name]',
      suffix: site(read('website_url')),
    },
  ];
  if (read('management_company_name')) {
    lines.push({
      key: 'manager',
      prefix: 'MANAGEMENT COMPANY: ',
      value: read('management_company_name'),
      suffix: site(read('management_company_website')),
    });
  }
  if (read('description')) {
    lines.push({ key: 'overview', prefix: 'Overview: ', value: read('description'), suffix: '' });
  }
  return lines;
};

/**
 * The first question of a questionnaire as the model receives it
 * (compose_question_text): its section heading, with the section's
 * description when it has one, the question, and its "where to look" hint.
 * Null when the questionnaire has no question, or its structure is unknown.
 */
export const questionExample = questionnaire => {
  for (const section of questionnaire?.sections || []) {
    const question = section.questions?.[0];
    if (!question) continue;
    const parts = [];
    if (section.title) {
      const description = (section.description || '').trim();
      parts.push(`[Section: ${section.title}]${description ? `\n${description}` : ''}`);
    }
    parts.push(question.question_text);
    const sources = (question.context_prompt || '').trim();
    if (sources) parts.push(`Where to look: ${sources}`);
    return parts.join('\n\n');
  }
  return null;
};
