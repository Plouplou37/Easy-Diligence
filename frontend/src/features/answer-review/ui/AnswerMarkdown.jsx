import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const PLUGINS = [remarkGfm];

// The model answers with markdown tables often enough to matter (22 of the 72
// answers of one full run). `prose` styles them but does not make them
// scrollable: in a narrow column, the right-hand columns were out of reach.
const COMPONENTS = {
  // `node` (react-markdown's syntax tree) must not reach the DOM.
  table: ({ node, ...props }) => (
    <div className="overflow-x-auto">
      <table {...props} />
    </div>
  ),
};

/** The text of an answer (markdown), rendered as wherever answers are read. */
const AnswerMarkdown = ({ children, className = '' }) => (
  <div className={`prose prose-sm max-w-none text-content ${className}`}>
    <ReactMarkdown remarkPlugins={PLUGINS} components={COMPONENTS}>
      {children}
    </ReactMarkdown>
  </div>
);

export default AnswerMarkdown;
