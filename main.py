from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from pipeline.orchestrator import Orchestrator
from protocol.message import ConsensusResult, ReviewResult

app = typer.Typer(help="Multi-Agent Code Review — powered by Qwen Cloud")
console = Console()

SEVERITY_COLOR = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}


def render_result(result: ReviewResult) -> None:
    m = result.metrics
    console.print(
        Panel(
            f"[bold]{result.filename}[/bold]  "
            f"findings: {result.total_findings}  "
            f"conflicts: {m.conflicts_detected} detected / {m.conflicts_resolved} resolved  "
            f"human review needed: {m.requires_human_review}",
            title="[bold blue]Review Complete[/bold blue]",
        )
    )

    table = Table(box=box.SIMPLE_HEAD, show_lines=True)
    table.add_column("Sev", style="bold", width=8)
    table.add_column("Agent", width=12)
    table.add_column("Line", width=6)
    table.add_column("Title", width=30)
    table.add_column("Confidence", width=10)
    table.add_column("Consensus", width=10)
    table.add_column("Human?", width=7)

    for r in result.consensus_findings:
        f = r.finding
        color = SEVERITY_COLOR.get(f.severity, "white")
        table.add_row(
            f"[{color}]{f.severity.upper()}[/{color}]",
            f.category.value,
            str(f.line) if f.line else "—",
            f.title,
            f"{f.confidence:.0%}",
            "[green]yes[/green]" if r.consensus_reached else "[red]no[/red]",
            "[yellow]yes[/yellow]" if r.requires_human_review else "",
        )

    console.print(table)

    for r in result.consensus_findings:
        f = r.finding
        color = SEVERITY_COLOR.get(f.severity, "white")
        console.print(Panel(
            f"[bold]{f.title}[/bold]\n\n"
            f"{f.description}\n\n"
            f"[bold cyan]Suggestion:[/bold cyan] {f.suggestion}\n\n"
            f"[dim]{f.evidence}[/dim]\n\n"
            f"[italic]{r.resolution}[/italic]",
            title=f"[{color}]{f.severity.upper()}[/{color}] — {f.category.value} (line {f.line})",
            border_style=color,
        ))

    if result.unresolved_conflicts:
        console.print(f"\n[bold red]{len(result.unresolved_conflicts)} unresolved conflict(s) — manual review required[/bold red]")


@app.command()
def review(
    path: Path = typer.Argument(..., help="File to review"),
    diff: str | None = typer.Option(None, "--diff", help="Git diff string"),
) -> None:
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)

    code = path.read_text()
    console.print(f"[bold blue]Reviewing {path.name} with 5 specialist agents...[/bold blue]")

    orchestrator = Orchestrator()
    result = asyncio.run(orchestrator.review(code, path.name, diff))
    render_result(result)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
) -> None:
    import uvicorn
    uvicorn.run("api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    app()
