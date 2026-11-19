import toast from 'react-hot-toast';
import { ddTypesAPI, useDdTypes } from '@/entities/dd-type';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';
import { generateCode, guessIcon } from '../lib/ddTypeDefaults';

/**
 * Every DD type, inactive ones included, and what an admin does with them:
 * create (by hand or from a file), edit, (de)activate, delete. Each change
 * clears the shared cache (ddTypesAPI), then the list is fetched again.
 */
export const useDdTypeAdmin = () => {
  const confirm = useConfirm();
  const { ddTypes, loading, reload } = useDdTypes({ activeOnly: false });

  const attempt = async (action, success, failure) => {
    try {
      await action();
      toast.success(success);
      await reload();
      return true;
    } catch (error) {
      toast.error(errorMessage(error, failure));
      return false;
    }
  };

  const create = ({ name, description, file }) => {
    const code = generateCode(name);
    const icon = guessIcon(name);
    if (file) {
      const form = new FormData();
      form.append('code', code);
      form.append('name', name);
      form.append('description', description || '');
      form.append('icon', icon);
      form.append('file', file);
      return attempt(
        () => ddTypesAPI.importFromFile(form),
        `DD Type "${name}" created with its imported sections and questions`,
        'Failed to import DD type'
      );
    }
    const lastOrder = Math.max(0, ...ddTypes.map(ddType => ddType.order_index || 0));
    return attempt(
      () => ddTypesAPI.create({ code, name, description, icon, order_index: lastOrder + 1 }),
      'DD type created successfully',
      'Failed to create DD type'
    );
  };

  const update = (ddType, { name, description }) =>
    attempt(
      () =>
        ddTypesAPI.update(ddType.code, {
          code: ddType.code,
          name,
          description,
          icon: ddType.icon || guessIcon(name),
          order_index: ddType.order_index,
        }),
      'DD type updated successfully',
      'Failed to update DD type'
    );

  const toggleActive = ddType =>
    ddType.is_active
      ? attempt(
          () => ddTypesAPI.deactivate(ddType.code),
          'DD type deactivated',
          'Failed to deactivate DD type'
        )
      : attempt(
          () => ddTypesAPI.activate(ddType.code),
          'DD type activated',
          'Failed to activate DD type'
        );

  const remove = async ddType => {
    const confirmed = await confirm({
      title: 'Delete DD type',
      message: `Delete "${ddType.name}" with its questionnaire? This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return false;
    return attempt(
      () => ddTypesAPI.delete(ddType.code),
      'DD type deleted successfully',
      'Failed to delete DD type'
    );
  };

  return { ddTypes, loading, create, update, toggleActive, remove };
};
