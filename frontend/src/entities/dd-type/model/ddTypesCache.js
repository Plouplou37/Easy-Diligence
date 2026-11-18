import { useCallback, useEffect, useState } from 'react';
import { api } from '@/shared/api';

// The DD types, fetched once and shared by every page and card that needs
// them, until a change (ddTypesAPI, questionsAPI) clears the cache. They used
// to be fetched in six places, once per DD card.
const cache = new Map();

/** The DD types the user can see, with their structure or not: a promise,
 * shared while it is cached. */
export const fetchDdTypes = ({ withQuestions = false, activeOnly = true } = {}) => {
  const key = `${withQuestions ? 'structure' : 'list'}:${activeOnly}`;
  if (!cache.has(key)) {
    const url = withQuestions ? '/questions/dd-types' : '/dd-types/';
    const request = api
      .get(url, { params: { active_only: activeOnly } })
      .then((response) => response.data)
      .catch((error) => {
        cache.delete(key); // a failure is not kept
        throw error;
      });
    cache.set(key, request);
  }
  return cache.get(key);
};

export const invalidateDdTypes = () => cache.clear();

/** { ddTypes, loading, error, reload }: the DD types, for a component. */
export const useDdTypes = ({ withQuestions = false, activeOnly = true } = {}) => {
  const [state, setState] = useState({ ddTypes: [], loading: true, error: null });

  const load = useCallback(() => {
    setState((previous) => ({ ...previous, loading: true }));
    return fetchDdTypes({ withQuestions, activeOnly })
      .then((ddTypes) => setState({ ddTypes, loading: false, error: null }))
      .catch((error) => setState({ ddTypes: [], loading: false, error }));
  }, [withQuestions, activeOnly]);

  useEffect(() => {
    load();
  }, [load]);

  const reload = useCallback(() => {
    invalidateDdTypes();
    return load();
  }, [load]);

  return { ...state, reload };
};
