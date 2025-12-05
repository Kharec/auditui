# auditui

A terminal-based user interface (TUI) client for Audible, written in Python 3.

Listen to your audiobooks or podcasts, browse your library, and more.

## What it does and where are we

`main.py` offers a TUI interface for browsing your Audible library, listing your books with progress information. You can sort by progress or title, show all books, or show only unfinished books which is the default.

Now, I'm working on the "play" feature, which should allow you to play/pause/unpause a book from the terminal by pressing `Space` on a book in the list.

Then, the next thing to add is a progress bar at the bottom of the interface, to show the progress of the book while it's playing.

Look at the [roadmap](#roadmap) for more details.

It's still a work in progress, so :

- currently, most code resides in `main.py`, except for some experimental files that aren't part of the final structure:
  - `player.py` is the test playground for the download and play functionality
  - `stats.py` is the test playground for the stats functionality
- expect bugs and missing features
- the code is not yet organized as I'm currently experimenting

## How to run

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# install dependencies (creates .venv)
$ uv sync

# run the TUI
$ uv run main.py # or player.py or stats.py
```

Please also note that as of now, you need to have [ffmpeg](https://ffmpeg.org/) installed to play audio files.

## Roadmap

- [x] list your library
- [x] list your unfinished books with progress information
- [ ] play/pause a book
- [ ] resume playback of a book from the last position, regardless of which device was used previously
- [ ] save the current playback position when pausing or exiting the app
- [ ] print progress at the bottom of the app while a book is playing
- [ ] add control to go to the previous/next chapter
- [ ] add a control to jump 30s earlier/later
- [ ] mark a book as finished or unfinished
- [ ] search the marketplace for books
- [ ] add a book in your wishlist
- [ ] get your listening stats from Audible

All of this, and of course:

- [ ] build a decent TUI interface using [Textual](https://textual.textualize.io/)
- [ ] code cleanup / organization

## Auth / credentials

Login is handled and credentials are stored in `~/.config/auditui/auth.json`.

OTP is supported if you use a two-factor authentication device.

## License

This project is licensed under the GPLv3+ License. See the [LICENSE](LICENSE) file for details.
