import Breadcrumb from './Breadcrumb';
import { pageHeader } from './styles';

/**
 * Page header shared by every screen: optional breadcrumb, title, subtitle,
 * actions on the right of the title, gradient hairline. Pages used to mix a
 * breadcrumb, a "Back to…" button, a header inside a panel, or nothing at all.
 * @param {Object} props
 * @param {Array<{label: string, href?: string}>} props.breadcrumb - Trail after "Dashboard"; omit on the Dashboard itself
 * @param {React.ReactNode} props.title - Page title
 * @param {React.ReactNode} props.subtitle - Optional line under the title
 * @param {React.ReactNode} props.meta - Optional small line under the subtitle
 * @param {React.ReactNode} props.actions - Buttons shown on the right of the title
 */
export const PageHeader = ({ breadcrumb, title, subtitle, meta, actions }) => (
  <div>
    {breadcrumb && <Breadcrumb items={breadcrumb} />}
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className={pageHeader.title}>{title}</h1>
        {subtitle && <p className={pageHeader.subtitle}>{subtitle}</p>}
        {meta && <div className="mt-2 text-xs text-content-muted">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
    <div className={pageHeader.hairline} />
  </div>
);
