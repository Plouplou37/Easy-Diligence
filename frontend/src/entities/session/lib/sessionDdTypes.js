/**
 * The DD types of a session: those chosen at its creation (`dd_types_json`),
 * or else those it has actually run. Showing the whole library instead put
 * Start buttons on questionnaires that were never part of the session.
 */
export const getSessionDdTypes = (session, ddTypes, progressByCode) => {
  if (session?.dd_types_json) {
    try {
      const chosen = JSON.parse(session.dd_types_json);
      const found = ddTypes.filter((ddType) => chosen.some((item) => item.code === ddType.code));
      if (found.length > 0) return found;
    } catch (error) {
      console.error('Unreadable dd_types_json for this session:', error);
    }
  }
  return ddTypes.filter((ddType) => progressByCode[ddType.code] !== undefined);
};
