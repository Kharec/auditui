# auditui

A terminal-based user interface (TUI) client for Audible, written in Python 3.

Listen to your audiobooks or podcasts, browse your library, search for new titles, add them to your wishlist, and more.

## What it does

For now, it can:

- [x] list your entire library
- [x] list your unfinished books with progress information
- [ ] play a book (start when it was last paused, mark the position when it's paused)
- [ ] open a pdf if one's attached to the book
- [ ] mark a book as finished
- [ ] mark a book as unfinished
- [ ] search for new titles
- [ ] add a book to your wishlist

Once it'll do all of this (more or less), I'll think of a better code structure and the TUI interface.

I'm still experimenting the `audible` library and its API.

## Credentials

Login is handled and credentials are stored in `~/.config/auditui/auth.json`.

OTP is supported if you use a two-factor authentication device.

## License

This project is licensed under the GPLv3+ License. See the [LICENSE](LICENSE) file for details.
