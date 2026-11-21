import { useNavigate } from 'react-router-dom';
import {
  CheckCircleIcon,
  EyeIcon,
  EyeSlashIcon,
  ListBulletIcon,
  PencilIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { getDdTypeIcon } from '@/entities/dd-type';
import { useAuth } from '@/entities/viewer';
import { Badge, Button, tableStyles } from '@/shared/ui';

/** Who a questionnaire belongs to, by the backend's rules (services/authz.py). */
const ownerOf = (ddType, user) => {
  if (ddType.is_system) return 'System, shared';
  if (ddType.created_by == null) return 'Shared';
  if (ddType.created_by === user?.id) return 'You';
  return 'Another user';
};

/**
 * The questionnaires, with their size, status and owner, the link to their
 * questions and the actions. `counts`: { [code]: { sections, questions } }.
 */
export const DdTypesTable = ({ ddTypes, counts = {}, onEdit, onToggleActive, onDelete }) => {
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const open = ddType => navigate(`/questions?dd_type_code=${ddType.code}`);

  return (
    <div className={tableStyles.wrapper}>
      <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
        <thead className={tableStyles.thead}>
          <tr>
            <th className={tableStyles.th}>Questionnaire</th>
            <th className={tableStyles.th}>Code</th>
            <th className={tableStyles.thRight}>Sections</th>
            <th className={tableStyles.thRight}>Questions</th>
            <th className={tableStyles.th}>Status</th>
            <th className={tableStyles.th}>Owner</th>
            <th className={tableStyles.thRight}>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {ddTypes.map(ddType => {
            const Icon = getDdTypeIcon(ddType);
            const count = counts[ddType.code];
            // Only its owner, or an admin, may change it (services/authz.py).
            const canModify =
              isAdmin || (ddType.created_by != null && ddType.created_by === user?.id);
            return (
              <tr key={ddType.code} className={tableStyles.row}>
                <td className={`${tableStyles.td} min-w-64`}>
                  <div className="flex items-start gap-3">
                    <Icon
                      className="mt-0.5 h-5 w-5 shrink-0 text-content-muted"
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <button
                        type="button"
                        onClick={() => open(ddType)}
                        className="text-left font-medium text-content transition-colors hover:text-accent-blue"
                      >
                        {ddType.name}
                      </button>
                      {ddType.description && (
                        <p
                          className="mt-0.5 line-clamp-2 text-xs text-content-secondary"
                          title={ddType.description}
                        >
                          {ddType.description}
                        </p>
                      )}
                    </div>
                  </div>
                </td>
                <td className={`${tableStyles.td} whitespace-nowrap`}>
                  <code className="font-mono text-xs text-content-secondary">{ddType.code}</code>
                </td>
                <td className={`${tableStyles.tdRight} tabular-nums`}>
                  {count ? count.sections : '—'}
                </td>
                <td className={`${tableStyles.tdRight} tabular-nums`}>
                  {count ? count.questions : '—'}
                </td>
                <td className={tableStyles.td}>
                  <div className="flex flex-wrap items-center gap-1">
                    {ddType.is_validated ? (
                      <span title="Its sections and questions are frozen">
                        <Badge variant="success" size="sm" icon={CheckCircleIcon}>
                          Validated
                        </Badge>
                      </span>
                    ) : (
                      <span title="Its sections and questions can still change">
                        <Badge variant="neutral" size="sm">
                          Draft
                        </Badge>
                      </span>
                    )}
                    {!ddType.is_active && (
                      <span title="Not offered for new due diligences">
                        <Badge variant="warning" size="sm">
                          Inactive
                        </Badge>
                      </span>
                    )}
                  </div>
                </td>
                <td className={`${tableStyles.td} whitespace-nowrap`}>
                  <p className="text-sm text-content">{ownerOf(ddType, user)}</p>
                  <p className="text-xs tabular-nums text-content-muted">
                    Created {new Date(ddType.created_at).toLocaleDateString()}
                  </p>
                </td>
                <td className={`${tableStyles.tdRight} whitespace-nowrap`}>
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="secondary"
                      icon={ListBulletIcon}
                      onClick={() => open(ddType)}
                      title="See its sections and questions"
                    >
                      Questions
                    </Button>
                    {canModify ? (
                      <>
                        <Button
                          variant="ghost"
                          size="lg"
                          icon={ddType.is_active ? EyeSlashIcon : EyeIcon}
                          onClick={() => onToggleActive(ddType)}
                          title={
                            ddType.is_active
                              ? 'Deactivate: no longer offer it for new due diligences'
                              : 'Activate: offer it again for new due diligences'
                          }
                          aria-label={
                            ddType.is_active
                              ? `Deactivate ${ddType.name}`
                              : `Activate ${ddType.name}`
                          }
                        />
                        <Button
                          variant="ghost"
                          size="lg"
                          icon={PencilIcon}
                          onClick={() => onEdit(ddType)}
                          title="Edit its name and description"
                          aria-label={`Edit ${ddType.name}`}
                        />
                        {!ddType.is_system && (
                          <Button
                            variant="danger"
                            size="lg"
                            icon={TrashIcon}
                            onClick={() => onDelete(ddType)}
                            title="Delete"
                            aria-label={`Delete ${ddType.name}`}
                          />
                        )}
                      </>
                    ) : (
                      <span
                        className="px-2 text-xs text-content-muted"
                        title="Only its owner or an administrator can change it"
                      >
                        Read only
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
