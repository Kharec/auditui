# auditui

A terminal-based user interface (TUI) client for Audible, written in Python 3.

Listen to your audiobooks or podcasts, browse your library, search for new titles, add them to your wishlist, and more.

## What it does

For now, it can:

- [x] list your entire library
- [x] list your unfinished books with progress information
- [ ] play a book (start when it was last paused, mark the position when it's paused)
- [ ] mark a book as finished
- [ ] mark a book as unfinished
- [ ] search for new titles
- [ ] add a book to your wishlist

Login is handled and credentials are stored in `~/.config/auditui/auth.json`.

OTP is supported if you use a two-factor authentication device.

## License

GNU General Public License v3.0
