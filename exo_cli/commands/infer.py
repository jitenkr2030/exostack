import typer
app = typer.Typer()

@app.command()
def run():
    print("Running inference...")
