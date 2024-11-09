import os
import subprocess
import sys
from pathlib import Path

import click

@click.group()
@click.version_option()
def cli():
    """PremSQL CLI to manage API servers and Streamlit app"""
    pass

@cli.group()
def launch():
    """Launch PremSQL services"""
    pass


@launch.command(name='all')
def launch_all():
    """Launch both API server and Streamlit app"""
    premsql_path = Path(__file__).parent.parent.absolute()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(premsql_path)
    
    # Start API server
    manage_py_path = premsql_path / "premsql" / "playground" / "backend" / "manage.py"
    if not manage_py_path.exists():
        click.echo(f"Error: manage.py not found at {manage_py_path}", err=True)
        sys.exit(1)

    # Run migrations first
    click.echo("Running database migrations...")
    try:
        subprocess.run([sys.executable, str(manage_py_path), "makemigrations"], env=env, check=True)
        subprocess.run([sys.executable, str(manage_py_path), "migrate"], env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running migrations: {e}", err=True)
        sys.exit(1)

    click.echo("Starting the PremSQL backend API server...")
    subprocess.Popen([sys.executable, str(manage_py_path), "runserver"], env=env)

    # Launch the streamlit app
    click.echo("Starting the PremSQL Streamlit app...")
    main_py_path = premsql_path / "premsql" / "playground" / "frontend" / "main.py"
    if not main_py_path.exists():
        click.echo(f"Error: main.py not found at {main_py_path}", err=True)
        sys.exit(1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(main_py_path), "--server.maxUploadSize=500"]
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        click.echo("Stopping all services...")
        stop()

@launch.command(name='api')
def launch_api():
    """Launch only the API server"""
    premsql_path = Path(__file__).parent.parent.absolute()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(premsql_path)
    manage_py_path = premsql_path / "premsql" / "playground" / "backend" / "manage.py"

    if not manage_py_path.exists():
        click.echo(f"Error: manage.py not found at {manage_py_path}", err=True)
        sys.exit(1)

    # Run makemigrations
    click.echo("Running database migrations...")
    try:
        subprocess.run([sys.executable, str(manage_py_path), "makemigrations"], env=env, check=True)
        subprocess.run([sys.executable, str(manage_py_path), "migrate"], env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running migrations: {e}", err=True)
        sys.exit(1)

    click.echo("Starting the PremSQL backend API server...")
    cmd = [sys.executable, str(manage_py_path), "runserver"]
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        click.echo("API server stopped.")

@cli.command()
def stop():
    """Stop all PremSQL services"""
    click.echo("Stopping all PremSQL services...")

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq premsql*"],
                check=True,
            )
        else:
            subprocess.run(["pkill", "-f", "manage.py runserver"], check=True)
            subprocess.run(["pkill", "-f", "streamlit"], check=True)
        click.echo("All services stopped successfully.")
    except subprocess.CalledProcessError:
        click.echo("No running services found.")
    except Exception as e:
        click.echo(f"Error stopping services: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()