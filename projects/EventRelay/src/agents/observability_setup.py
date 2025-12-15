#!/usr/bin/env python3
"""
UVAI Observability Setup
Implements OpenTelemetry tracing for video processing pipeline
Based on IBM Instana vLLM observability patterns
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    # Security: Check if we're in production mode - observability should not fail silently
    is_production = os.getenv("REAL_MODE_ONLY", "false").lower() in ("1", "true", "yes")
    if is_production:
        logging.error(
            "CRITICAL: OpenTelemetry not available in production mode. "
            "Install with: pip install opentelemetry-distro opentelemetry-exporter-otlp"
        )
    else:
        logging.warning(
            "OpenTelemetry not available. Install with: pip install opentelemetry-distro opentelemetry-exporter-otlp"
        )

class UVAIObservability:
    """Observability system for UVAI video processing pipeline"""
    
    def __init__(self, service_name: str = "uvai-video-processor"):
        self.service_name = service_name
        self.tracer = None
        self.meter = None
        self.setup_complete = False
        self.observability_status = "disabled"
        
        self._otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        self._is_production = os.getenv("REAL_MODE_ONLY", "false").lower() in ("1", "true", "yes")

        if TELEMETRY_AVAILABLE and self._otlp_endpoint:
            self._setup_tracing()
            self._setup_metrics()
            self.setup_complete = True
            self.observability_status = "enabled"
        else:
            # Security: In production, log at ERROR level when telemetry is unavailable
            log_level = logging.ERROR if self._is_production else logging.DEBUG
            logging.getLogger(__name__).log(
                log_level,
                "OpenTelemetry %s (available=%s, endpoint=%s, production=%s)",
                "UNAVAILABLE IN PRODUCTION" if self._is_production else "disabled",
                TELEMETRY_AVAILABLE,
                self._otlp_endpoint or "<unset>",
                self._is_production,
            )
            self.observability_status = "unavailable" if not TELEMETRY_AVAILABLE else "not_configured"
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Health check endpoint for observability status.
        
        Security: Operations teams need visibility into observability health,
        especially in production environments where silent failures are unacceptable.
        
        Returns:
            Dict with observability health status
        """
        return {
            "service": self.service_name,
            "observability_enabled": self.setup_complete,
            "status": self.observability_status,
            "telemetry_available": TELEMETRY_AVAILABLE,
            "otlp_endpoint": self._otlp_endpoint or None,
            "is_production": self._is_production,
            "tracer_configured": self.tracer is not None,
            "meter_configured": self.meter is not None,
        }
        
    def _setup_tracing(self):
        """Configure OpenTelemetry tracing"""
        # Set up trace provider
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()
        
        # Configure OTLP exporter (can be configured for different backends)
        otlp_exporter = OTLPSpanExporter(endpoint=self._otlp_endpoint)
        
        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Get tracer
        self.tracer = trace.get_tracer(self.service_name)
        
    def _setup_metrics(self):
        """Configure OpenTelemetry metrics"""
        # Set up metrics provider
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=self._otlp_endpoint),
            export_interval_millis=5000,
        )
        
        metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
        self.meter = metrics.get_meter(self.service_name)
        
    def trace_video_processing(self, video_url: str, operation: str):
        """Context manager for tracing video processing operations"""
        if not self.setup_complete:
            return DummyTracer()
            
        return self.tracer.start_as_current_span(
            f"video_processing.{operation}",
            attributes={
                "video.url": video_url,
                "operation": operation,
                "service": self.service_name,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def record_processing_metrics(self, 
                                video_id: str,
                                processing_time: float,
                                transcript_segments: int,
                                success: bool):
        """Record video processing metrics"""
        if not self.setup_complete:
            return
            
        # Create counters and histograms
        processing_counter = self.meter.create_counter(
            "video_processing_total",
            description="Total number of videos processed"
        )
        
        processing_duration = self.meter.create_histogram(
            "video_processing_duration_seconds",
            description="Time taken to process videos"
        )
        
        transcript_size = self.meter.create_histogram(
            "video_transcript_segments",
            description="Number of transcript segments per video"
        )
        
        # Record metrics
        processing_counter.add(1, {
            "video_id": video_id,
            "success": str(success)
        })
        
        processing_duration.record(processing_time, {
            "video_id": video_id,
            "operation": "full_processing"
        })
        
        transcript_size.record(transcript_segments, {
            "video_id": video_id
        })

class DummyTracer:
    """Fallback tracer when OpenTelemetry is not available"""
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key, value):
        pass

# Usage example and testing
if __name__ == "__main__":
    import time
    
    print("=== UVAI Observability Setup ===")
    
    # Initialize observability
    obs = UVAIObservability()
    
    if obs.setup_complete:
        print("✅ OpenTelemetry configured successfully")
        
        # Test tracing
        with obs.trace_video_processing("https://www.youtube.com/watch?v=2bGh_DlkubM", "transcript_extraction"):
            # Simulate video processing
            time.sleep(0.1)
            print("📊 Tracing video processing operation")
        
        # Test metrics
        obs.record_processing_metrics(
            video_id="2bGh_DlkubM",
            processing_time=1.5,
            transcript_segments=355,
            success=True
        )
        
        print("📈 Metrics recorded successfully")
        
    else:
        print("⚠️ OpenTelemetry not available - using fallback mode")
        
        # Test fallback
        with obs.trace_video_processing("test_url", "test_operation"):
            print("📊 Fallback tracing (no-op)")
    
    print("✅ Observability setup complete")
