import typer
from .commands import register, infer, deploy, top

app = typer.Typer()
app.add_typer(register.app, name="register")
app.add_typer(infer.app, name="infer")
app.add_typer(deploy.app, name="deploy")
app.add_typer(top.app, name="top")

if __name__ == "__main__":
    app()
