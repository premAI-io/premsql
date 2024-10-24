import click
import os
import subprocess
import sys
from pathlib import Path

@click.group()
def cli():
    """PremSQL CLI to manage API servers"""
    pass

@cli.command()
def startapi():
    click.echo("Starting the PremSQL backend API server ...")
    premsql_path = Path(__file__).parent.parent.absolute()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(premsql_path)
    manage_py_path = premsql_path / "premsql" / "playground" / "backend" / "manage.py"
    
    if not manage_py_path.exists():
        click.echo(f"Error: manage.py not found at {manage_py_path}", err=True)
        sys.exit(1)
    
    cmd = [sys.executable, str(manage_py_path), "runserver"]
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error starting the API server: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("API server stopped.")


@cli.command()
def stopapi():
    click.echo("Stopping PremsQL API server...")
    
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq premsql*"], check=True)
        else:
            subprocess.run(["pkill", "-f", "manage.py runserver"], check=True)
        click.echo("API server stopped successfully.")
    except subprocess.CalledProcessError:
        click.echo("No running API server found.")
    except Exception as e:
        click.echo(f"Error stopping the API server: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()