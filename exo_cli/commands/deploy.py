import typer
app = typer.Typer()

@app.command()
def model(name: str):
    print(f"Deploying model: {name}")
