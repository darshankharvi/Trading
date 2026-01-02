import time
import schedule
import typer
import datetime
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.security import DataProtection

# Load environment variables
load_dotenv()

console = Console()
app = typer.Typer()
security = DataProtection()

def job(ticker: str, graph: TradingAgentsGraph, save_dir: Path, encrypt: bool):
    """
    The periodic job that runs the analysis.
    """
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    
    console.print(f"[bold blue]Starting scheduled analysis for {ticker} at {time_str}...[/bold blue]")
    
    try:
        # Run propagation
        # Note: propagate method signature might vary, usually takes ticker and date
        # We assume the graph is stateful or handles the logic
        final_state, decision = graph.propagate(ticker, date_str)
        
        # Prepare output
        output_data = {
            "timestamp": now.isoformat(),
            "ticker": ticker,
            "decision": decision,
            "final_state": final_state
        }
        
        # Save result
        file_name = f"{date_str}_{time_str}_{ticker}.json"
        file_path = save_dir / file_name
        
        json_content = json.dumps(output_data, indent=2, default=str)
        
        with open(file_path, "w") as f:
            f.write(json_content)
            
        console.print(f"[green]Analysis complete. Saved to {file_path}[/green]")
        
        # Optional Encryption
        if encrypt:
            security.encrypt_file(str(file_path))
            console.print(f"[yellow]File encrypted.[/yellow]")
            
    except Exception as e:
        console.print(f"[bold red]Error during execution: {e}[/bold red]")

@app.command()
def start(
    ticker: str = typer.Option("RELIANCE.NS", help="Ticker symbol to analyze (e.g. RELIANCE.NS)"),
    interval: int = typer.Option(60, help="Interval in minutes between runs"),
    mode: str = typer.Option("once", help="Mode: 'once' or 'loop'"),
    encrypt: bool = typer.Option(False, help="Encrypt output files"),
    results_dir: str = typer.Option("./results/live", help="Directory to save live results")
):
    """
    Start the real-time analysis runner.
    """
    console.print(f"Initializing Real-time Runner for [bold]{ticker}[/bold]")
    
    # Initialize Graph
    # We use a default set of analysts for the automated runner
    analysts = ["market", "news", "technical"] 
    
    # Ensure config has 'openrouter' if set in env, or load from default
    # The default_config.py should be picked up by TradingAgentsGraph
    
    graph = TradingAgentsGraph(
        selected_analysts=analysts,
        config=DEFAULT_CONFIG,
        debug=False
    )
    
    # Setup Directory
    save_path = Path(results_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    
    if mode == "once":
        job(ticker, graph, save_path, encrypt)
    else:
        # Schedule the job
        schedule.every(interval).minutes.do(job, ticker, graph, save_path, encrypt)
        
        console.print(f"[green]Scheduler started. Running every {interval} minutes.[/green]")
        
        # Run immediately once
        job(ticker, graph, save_path, encrypt)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    app()
