import toast from 'react-hot-toast';
import { ddTypesAPI, useDdTypes } from '@/entities/dd-type';
import { errorMessage } from '@/shared/api';
import { useConfirm } from '@/shared/lib/confirm';
import { generateCode, guessIcon } from '../lib/ddTypeDefaults';

/** { [code]: { sections, questions } }: the size of each questionnaire. */
const countStructures = structures =>
  Object.fromEntries(
    structures.map(ddType => [
      ddType.code,
      {
        sections: ddType.sections?.length || 0,
        questions: (ddType.sections || []).reduce(
          (total, section) => total + (section.questions?.length || 0),
          0
        ),
      },
    ])
  );

/**
 * Every questionnaire (DD type), inactive ones included, with the number of
 * its sections and questions (`counts`, by code: empty until known), and what
 * a user does with them: create (empty or from a file), edit, (de)activate,
 * delete. Each change clears the shared cache (ddTypesAPI), then both lists
 * are fetched again.
 */
export const useDdTypeAdmin = () => {
  const confirm = useConfirm();
  const { ddTypes, loading, reload } = useDdTypes({ activeOnly: false });
  const structures = useDdTypes({ withQuestions: true, activeOnly: false });
  const counts = countStructures(structures.ddTypes);

  const attempt = async (action, success, failure) => {
    try {
      await action();
      toast.success(success);
      await Promise.all([reload(), structures.reload()]);
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
        `Questionnaire "${name}" imported with its sections and questions`,
        'The questionnaire could not be imported'
      );
    }
    const lastOrder = Math.max(0, ...ddTypes.map(ddType => ddType.order_index || 0));
    return attempt(
      () => ddTypesAPI.create({ code, name, description, icon, order_index: lastOrder + 1 }),
      `Questionnaire "${name}" created`,
      'The questionnaire could not be created'
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
      'Questionnaire updated',
      'The questionnaire could not be updated'
    );

  const toggleActive = ddType =>
    ddType.is_active
      ? attempt(
          () => ddTypesAPI.deactivate(ddType.code),
          `"${ddType.name}" is no longer offered for new due diligences`,
          'The questionnaire could not be deactivated'
        )
      : attempt(
          () => ddTypesAPI.activate(ddType.code),
          `"${ddType.name}" is offered again for new due diligences`,
          'The questionnaire could not be activated'
        );

  const remove = async ddType => {
    const confirmed = await confirm({
      title: 'Delete questionnaire',
      message: `Delete "${ddType.name}" with its sections and questions? This cannot be undone.`,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!confirmed) return false;
    return attempt(
      () => ddTypesAPI.delete(ddType.code),
      'Questionnaire deleted',
      'The questionnaire could not be deleted'
    );
  };

  return {
    ddTypes,
    loading,
    counts,
    countsLoading: structures.loading,
    create,
    update,
    toggleActive,
    remove,
  };
};
