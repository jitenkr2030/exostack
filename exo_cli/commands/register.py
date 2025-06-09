import typer
app = typer.Typer()

@app.command()
def agent(id: str):
    print(f"Registering agent {id}")
