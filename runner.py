import os
import sys
import time
import socket
import argparse
import subprocess
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

# Import logging configuration
from utils import setup_logger

console = Console()
logger = setup_logger()

# Constants
CHROME_PORT = 9222
DEFAULT_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

def is_chrome_running(port=CHROME_PORT) -> bool:
    """Checks if a process is listening on the remote debugging port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

def launch_chrome(chrome_path=DEFAULT_CHROME_PATH, port=CHROME_PORT):
    """Launches Google Chrome with remote debugging on port 9222 in a dedicated profile directory."""
    if not os.path.exists(chrome_path):
        msg = f"Google Chrome binary not found at '{chrome_path}'"
        logger.error(msg)
        console.print(f"[bold red]Error: {msg}[/bold red]")
        sys.exit(1)
        
    os.makedirs(PROFILE_DIR, exist_ok=True)
    
    # Chrome flags to open debugging port, use a separate data directory, and launch safely
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    logger.info(f"Auto-launching Chrome: {' '.join(cmd)}")
    console.print(f"[blue]Launching Google Chrome in background on port {port}...[/blue]")
    
    # Run Chrome as a background subprocess (detached)
    # On macOS, stdin/stdout redirection prevents blocking
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True
    )
    
    # Give Chrome 4 seconds to fully start and initialize the port
    time.sleep(4)
    
    if is_chrome_running(port):
        msg = f"Chrome successfully launched and listening on port {port}."
        logger.info(msg)
        console.print(f"[green]✔ {msg}[/green]")
    else:
        msg = f"Chrome launch command was run but port {port} is still unreachable."
        logger.error(msg)
        console.print(f"[bold yellow]Warning: {msg}[/bold yellow]")

def run_scraper_process(max_retries=2) -> bool:
    """Runs the main scraper script as a subprocess and logs its output.
    
    Args:
        max_retries: Maximum number of retry attempts if browser is unresponsive
    
    Returns:
        True if scraper succeeded, False otherwise
    """
    retry_count = 0
    
    while retry_count <= max_retries:
        logger.info(f"Starting scraper run from runner... (Attempt {retry_count + 1}/{max_retries + 1})")
        console.print("[yellow]Executing scraper...[/yellow]")
        
        # Run scraper.py and stream output to terminal
        try:
            # We run using the current python executable to guarantee correct virtualenv/environment
            result = subprocess.run(
                [sys.executable, "scraper.py"],
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Scraper process finished successfully.")
                return True
            else:
                logger.error(f"Scraper process failed with exit code: {result.returncode}")
                
                # Check if this might be a browser-related error
                if retry_count < max_retries:
                    logger.warning("Possible browser unresponsiveness detected. Attempting to restart Chrome...")
                    console.print("[bold yellow]Browser may be unresponsive. Restarting Chrome and retrying...[/bold yellow]")
                    
                    # Kill existing Chrome process
                    try:
                        subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
                        time.sleep(2)
                    except:
                        pass
                    
                    # Relaunch Chrome
                    launch_chrome(port=CHROME_PORT)
                    retry_count += 1
                else:
                    logger.error("Max retries reached. Scraper failed.")
                    return False
                    
        except Exception as e:
            logger.exception(f"Unexpected error executing scraper process: {e}")
            
            if retry_count < max_retries:
                logger.warning("Attempting to restart Chrome and retry...")
                console.print("[bold yellow]Error encountered. Restarting Chrome and retrying...[/bold yellow]")
                
                # Kill existing Chrome process
                try:
                    subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
                    time.sleep(2)
                except:
                    pass
                
                # Relaunch Chrome
                launch_chrome(port=CHROME_PORT)
                retry_count += 1
            else:
                logger.error("Max retries reached. Scraper failed.")
                return False
    
    return False

def maintain_and_run(args):
    """Ensures Chrome is running, runs the scraper, and maintains the process loop."""
    logger.info("=== Runner Initialized ===")
    
    # Ensure Chrome is running unless disabled
    if not args.no_launch:
        if is_chrome_running():
            logger.info("Chrome remote debugging is already active on port 9222.")
            console.print("[green]✔ Chrome remote debugging is already active on port 9222.[/green]")
        else:
            launch_chrome(chrome_path=args.chrome_path, port=CHROME_PORT)
            console.print(Panel(
                "[bold yellow]IMPORTANT ACTION REQUIRED[/bold yellow]\n"
                "A dedicated Google Chrome profile window has been opened for you.\n"
                "Please make sure to log into LinkedIn in that window so the scraper can use your session!\n"
                "Once logged in, your session is saved in 'chrome_profile' and won't need to be re-entered."
            ))
            # Pause to give the user time to log in if they need to
            console.print("[blue]Press Enter when you are ready to continue and run the scraper...[/blue]")
            input()
    else:
        if not is_chrome_running():
            msg = "no_launch was specified, but Chrome is not running on port 9222. The scraper will fail."
            logger.warning(msg)
            console.print(f"[bold yellow]Warning: {msg}[/bold yellow]")
            
    # Run once or enter schedule loop
    if args.interval == 0:
        logger.info("Executing on-demand single run.")
        success = run_scraper_process()
        if success:
            console.print("[bold green]✔ Scraper complete![/bold green]")
        else:
            console.print("[bold red]✖ Scraper run failed. Check scraper.log for details.[/bold red]")
    else:
        logger.info(f"Entering schedule loop. Scraping interval: every {args.interval} hour(s).")
        console.print(Panel(
            f"[bold green]Scraper Daemon Active[/bold green]\n"
            f"The scraper will run automatically every [bold]{args.interval}[/bold] hour(s).\n"
            f"Press Ctrl+C to stop the daemon safely. Monitoring logs are saved to 'scraper.log'."
        ))
        
        # Immediate first run
        run_scraper_process()
        
        seconds_interval = args.interval * 3600
        while True:
            logger.info(f"Sleeping for {args.interval} hours...")
            
            # Use small sleep increments to allow responsive Ctrl+C interrupt
            for _ in range(int(seconds_interval)):
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Runner daemon stopped by user.")
                    console.print("\n[bold yellow]Runner daemon stopped by user. Goodbye![/bold yellow]")
                    return
            
            # Check if Chrome is still alive, restart if dead
            if not is_chrome_running() and not args.no_launch:
                logger.warning("Scheduled Run: Chrome port 9222 went down. Attempting auto-restart...")
                launch_chrome(chrome_path=args.chrome_path, port=CHROME_PORT)
                
            logger.info("Executing scheduled run...")
            run_scraper_process()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Scraper Runner & Maintenance Tool")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Run scraper repeatedly at this interval in hours (e.g., 12.0). Default is 0 (run once and exit)."
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Do not attempt to auto-launch Google Chrome on port 9222."
    )
    parser.add_argument(
        "--chrome-path",
        type=str,
        default=DEFAULT_CHROME_PATH,
        help="Absolute path to the Google Chrome executable."
    )
    
    args = parser.parse_args()
    try:
        maintain_and_run(args)
    except KeyboardInterrupt:
        logger.info("Runner interrupted by user.")
        console.print("\n[bold yellow]Runner interrupted. Exiting...[/bold yellow]")
