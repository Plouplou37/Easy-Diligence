import { useEffect, useState } from 'react';
import { companyAPI } from '@/entities/company';
import { AiBadge } from '@/shared/ui';

/** A website, as a link that opens in a new tab, shown without its scheme. */
const Website = ({ url }) =>
  url ? (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="text-xs text-accent-blue hover:underline break-all"
    >
      {url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
    </a>
  ) : null;

/**
 * The fund under review and the company running it. The model reads all of
 * this before every question (services/processing.build_company_info): the
 * names, the two websites and the description, hence the badge and every
 * field shown.
 */
export const FundCard = ({ session }) => {
  const [company, setCompany] = useState(null);

  useEffect(() => {
    if (!session.company_id) return undefined;
    let current = true;
    companyAPI
      .get(session.company_id)
      .then(response => {
        if (current) setCompany(response.data);
      })
      // The names below come with the session: the card stays useful.
      .catch(() => {});
    return () => {
      current = false;
    };
  }, [session.company_id]);

  const name = company?.name || session.company_name;
  const manager = company?.management_company_name || session.management_company_name;

  return (
    <section
      aria-labelledby="fund-card-title"
      className="rounded-xl border border-border bg-surface p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="fund-card-title" className="eyebrow">
          Fund
        </h2>
        <AiBadge title="The AI reads all of these before every question.">Sent to the AI</AiBadge>
      </div>
      <p className="mt-2 font-semibold text-content wrap-break-word">{name || 'Fund not named'}</p>
      <Website url={company?.website_url} />
      {company?.description && (
        <p className="mt-2 text-xs text-content-secondary wrap-break-word line-clamp-4">
          {company.description}
        </p>
      )}
      {manager && (
        <div className="mt-3">
          <p className="text-xs text-content-muted">Management company</p>
          <p className="text-sm text-content wrap-break-word">{manager}</p>
          <Website url={company?.management_company_website} />
        </div>
      )}
      <p className="mt-3 border-t border-border pt-3 text-xs text-content-muted tabular-nums">
        {session.session_code || `SES-${session.id}`} · created{' '}
        {new Date(session.created_at).toLocaleDateString()}
      </p>
    </section>
  );
};
