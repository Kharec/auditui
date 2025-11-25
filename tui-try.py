from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, DataTable


class AudituiApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("s", "sort", "Sort by title"),
        ("r", "reverse_sort", "Reverse sort"),
        ("q", "quit", "Quit application")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        table = DataTable()
        table.zebra_stripes = True
        table.cursor_type = "row"
        yield table
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Title", "Author", "Length", "Progress")

        sample_books = [
            ("The Great Gatsby", "F. Scott Fitzgerald", "4h 30m", "100%"),
            ("1984", "George Orwell", "11h 25m", "75%"),
            ("To Kill a Mockingbird", "Harper Lee", "12h 17m", "50%"),
            ("Pride and Prejudice", "Jane Austen", "11h 35m", "0%"),
            ("The Catcher in the Rye", "J.D. Salinger", "7h 20m", "25%"),
            ("Lord of the Flies", "William Golding", "6h 35m", "100%"),
            ("Animal Farm", "George Orwell", "3h 15m", "90%"),
            ("Brave New World", "Aldous Huxley", "10h 45m", "60%"),
        ]

        for title, author, length, progress in sample_books:
            table.add_row(title, author, length, progress, key=title)

    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_sort(self) -> None:
        table = self.query_one(DataTable)
        table.sort("Title")

    def action_reverse_sort(self) -> None:
        table = self.query_one(DataTable)
        table.sort("Title", reverse=True)


if __name__ == "__main__":
    app = AudituiApp()
    app.run()
