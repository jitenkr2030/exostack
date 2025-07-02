#!/usr/bin/env python3
"""
ExoStack CLI Tool
Comprehensive command-line interface for managing ExoStack components.
"""

import click
import asyncio
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.tree import Tree

console = Console()

def print_success(message: str):
    """Print success message in green."""
    console.print(f"✅ {message}", style="green")

def print_error(message: str):
    """Print error message in red."""
    console.print(f"❌ {message}", style="red")

def print_warning(message: str):
    """Print warning message in yellow."""
    console.print(f"⚠️ {message}", style="yellow")

def print_info(message: str):
    """Print info message in blue."""
    console.print(f"ℹ️ {message}", style="blue")

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """ExoStack - Distributed AI Inference Platform CLI"""
    pass

@cli.group()
def hub():
    """Hub management commands"""
    pass

@cli.group()
def agent():
    """Agent management commands"""
    pass

@cli.group()
def task():
    """Task management commands"""
    pass

@cli.group()
def system():
    """System management commands"""
    pass

@cli.group()
def deploy():
    """Deployment and infrastructure commands"""
    pass

# Hub Commands
@hub.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def start(host: str, port: int, reload: bool):
    """Start the ExoStack hub server."""
    import uvicorn
    from exo_hub.main import app
    
    print_info(f"Starting ExoStack Hub on {host}:{port}")
    
    try:
        uvicorn.run(
            "exo_hub.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print_info("Hub server stopped")
    except Exception as e:
        print_error(f"Failed to start hub: {e}")

@hub.command()
@click.option('--url', default='http://localhost:8000', help='Hub URL')
def status(url: str):
    """Check hub status and display system information."""
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Connecting to hub...", total=None)
            
            # Get system status
            response = requests.get(f"{url}/status", timeout=10)
            response.raise_for_status()
            status_data = response.json()
            
            # Get nodes
            nodes_response = requests.get(f"{url}/nodes/status", timeout=10)
            nodes_response.raise_for_status()
            nodes_data = nodes_response.json()
            
            # Get tasks
            tasks_response = requests.get(f"{url}/tasks/status", timeout=10)
            tasks_response.raise_for_status()
            tasks_data = tasks_response.json()
            
        # Display results
        print_success(f"Connected to hub at {url}")
        
        # System overview
        panel = Panel.fit(
            f"[bold]ExoStack Hub Status[/bold]\\n\\n"
            f"🖥️  Nodes: {status_data.get('nodes', {}).get('total', 0)} total, "
            f"{status_data.get('nodes', {}).get('online', 0)} online\\n"
            f"📋 Tasks: {status_data.get('tasks', {}).get('total', 0)} total, "
            f"{status_data.get('tasks', {}).get('running', 0)} running, "
            f"{status_data.get('tasks', {}).get('pending', 0)} pending",
            title="System Overview"
        )
        console.print(panel)
        
        # Nodes table
        if nodes_data:
            nodes_table = Table(title="Registered Nodes")
            nodes_table.add_column("Node ID", style="cyan")
            nodes_table.add_column("Status", style="green")
            nodes_table.add_column("Last Heartbeat", style="yellow")
            nodes_table.add_column("Tasks Completed", style="blue")
            
            for node in nodes_data[:10]:  # Show first 10 nodes
                status_style = "green" if node.get("status") == "online" else "red"
                nodes_table.add_row(
                    node.get("id", "N/A"),
                    f"[{status_style}]{node.get('status', 'unknown')}[/{status_style}]",
                    node.get("last_heartbeat", "N/A"),
                    str(node.get("tasks_completed", 0))
                )
            
            console.print(nodes_table)
        
        # Recent tasks
        if tasks_data:
            tasks_table = Table(title="Recent Tasks")
            tasks_table.add_column("Task ID", style="cyan")
            tasks_table.add_column("Status", style="green")
            tasks_table.add_column("Model", style="yellow")
            tasks_table.add_column("Node", style="blue")
            tasks_table.add_column("Created", style="magenta")
            
            for task in tasks_data[:10]:  # Show first 10 tasks
                status_style = {
                    "completed": "green",
                    "running": "blue",
                    "pending": "yellow",
                    "failed": "red"
                }.get(task.get("status"), "white")
                
                tasks_table.add_row(
                    task.get("id", "N/A")[:12] + "...",
                    f"[{status_style}]{task.get('status', 'unknown')}[/{status_style}]",
                    task.get("model", "N/A"),
                    task.get("node_id", "N/A") or "unassigned",
                    task.get("created_at", "N/A")
                )
            
            console.print(tasks_table)
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to hub: {e}")
    except Exception as e:
        print_error(f"Error: {e}")

# Agent Commands
@agent.command()
@click.option('--agent-id', help='Agent ID (default: auto-generated)')
@click.option('--hub-url', default='http://localhost:8000', help='Hub URL')
def start(agent_id: str, hub_url: str):
    """Start an ExoStack agent."""
    from exo_agent.agent import main_loop
    
    if agent_id:
        import os
        os.environ['AGENT_ID'] = agent_id
    
    print_info(f"Starting ExoStack Agent (connecting to {hub_url})")
    
    try:
        main_loop()
    except KeyboardInterrupt:
        print_info("Agent stopped")
    except Exception as e:
        print_error(f"Agent failed: {e}")

@agent.command()
@click.option('--hub-url', default='http://localhost:8000', help='Hub URL')
def list(hub_url: str):
    """List all registered agents."""
    try:
        response = requests.get(f"{hub_url}/nodes/status", timeout=10)
        response.raise_for_status()
        nodes = response.json()
        
        if not nodes:
            print_warning("No agents registered")
            return
        
        table = Table(title="Registered Agents")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Last Heartbeat", style="yellow")
        table.add_column("Tasks Completed", style="blue")
        table.add_column("Tasks Failed", style="red")
        
        for node in nodes:
            status_style = "green" if node.get("status") == "online" else "red"
            table.add_row(
                node.get("id", "N/A"),
                f"[{status_style}]{node.get('status', 'unknown')}[/{status_style}]",
                node.get("last_heartbeat", "N/A"),
                str(node.get("tasks_completed", 0)),
                str(node.get("tasks_failed", 0))
            )
        
        console.print(table)
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to hub: {e}")
    except Exception as e:
        print_error(f"Error: {e}")

# Task Commands
@task.command()
@click.option('--model', default='microsoft/DialoGPT-medium', help='Model to use')
@click.option('--prompt', required=True, help='Input prompt')
@click.option('--max-tokens', default=100, help='Maximum tokens to generate')
@click.option('--temperature', default=0.7, help='Temperature for generation')
@click.option('--hub-url', default='http://localhost:8000', help='Hub URL')
@click.option('--wait', is_flag=True, help='Wait for task completion')
def create(model: str, prompt: str, max_tokens: int, temperature: float, hub_url: str, wait: bool):
    """Create a new inference task."""
    try:
        task_data = {
            "model": model,
            "input_data": {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        }
        
        print_info(f"Creating task with model: {model}")
        
        response = requests.post(f"{hub_url}/tasks/create", json=task_data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        task_id = result.get("task_id")
        print_success(f"Task created: {task_id}")
        
        if wait:
            print_info("Waiting for task completion...")
            
            while True:
                status_response = requests.get(f"{hub_url}/tasks/{task_id}", timeout=10)
                status_response.raise_for_status()
                task_status = status_response.json()
                
                status = task_status.get("status")
                
                if status == "completed":
                    print_success("Task completed!")
                    result = task_status.get("result", {})
                    
                    panel = Panel(
                        f"[bold]Task Result[/bold]\\n\\n"
                        f"Output: {result.get('output', 'N/A')}\\n"
                        f"Tokens: {result.get('tokens_generated', 'N/A')}\\n"
                        f"Time: {result.get('processing_time', 'N/A')}s",
                        title=f"Task {task_id[:12]}..."
                    )
                    console.print(panel)
                    break
                    
                elif status == "failed":
                    print_error("Task failed!")
                    error = task_status.get("result", {}).get("error", "Unknown error")
                    print_error(f"Error: {error}")
                    break
                    
                elif status in ["pending", "running"]:
                    print_info(f"Task status: {status}")
                    time.sleep(2)
                    
                else:
                    print_warning(f"Unknown status: {status}")
                    break
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to create task: {e}")
    except Exception as e:
        print_error(f"Error: {e}")

@task.command()
@click.argument('task_id')
@click.option('--hub-url', default='http://localhost:8000', help='Hub URL')
def status(task_id: str, hub_url: str):
    """Get task status and details."""
    try:
        response = requests.get(f"{hub_url}/tasks/{task_id}", timeout=10)
        response.raise_for_status()
        task_data = response.json()
        
        status = task_data.get("status", "unknown")
        model = task_data.get("model", "N/A")
        created = task_data.get("created_at", "N/A")
        node_id = task_data.get("node_id", "unassigned")
        
        # Create status display
        status_style = {
            "completed": "green",
            "running": "blue", 
            "pending": "yellow",
            "failed": "red"
        }.get(status, "white")
        
        info_text = (
            f"[bold]Task Details[/bold]\\n\\n"
            f"ID: {task_id}\\n"
            f"Status: [{status_style}]{status}[/{status_style}]\\n"
            f"Model: {model}\\n"
            f"Node: {node_id}\\n"
            f"Created: {created}"
        )
        
        # Add result if available
        if "result" in task_data and task_data["result"]:
            result = task_data["result"]
            if status == "completed":
                info_text += f"\\n\\nResult:\\n{result.get('output', 'N/A')}"
                info_text += f"\\nTokens: {result.get('tokens_generated', 'N/A')}"
                info_text += f"\\nProcessing time: {result.get('processing_time', 'N/A')}s"
            elif status == "failed":
                info_text += f"\\n\\nError: {result.get('error', 'Unknown error')}"
        
        panel = Panel(info_text, title="Task Status")
        console.print(panel)
        
    except requests.exceptions.RequestException as e:
        if "404" in str(e):
            print_error(f"Task not found: {task_id}")
        else:
            print_error(f"Failed to get task status: {e}")
    except Exception as e:
        print_error(f"Error: {e}")

@task.command()
@click.option('--hub-url', default='http://localhost:8000', help='Hub URL')
@click.option('--limit', default=20, help='Number of tasks to show')
def list(hub_url: str, limit: int):
    """List recent tasks."""
    try:
        response = requests.get(f"{hub_url}/tasks/status", timeout=10)
        response.raise_for_status()
        tasks = response.json()
        
        if not tasks:
            print_warning("No tasks found")
            return
        
        table = Table(title="Recent Tasks")
        table.add_column("Task ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Model", style="yellow")
        table.add_column("Node", style="blue")
        table.add_column("Created", style="magenta")
        
        for task in tasks[:limit]:
            status_style = {
                "completed": "green",
                "running": "blue",
                "pending": "yellow", 
                "failed": "red"
            }.get(task.get("status"), "white")
            
            table.add_row(
                task.get("id", "N/A")[:12] + "...",
                f"[{status_style}]{task.get('status', 'unknown')}[/{status_style}]",
                task.get("model", "N/A"),
                task.get("node_id", "N/A") or "unassigned",
                task.get("created_at", "N/A")
            )
        
        console.print(table)
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to hub: {e}")
    except Exception as e:
        print_error(f"Error: {e}")

# System Commands
@system.command()
def info():
    """Display system information."""
    try:
        from exo_agent.executor import get_inference_info
        
        tree = Tree("ExoStack System Information")
        
        # Python environment
        python_branch = tree.add("🐍 Python Environment")
        python_branch.add(f"Python: {sys.version}")
        python_branch.add(f"Platform: {sys.platform}")
        
        # Inference engine info
        try:
            info = get_inference_info()
            ai_branch = tree.add("🤖 AI/ML Environment")
            ai_branch.add(f"Device: {info.get('device', 'unknown')}")
            ai_branch.add(f"PyTorch: {info.get('torch_version', 'unknown')}")
            ai_branch.add(f"CUDA Available: {info.get('cuda_available', False)}")
            if info.get('cuda_version'):
                ai_branch.add(f"CUDA Version: {info.get('cuda_version')}")
            ai_branch.add(f"Cache Dir: {info.get('cache_dir', 'unknown')}")
            
            if info.get('loaded_models'):
                models_branch = ai_branch.add("Loaded Models")
                for model in info['loaded_models']:
                    models_branch.add(model)
            
        except Exception as e:
            tree.add(f"⚠️ AI/ML info unavailable: {e}")
        
        # File system
        fs_branch = tree.add("📁 File System")
        project_root = Path(__file__).parent
        fs_branch.add(f"Project Root: {project_root}")
        fs_branch.add(f"Config File: {project_root / '.env'}")
        fs_branch.add(f"Logs Dir: {project_root / 'logs'}")
        fs_branch.add(f"Models Dir: {project_root / 'models'}")
        
        console.print(tree)
        
    except Exception as e:
        print_error(f"Failed to get system info: {e}")

@system.command()
def test():
    """Run system tests."""
    import subprocess
    
    print_info("Running ExoStack tests...")
    
    try:
        # Run pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_success("All tests passed!")
        else:
            print_error("Some tests failed!")
            
        # Show output
        if result.stdout:
            console.print("\\n[bold]Test Output:[/bold]")
            console.print(result.stdout)
        
        if result.stderr:
            console.print("\\n[bold]Test Errors:[/bold]")
            console.print(result.stderr, style="red")
            
    except FileNotFoundError:
        print_error("pytest not found. Please install with: pip install pytest")
    except Exception as e:
        print_error(f"Failed to run tests: {e}")

# Deployment Commands
@deploy.command()
@click.option('--namespace', default='exostack', help='Kubernetes namespace')
@click.option('--dry-run', is_flag=True, help='Show what would be deployed without applying')
def kubernetes(namespace: str, dry_run: bool):
    """Deploy ExoStack to Kubernetes cluster."""
    import subprocess
    import os
    
    print_info(f"Deploying ExoStack to Kubernetes namespace: {namespace}")
    
    k8s_dir = Path("k8s")
    if not k8s_dir.exists():
        print_error("k8s directory not found. Make sure you're in the ExoStack root directory.")
        return
    
    # List of manifest files in order
    manifests = [
        "namespace.yaml",
        "secrets.yaml", 
        "configmap.yaml",
        "redis-deployment.yaml",
        "hub-deployment.yaml",
        "agent-deployment.yaml"
    ]
    
    try:
        # Check if kubectl is available
        subprocess.run(["kubectl", "version", "--client"], 
                      capture_output=True, check=True)
        
        for manifest in manifests:
            manifest_path = k8s_dir / manifest
            if manifest_path.exists():
                print_info(f"Applying {manifest}...")
                
                cmd = ["kubectl", "apply", "-f", str(manifest_path)]
                if dry_run:
                    cmd.append("--dry-run=client")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_success(f"✅ {manifest} applied successfully")
                    if dry_run:
                        console.print(result.stdout)
                else:
                    print_error(f"❌ Failed to apply {manifest}")
                    console.print(result.stderr, style="red")
            else:
                print_warning(f"⚠️ {manifest} not found, skipping")
        
        if not dry_run:
            print_info("\nChecking deployment status...")
            
            # Wait for deployments to be ready
            deployments = ["redis", "exostack-hub", "exostack-agent"]
            for deployment in deployments:
                print_info(f"Waiting for {deployment} to be ready...")
                result = subprocess.run([
                    "kubectl", "rollout", "status", 
                    f"deployment/{deployment}", 
                    "-n", namespace,
                    "--timeout=300s"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_success(f"✅ {deployment} is ready")
                else:
                    print_warning(f"⚠️ {deployment} may not be ready yet")
            
            print_success("\n🎉 ExoStack deployment completed!")
            print_info("\nTo access the hub service:")
            print_info(f"kubectl port-forward -n {namespace} service/exostack-hub-service 8000:8000")
            
    except subprocess.CalledProcessError:
        print_error("kubectl not found or not working. Please install kubectl and configure cluster access.")
    except Exception as e:
        print_error(f"Deployment failed: {e}")

@deploy.command()
@click.option('--registry', default='exostack', help='Docker registry prefix')
@click.option('--tag', default='latest', help='Docker image tag')
@click.option('--push', is_flag=True, help='Push images to registry')
def docker(registry: str, tag: str, push: bool):
    """Build Docker images for ExoStack components."""
    import subprocess
    
    print_info("Building ExoStack Docker images...")
    
    docker_dir = Path("docker")
    if not docker_dir.exists():
        print_error("docker directory not found. Make sure you're in the ExoStack root directory.")
        return
    
    # Images to build
    images = [
        {"name": "hub", "dockerfile": "Dockerfile.hub", "context": "."},
        {"name": "agent", "dockerfile": "Dockerfile.agent", "context": "."}
    ]
    
    try:
        # Check if docker is available
        subprocess.run(["docker", "version"], capture_output=True, check=True)
        
        for image in images:
            image_name = f"{registry}/{image['name']}:{tag}"
            dockerfile_path = docker_dir / image["dockerfile"]
            
            if dockerfile_path.exists():
                print_info(f"Building {image_name}...")
                
                cmd = [
                    "docker", "build",
                    "-f", str(dockerfile_path),
                    "-t", image_name,
                    image["context"]
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_success(f"✅ {image_name} built successfully")
                    
                    if push:
                        print_info(f"Pushing {image_name}...")
                        push_result = subprocess.run(
                            ["docker", "push", image_name],
                            capture_output=True, text=True
                        )
                        
                        if push_result.returncode == 0:
                            print_success(f"✅ {image_name} pushed successfully")
                        else:
                            print_error(f"❌ Failed to push {image_name}")
                            console.print(push_result.stderr, style="red")
                            
                else:
                    print_error(f"❌ Failed to build {image_name}")
                    console.print(result.stderr, style="red")
            else:
                print_warning(f"⚠️ {dockerfile_path} not found, skipping")
        
        print_success("\n🎉 Docker image building completed!")
        
    except subprocess.CalledProcessError:
        print_error("Docker not found or not working. Please install Docker.")
    except Exception as e:
        print_error(f"Docker build failed: {e}")

@deploy.command()
@click.option('--namespace', default='exostack', help='Kubernetes namespace')
def status(namespace: str):
    """Check deployment status."""
    import subprocess
    
    print_info(f"Checking ExoStack deployment status in namespace: {namespace}")
    
    try:
        # Check if kubectl is available
        subprocess.run(["kubectl", "version", "--client"], 
                      capture_output=True, check=True)
        
        # Get pods
        result = subprocess.run([
            "kubectl", "get", "pods", "-n", namespace,
            "-o", "wide"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("\n[bold]Pods:[/bold]")
            console.print(result.stdout)
        
        # Get services
        result = subprocess.run([
            "kubectl", "get", "services", "-n", namespace
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("\n[bold]Services:[/bold]")
            console.print(result.stdout)
        
        # Get deployments
        result = subprocess.run([
            "kubectl", "get", "deployments", "-n", namespace
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("\n[bold]Deployments:[/bold]")
            console.print(result.stdout)
        
    except subprocess.CalledProcessError:
        print_error("kubectl not found or not working. Please install kubectl and configure cluster access.")
    except Exception as e:
        print_error(f"Failed to get status: {e}")

@deploy.command()
@click.option('--namespace', default='exostack', help='Kubernetes namespace')
@click.confirmation_option(prompt='Are you sure you want to destroy the ExoStack deployment?')
def destroy(namespace: str):
    """Destroy ExoStack deployment."""
    import subprocess
    
    print_warning(f"Destroying ExoStack deployment in namespace: {namespace}")
    
    try:
        # Delete namespace (this will delete everything in it)
        result = subprocess.run([
            "kubectl", "delete", "namespace", namespace
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_success(f"✅ Namespace {namespace} deleted successfully")
        else:
            print_error(f"❌ Failed to delete namespace {namespace}")
            console.print(result.stderr, style="red")
            
    except Exception as e:
        print_error(f"Failed to destroy deployment: {e}")

if __name__ == "__main__":
    cli()
