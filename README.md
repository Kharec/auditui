# auditui

A terminal-based user interface (TUI) client for Audible, written in Python 3.

Listen to your audiobooks or podcasts, browse your library, and more.

## What it does and where are we

The project offers a TUI interface for browsing your Audible library, listing your books with progress information. You can sort by progress or title, show all books, or show only unfinished books which is the default.

You can also play a book by pressing `Enter` on a book in the list, and pause/resume the playback by pressing `Space`. `Left` and `Right` let you move 30 seconds backward/forward.

Currently, the only available theme is Catppuccin Mocha, following their [style guide](https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md), as it's my preferred theme across most of my tools.

Look at the [roadmap](#roadmap) for more details.

It's still a work in progress, so expect bugs and missing features.

## How to run

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# install dependencies (creates .venv)
$ uv sync

# run the TUI
$ uv run main.py
```

(`stats.py` is a playground for the stats functionality)

Please also note that as of now, you need to have [ffmpeg](https://ffmpeg.org/) installed to play audio files.

## Roadmap

- [x] list your library
- [x] list your unfinished books with progress information
- [x] play/pause a book
- [x] catppuccin mocha theme
- [x] print chapter and progress in the footer of the app while a book is playing
- [x] chapter progress bar in footer
- [x] add a control to jump 30s earlier/later
- [x] add control to go to the previous/next chapter
- [ ] mark a book as finished or unfinished
- [ ] save/resume playback of a book from the last position, regardless of which device was used previously
- [ ] search the marketplace for books
- [ ] add a book in your wishlist
- [ ] get your listening stats from Audible
- [ ] add multiple themes and theme selector

All of this, and of course:

- [ ] build a decent TUI interface using [Textual](https://textual.textualize.io/)
- [ ] code cleanup / organization

## Auth / credentials

Login is handled and credentials are stored in `~/.config/auditui/auth.json`.

OTP is supported if you use a two-factor authentication device.

## License

This project is licensed under the GPLv3+ License. See the [LICENSE](LICENSE) file for details.
