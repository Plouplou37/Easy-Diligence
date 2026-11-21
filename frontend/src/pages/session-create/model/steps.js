// The four steps of "New due diligence": the list on the left, the head of
// the step in the centre.
export const STEPS = [
  {
    label: 'Fund and manager',
    hint: 'Who the review is about',
    title: 'Fund and management company',
    description:
      'The AI reads these before every question, to know which entity a question is about.',
  },
  {
    label: 'Documents',
    hint: 'What the AI searches · optional',
    title: 'Documents',
    description:
      'The AI searches them for every question. They are not sent whole: only the passages the search finds. You can also add them later.',
  },
  {
    label: 'Questionnaires',
    hint: 'What the AI answers',
    title: 'Questionnaires',
    description: 'The questions the AI answers, one by one, in their order. Choose one or more.',
  },
  {
    label: 'Review and create',
    hint: 'Check what is sent',
    title: 'Review and create',
    description:
      'Check what the AI will receive, in the “What the AI receives” panel. Creating the due diligence sends nothing to OpenAI: you start the run on its page.',
  },
];
