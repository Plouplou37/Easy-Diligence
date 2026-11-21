import { FOCUS_RING } from '../lib/focus';
import { ThinBar } from './Chips';

const SectionItem = ({ label, done, total, pressed, onClick }) => (
  <li>
    <button
      type="button"
      onClick={onClick}
      aria-pressed={pressed}
      className={`flex min-h-11 w-full flex-col gap-1.5 rounded-lg border px-2.5 py-2 text-left text-sm transition-colors ${FOCUS_RING} ${
        pressed ? 'border-primary bg-primary-dark' : 'border-transparent hover:bg-surface-hover'
      }`}
    >
      <span className="flex w-full items-start justify-between gap-2">
        <span className="min-w-0 font-medium text-content wrap-break-word">{label}</span>
        <span className="shrink-0 text-xs text-content-secondary tabular-nums">
          {done}/{total}
        </span>
      </span>
      <ThinBar
        percentage={total > 0 ? (done / total) * 100 : 0}
        fill={total > 0 && done === total ? 'bg-theme-success' : 'bg-primary'}
      />
    </button>
  </li>
);

/** The sections of the questionnaire, answered / total: picking one filters the list. */
export const SectionNav = ({ sections, done, total, selected, onSelect }) => (
  <nav aria-labelledby="sections-title" className="rounded-xl border border-border bg-surface p-3">
    <h2 id="sections-title" className="eyebrow px-1 pb-2">
      Sections
    </h2>
    <ul className="space-y-0.5">
      <SectionItem
        label="All questions"
        done={done}
        total={total}
        pressed={!selected}
        onClick={() => onSelect('')}
      />
      {sections.map(section => (
        <SectionItem
          key={section.key}
          label={section.label}
          done={section.done}
          total={section.total}
          pressed={selected === section.key}
          onClick={() => onSelect(section.key)}
        />
      ))}
    </ul>
  </nav>
);
