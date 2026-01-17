from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SessionCleanupMiddleware:
    """
    Middleware to clean up expired session data.
    Runs on each request and checks for expired batches.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Clean up expired session data before processing the request
        self._cleanup_expired_sessions(request)

        response = self.get_response(request)

        return response

    def _cleanup_expired_sessions(self, request):
        """
        Clean up expired batches and related data from the session.
        """
        if not hasattr(request, 'session') or not request.session:
            return

        try:
            session_data = request.session

            # Get recruiter data from session
            recruiter_data = session_data.get('recruiter_data', {})
            batches = recruiter_data.get('batches', {})

            # Track which batches to remove
            expired_batches = []

            # Check each batch for expiration
            for batch_id, batch_data in batches.items():
                expires_at = batch_data.get('expires_at')
                if expires_at:
                    try:
                        # Parse the expiration time
                        if isinstance(expires_at, str):
                            from datetime import datetime
                            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

                        # Check if batch is expired
                        if expires_at <= timezone.now():
                            expired_batches.append(batch_id)
                            logger.info(f"Batch {batch_id} expired and will be removed from session")
                    except Exception as e:
                        logger.error(f"Error parsing expiration time for batch {batch_id}: {e}")

            # Remove expired batches
            for batch_id in expired_batches:
                del batches[batch_id]

            # Update session with cleaned batches
            recruiter_data['batches'] = batches
            session_data['recruiter_data'] = recruiter_data

            # Also clean up any orphaned analysis results
            self._cleanup_orphaned_results(session_data)

            # Mark session as modified
            request.session.modified = True

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")

    def _cleanup_orphaned_results(self, session_data):
        """
        Clean up analysis results that don't have corresponding batches.
        """
        try:
            recruiter_data = session_data.get('recruiter_data', {})
            analysis_results = recruiter_data.get('analysis_results', {})
            batches = recruiter_data.get('batches', {})

            # Find orphaned results
            orphaned_results = []
            for result_id, result_data in analysis_results.items():
                batch_id = result_data.get('batch_id')
                if batch_id and batch_id not in batches:
                    orphaned_results.append(result_id)

            # Remove orphaned results
            for result_id in orphaned_results:
                del analysis_results[result_id]
                logger.info(f"Removed orphaned analysis result {result_id}")

            # Update session
            recruiter_data['analysis_results'] = analysis_results
            session_data['recruiter_data'] = recruiter_data

        except Exception as e:
            logger.error(f"Error cleaning up orphaned results: {e}")


class SessionDataMiddleware:
    """
    Middleware to ensure session data is properly initialized.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize session data structure if needed
        self._initialize_session_data(request)

        response = self.get_response(request)

        return response

    def _initialize_session_data(self, request):
        """
        Initialize the session data structure for recruiter functionality.
        """
        if not hasattr(request, 'session') or not request.session:
            return

        try:
            session_data = request.session

            # Initialize recruiter data structure
            if 'recruiter_data' not in session_data:
                session_data['recruiter_data'] = {
                    'batches': {},
                    'analysis_results': {},
                    'uploads': {},
                    'last_cleanup': timezone.now().isoformat()
                }
            else:
                recruiter_data = session_data['recruiter_data']

                # Ensure required sub-structures exist
                if 'batches' not in recruiter_data:
                    recruiter_data['batches'] = {}
                if 'analysis_results' not in recruiter_data:
                    recruiter_data['analysis_results'] = {}
                if 'uploads' not in recruiter_data:
                    recruiter_data['uploads'] = {}

                # Update last cleanup time
                recruiter_data['last_cleanup'] = timezone.now().isoformat()

                session_data['recruiter_data'] = recruiter_data

            # Mark session as modified if we made changes
            request.session.modified = True

        except Exception as e:
            logger.error(f"Error initializing session data: {e}")