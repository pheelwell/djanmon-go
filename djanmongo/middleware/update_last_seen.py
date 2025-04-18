from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class UpdateLastSeenMiddleware(MiddlewareMixin):
    """Updates the last_seen timestamp for authenticated users on each request."""
    
    def process_request(self, request):
        # Check if user is authenticated and not anonymous
        if request.user.is_authenticated:
            # Update last_seen timestamp using update to avoid signals and save overhead
            # Use timezone.now() to ensure timezone-aware datetime
            request.user.__class__.objects.filter(pk=request.user.pk).update(last_seen=timezone.now()) 