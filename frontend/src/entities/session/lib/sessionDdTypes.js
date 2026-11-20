/**
 * The DD types of a session: those chosen at its creation (`session.dd_types`,
 * in the order chosen), or else those it has actually run. Showing the whole
 * library instead put Start buttons on questionnaires that were never part of
 * the session.
 *
 * Matched by id: a DD type renamed, or given a new code, stays the session's.
 */
export const getSessionDdTypes = (session, ddTypes, progressByCode) => {
  const chosen = session?.dd_types ?? [];
  if (chosen.length > 0) {
    const byId = new Map(ddTypes.map(ddType => [ddType.id, ddType]));
    const found = chosen.map(item => byId.get(item.id)).filter(Boolean);
    if (found.length > 0) return found;
  }
  return ddTypes.filter(ddType => progressByCode[ddType.code] !== undefined);
};
