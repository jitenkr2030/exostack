import typer
app = typer.Typer()

@app.command()
def agents():
    print("Listing agents...")
