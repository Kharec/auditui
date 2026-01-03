# auditui

A terminal-based user interface (TUI) client for Audible, written in Python 3 : listen to your audiobooks (even offline), browse and manage your library, and more!

Currently, the only available theme is Catppuccin Mocha, following their [style guide](https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md), as it's my preferred theme across most of my tools.

Look at the [roadmap](#roadmap) for more details.

It's still a work in progress, so expect bugs and missing features.

## How to run

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# install dependencies (creates .venv)
$ uv sync

# run the TUI
$ uv run python -m auditui.cli
```

(`stats.py` is a playground for the stats functionality)

Please also note that as of now, you need to have [ffmpeg](https://ffmpeg.org/) installed to play audio files.

### Bindings

| Key          | Action                      |
| ------------ | --------------------------- |
| `?`          | Show help screen            |
| `n`          | Sort by name                |
| `p`          | Sort by progress            |
| `a`          | Show all/unfinished         |
| `enter`      | Play the selected book      |
| `space`      | Pause/resume the playback   |
| `left`       | Seek backward 30 seconds    |
| `right`      | Seek forward 30 seconds     |
| `ctrl+left`  | Go to the previous chapter  |
| `ctrl+right` | Go to the next chapter      |
| `up`         | Increase playback speed     |
| `down`       | Decrease playback speed     |
| `f`          | Mark as finished/unfinished |
| `d`          | Download/delete from cache  |
| `q`          | Quit the application        |

## Roadmap

- [x] list your library
- [x] list your unfinished books with progress information
- [x] play/pause a book
- [x] catppuccin mocha theme
- [x] print chapter and progress in the footer of the app while a book is playing
- [x] chapter progress bar in footer
- [x] add a control to jump 30s earlier/later
- [x] add control to go to the previous/next chapter
- [x] save/resume playback of a book from the last position, regardless of which device was used previously
- [x] download/remove a book in the cache without having to play it
- [x] add a help screen with all the keybindings
- [x] increase/decrease reading speed
- [x] mark a book as finished or unfinished
- [x] make ui responsive
- [ ] get your stats in a separated pane
- [ ] filter books on views
- [ ] search in your book library
- [ ] search the marketplace for books
- [ ] add a book in your wishlist
- [ ] installation setup

## Auth / credentials

Login is handled and credentials are stored in `~/.config/auditui/auth.json`.

OTP is supported if you use a two-factor authentication device.

## License

This project is licensed under the GPLv3+ License. See the [LICENSE](LICENSE) file for details.
