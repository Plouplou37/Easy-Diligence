import { DocumentMagnifyingGlassIcon, GlobeAltIcon } from '@heroicons/react/24/outline';
import { SparklesIcon } from '@heroicons/react/16/solid';
import { EARLIER_ANSWERS_MAX_CHARS, ROLE_LINE, promptHeader } from '../lib/aiContext';
import { plural } from '../lib/text';

const PRE =
  'form-surface p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words text-content';

const Part = ({ title, children }) => (
  <div className="flex flex-col gap-1.5">
    <h3 className="eyebrow font-semibold">{title}</h3>
    {children}
  </div>
);

/**
 * What the model receives for this due diligence, as the draft stands: the
 * head of the system prompt, rebuilt from the fund's fields (lib/aiContext),
 * what comes with each question, the tools, and what is never sent.
 * `fields`: the fund as the AI would read it now. `collection`:
 * { name, files } or null. `example`: a question as the model gets it, or null.
 */
export const AiPreview = ({ fields, collection, example }) => {
  const header = promptHeader(fields);

  return (
    <div className="flex flex-col gap-5 rounded-xl border border-theme-ai-border bg-surface p-5">
      <div>
        <h2 className="flex items-center gap-2 font-semibold text-theme-ai">
          <SparklesIcon aria-hidden="true" className="h-4 w-4 shrink-0" />
          What the AI receives
        </h2>
        <p className="mt-1 text-xs text-content-secondary">
          Updated as you type. Nothing is sent before you start the run.
        </p>
      </div>

      <Part title="Before every question">
        <pre className={PRE}>
          <span className="text-content-muted">{ROLE_LINE}</span>
          {'\n\n'}
          {header.map((line, index) => (
            <span key={line.key}>
              {line.prefix}
              {line.value || <span className="text-content-muted">{line.placeholder}</span>}
              {line.suffix}
              {index < header.length - 1 ? '\n' : ''}
            </span>
          ))}
        </pre>
        <p className="text-xs text-content-secondary">
          Then the rules every answer follows: whether a question is about the fund or its
          management company, which tools to use, how to cite.
        </p>
      </Part>

      <Part title={example ? 'With each question, for example' : 'With each question'}>
        {example && <pre className={`${PRE} max-h-56 overflow-y-auto`}>{example}</pre>}
        <p className="text-xs text-content-secondary">
          Each question comes with its section, its “where to look” hint, and the answers already
          written for the earlier questions, up to{' '}
          {EARLIER_ANSWERS_MAX_CHARS.toLocaleString('en-US')} characters, as context.
        </p>
      </Part>

      <Part title="Tools it may use">
        <ul className="flex flex-col gap-2 text-sm text-content">
          <li className="flex items-start gap-2">
            <DocumentMagnifyingGlassIcon
              aria-hidden="true"
              className="mt-0.5 h-4 w-4 shrink-0 text-content-secondary"
            />
            {collection ? (
              <span>
                Search in <strong className="font-semibold">{collection.name}</strong>
                {collection.files !== null && ` (${plural(collection.files, 'file')})`}: only the
                passages it finds are sent.
              </span>
            ) : (
              <span className="text-content-secondary">
                No document search: no collection is chosen. The AI is told to say when a fact needs
                the fund&apos;s own documents.
              </span>
            )}
          </li>
          <li className="flex items-start gap-2">
            <GlobeAltIcon
              aria-hidden="true"
              className="mt-0.5 h-4 w-4 shrink-0 text-content-secondary"
            />
            <span>
              Web search: regulators&apos; registers, exchange filings, the press, the
              manager&apos;s website.
            </span>
          </li>
        </ul>
      </Part>

      <div className="border-t border-border pt-4">
        <h3 className="eyebrow font-semibold">Never sent</h3>
        <p className="mt-1 text-xs text-content-secondary">
          The name and description of this due diligence, your team&apos;s notes and comments, your
          name.
        </p>
      </div>
    </div>
  );
};
