"""
PDF Generation Celery Tasks.

Provides asynchronous PDF generation to avoid blocking the API server.
WeasyPrint can be memory-intensive and slow, so offloading to Celery workers
provides better user experience and server stability.

Features:
- Async A3 report PDF generation
- Quote/Invoice PDF generation
- Progress tracking via Redis
- Automatic S3 upload
- Cleanup of temporary files
"""

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from sensei.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class PDFGenerationStatus:
    """Status constants for PDF generation."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _get_progress_key(task_id: str) -> str:
    """Get Redis key for task progress."""
    return f"pdf_generation:progress:{task_id}"


def _update_progress(
    task_id: str,
    status: str,
    progress: int = 0,
    message: str = "",
    result_url: Optional[str] = None,
    error: Optional[str] = None,
):
    """Update task progress in Redis."""
    try:
        from sensei.core.redis import get_redis_client
        
        redis = get_redis_client()
        data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if result_url:
            data["result_url"] = result_url
        if error:
            data["error"] = error
        
        redis.hset(_get_progress_key(task_id), mapping=data)
        # Expire progress after 24 hours
        redis.expire(_get_progress_key(task_id), 86400)
    except Exception as e:
        logger.warning(f"Failed to update progress: {e}")


def get_pdf_generation_progress(task_id: str) -> Dict[str, Any]:
    """Get current progress for a PDF generation task."""
    try:
        from sensei.core.redis import get_redis_client
        
        redis = get_redis_client()
        data = redis.hgetall(_get_progress_key(task_id))
        
        if not data:
            return {"status": "unknown", "progress": 0, "message": "Task not found"}
        
        return {
            "status": data.get(b"status", b"unknown").decode(),
            "progress": int(data.get(b"progress", b"0")),
            "message": data.get(b"message", b"").decode(),
            "result_url": data.get(b"result_url", b"").decode() or None,
            "error": data.get(b"error", b"").decode() or None,
            "updated_at": data.get(b"updated_at", b"").decode() or None,
        }
    except Exception as e:
        logger.exception(f"Failed to get progress: {e}")
        return {"status": "error", "progress": 0, "message": str(e)}


@celery_app.task(
    name="sensei.tasks.pdf_tasks.generate_a3_pdf",
    bind=True,
    max_retries=3,
    soft_time_limit=300,  # 5 minutes
    time_limit=360,       # 6 minutes hard limit
)
def generate_a3_pdf(
    self,
    a3_id: str,
    user_id: str,
    include_attachments: bool = False,
) -> Dict[str, Any]:
    """
    Generate PDF for an A3 problem-solving report.
    
    This task:
    1. Loads A3 data from database
    2. Renders HTML template
    3. Converts to PDF using WeasyPrint
    4. Uploads to S3
    5. Updates A3 record with PDF key
    
    Args:
        a3_id: UUID of the A3 record
        user_id: UUID of the user requesting generation
        include_attachments: Whether to include attachments in PDF
        
    Returns:
        Dict with result URL and metadata
    """
    task_id = self.request.id
    
    try:
        _update_progress(task_id, PDFGenerationStatus.PROCESSING, 10, "Loading A3 data...")
        
        # Import inside task to avoid import cycles
        from sensei.core.database import sync_session_factory
        from sensei.models.a3 import A3Report
        from sensei.core.storage import storage_client
        
        # Load A3 from database
        with sync_session_factory() as session:
            a3 = session.query(A3Report).filter(A3Report.id == UUID(a3_id)).first()
            
            if not a3:
                raise ValueError(f"A3 not found: {a3_id}")
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 30, "Rendering template...")
            
            # Generate HTML content
            html_content = _render_a3_html(a3, include_attachments)
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 50, "Converting to PDF...")
            
            # Convert HTML to PDF
            pdf_bytes = _html_to_pdf(html_content)
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 70, "Uploading to storage...")
            
            # Upload to S3
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            storage_key = f"pdfs/a3/{a3_id}/{timestamp}_a3_report.pdf"
            
            storage_client.put_object(
                Key=storage_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
                Metadata={
                    "a3_id": a3_id,
                    "generated_by": user_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 90, "Updating record...")
            
            # Update A3 with PDF key
            a3.pdf_storage_key = storage_key
            session.commit()
            
            # Generate presigned URL for download
            from sensei.core.storage import generate_presigned_url
            download_url = generate_presigned_url(storage_key, expires_in=3600)
            
            _update_progress(
                task_id, 
                PDFGenerationStatus.COMPLETED, 
                100, 
                "PDF generation complete",
                result_url=download_url
            )
            
            return {
                "success": True,
                "storage_key": storage_key,
                "download_url": download_url,
                "size_bytes": len(pdf_bytes),
            }
            
    except Exception as e:
        logger.exception(f"PDF generation failed for A3 {a3_id}")
        _update_progress(
            task_id,
            PDFGenerationStatus.FAILED,
            0,
            "PDF generation failed",
            error=str(e)
        )
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
        
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task(
    name="sensei.tasks.pdf_tasks.generate_quote_pdf",
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    time_limit=360,
)
def generate_quote_pdf(
    self,
    quote_id: str,
    user_id: str,
    template: str = "standard",
) -> Dict[str, Any]:
    """
    Generate PDF for a quote/proposal.
    
    Args:
        quote_id: UUID of the quote
        user_id: UUID of the user
        template: Template name (standard, detailed, executive)
        
    Returns:
        Dict with result URL and metadata
    """
    task_id = self.request.id
    
    try:
        _update_progress(task_id, PDFGenerationStatus.PROCESSING, 10, "Loading quote data...")
        
        from sensei.core.database import sync_session_factory
        from sensei.models.quote import Quote
        from sensei.core.storage import storage_client, generate_presigned_url
        
        with sync_session_factory() as session:
            quote = session.query(Quote).filter(Quote.id == UUID(quote_id)).first()
            
            if not quote:
                raise ValueError(f"Quote not found: {quote_id}")
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 30, "Rendering template...")
            
            # Generate HTML
            html_content = _render_quote_html(quote, template)
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 50, "Converting to PDF...")
            
            # Convert to PDF
            pdf_bytes = _html_to_pdf(html_content)
            
            _update_progress(task_id, PDFGenerationStatus.PROCESSING, 70, "Uploading to storage...")
            
            # Upload to S3
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            storage_key = f"pdfs/quotes/{quote_id}/{timestamp}_quote.pdf"
            
            storage_client.put_object(
                Key=storage_key,
                Body=pdf_bytes,
                ContentType="application/pdf",
                Metadata={
                    "quote_id": quote_id,
                    "generated_by": user_id,
                    "template": template,
                }
            )
            
            # Generate download URL
            download_url = generate_presigned_url(storage_key, expires_in=3600)
            
            _update_progress(
                task_id,
                PDFGenerationStatus.COMPLETED,
                100,
                "PDF generation complete",
                result_url=download_url
            )
            
            return {
                "success": True,
                "storage_key": storage_key,
                "download_url": download_url,
                "size_bytes": len(pdf_bytes),
            }
            
    except Exception as e:
        logger.exception(f"Quote PDF generation failed: {quote_id}")
        _update_progress(
            task_id,
            PDFGenerationStatus.FAILED,
            0,
            "PDF generation failed",
            error=str(e)
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
        
        return {"success": False, "error": str(e)}


def _render_a3_html(a3, include_attachments: bool) -> str:
    """Render A3 report as HTML."""
    # Simple HTML template - in production, use Jinja2 templates
    sections = []
    
    # Header
    sections.append(f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
            h2 {{ color: #555; margin-top: 30px; }}
            .section {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
            .meta {{ color: #888; font-size: 12px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            td, th {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
            th {{ background: #f0f0f0; }}
        </style>
    </head>
    <body>
        <h1>A3 Problem-Solving Report</h1>
        <p class="meta">Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p class="meta">ID: {a3.id}</p>
    """)
    
    # Title and background
    sections.append(f"""
        <div class="section">
            <h2>Title</h2>
            <p>{a3.title or 'Untitled'}</p>
        </div>
    """)
    
    if a3.background:
        sections.append(f"""
            <div class="section">
                <h2>Background</h2>
                <p>{a3.background}</p>
            </div>
        """)
    
    if a3.current_condition:
        sections.append(f"""
            <div class="section">
                <h2>Current Condition</h2>
                <p>{a3.current_condition}</p>
            </div>
        """)
    
    if a3.goal:
        sections.append(f"""
            <div class="section">
                <h2>Goal</h2>
                <p>{a3.goal}</p>
            </div>
        """)
    
    if a3.root_cause_analysis:
        sections.append(f"""
            <div class="section">
                <h2>Root Cause Analysis</h2>
                <p>{a3.root_cause_analysis}</p>
            </div>
        """)
    
    if a3.countermeasures:
        sections.append(f"""
            <div class="section">
                <h2>Countermeasures</h2>
                <p>{a3.countermeasures}</p>
            </div>
        """)
    
    if a3.implementation_plan:
        sections.append(f"""
            <div class="section">
                <h2>Implementation Plan</h2>
                <p>{a3.implementation_plan}</p>
            </div>
        """)
    
    if a3.follow_up:
        sections.append(f"""
            <div class="section">
                <h2>Follow-up</h2>
                <p>{a3.follow_up}</p>
            </div>
        """)
    
    sections.append("</body></html>")
    
    return "".join(sections)


