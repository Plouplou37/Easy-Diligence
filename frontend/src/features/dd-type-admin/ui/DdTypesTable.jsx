import { useNavigate } from 'react-router-dom';
import { DocumentTextIcon, EyeIcon, EyeSlashIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { getDdTypeIcon } from '@/entities/dd-type';
import { Badge, Button, tableStyles } from '@/shared/ui';

/** The DD types, with their questionnaire link and the admin actions. */
export const DdTypesTable = ({ ddTypes, onEdit, onToggleActive, onDelete }) => {
  const navigate = useNavigate();
  return (
  <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
    <thead className={tableStyles.thead}>
      <tr>
        <th className={tableStyles.th}>DD Type</th>
        <th className={tableStyles.th}>Status</th>
        <th className={tableStyles.thRight}>Actions</th>
      </tr>
    </thead>
    <tbody>
      {ddTypes.map((ddType, index) => {
        const Icon = getDdTypeIcon(ddType);
        return (
          <tr key={ddType.code} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
            <td className={tableStyles.td}>
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5 flex-shrink-0 text-content-secondary" />
                <div className="min-w-0">
                  {/* The code is internal: kept in the tooltip. */}
                  <h3 className="text-sm font-medium text-content" title={`Code: ${ddType.code}`}>
                    {ddType.name}
                  </h3>
                  {ddType.description && (
                    <p className="mt-0.5 text-xs text-content-secondary line-clamp-2" title={ddType.description}>
                      {ddType.description}
                    </p>
                  )}
                  <p className="mt-1 text-xs text-content-muted">
                    Created: {new Date(ddType.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </td>
            <td className={tableStyles.td}>
              <div className="flex flex-wrap items-center gap-1">
                {ddType.is_system && (
                  <Badge variant="info" size="sm">
                    System
                  </Badge>
                )}
                {!ddType.is_active && (
                  <Badge variant="warning" size="sm">
                    Inactive
                  </Badge>
                )}
              </div>
            </td>
            <td className={`${tableStyles.tdRight} whitespace-nowrap`}>
              <div className="flex items-center justify-end space-x-1">
                <Button
                  variant="secondary"
                  size="sm"
                  icon={DocumentTextIcon}
                  onClick={() => navigate(`/questions?dd_type_code=${ddType.code}`)}
                  title="Manage the questionnaire of this DD type"
                >
                  Questions
                </Button>
                <Button
                  variant="ghost"
                  icon={ddType.is_active ? EyeIcon : EyeSlashIcon}
                  onClick={() => onToggleActive(ddType)}
                  title={ddType.is_active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
                  aria-label={ddType.is_active ? `Deactivate ${ddType.name}` : `Activate ${ddType.name}`}
                />
                <Button
                  variant="ghost"
                  icon={PencilIcon}
                  onClick={() => onEdit(ddType)}
                  title="Edit"
                  aria-label={`Edit ${ddType.name}`}
                />
                {!ddType.is_system && (
                  <Button
                    variant="danger"
                    icon={TrashIcon}
                    onClick={() => onDelete(ddType)}
                    title="Delete"
                    aria-label={`Delete ${ddType.name}`}
                  />
                )}
              </div>
            </td>
          </tr>
        );
      })}
    </tbody>
  </table>
  );
};
