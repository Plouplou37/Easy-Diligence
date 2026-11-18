import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  EyeSlashIcon,
  EyeIcon,
  DocumentTextIcon,
  ArrowUpTrayIcon
} from '@heroicons/react/24/outline';
import {
  Button,
  LoadingSpinner,
  Badge,
  EmptyState,
  PageHeader,
  field,
  modalStyles,
  pageLayout,
  panel,
  sectionHeader,
  tableStyles,
  tabs,
} from '@/shared/ui';
import { ddTypesAPI, fetchDdTypes, getDdTypeIcon, questionsAPI } from '@/entities/dd-type';
import toast from 'react-hot-toast';

const DDTypeManagement = () => {
  const [ddTypes, setDdTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingType, setEditingType] = useState(null);
  const [creationMode, setCreationMode] = useState('manual'); // 'manual' or 'import'
  const navigate = useNavigate();

  useEffect(() => {
    loadDdTypes();
  }, []);

  const loadDdTypes = async () => {
    try {
      setLoading(true);
      setDdTypes(await fetchDdTypes({ activeOnly: false })); // inactive ones too
    } catch (error) {
      toast.error('Failed to load DD types');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setCreationMode('manual');
    setEditingType({
      code: '',
      name: '',
      description: '',
      icon: '',
      file: null,
      isNew: true
    });
  };

  // Function to auto-generate a unique code based on the DD Type name
  const generateUniqueCode = (name) => {
    if (!name) return '';
    
    // Create base code from name (first 3-4 words, uppercase, underscore-separated)
    const baseCode = name
      .split(' ')
      .slice(0, 3)
      .map(word => word.toUpperCase())
      .join('_')
      .replace(/[^A-Z0-9_]/g, '')
      .substring(0, 20);
    
    // Add timestamp suffix for uniqueness
    const timestamp = Date.now().toString(36).toUpperCase().slice(-4);
    
    return `${baseCode}_${timestamp}`;
  };

  // Function to auto-select an icon based on the DD Type name
  const selectAutoIcon = (name) => {
    const nameLower = name.toLowerCase();
    
    // Keywords to icon mapping
    const iconMap = {
      'technical': '🔧',
      'tech': '🔧',
      'legal': '⚖️',
      'law': '⚖️',
      'compliance': '⚖️',
      'financial': '💰',
      'finance': '💰',
      'accounting': '💰',
      'commercial': '💼',
      'business': '💼',
      'sales': '💼',
      'market': '📊',
      'marketing': '📊',
      'hr': '👥',
      'human': '👥',
      'people': '👥',
      'environmental': '🌱',
      'esg': '🌱',
      'sustainability': '🌱',
      'it': '💻',
      'software': '💻',
      'security': '🔒',
      'cyber': '🔒',
      'data': '📊',
      'operational': '⚙️',
      'operations': '⚙️',
      'supply': '📦',
      'logistics': '📦',
      'product': '🛠️',
      'quality': '✅',
      'risk': '⚠️',
      'audit': '📋',
      'tax': '📑',
      'intellectual': '💡',
      'property': '🏢',
      'real estate': '🏢'
    };
    
    // Find matching keyword
    for (const [keyword, icon] of Object.entries(iconMap)) {
      if (nameLower.includes(keyword)) {
        return icon;
      }
    }
    
    // Default icon
    return '📋';
  };

  const handleEdit = (ddType) => {
    setEditingType({
      ...ddType,
      isNew: false
    });
  };

  const handleSave = async () => {
    try {
      if (editingType.isNew) {
        // Auto-generate code if not provided
        const finalCode = editingType.code || generateUniqueCode(editingType.name);

        // Auto-select icon if not provided
        const finalIcon = editingType.icon || selectAutoIcon(editingType.name);

        if (creationMode === 'import' && editingType.file) {
          // Handle file import
          const formData = new FormData();
          formData.append('code', finalCode);
          formData.append('name', editingType.name);
          formData.append('description', editingType.description || '');
          formData.append('icon', finalIcon);
          formData.append('file', editingType.file);

          await ddTypesAPI.importFromFile(formData);
          toast.success(`DD Type "${editingType.name}" created successfully with imported sections and questions`);
        } else {
          // Handle manual creation
          // Auto-calculate order_index based on existing types
          const maxOrder = Math.max(...ddTypes.map(t => t.order_index || 0), 0);

          await ddTypesAPI.create({
            code: finalCode,
            name: editingType.name,
            description: editingType.description,
            icon: finalIcon,
            order_index: maxOrder + 1
          });
          toast.success('DD type created successfully');
        }
      } else {
        await ddTypesAPI.update(editingType.code, {
          code: editingType.code,
          name: editingType.name,
          description: editingType.description,
          icon: editingType.icon || selectAutoIcon(editingType.name),
          order_index: editingType.order_index
        });
        toast.success('DD type updated successfully');
      }

      setEditingType(null);
      setCreationMode('manual');
      await loadDdTypes();
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to save DD type';
      toast.error(errorMessage);
    }
  };

  const handleDelete = async (ddType) => {
    if (!window.confirm(`Are you sure you want to delete "${ddType.name}"?`)) {
      return;
    }

    try {
      await ddTypesAPI.delete(ddType.code);
      toast.success('DD type deleted successfully');
      await loadDdTypes();
    } catch (error) {
      if (error.response?.status === 409) {
        toast.error('Cannot delete DD type that is in use. Deactivate it instead.');
      } else if (error.response?.status === 403) {
        toast.error('Cannot delete system DD type.');
      } else {
        toast.error('Failed to delete DD type');
      }
    }
  };

  const handleToggleActive = async (ddType) => {
    try {
      if (ddType.is_active) {
        await ddTypesAPI.deactivate(ddType.code);
        toast.success('DD type deactivated');
      } else {
        await ddTypesAPI.activate(ddType.code);
        toast.success('DD type activated');
      }
      await loadDdTypes();
    } catch (error) {
      toast.error('Failed to update DD type status');
    }
  };

  const handleManageQuestions = async (ddType) => {
    try {
      navigate(`/questions?dd_type_code=${ddType.code}`);
    } catch (error) {
      toast.error('Failed to navigate to questions page');
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['.xlsx', '.xls', '.csv', '.json'];
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

      if (!validTypes.includes(fileExtension)) {
        toast.error('Please select a valid file format (.xlsx, .xls, .csv, .json)');
        return;
      }

      // Update the editing type with the file
      setEditingType(prev => ({ ...prev, file }));

      // Auto-suggest name from file name if not already set
      if (!editingType.name) {
        const suggestedName = file.name
          .replace(/\.[^/.]+$/, '') // Remove file extension
          .replace(/[_-]/g, ' ')     // Replace underscores and hyphens with spaces
          .replace(/\b\w/g, l => l.toUpperCase()); // Capitalize first letter of each word

        setEditingType(prev => ({
          ...prev,
          name: suggestedName,
          icon: selectAutoIcon(suggestedName)
        }));
      }
    }
  };

  if (loading) {
    return (
      <>
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" text="Loading DD types..." />
        </div>
      </>
    );
  }

  return (
    <>
      <div className={pageLayout.container}>
        <PageHeader
          breadcrumb={[{ label: 'DD Types' }]}
          title="DD Type Management"
          subtitle="Manage due diligence types available in the system"
          actions={(
            <Button onClick={handleCreate} variant="primary" icon={PlusIcon}>
              Add DD Type
            </Button>
          )}
        />

        {/* DD Types List */}
        <div className={`${panel.base} overflow-hidden`}>
          <div className={panel.header}>
            <div className={sectionHeader.wrapper}>
              <h2 className={sectionHeader.title}>Available DD Types</h2>
              <div className={sectionHeader.hairline} />
            </div>
          </div>

          <div className={tableStyles.wrapper}>
            {ddTypes.length > 0 ? (
              <table className={`${tableStyles.table} ${tableStyles.inPanel}`}>
                <thead className={tableStyles.thead}>
                  <tr>
                    <th className={tableStyles.th}>DD Type</th>
                    <th className={tableStyles.th}>Status</th>
                    <th className={tableStyles.thRight}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {ddTypes.map((ddType, index) => (
                    <tr key={ddType.code} className={`${tableStyles.row} ${tableStyles.rowAlt(index)}`}>
                      <td className={tableStyles.td}>
                        <div className="flex items-center gap-3">
                          {(() => {
                            const Icon = getDdTypeIcon(ddType);
                            return <Icon className="w-5 h-5 flex-shrink-0 text-content-secondary" />;
                          })()}
                          <div className="min-w-0">
                            {/* The code is internal: kept in the tooltip. */}
                            <h3 className="text-sm font-medium text-content" title={`Code: ${ddType.code}`}>{ddType.name}</h3>
                            {ddType.description && (
                              <p className="mt-0.5 text-xs text-content-secondary line-clamp-2" title={ddType.description}>
                                {ddType.description}
                              </p>
                            )}
                            <div className="flex items-center space-x-4 mt-1 text-xs text-content-muted">
                              <span>Created: {new Date(ddType.created_at).toLocaleDateString()}</span>
                            </div>
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
                            onClick={() => handleManageQuestions(ddType)}
                            variant="secondary"
                            size="sm"
                            icon={DocumentTextIcon}
                            title="Manage Questions for DD Type"
                          >
                            Questions
                          </Button>
                          <button
                            onClick={() => handleToggleActive(ddType)}
                            className="p-1.5 rounded-md text-content-muted hover:text-content hover:bg-surface-hover transition-colors"
                            title={ddType.is_active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
                          >
                            {ddType.is_active ? (
                              <EyeIcon className="w-4 h-4" />
                            ) : (
                              <EyeSlashIcon className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => handleEdit(ddType)}
                            className="p-1.5 rounded-md text-content-muted hover:text-content hover:bg-surface-hover transition-colors"
                            title="Edit"
                          >
                            <PencilIcon className="w-4 h-4" />
                          </button>
                          {!ddType.is_system && (
                            <button
                              onClick={() => handleDelete(ddType)}
                              className="p-1.5 rounded-md text-content-muted hover:text-theme-error hover:bg-theme-error-bg transition-colors"
                              title="Delete"
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState
                icon={DocumentTextIcon}
                title="No DD types found."
                action={(
                  <Button onClick={handleCreate} variant="ghost" size="sm">
                    Create the first one
                  </Button>
                )}
              />
            )}
          </div>
        </div>

        {/* Edit Modal */}
        {editingType && (
          <div className={modalStyles.overlay}>
            <div className={`${modalStyles.panel} max-w-2xl`}>
              <div className={modalStyles.header}>
                <h3 className={modalStyles.title}>
                  {editingType.isNew ? 'Create New DD Type' : 'Edit DD Type'}
                </h3>
              </div>

              {/* Creation Mode Toggle (only for new DD Types) */}
              {editingType.isNew && (
                <div className="px-5 py-3 border-b border-border">
                  <div className={tabs.group}>
                    <button
                      onClick={() => setCreationMode('manual')}
                      className={`${tabs.tab} ${
                        creationMode === 'manual'
                          ? tabs.active
                          : tabs.inactive
                      }`}
                    >
                      Manual Entry
                      <span className={creationMode === 'manual' ? tabs.indicator : ''} />
                    </button>
                    <button
                      onClick={() => setCreationMode('import')}
                      className={`${tabs.tab} ${tabs.divider} flex items-center ${
                        creationMode === 'import'
                          ? tabs.active
                          : tabs.inactive
                      }`}
                    >
                      <ArrowUpTrayIcon className="w-4 h-4 mr-2" />
                      Import from File
                      <span className={creationMode === 'import' ? tabs.indicator : ''} />
                    </button>
                  </div>
                </div>
              )}

              <div className={`${modalStyles.body} space-y-4`}>
                {/* Show code field only when editing existing DD Types */}
                {!editingType.isNew && (
                  <div>
                    <label className={field.label}>
                      Code (Read-only)
                    </label>
                    <input
                      type="text"
                      value={editingType.code}
                      className="form-input w-full px-3 py-2 text-sm opacity-60"
                      disabled={true}
                    />
                  </div>
                )}

                <div>
                  <label className={field.label}>
                    Name *
                  </label>
                  <input
                    type="text"
                    value={editingType.name}
                    onChange={(e) => setEditingType(prev => ({
                      ...prev,
                      name: e.target.value
                    }))}
                    className="form-input w-full px-3 py-2 text-sm"
                    placeholder="Technical Due Diligence"
                  />
                </div>

                <div>
                  <label className={field.label}>
                    Description
                  </label>
                  <textarea
                    value={editingType.description || ''}
                    onChange={(e) => setEditingType(prev => ({
                      ...prev,
                      description: e.target.value
                    }))}
                    rows={3}
                    className="form-input w-full px-3 py-2 text-sm"
                    placeholder="Detailed technical assessment of systems and infrastructure"
                  />
                </div>

                {/* File Upload Section (only for import mode) */}
                {editingType.isNew && creationMode === 'import' && (
                  <div>
                    <label className={field.label}>
                      Upload File *
                    </label>
                    <div className="mt-1">
                      <input
                        type="file"
                        accept=".xlsx,.xls,.csv,.json"
                        onChange={handleFileChange}
                        className="block w-full text-sm text-content-secondary file:mr-3 file:rounded-md file:border-0 file:bg-accent-blue/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent-blue file:cursor-pointer hover:file:bg-accent-blue/20"
                      />
                      <p className={field.help}>
                        Supported formats: Excel (.xlsx, .xls), CSV (.csv), JSON (.json)
                      </p>
                    </div>

                    {/* File Preview */}
                    {editingType.file && (
                      <div className="mt-3 p-3 form-surface">
                        <div className="flex items-center">
                          <DocumentTextIcon className="w-5 h-5 text-content-muted mr-2" />
                          <div>
                            <p className="text-sm text-content">
                              {editingType.file.name}
                            </p>
                            <p className="text-xs text-content-muted">
                              {(editingType.file.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className={modalStyles.footer}>
                <Button
                  onClick={() => {
                    setEditingType(null);
                    setCreationMode('manual');
                  }}
                  variant="secondary"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={!editingType.name || (creationMode === 'import' && editingType.isNew && !editingType.file)}
                  variant="primary"
                >
                  {editingType.isNew ?
                    (creationMode === 'import' ? 'Import DD Type' : 'Create DD Type')
                    : 'Save Changes'}
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </>
  );
};

export default DDTypeManagement;