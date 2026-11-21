import { Navigate, useLocation, useParams } from 'react-router-dom';

/**
 * The answers of a session used to have their own page; they are now part of
 * the session's workspace. Links to the old address (`?dd_type=…&tab=…`) land
 * there, on the same questionnaire and tab.
 */
const SessionAnswersRedirect = () => {
  const { sessionId } = useParams();
  const { search } = useLocation();
  return <Navigate replace to={{ pathname: `/session/${sessionId}`, search }} />;
};

export default SessionAnswersRedirect;