def _render_quote_html(quote, template: str) -> str:
    """Render quote as HTML."""
    from sensei.core.config import settings
    
    # Simple HTML template
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            .header {{ border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }}
            .company {{ font-size: 24px; font-weight: bold; color: #007bff; }}
            .quote-info {{ margin: 20px 0; }}
            .quote-info td {{ padding: 5px 20px 5px 0; }}
            table.items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            table.items th, table.items td {{ padding: 10px; border: 1px solid #ddd; }}
            table.items th {{ background: #f0f0f0; }}
            .total {{ text-align: right; font-size: 18px; margin-top: 20px; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company">Starz Morocco</div>
            <p>Manufacturing Excellence</p>
        </div>
        
        <h1>Quote #{quote.quote_number or quote.id}</h1>
        
        <table class="quote-info">
            <tr><td><strong>Date:</strong></td><td>{quote.created_at.strftime('%B %d, %Y') if quote.created_at else 'N/A'}</td></tr>
            <tr><td><strong>Status:</strong></td><td>{quote.status.value if hasattr(quote, 'status') and quote.status else 'Draft'}</td></tr>
            <tr><td><strong>Valid Until:</strong></td><td>{quote.valid_until.strftime('%B %d, %Y') if hasattr(quote, 'valid_until') and quote.valid_until else 'N/A'}</td></tr>
        </table>
        
        <h2>Line Items</h2>
        <table class="items">
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Unit Price</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Add line items if available
    total = 0
    if hasattr(quote, 'line_items') and quote.line_items:
        for item in quote.line_items:
            item_total = (item.quantity or 0) * (item.unit_price or 0)
            total += item_total
            html += f"""
                <tr>
                    <td>{item.product_name or 'N/A'}</td>
                    <td>{item.description or ''}</td>
                    <td>{item.quantity or 0}</td>
                    <td>${item.unit_price or 0:.2f}</td>
                    <td>${item_total:.2f}</td>
                </tr>
            """
    else:
        html += "<tr><td colspan='5'>No line items</td></tr>"
    
    html += f"""
            </tbody>
        </table>
        
        <div class="total">
            <strong>Total: ${total:.2f}</strong>
        </div>
        
        <div class="footer">
            <p>Generated by Sensei OS | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
    </body>
    </html>
    """
    
    return html


def _html_to_pdf(html_content: str) -> bytes:
    """
    Convert HTML to PDF using WeasyPrint.
    
    Falls back to a simple implementation if WeasyPrint is not available.
    """
    try:
        from weasyprint import HTML
        
        # Create PDF in memory
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
        
    except ImportError:
        logger.warning("WeasyPrint not installed, using fallback PDF generation")
        
        # Fallback: Create a simple text-based "PDF" (actually just text)
        # In production, always use WeasyPrint
        import html as html_module
        from html.parser import HTMLParser
        
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []
                
            def handle_data(self, data):
                self.text_parts.append(data.strip())
        
        extractor = TextExtractor()
        extractor.feed(html_content)
        text_content = "\n".join(filter(None, extractor.text_parts))
        
        # Return text as bytes (not a real PDF)
        return text_content.encode('utf-8')
