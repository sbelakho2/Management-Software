"""
OpenTelemetry Distributed Tracing Setup

Provides comprehensive distributed tracing for observability:
- Automatic instrumentation for FastAPI, SQLAlchemy, httpx, Redis
- Custom span creation for business logic
- Trace context propagation across services
- Export to OTLP-compatible backends (Jaeger, Tempo, etc.)

Usage:
    from sensei.core.telemetry import setup_telemetry, get_tracer
    
    # In main.py, before creating the app:
    setup_telemetry()
    
    # In your code:
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("my-operation") as span:
        span.set_attribute("key", "value")
        # do work
"""

import logging
from functools import lru_cache
from typing import Optional, Dict, Any

from sensei.core.config import settings

logger = logging.getLogger(__name__)

# Lazy imports for OpenTelemetry (optional dependency)
_tracer = None
_meter = None
_initialized = False


def setup_telemetry(
    service_name: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
) -> bool:
    """
    Initialize OpenTelemetry tracing and metrics.
    
    This should be called once at application startup, before
    any traces are created.
    
    Args:
        service_name: Service name for traces (defaults to settings)
        otlp_endpoint: OTLP exporter endpoint (defaults to settings)
        enable_console_export: Also export to console (for debugging)
        
    Returns:
        True if telemetry was successfully initialized
    """
    global _initialized
    
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry is disabled via settings")
        return False
    
    if _initialized:
        logger.warning("OpenTelemetry already initialized")
        return True
    
    try:
        # Import OpenTelemetry components
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            PeriodicExportingMetricReader,
            ConsoleMetricExporter,
        )
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        
        # Create resource with service info
        resource = Resource(attributes={
            SERVICE_NAME: service_name or settings.OTEL_SERVICE_NAME,
            SERVICE_VERSION: settings.VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        })
        
        # Set up trace provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Add OTLP exporter
        endpoint = otlp_endpoint or settings.OTEL_EXPORTER_OTLP_ENDPOINT
        if endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                insecure=not endpoint.startswith("https"),
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(f"OTLP trace exporter configured: {endpoint}")
        
        # Add console exporter for debugging
        if enable_console_export:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )
        
        # Register tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Set up metrics provider
        metric_readers = []
        
        if endpoint:
            otlp_metric_exporter = OTLPMetricExporter(
                endpoint=endpoint,
                insecure=not endpoint.startswith("https"),
            )
            metric_readers.append(
                PeriodicExportingMetricReader(
                    otlp_metric_exporter,
                    export_interval_millis=settings.OTEL_METRIC_EXPORT_INTERVAL_MS,
                )
            )
        
        if enable_console_export:
            metric_readers.append(
                PeriodicExportingMetricReader(
                    ConsoleMetricExporter(),
                    export_interval_millis=60000,
                )
            )
        
        if metric_readers:
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=metric_readers,
            )
            metrics.set_meter_provider(meter_provider)
        
        # Auto-instrumentation
        _setup_auto_instrumentation()
        
        _initialized = True
        logger.info(
            "OpenTelemetry initialized",
            extra={
                "service_name": service_name or settings.OTEL_SERVICE_NAME,
                "endpoint": endpoint,
            }
        )
        return True
        
    except ImportError as e:
        logger.warning(
            f"OpenTelemetry packages not installed: {e}. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-otlp opentelemetry-instrumentation-fastapi"
        )
        return False
    except Exception as e:
        logger.exception(f"Failed to initialize OpenTelemetry: {e}")
        return False


def _setup_auto_instrumentation():
    """Set up automatic instrumentation for common libraries."""
    
    # FastAPI instrumentation
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor().instrument()
        logger.debug("FastAPI instrumentation enabled")
    except ImportError:
        logger.debug("FastAPI instrumentation not available")
    except Exception as e:
        logger.warning(f"FastAPI instrumentation failed: {e}")
    
    # SQLAlchemy instrumentation
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
        logger.debug("SQLAlchemy instrumentation enabled")
    except ImportError:
        logger.debug("SQLAlchemy instrumentation not available")
    except Exception as e:
        logger.warning(f"SQLAlchemy instrumentation failed: {e}")
    
    # httpx instrumentation (for outgoing HTTP calls)
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
        logger.debug("httpx instrumentation enabled")
    except ImportError:
        logger.debug("httpx instrumentation not available")
    except Exception as e:
        logger.warning(f"httpx instrumentation failed: {e}")
    
    # Redis instrumentation
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.debug("Redis instrumentation enabled")
    except ImportError:
        logger.debug("Redis instrumentation not available")
    except Exception as e:
        logger.warning(f"Redis instrumentation failed: {e}")
    
    # Celery instrumentation
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.debug("Celery instrumentation enabled")
    except ImportError:
        logger.debug("Celery instrumentation not available")
    except Exception as e:
        logger.warning(f"Celery instrumentation failed: {e}")


@lru_cache(maxsize=32)
def get_tracer(name: str = __name__):
    """
    Get a tracer instance for creating spans.
    
    Args:
        name: Tracer name (typically __name__)
        
    Returns:
        Tracer instance (NoOpTracer if telemetry disabled)
    """
    if not settings.OTEL_ENABLED:
        # Return a no-op tracer
        from opentelemetry.trace import NoOpTracer
        return NoOpTracer()
    
    try:
        from opentelemetry import trace
        return trace.get_tracer(name, settings.VERSION)
    except ImportError:
        from opentelemetry.trace import NoOpTracer
        return NoOpTracer()


@lru_cache(maxsize=32)
def get_meter(name: str = __name__):
    """
    Get a meter instance for creating metrics.
    
    Args:
        name: Meter name (typically __name__)
        
    Returns:
        Meter instance (NoOpMeter if telemetry disabled)
    """
    if not settings.OTEL_ENABLED:
        from opentelemetry.metrics import NoOpMeter
        return NoOpMeter(name)
    
    try:
        from opentelemetry import metrics
        return metrics.get_meter(name, settings.VERSION)
    except ImportError:
        from opentelemetry.metrics import NoOpMeter
        return NoOpMeter(name)


def trace_function(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to trace a function execution.
    
    Usage:
        @trace_function("my-operation")
        async def my_function():
            pass
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = name or func.__name__
            tracer = get_tracer(func.__module__)
            
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(
                        trace.Status(trace.StatusCode.ERROR, str(e))
                    )
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = name or func.__name__
            tracer = get_tracer(func.__module__)
            
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Import trace module at module level for decorator use
try:
    from opentelemetry import trace
except ImportError:
    trace = None
