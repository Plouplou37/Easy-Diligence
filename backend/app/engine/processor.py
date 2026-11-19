import logging
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import get_db
from app.engine.openai_client import OpenAIProcessor
from app.engine.rate_limiter import RateLimiter
from app.models.answer import AnswerStatus, DDAnswer, ErrorType
from app.models.answer_history import DDAnswerHistory
from app.models.execution import DDExecution, ExecutionStatus
from app.models.message import DDMessage
from app.models.questions import DDQuestion, DDSection
from app.models.response import DDResponse

logger = logging.getLogger(__name__)


class DDProcessor:
    MAX_RETRIES = 3  # Maximum retry attempts per question
    CIRCUIT_BREAKER_THRESHOLD = 1  # Stop after N questions fail with global errors

    def __init__(self, session_id: int, dd_type: str):
        self.session_id = session_id
        self.dd_type = dd_type
        self.openai_processor = OpenAIProcessor()
        self.rate_limiter = RateLimiter()
        self.execution = None
        self.conversation_id = None

        # Circuit breaker state for global errors (quota, API down, network)
        self.consecutive_global_failures = 0
        self.last_global_error_type = None
        self.circuit_open = False

    def _categorize_error(self, error: Exception) -> tuple[ErrorType, bool]:
        """
        Categorize error and determine if it's retryable
        Returns: (ErrorType, is_retryable)
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()

        # Rate limit errors
        if "rate" in error_str and "limit" in error_str:
            return ErrorType.RATE_LIMIT, True

        # Context overflow errors
        if "context" in error_str and (
            "length" in error_str or "exceeded" in error_str or "overflow" in error_str
        ):
            return ErrorType.CONTEXT_OVERFLOW, True

        # Network/connection errors
        if any(keyword in error_type_name for keyword in ["connection", "timeout", "network"]):
            return ErrorType.NETWORK_ERROR, True
        if any(keyword in error_str for keyword in ["connection", "timeout", "network"]):
            return ErrorType.NETWORK_ERROR, True

        # Timeout errors
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT, True

        # Validation errors (not retryable)
        if "validation" in error_str or "invalid" in error_str:
            return ErrorType.VALIDATION_ERROR, False

        # General API errors (retryable with caution)
        if "api" in error_str or "openai" in error_str:
            return ErrorType.API_ERROR, True

        # Unknown error (retryable with caution)
        return ErrorType.UNKNOWN, True

    @staticmethod
    def compose_question_text(question) -> str:
        """The question as the model sees it: section heading + text + sources.

        Two things used to be dropped on the floor here. The section title never
        left the database, so a question arrived stripped of its theme. And
        ``context_prompt`` -- offered in the UI as "Context Prompt / Provide
        context or hints for answering..." -- was stored and displayed but never
        sent, so anyone filling it in was working for nothing.

        ``context_prompt`` now carries the "where to look" instruction of the
        reference questionnaires, moved out of the question text so it can be
        edited. It is labelled "Where to look" whatever its origin, which is what
        makes questionnaires speak the same language when their source workbooks
        name that column differently ("Document / evidence expected" against
        "Expected answer / evidence").
        """
        parts = []

        section = getattr(question, "section", None)
        if section is not None and section.title:
            heading = f"[Section: {section.title}]"
            # The section description is analyst-written context about the theme.
            # It is only sent when it says something: imports used to fill it with
            # "Section for <title>", which would repeat the title once per question.
            description = (getattr(section, "description", None) or "").strip()
            if description:
                heading = f"{heading}\n{description}"
            parts.append(heading)

        parts.append(question.question_text)

        sources = (getattr(question, "context_prompt", None) or "").strip()
        if sources:
            parts.append(f"Where to look: {sources}")

        return "\n\n".join(parts)

    def _calculate_backoff_delay(self, retry_attempt: int, error_type: ErrorType) -> float:
        """
        Calculate exponential backoff delay in seconds
        """
        base_delay = 1.0  # 1 second base

        # Different backoff strategies based on error type
        if error_type == ErrorType.RATE_LIMIT:
            # Longer backoff for rate limits
            base_delay = 5.0
        elif error_type == ErrorType.CONTEXT_OVERFLOW:
            # Shorter backoff for context issues
            base_delay = 0.5
        elif error_type == ErrorType.NETWORK_ERROR:
            # Medium backoff for network issues
            base_delay = 2.0

        # Exponential backoff: delay = base * (2 ^ attempt)
        delay = base_delay * (2**retry_attempt)

        # Cap at 60 seconds
        return min(delay, 60.0)

    def _is_global_error(self, error_type: ErrorType) -> bool:
        """
        Determine if error affects all questions (global) or just one (local)

        Global errors (affect ALL questions):
        - RATE_LIMIT: API quota exceeded, all questions will fail
        - NETWORK_ERROR: Network/connection down, all questions will fail
        - API_ERROR: OpenAI API server issues (500 errors), all questions will fail

        Local errors (question-specific):
        - CONTEXT_OVERFLOW: Question too long, only affects this question
        - VALIDATION_ERROR: Invalid parameters, only affects this question
        - TIMEOUT: May be question-specific (complex query)
        - UNKNOWN: Could be either, treat as local to be safe
        """
        return error_type in [ErrorType.RATE_LIMIT, ErrorType.NETWORK_ERROR, ErrorType.API_ERROR]

    def _should_continue_processing(self, db: Session) -> bool:
        """
        Check if processing should continue or has been paused by user
        Returns False if execution status changed to FAILED (paused)
        """
        if not self.execution:
            return True

        # Refresh execution status from database
        db.refresh(self.execution)

        # Stop processing if status changed to FAILED (paused by user)
        if self.execution.status != ExecutionStatus.IN_PROGRESS:
            logger.info(f"Processing stopped: execution status is {self.execution.status}")
            return False

        return True

    def start_processing(self, vector_store_ids: list, company_info: dict) -> bool:
        """Start processing DD questions for the given type with new execution workflow"""
        db = next(get_db())
        try:
            # Create or get execution record
            self.execution = self._get_or_create_execution(db)
            self.conversation_id = str(uuid.uuid4())

            # Update execution status to in_progress
            self.execution.status = ExecutionStatus.IN_PROGRESS
            self.execution.conversation_id = self.conversation_id
            db.commit()

            # Get questions to process
            questions = self._get_questions_to_process(db)

            logger.info(
                f"Starting processing for execution {self.execution.id} with {len(questions)} questions"
            )

            # Track success and failure counts
            successful_count = 0
            failed_count = 0

            # Process each question
            for question in questions:
                # Check if processing should continue (user may have paused)
                if not self._should_continue_processing(db):
                    logger.info(
                        f"Processing paused by user after {successful_count} successful questions"
                    )
                    break

                # Check circuit breaker - stop if too many consecutive global errors
                if self.circuit_open:
                    logger.error(
                        f"Circuit breaker OPEN - stopping processing after {self.consecutive_global_failures} "
                        f"consecutive {self.last_global_error_type.value} errors. "
                        f"Processed {successful_count}/{len(questions)} questions successfully, "
                        f"{failed_count} failed. Remaining questions skipped to avoid wasting retries."
                    )
                    self.execution.status = ExecutionStatus.FAILED
                    db.commit()
                    break

                try:
                    self._process_single_question(db, question, vector_store_ids, company_info)
                    successful_count += 1
                    logger.info(
                        f"Successfully processed question {question.question_code} ({successful_count}/{len(questions)})"
                    )
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing question {question.question_code}: {e}")
                    logger.error(f"Error type: {type(e).__name__}")
                    import traceback

                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    logger.error(f"Failed questions count: {failed_count}/{len(questions)}")

                    # Track consecutive failures for circuit breaker
                    error_type, _ = self._categorize_error(e)
                    if self._is_global_error(error_type):
                        self.consecutive_global_failures += 1
                        self.last_global_error_type = error_type
                        logger.warning(
                            f"Global error detected ({error_type.value}). "
                            f"Consecutive failures: {self.consecutive_global_failures}/{self.CIRCUIT_BREAKER_THRESHOLD}"
                        )

                        # Check if circuit breaker threshold reached
                        if self.consecutive_global_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                            self.circuit_open = True
                            logger.error(
                                f"CIRCUIT BREAKER OPENED: {self.consecutive_global_failures} consecutive "
                                f"{error_type.value} errors detected. Stopping processing to avoid wasting retries."
                            )
                    else:
                        # Local error - reset counter (question-specific issue)
                        if self.consecutive_global_failures > 0:
                            logger.info(
                                f"Local error ({error_type.value}) after {self.consecutive_global_failures} global failures. "
                                f"Resetting circuit breaker counter (question-specific issue)."
                            )
                            self.consecutive_global_failures = 0
                            self.circuit_open = False

                    continue

            # Determine final status based on results
            total_questions = len(questions)
            success_rate = (successful_count / total_questions * 100) if total_questions > 0 else 0
            processed_count = successful_count + failed_count

            # Check if processing was interrupted (paused by user)
            if processed_count < total_questions:
                # Processing was interrupted - don't change status, keep it as is (likely FAILED from pause)
                logger.info(
                    f"Processing interrupted: {processed_count}/{total_questions} questions processed before interruption"
                )
            elif failed_count > 0:
                # Any failures - mark as FAILED
                self.execution.status = ExecutionStatus.FAILED
                logger.error(
                    f"Execution failed: {successful_count}/{total_questions} ({success_rate:.1f}%) questions succeeded, {failed_count} failed"
                )
            else:
                # All questions succeeded
                self.execution.status = ExecutionStatus.GENERATED
                logger.info(
                    f"Full success: All {successful_count} questions processed successfully"
                )

            db.commit()

            logger.info(f"Processing completed for execution {self.execution.id}")
            return True

        except Exception as e:
            logger.error(f"Error in DD processing: {e}")
            if self.execution:
                self.execution.status = ExecutionStatus.NOT_STARTED
                db.commit()
            return False
        finally:
            db.close()

    def resume_processing(self, vector_store_ids: list, company_info: dict) -> bool:
        """Resume processing from where it left off, preserving conversation context"""
        logger.info(
            f"RESUME: Starting resume_processing for session={self.session_id}, dd_type={self.dd_type}"
        )
        db = next(get_db())
        try:
            # Get dd_type_id from code
            from app.models.dd_types import DDType as DDTypeModel

            dd_type_obj = db.query(DDTypeModel).filter(DDTypeModel.code == self.dd_type).first()
            if not dd_type_obj:
                logger.error(f"DD type with code {self.dd_type} not found")
                return False

            # Get existing execution
            self.execution = (
                db.query(DDExecution)
                .filter(
                    DDExecution.session_id == self.session_id,
                    DDExecution.dd_type_id == dd_type_obj.id,
                )
                .first()
            )

            if not self.execution:
                logger.error(
                    f"No execution found for session {self.session_id}, DD type {self.dd_type}"
                )
                return False

            resumable_statuses = [
                ExecutionStatus.NOT_STARTED,
                ExecutionStatus.IN_PROGRESS,
                ExecutionStatus.GENERATED,
                ExecutionStatus.FAILED,
                ExecutionStatus.PAUSED,
            ]
            if self.execution.status not in resumable_statuses:
                logger.warning(
                    f"Execution {self.execution.id} is in status {self.execution.status}, cannot resume"
                )
                return False

            # CRITICAL: Preserve existing conversation_id to maintain context chain
            if self.execution.conversation_id:
                self.conversation_id = self.execution.conversation_id
                logger.info(f"Resuming with existing conversation_id: {self.conversation_id}")
            else:
                # Create new conversation_id if none exists
                self.conversation_id = str(uuid.uuid4())
                self.execution.conversation_id = self.conversation_id
                logger.info(f"No existing conversation_id, created new one: {self.conversation_id}")

            # Update execution status to in_progress
            self.execution.status = ExecutionStatus.IN_PROGRESS
            db.commit()

            # Get all questions for this DD type
            all_questions = self._get_questions_to_process(db)

            # Get successfully answered question IDs (exclude failed answers)
            successfully_answered = set(
                db.query(DDAnswer.question_id)
                .filter(
                    DDAnswer.execution_id == self.execution.id,
                    DDAnswer.status != AnswerStatus.FAILED,  # Exclude failed answers for retry
                )
                .distinct()
                .all()
            )
            successfully_answered = {q_id[0] for q_id in successfully_answered}

            # Get failed answers to retry
            failed_answers = (
                db.query(DDAnswer)
                .filter(
                    DDAnswer.execution_id == self.execution.id,
                    DDAnswer.status == AnswerStatus.FAILED,
                )
                .all()
            )

            # Mark old failed/pending answers as is_current=False to avoid duplicates
            # This ensures only the latest retry attempt is marked as current
            old_answers_to_retry = (
                db.query(DDAnswer)
                .filter(
                    DDAnswer.execution_id == self.execution.id,
                    DDAnswer.question_id.in_([fa.question_id for fa in failed_answers]),
                    DDAnswer.is_current == True,
                )
                .all()
            )

            for old_answer in old_answers_to_retry:
                old_answer.is_current = False
                logger.info(f"Marking old answer {old_answer.id} as is_current=False before retry")

            if old_answers_to_retry:
                db.commit()
                logger.info(f"Marked {len(old_answers_to_retry)} old answers as is_current=False")

            # Filter questions: include unanswered + failed answers
            questions_to_process = [q for q in all_questions if q.id not in successfully_answered]

            if not questions_to_process:
                logger.info(
                    f"All questions successfully answered for execution {self.execution.id}. Marking as GENERATED."
                )
                self.execution.status = ExecutionStatus.GENERATED
                db.commit()
                return True

            failed_count = len(
                [q for q in all_questions if q.id in [fa.question_id for fa in failed_answers]]
            )
            unanswered_count = len(questions_to_process) - failed_count

            logger.info(
                f"Resuming execution {self.execution.id}: {len(questions_to_process)} questions to process ({unanswered_count} unanswered, {failed_count} failed, out of {len(all_questions)} total)"
            )

            # Track success and failure counts
            successful_count = 0
            failed_count = 0

            # Process remaining questions
            for question in questions_to_process:
                # Check if processing should continue (user may have paused)
                if not self._should_continue_processing(db):
                    logger.info(
                        f"Processing paused by user after {successful_count} successful questions"
                    )
                    break

                # Check circuit breaker - stop if too many consecutive global errors
                if self.circuit_open:
                    logger.error(
                        f"Circuit breaker OPEN - stopping processing after {self.consecutive_global_failures} "
                        f"consecutive {self.last_global_error_type.value} errors. "
                        f"Processed {successful_count}/{len(questions_to_process)} questions successfully, "
                        f"{failed_count} failed. Remaining questions skipped to avoid wasting retries."
                    )
                    self.execution.status = ExecutionStatus.FAILED
                    db.commit()
                    break

                try:
                    self._process_single_question(db, question, vector_store_ids, company_info)
                    successful_count += 1
                    logger.info(
                        f"Successfully processed question {question.question_code} ({successful_count}/{len(questions_to_process)})"
                    )
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing question {question.question_code}: {e}")
                    import traceback

                    logger.error(f"Full traceback: {traceback.format_exc()}")

                    # Track consecutive failures for circuit breaker
                    error_type, _ = self._categorize_error(e)
                    if self._is_global_error(error_type):
                        self.consecutive_global_failures += 1
                        self.last_global_error_type = error_type
                        logger.warning(
                            f"Global error detected ({error_type.value}). "
                            f"Consecutive failures: {self.consecutive_global_failures}/{self.CIRCUIT_BREAKER_THRESHOLD}"
                        )

                        # Check if circuit breaker threshold reached
                        if self.consecutive_global_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
                            self.circuit_open = True
                            logger.error(
                                f"CIRCUIT BREAKER OPENED: {self.consecutive_global_failures} consecutive "
                                f"{error_type.value} errors detected. Stopping processing to avoid wasting retries."
                            )
                    else:
                        # Local error - reset counter (question-specific issue)
                        if self.consecutive_global_failures > 0:
                            logger.info(
                                f"Local error ({error_type.value}) after {self.consecutive_global_failures} global failures. "
                                f"Resetting circuit breaker counter (question-specific issue)."
                            )
                            self.consecutive_global_failures = 0
                            self.circuit_open = False

                    continue

            # Determine final status
            total_questions = len(questions_to_process)
            success_rate = (successful_count / total_questions * 100) if total_questions > 0 else 0
            processed_count = successful_count + failed_count

            # Check if processing was interrupted (paused by user)
            if processed_count < total_questions:
                # Processing was interrupted - don't change status, keep it as is (likely FAILED from pause)
                logger.info(
                    f"Processing interrupted: {processed_count}/{total_questions} questions processed before interruption"
                )
            elif failed_count > 0:
                # Any failures - mark as FAILED
                self.execution.status = ExecutionStatus.FAILED
                logger.error(
                    f"Resume execution failed: {successful_count}/{total_questions} ({success_rate:.1f}%) questions succeeded, {failed_count} failed"
                )
            else:
                # All questions succeeded
                self.execution.status = ExecutionStatus.GENERATED
                logger.info(
                    f"Full success: All {successful_count} remaining questions processed successfully"
                )

            db.commit()
            logger.info(f"Resume processing completed for execution {self.execution.id}")
            return True

        except Exception as e:
            logger.error(f"RESUME ERROR: Error resuming processing: {e}")
            import traceback

            logger.error(f"RESUME ERROR: Full traceback: {traceback.format_exc()}")
            if self.execution:
                self.execution.status = ExecutionStatus.FAILED
                db.commit()
            return False
        finally:
            logger.info("RESUME: Completed resume_processing (finally block)")
            db.close()

    def _get_questions_to_process(self, db: Session) -> list:
        """Get all questions for the DD type"""
        # Find DD type by code first, then get its sections directly
        from app.models.dd_types import DDType as DDTypeModel

        dd_type_obj = db.query(DDTypeModel).filter(DDTypeModel.code == self.dd_type).first()
        if not dd_type_obj:
            raise ValueError(f"DD type with code {self.dd_type} not found")

        # Get questions directly from sections that belong to this DD type
        questions = (
            db.query(DDQuestion)
            .join(DDSection)
            .filter(DDSection.dd_type_id == dd_type_obj.id)
            .order_by(DDSection.order_index, DDQuestion.order_index)
            .all()
        )

        if not questions:
            raise ValueError(f"No questions found for DD type {self.dd_type}")

        return questions

    def _get_or_create_execution(self, db: Session) -> DDExecution:
        """Get existing execution or create new one"""
        # Get dd_type_id from code
        from app.models.dd_types import DDType as DDTypeModel

        dd_type_obj = db.query(DDTypeModel).filter(DDTypeModel.code == self.dd_type).first()
        if not dd_type_obj:
            raise ValueError(f"DD type with code {self.dd_type} not found")

        execution = (
            db.query(DDExecution)
            .filter(
                DDExecution.session_id == self.session_id, DDExecution.dd_type_id == dd_type_obj.id
            )
            .first()
        )

        if not execution:
            execution = DDExecution(
                session_id=self.session_id,
                dd_type_id=dd_type_obj.id,
                status=ExecutionStatus.NOT_STARTED,
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            logger.info(
                f"Created new execution {execution.id} for session {self.session_id}, DD type {self.dd_type}"
            )

        return execution

    def _store_openai_response(self, db: Session, result: dict) -> DDResponse:
        """Store the complete OpenAI response"""
        response_record = DDResponse(
            execution_id=self.execution.id,
            response_id=result["response_id"],
            previous_response_id=result.get("previous_response_id"),
            openai_response=result.get("full_response", {}),
        )
        db.add(response_record)
        db.commit()
        db.refresh(response_record)

        logger.debug(f"Stored OpenAI response {response_record.response_id}")
        return response_record

    def _store_response_messages(self, db: Session, response_record: DDResponse, result: dict):
        """Extract and store messages from OpenAI response"""
        messages = result.get("messages", [])

        # Add null check for messages iteration
        if messages and isinstance(messages, list):
            for idx, message in enumerate(messages):
                if message is None:
                    continue
                openai_msg_id = message.get("id")
                message_record = DDMessage(
                    response_id=response_record.response_id,
                    message_index=idx,
                    role=message.get("role", "unknown"),
                    content=message.get("content"),
                    tool_calls=message.get("tool_calls"),
                    openai_message_id=openai_msg_id,
                )
                db.add(message_record)

            if len(messages) > 0:
                db.commit()
                logger.debug(
                    f"Stored {len(messages)} messages for response {response_record.response_id}"
                )

    def _process_single_question(
        self,
        db: Session,
        question: DDQuestion,
        vector_store_ids: list,
        company_info: dict,
    ):
        """Process a single question with full response tracking"""
        try:
            # Validate question data before processing
            if question is None:
                raise ValueError("Question object is None")
            if not question.question_code:
                raise ValueError("Question code is None or empty")
            if question.section is None:
                raise ValueError(f"Question {question.question_code} has no section")
            if not question.section.section_code:
                raise ValueError(f"Question {question.question_code} section has no section_code")
            if not question.question_text:
                raise ValueError(f"Question {question.question_code} has no question_text")

            logger.info(f"Starting to process question {question.question_code}")
            logger.debug(f"Question text: {question.question_text[:100]}...")
            logger.debug(f"Section code: {question.section.section_code}")

            # ISSUE #7 FIX: Get previous response_id using question order, not created_at
            # This ensures correct context chain when retrying failed questions
            previous_response_id = None

            # Find the previous question in the sequence (by order_index)
            previous_answer = (
                db.query(DDAnswer)
                .join(DDQuestion, DDAnswer.question_id == DDQuestion.id)
                .filter(
                    DDAnswer.execution_id == self.execution.id,
                    DDQuestion.order_index < question.order_index,
                    DDAnswer.status == AnswerStatus.COMPLETED,
                    DDAnswer.response_id.isnot(None),  # Only completed answers have response_id
                )
                .order_by(DDQuestion.order_index.desc())
                .first()
            )

            previous_response_id = previous_answer.response_id if previous_answer else None

            if previous_response_id:
                logger.debug(
                    f"Using response chaining with ID: {previous_response_id} from previous question in sequence"
                )
            else:
                logger.debug(
                    "First question or no previous completed answers - starting fresh conversation"
                )

            # Validate parameters for OpenAI call
            if vector_store_ids is None:
                logger.warning("vector_store_ids is None, using empty list")
                vector_store_ids = []

            if company_info is None:
                logger.warning("company_info is None, using empty dict")
                company_info = {}

            # Process with OpenAI with retry logic
            logger.debug("Calling OpenAI processor")
            logger.debug(f"Vector store IDs: {vector_store_ids}")
            logger.debug(f"Company info keys: {list(company_info.keys()) if company_info else []}")

            result = None
            last_error = None
            retry_count = 0

            for attempt in range(self.MAX_RETRIES):
                try:
                    result = self.openai_processor.process_question(
                        question_text=self.compose_question_text(question),
                        vector_store_ids=vector_store_ids,
                        previous_response_id=previous_response_id,
                        company_info=company_info,
                    )
                    logger.info("OpenAI processing completed successfully")
                    break  # Success, exit retry loop

                except Exception as e:
                    last_error = e
                    retry_count = attempt + 1

                    # Categorize error
                    error_type, is_retryable = self._categorize_error(e)

                    logger.error(
                        f"Error in OpenAI call (attempt {retry_count}/{self.MAX_RETRIES}): {str(e)}"
                    )
                    logger.error(
                        f"Error categorized as: {error_type.value}, Retryable: {is_retryable}"
                    )

                    # If not retryable or last attempt, don't retry
                    if not is_retryable or attempt == self.MAX_RETRIES - 1:
                        logger.error(
                            f"Not retrying - Retryable: {is_retryable}, Attempt: {retry_count}/{self.MAX_RETRIES}"
                        )
                        raise

                    # Calculate backoff delay
                    delay = self._calculate_backoff_delay(attempt, error_type)
                    logger.warning(f"Retrying after {delay:.1f}s backoff...")
                    time.sleep(delay)

            if result is None:
                # All retries exhausted
                raise last_error

        except Exception as e:
            # Save error information to answer record for debugging
            error_type, _ = self._categorize_error(e)

            # ISSUE #9 FIX: Mark old answers as is_current=False before creating new failed answer
            old_answers = (
                db.query(DDAnswer)
                .filter(
                    DDAnswer.execution_id == self.execution.id,
                    DDAnswer.question_id == question.id,
                    DDAnswer.is_current == True,
                )
                .all()
            )

            for old_answer in old_answers:
                old_answer.is_current = False
                logger.info(
                    f"Marking old answer {old_answer.id} as is_current=False before creating new failed answer"
                )

            if old_answers:
                db.commit()
                logger.info(f"Marked {len(old_answers)} old answers as is_current=False")

            # Create failed answer record with error information
            failed_answer = DDAnswer(
                session_id=self.session_id,
                execution_id=self.execution.id,
                dd_type_id=self.execution.dd_type_id,
                section_code=question.section.section_code,
                question_code=question.question_code,
                section_id=question.section.id,
                question_id=question.id,
                status=AnswerStatus.FAILED,
                retry_count=retry_count,
                error_type=error_type,
                error_message=str(e)[:1000],  # Limit to 1000 chars
                last_error_at=datetime.now(),
            )
            db.add(failed_answer)
            db.commit()

            logger.error(f"Error in _process_single_question: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

        # Store OpenAI response
        response_record = self._store_openai_response(db, result)

        # Extract and store messages
        self._store_response_messages(db, response_record, result)

        # CRITICAL FIX: Ensure sources are properly formatted for JSONB storage
        sources_data = result.get("sources", {})

        # Ensure sources is always a dict, never a string or list
        if sources_data is None:
            sources_data = {}
        elif isinstance(sources_data, str):
            logger.warning(
                f"Sources is a string! Converting to empty dict. Original: {sources_data}"
            )
            sources_data = {}
        elif isinstance(sources_data, list):
            logger.warning(
                f"Sources is a list! Converting to structured dict. Original: {sources_data}"
            )
            # If it's a list, structure it properly
            sources_data = {
                "files": [
                    s
                    for s in sources_data
                    if isinstance(s, dict) and s.get("type") == "file_search"
                ],
                "web": [
                    s for s in sources_data if isinstance(s, dict) and s.get("type") == "web_search"
                ],
                "total_count": len(sources_data),
            }

        # Final validation - ensure it's a dict
        if not isinstance(sources_data, dict):
            logger.error(
                f"Sources is not a dict after processing! Type: {type(sources_data)}, Value: {sources_data}"
            )
            sources_data = {}

        # ISSUE #9 FIX: Mark old answers as is_current=False before creating new completed answer
        old_answers = (
            db.query(DDAnswer)
            .filter(
                DDAnswer.execution_id == self.execution.id,
                DDAnswer.question_id == question.id,
                DDAnswer.is_current == True,
            )
            .all()
        )

        for old_answer in old_answers:
            old_answer.is_current = False
            logger.info(
                f"Marking old answer {old_answer.id} as is_current=False before creating new completed answer"
            )

        if old_answers:
            db.commit()
            logger.info(f"Marked {len(old_answers)} old answers as is_current=False")

        # Create answer record (metadata only, content will be in history)
        answer = DDAnswer(
            session_id=self.session_id,
            execution_id=self.execution.id,  # Link to execution
            dd_type_id=self.execution.dd_type_id,  # DD type ID
            section_code=question.section.section_code,  # Required legacy field
            question_code=question.question_code,  # Required legacy field
            section_id=question.section.id,
            question_id=question.id,
            answer_text=result["answer"],
            sources=sources_data,
            tokens_used=result["tokens_used"],
            confidence_score=result.get("confidence_score"),
            response_id=response_record.response_id,  # ISSUE #7 FIX: Store response_id for context chain tracking
            status=AnswerStatus.COMPLETED,  # Mark as completed since AI successfully generated answer
            version=1,
            is_current=True,
        )

        db.add(answer)
        db.flush()  # Get ID without committing transaction

        # Create history entry for version 1 (original AI-generated answer)
        history_entry = DDAnswerHistory(
            answer_id=answer.id,
            version=1,
            content=result["answer"],
            sources=sources_data,
            edited_by=None,  # NULL indicates AI-generated
            edit_reason="Initial AI-generated answer",
        )

        db.add(history_entry)
        db.flush()  # Get history ID

        db.commit()
        db.refresh(answer)

        logger.debug(f"Processed question {question.question_code} - Answer ID: {answer.id}")

        # Reset circuit breaker on success
        if self.consecutive_global_failures > 0:
            logger.info(
                f"Question processed successfully. Resetting circuit breaker "
                f"(was at {self.consecutive_global_failures} consecutive failures)."
            )
        self.consecutive_global_failures = 0
        self.circuit_open = False
        self.last_global_error_type = None

        # Apply rate limiting with proper rate limiter
        self.rate_limiter.check_and_sleep_sync(tokens_used=result["tokens_used"])

    def regenerate_single_answer(
        self,
        db: Session,
        answer: DDAnswer,
        vector_store_ids: list,
        company_info: dict,
        instruction: str | None = None,
        reference_url: str | None = None,
        extra_file_source: dict | None = None,
    ) -> DDAnswer:
        """Regenerate ONE existing answer on demand (interactive).

        Reuses the conversation chain (previous answers) for context, but skips
        the batch rate-limiter and circuit breaker since this is a single,
        user-triggered call. Updates the answer in place as a new version
        (mirrors the manual-edit pattern), so the version history and the
        'revert to version' feature keep working. Status -> NEEDS_REVIEW.

        Optional guidance: ``instruction`` (analyst re-prompt) and
        ``reference_url`` are appended to the question; ``extra_file_source``
        (a file uploaded by the caller to a session vector store) is merged into
        the answer's sources. When any guidance is present, the call uses
        ``tool_choice="auto"`` so file_search (attached doc) and web_search
        (reference URL) are both usable instead of the default forced web search.
        """
        question = answer.question
        if question is None or question.section is None:
            raise ValueError("Answer has no associated question/section")
        self.execution = answer.execution
        if self.execution is None:
            raise ValueError("Answer has no associated execution")

        # Context = previous completed answer in the question order (same chain
        # the engine uses). Later answers are intentionally not included.
        previous_answer = (
            db.query(DDAnswer)
            .join(DDQuestion, DDAnswer.question_id == DDQuestion.id)
            .filter(
                DDAnswer.execution_id == self.execution.id,
                DDQuestion.order_index < question.order_index,
                DDAnswer.status == AnswerStatus.COMPLETED,
                DDAnswer.response_id.isnot(None),
            )
            .order_by(DDQuestion.order_index.desc())
            .first()
        )
        previous_response_id = previous_answer.response_id if previous_answer else None

        vector_store_ids = vector_store_ids or []
        company_info = company_info or {}

        # Build the (optionally guided) question text without touching the
        # previous_response_id conversation chain.
        guided = bool(instruction or reference_url or extra_file_source)
        extras = []
        if instruction:
            extras.append("Consigne supplémentaire de l'analyste : " + instruction)
        if reference_url:
            extras.append("Source web à consulter en priorité : " + reference_url)
        question_text = self.compose_question_text(question) + (
            ("\n\n" + "\n".join(extras)) if extras else ""
        )

        # Use 'auto' whenever there are documents to reuse (the session vector
        # store(s) that served this answer) or explicit guidance, so file_search
        # actually queries them instead of being shadowed by the forced web
        # search. Only fall back to the default (forced web) when there is
        # nothing to reuse and no guidance.
        tool_choice = "auto" if (guided or vector_store_ids) else None

        # Call OpenAI with the same retry/backoff policy as the main engine
        result = None
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                result = self.openai_processor.process_question(
                    question_text=question_text,
                    vector_store_ids=vector_store_ids,
                    previous_response_id=previous_response_id,
                    company_info=company_info,
                    tool_choice=tool_choice,
                )
                break
            except Exception as e:
                last_error = e
                error_type, is_retryable = self._categorize_error(e)
                if not is_retryable or attempt == self.MAX_RETRIES - 1:
                    raise
                time.sleep(self._calculate_backoff_delay(attempt, error_type))
        if result is None:
            raise last_error

        # Persist the OpenAI response + messages (keeps the chain consistent)
        response_record = self._store_openai_response(db, result)
        self._store_response_messages(db, response_record, result)

        sources_data = result.get("sources", {})
        if not isinstance(sources_data, dict):
            sources_data = {}

        # Inject the analyst-attached file into the sources (so it shows up in
        # the UI and the PDF), unless the model already cited it via file_search.
        if extra_file_source and extra_file_source.get("file_id"):
            files_list = sources_data.get("files")
            if not isinstance(files_list, list):
                files_list = []
            already = any(
                isinstance(s, dict) and s.get("file_id") == extra_file_source["file_id"]
                for s in files_list
            )
            if not already:
                files_list.append(extra_file_source)
                sources_data["files"] = files_list
                sources_data["total_count"] = sources_data.get("total_count", 0) + 1

        # Traceability: keep the analyst instruction when provided.
        if instruction:
            edit_reason = "Régénéré par l'IA — consigne : " + instruction[:200]
        elif reference_url or extra_file_source:
            edit_reason = "Régénéré par l'IA (guidé)"
        else:
            edit_reason = "Régénéré par l'IA"

        # New version on the same answer row + history entry
        new_version = (answer.version or 1) + 1
        history_entry = DDAnswerHistory(
            answer_id=answer.id,
            version=new_version,
            content=result["answer"],
            sources=sources_data,
            edited_by=None,  # NULL = AI-generated
            edit_reason=edit_reason,
        )
        db.add(history_entry)
        db.flush()

        answer.version = new_version
        answer.answer_text = result["answer"]
        answer.sources = sources_data
        answer.tokens_used = result.get("tokens_used")
        answer.confidence_score = result.get("confidence_score")
        answer.response_id = response_record.response_id
        answer.status = AnswerStatus.NEEDS_REVIEW
        answer.edited_by = None
        answer.edited_at = func.now()
        answer.is_current = True

        db.commit()
        db.refresh(answer)
        logger.info(f"Regenerated answer {answer.id} (new version {new_version})")
        return answer
