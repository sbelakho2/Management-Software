#!/usr/bin/env python3
"""
Knowledge Pack CLI - Ingest open-license learning content.

Usage:
    python -m sensei.cli.knowledge ingest <url> --title "Document Title" [options]
    python -m sensei.cli.knowledge list
    python -m sensei.cli.knowledge process <document-id>
    python -m sensei.cli.knowledge stats
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.database import async_session_maker
from sensei.models.knowledge_pack import (
    KnowledgeDocument,
    KnowledgeChunk,
    IngestionLog,
    LicenseType,
)
from sensei.services.ai.knowledge_ingestion import KnowledgePackIngestionService
from sensei.services.ai.knowledge_embeddings import (
    EmbeddingService,
    KnowledgeEmbeddingService,
    SemanticSearchService,
)

app = typer.Typer(
    name="knowledge",
    help="Knowledge Pack ingestion and management CLI",
)
console = Console()


@app.command()
def ingest(
    url: str = typer.Argument(..., help="URL of content to ingest"),
    title: str = typer.Option(..., help="Document title"),
    author: Optional[str] = typer.Option(None, help="Author name"),
    license_url: Optional[str] = typer.Option(None, help="URL to license information"),
    license_text: Optional[str] = typer.Option(None, help="License text"),
    tags: Optional[list[str]] = typer.Option(None, "--tag", help="Taxonomy tags (can specify multiple)"),
    process_immediately: bool = typer.Option(True, "--process/--no-process", help="Process into chunks immediately"),
):
    """
    Ingest content from URL into knowledge pack.
    
    Example:
        python -m sensei.cli.knowledge ingest \\
            https://example.com/lean-guide.html \\
            --title "Lean Manufacturing Guide" \\
            --author "John Shook" \\
            --license-url "https://creativecommons.org/licenses/by/4.0/" \\
            --tag lean_principles --tag tps
    """
    asyncio.run(_ingest_async(url, title, author, license_url, license_text, tags or [], process_immediately))


async def _ingest_async(
    url: str,
    title: str,
    author: Optional[str],
    license_url: Optional[str],
    license_text: Optional[str],
    tags: list[str],
    process_immediately: bool,
):
    """Async implementation of ingest command."""
    service = KnowledgePackIngestionService()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching and ingesting...", total=None)
        
        # Ingest document
        document, message = service.ingest_url(
            url=url,
            title=title,
            author=author,
            license_url=license_url,
            license_text=license_text,
            tags=tags,
        )
        
        if document is None:
            console.print(f"[red]✗[/red] {message}")
            service.close()
            raise typer.Exit(1)
        
        # Save to database
        async with async_session_maker() as session:
            try:
                session.add(document)
                await session.commit()
                await session.refresh(document)
                
                # Log successful ingestion
                log = IngestionLog(
                    source_url=url,
                    operation="ingest",
                    status="success",
                    document_id=document.id,
                    extra_metadata={"title": title, "author": author},
                )
                session.add(log)
                await session.commit()
                
                console.print(f"[green]✓[/green] {message}")
                console.print(f"  Document ID: {document.id}")
                console.print(f"  License: {document.license_type.value}")
                console.print(f"  Word Count: {document.word_count:,}")
                
                # Process if requested
                if process_immediately:
                    progress.update(task, description="Processing into chunks...")
                    chunks = service.process_document(document)
                    
                    for chunk in chunks:
                        session.add(chunk)
                    
                    await session.commit()
                    
                    console.print(f"[green]✓[/green] Created {len(chunks)} chunks")
                
            except Exception as e:
                await session.rollback()
                
                # Log failure
                log = IngestionLog(
                    source_url=url,
                    operation="ingest",
                    status="failed",
                    error_message=str(e),
                    extra_metadata={"title": title, "author": author},
                )
                session.add(log)
                await session.commit()
                
                console.print(f"[red]✗[/red] Error saving to database: {e}")
                raise typer.Exit(1)
            finally:
                service.close()


@app.command()
def list(
    license_type: Optional[str] = typer.Option(None, help="Filter by license type"),
    tag: Optional[str] = typer.Option(None, help="Filter by tag"),
    limit: int = typer.Option(20, help="Number of documents to show"),
):
    """
    List ingested knowledge documents.
    """
    asyncio.run(_list_async(license_type, tag, limit))


async def _list_async(license_type: Optional[str], tag: Optional[str], limit: int):
    """Async implementation of list command."""
    async with async_session_maker() as session:
        query = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
        
        if license_type:
            query = query.where(KnowledgeDocument.license_type == license_type)
        
        if tag:
            query = query.where(KnowledgeDocument.tags.contains([tag]))
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        documents = result.scalars().all()
        
        if not documents:
            console.print("[yellow]No documents found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Knowledge Documents ({len(documents)})")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="bright_white")
        table.add_column("Author", style="dim")
        table.add_column("License", style="green")
        table.add_column("Words", justify="right")
        table.add_column("Chunks", justify="right")
        table.add_column("Tags", style="blue")
        
        for doc in documents:
            table.add_row(
                str(doc.id)[:8],
                doc.title[:50] + "..." if len(doc.title) > 50 else doc.title,
                doc.author or "—",
                doc.license_type.value,
                f"{doc.word_count:,}",
                str(doc.chunk_count) if doc.is_processed else "—",
                ", ".join(doc.tags[:3]) + ("..." if len(doc.tags) > 3 else ""),
            )
        
        console.print(table)


@app.command()
def process(
    document_id: str = typer.Argument(..., help="Document ID to process"),
):
    """
    Process a document into chunks.
    
    Example:
        python -m sensei.cli.knowledge process abc123def456
    """
    asyncio.run(_process_async(document_id))


async def _process_async(document_id: str):
    """Async implementation of process command."""
    service = KnowledgePackIngestionService()
    
    async with async_session_maker() as session:
        try:
            # Fetch document
            doc_uuid = UUID(document_id)
            result = await session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == doc_uuid)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                console.print(f"[red]✗[/red] Document not found: {document_id}")
                raise typer.Exit(1)
            
            if document.is_processed:
                console.print(f"[yellow]![/yellow] Document already processed ({document.chunk_count} chunks)")
                return
            
            # Process document
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Processing document...", total=None)
                
                chunks = service.process_document(document)
                
                for chunk in chunks:
                    session.add(chunk)
                
                await session.commit()
            
            console.print(f"[green]✓[/green] Created {len(chunks)} chunks")
            console.print(f"  Quality chunks: {sum(1 for c in chunks if c.quality_score and c.quality_score > 0.7)}")
            console.print(f"  Tags applied: {len(set(tag for chunk in chunks for tag in chunk.tags))}")
            
        except Exception as e:
            await session.rollback()
            console.print(f"[red]✗[/red] Error processing document: {e}")
            raise typer.Exit(1)
        finally:
            service.close()


@app.command()
def stats():
    """
    Show statistics about the knowledge pack.
    """
    asyncio.run(_stats_async())


async def _stats_async():
    """Async implementation of stats command."""
    async with async_session_maker() as session:
        # Count documents
        doc_count_result = await session.execute(
            select(func.count(KnowledgeDocument.id))
        )
        doc_count = doc_count_result.scalar()
        
        # Count chunks
        chunk_count_result = await session.execute(
            select(func.count(KnowledgeChunk.id))
        )
        chunk_count = chunk_count_result.scalar()
        
        # Count by license
        license_counts_result = await session.execute(
            select(
                KnowledgeDocument.license_type,
                func.count(KnowledgeDocument.id)
            ).group_by(KnowledgeDocument.license_type)
        )
        license_counts = license_counts_result.all()
        
        # Total words
        word_count_result = await session.execute(
            select(func.sum(KnowledgeDocument.word_count))
        )
        total_words = word_count_result.scalar() or 0
        
        # Create stats display
        console.print("\n[bold]Knowledge Pack Statistics[/bold]\n")
        
        console.print(f"  Documents: [cyan]{doc_count:,}[/cyan]")
        console.print(f"  Chunks: [cyan]{chunk_count:,}[/cyan]")
        console.print(f"  Total Words: [cyan]{total_words:,}[/cyan]")
        
        if license_counts:
            console.print("\n[bold]By License:[/bold]")
            for license_type, count in license_counts:
                console.print(f"  {license_type.value}: [green]{count}[/green]")
        
        console.print()


@app.command()
def verify_license(
    url: str = typer.Argument(..., help="URL to check"),
):
    """
    Verify if a URL's license is compatible with ingestion.
    
    Example:
        python -m sensei.cli.knowledge verify-license https://example.com/article
    """
    service = KnowledgePackIngestionService()
    
    console.print(f"[blue]Checking license for:[/blue] {url}")
    
    try:
        content_bytes, content_type = service.content_fetcher.fetch_url(url)
        content_text = content_bytes.decode("utf-8", errors="ignore")
        
        license_type = service.license_verifier.detect_license(content_text, url)
        
        if license_type:
            console.print(f"[green]✓[/green] Detected license: {license_type.value}")
            console.print(f"[green]✓[/green] License is allowed for ingestion")
        else:
            console.print(f"[red]✗[/red] No compatible license detected")
            console.print(f"[yellow]![/yellow] Manual verification required")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
    finally:
        service.close()


@app.command()
def embed(
    document_id: Optional[int] = typer.Option(None, help="Document ID to embed (if not specified, embeds all)"),
    model: str = typer.Option("all-MiniLM-L6-v2", help="Sentence-transformers model name"),
):
    """
    Generate embeddings for knowledge chunks.
    
    Example:
        python -m sensei.cli.knowledge embed --document-id 1
        python -m sensei.cli.knowledge embed  # Embed all unembedded chunks
    """
    async def _embed():
        embedding_service = EmbeddingService(model_name=model)
        knowledge_embedding_service = KnowledgeEmbeddingService(embedding_service)
        
        async with async_session_maker() as session:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                if document_id:
                    task = progress.add_task(f"Embedding document {document_id}...", total=None)
                    count = await knowledge_embedding_service.embed_document_chunks(
                        document_id, session
                    )
                    progress.update(task, completed=True)
                    console.print(f"[green]✓[/green] Embedded {count} chunks from document {document_id}")
                else:
                    task = progress.add_task("Embedding all unembedded chunks...", total=None)
                    count = await knowledge_embedding_service.embed_all_unembedded(session)
                    progress.update(task, completed=True)
                    console.print(f"[green]✓[/green] Embedded {count} total chunks")
    
    asyncio.run(_embed())


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, help="Maximum number of results"),
    min_similarity: float = typer.Option(0.6, help="Minimum similarity score (0-1)"),
    tags: Optional[list[str]] = typer.Option(None, "--tag", help="Filter by taxonomy tags"),
    model: str = typer.Option("all-MiniLM-L6-v2", help="Sentence-transformers model name"),
):
    """
    Semantic search over knowledge chunks.
    
    Example:
        python -m sensei.cli.knowledge search "5S workplace organization"
        python -m sensei.cli.knowledge search "PDCA cycle" --limit 10 --tag pdca
    """
    async def _search():
        embedding_service = EmbeddingService(model_name=model)
        search_service = SemanticSearchService(embedding_service)
        
        async with async_session_maker() as session:
            results = await search_service.search_with_context(
                query=query,
                session=session,
                limit=limit,
                min_similarity=min_similarity,
                filter_tags=tags,
            )
            
            if not results:
                console.print(f"[yellow]No results found for query: '{query}'[/yellow]")
                return
            
            console.print(f"\n[bold]Found {len(results)} results for:[/bold] '{query}'\n")
            
            for i, result in enumerate(results, 1):
                console.print(f"[bold cyan]{i}. {result['document_title']}[/bold cyan]")
                console.print(f"   Author: {result['document_author'] or 'N/A'}")
                console.print(f"   Section: {' > '.join(result['section_path']) if result['section_path'] else result['heading'] or 'N/A'}")
                console.print(f"   Similarity: {result['similarity']:.3f} | Quality: {result['quality_score']:.2f}")
                console.print(f"   Tags: {', '.join(result['tags']) if result['tags'] else 'None'}")
                console.print(f"   License: {result['license_type']}")
                console.print(f"\n   [dim]{result['chunk_text'][:200]}...[/dim]")
                console.print(f"   [italic]{result['citation']}[/italic]\n")
    
    asyncio.run(_search())


if __name__ == "__main__":
    app()
