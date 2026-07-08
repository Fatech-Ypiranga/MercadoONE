from rich.console import Console
from rich.prompt import Prompt
from rich.theme import Theme


CORE_THEME = Theme({
    "app.titulo": "bold #81A1C1",
    "app.subtitulo": "#81A1C1",
    "app.borda": "#4C566A",
    "app.texto": "#D8DEE9",
    "sucesso": "#A3BE8C",
    "aviso": "#EBCB8B",
    "erro": "#BF616A",
    "menu.numero": "bold #D8DEE9",
    "menu.texto": "#D8DEE9",
    "menu.atalho": "#D8DEE9",
    "dimmed": "#D8DEE9",
    "status.ok": "bold #A3BE8C",
})


console = Console(theme=CORE_THEME)


def pause_and_clear(message: str = "Pressione [bold]Enter[/bold] para continuar") -> None:
    Prompt.ask(message, default="", show_default=False)
    console.clear()