"""
Argos Control monitoring endpoints for health, metrics, and test tracking.
"""
import os
import time
import subprocess
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import User, UserSession, PassageAttempt, LessonAttempt, WritingSectionAttempt, MathSectionAttempt


# Store test run state (in-memory, or use database/cache in production)
_current_test_run = None


def validate_argos_token(request):
    """Validate Argos token from Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.replace('Bearer ', '')
    expected_token = os.environ.get('ARGOS_TOKEN', '')
    
    if not expected_token:
        return None  # Token not configured
    
    if token != expected_token:
        return None  # Invalid token
    
    return token


def require_argos_token(view_func):
    """Decorator to require valid Argos token"""
    def wrapped_view(request, *args, **kwargs):
        token = validate_argos_token(request)
        if not token:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(request, *args, **kwargs)
    return wrapped_view


@api_view(['GET'])
@permission_classes([AllowAny])
def argos_health(request):
    """
    Health check endpoint - checks database connectivity and overall service status.
    
    GET /api/v1/argos/health
    Authorization: Bearer <ARGOS_TOKEN>
    
    Returns:
    {
        "status": "ok" | "degraded" | "down",
        "service": "satlingo-backend",
        "version": "1.0.0",
        "uptime_seconds": 123456,
        "dependencies": {
            "db": "ok" | "down"
        },
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    # Check authentication
    token = validate_argos_token(request)
    if not token:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Check database connectivity
    db_status = 'ok'
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        db_status = 'down'
    
    # Determine overall status
    overall_status = 'ok'
    if db_status == 'down':
        overall_status = 'down'
    
    # Calculate uptime (approximate - time since Django started)
    # In production, you might want to track actual start time
    uptime_seconds = int(time.time() - (getattr(settings, '_START_TIME', time.time())))
    
    return Response({
        'status': overall_status,
        'service': os.environ.get('SERVICE_NAME', 'satlingo-backend'),
        'version': os.environ.get('VERSION', '1.0.0'),
        'uptime_seconds': uptime_seconds,
        'dependencies': {
            'db': db_status,
        },
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def argos_metrics(request):
    """
    Metrics endpoint - aggregates user counts, errors, and performance metrics.
    
    GET /api/v1/argos/metrics
    Authorization: Bearer <ARGOS_TOKEN>
    
    Returns:
    {
        "users_today": 1234,
        "users_total": 567890,
        "errors_24h": 5,
        "avg_latency_ms": 125,
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    # Check authentication
    token = validate_argos_token(request)
    if not token:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Calculate time thresholds
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = now - timedelta(hours=24)
        
        # Users active today (users with sessions or attempts in last 24h)
        users_today = User.objects.filter(
            Q(sessions__created_at__gte=yesterday) |
            Q(passageattempt__completed_at__gte=yesterday) |
            Q(lessonattempt__completed_at__gte=yesterday) |
            Q(writingsectionattempt__completed_at__gte=yesterday) |
            Q(mathsectionattempt__completed_at__gte=yesterday)
        ).distinct().count()
        
        # Total users
        users_total = User.objects.count()
        
        # Errors in last 24h (from Sentry if available, otherwise 0)
        # Note: This is a placeholder - you'd need to query Sentry API or your error logs
        errors_24h = 0
        if hasattr(settings, 'SENTRY_DSN') and settings.SENTRY_DSN:
            # In a real implementation, you'd query Sentry API here
            # For now, we'll return 0 and note that this requires Sentry API integration
            pass
        
        # Average latency (placeholder - would need request logging)
        # In production, you might track this in middleware or use APM
        avg_latency_ms = 0
        
        return Response({
            'users_today': users_today,
            'users_total': users_total,
            'errors_24h': errors_24h,
            'avg_latency_ms': avg_latency_ms,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        })
    
    except Exception as e:
        return Response(
            {'error': 'Failed to collect metrics', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def argos_tests_run(request):
    """
    Trigger E2E test run.
    
    POST /api/v1/argos/tests/run
    Authorization: Bearer <ARGOS_TOKEN>
    
    Returns:
    {
        "run_id": "test-run-1234567890",
        "status": "running",
        "duration_ms": 0,
        "results": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        },
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    # Check authentication
    token = validate_argos_token(request)
    if not token:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    global _current_test_run
    
    # Prevent concurrent runs
    if _current_test_run and _current_test_run.get('status') == 'running':
        return Response(
            {'error': 'Test run already in progress'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Create new test run
    run_id = f"test-run-{int(time.time() * 1000)}"
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    _current_test_run = {
        'run_id': run_id,
        'status': 'running',
        'start_time': time.time(),
        'timestamp': timestamp,
    }
    
    # Run tests in background (using Django test runner)
    def run_tests_async():
        global _current_test_run
        try:
            # Run Django tests
            # Note: This runs all tests - you might want to specify a test suite
            result = subprocess.run(
                ['python', 'manage.py', 'test', '--verbosity=0', '--no-input'],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            duration = int((time.time() - _current_test_run['start_time']) * 1000)
            
            # Parse test results (Django test output)
            # This is simplified - you might want to use JSON output or parse more carefully
            passed = 0
            failed = 0
            if result.returncode == 0:
                # Try to parse output for test counts
                # Django doesn't output JSON by default, so we'll use return code
                passed = 1  # Placeholder - would need proper parsing
                failed = 0
            else:
                passed = 0
                failed = 1
            
            _current_test_run = {
                **_current_test_run,
                'status': 'passed' if result.returncode == 0 else 'failed',
                'duration_ms': duration,
                'results': {
                    'total': passed + failed,
                    'passed': passed,
                    'failed': failed,
                    'skipped': 0,
                },
            }
        except subprocess.TimeoutExpired:
            _current_test_run = {
                **_current_test_run,
                'status': 'failed',
                'duration_ms': int((time.time() - _current_test_run['start_time']) * 1000),
                'results': {
                    'total': 0,
                    'passed': 0,
                    'failed': 1,
                    'skipped': 0,
                },
            }
        except Exception as e:
            _current_test_run = {
                **_current_test_run,
                'status': 'failed',
                'duration_ms': int((time.time() - _current_test_run.get('start_time', time.time())) * 1000),
                'results': {
                    'total': 0,
                    'passed': 0,
                    'failed': 1,
                    'skipped': 0,
                },
                'error': str(e),
            }
    
    # Start test run in background thread
    import threading
    thread = threading.Thread(target=run_tests_async)
    thread.daemon = True
    thread.start()
    
    # Return immediately
    return Response({
        'run_id': run_id,
        'status': 'running',
        'duration_ms': 0,
        'results': {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
        },
        'timestamp': timestamp,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def argos_tests_latest(request):
    """
    Get latest completed test run results.
    
    GET /api/v1/argos/tests/latest
    Authorization: Bearer <ARGOS_TOKEN>
    
    Returns:
    {
        "run_id": "test-run-1234567890",
        "status": "passed" | "failed",
        "duration_ms": 12345,
        "results": {
            "total": 10,
            "passed": 9,
            "failed": 1,
            "skipped": 0
        },
        "timestamp": "2024-01-15T10:30:00Z"
    }
    """
    # Check authentication
    token = validate_argos_token(request)
    if not token:
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    global _current_test_run
    
    if not _current_test_run:
        return Response(
            {'error': 'No test runs found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if _current_test_run.get('status') == 'running':
        return Response(
            {'error': 'Test run still in progress'},
            status=status.HTTP_202_ACCEPTED
        )
    
    # Return completed test run
    response_data = {
        'run_id': _current_test_run['run_id'],
        'status': _current_test_run['status'],
        'duration_ms': _current_test_run.get('duration_ms', 0),
        'results': _current_test_run.get('results', {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
        }),
        'timestamp': _current_test_run['timestamp'],
    }
    
    if 'error' in _current_test_run:
        response_data['error'] = _current_test_run['error']
    
    return Response(response_data)
