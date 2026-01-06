# auditui

A terminal-based user interface (TUI) client for [Audible](https://www.audible.fr/), written in Python 3.

Currently, the only available theme is Catppuccin Mocha, following their [style guide](https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md), as it's my preferred theme across most of my tools.

## Requirements

- [Python](https://www.python.org/) 3.10-3.12 (3.13+ is not yet supported by `audible` module)
- [ffmpeg](https://ffmpeg.org/) installed to play audio files.

## Features

- **Browse your library**: View all your Audible audiobooks in a clean, terminal-based interface
- **Offline playback**: Download audiobooks to your local cache and listen without an internet connection
- **Playback controls**: Play, pause, seek, adjust playback speed, and navigate between chapters
- **Library management**: Filter your library, sort by name or progress, and mark books as finished
- **Progress tracking**: See your listening progress for each book and resume where you left off
- **Statistics**: View listening statistics and library overview
- **Keyboard-driven**: Fully navigable with keyboard shortcuts for efficient use
- **Two-factor authentication**: Supports OTP for secure login

## Installation

Use [`pipx`](https://pipx.pypa.io/latest/installation/) to install `auditui`:

```bash
pipx install git+https://git.kharec.info/Kharec/auditui.git
```

Check the version to ensure installation was successful:

```bash
auditui --version
```

All set, run `auditui configure` to set up authentication, and then `auditui` to start the TUI.

### Workaround for Python 3.13 linux distribution

On some Linux distributions, Python 3.13 is already the default. So you have to install Python 3.12 manually before using `pipx`.

For Arch Linux:

```bash
yay -S python312
```

Once you have Python 3.12, run:

```bash
pipx install git+https://git.kharec.info/Kharec/auditui.git --python python3.12
```

As Python <3.14 is supported on `master` branch of the upstream [`audible`](https://github.com/mkb79/Audible), this should be temporary until the next version.

## Upgrade

Assuming it's already installed, use `pipx` to upgrade auditui:

```bash
pipx upgrade auditui
```

## Keybindings

| Key          | Action                     |
| ------------ | -------------------------- |
| `/`          | Filter library             |
| `?`          | Show help screen           |
| `enter`      | Play the selected book     |
| `space`      | Pause/resume the playback  |
| `escape`     | Clear filter               |
| `ctrl+left`  | Go to the previous chapter |
| `ctrl+right` | Go to the next chapter     |
| `up`         | Increase playback speed    |
| `down`       | Decrease playback speed    |
| `left`       | Seek backward 30 seconds   |
| `right`      | Seek forward 30 seconds    |
| `a`          | Show all/unfinished        |
| `d`          | Toggle download/delete     |
| `f`          | Mark as finished           |
| `n`          | Sort by name               |
| `p`          | Sort by progress           |
| `q`          | Quit the application       |
| `r`          | Refresh view               |
| `s`          | Show stats screen          |

## Cache

Books are downloaded to `~/.cache/auditui/books`.

The `d` key toggles the download state for the selected book: if the book is not cached, pressing `d` will download it; if it's already cached, pressing `d` will delete it from the cache.

To check the total size of your cache:

```bash
du -sh ~/.cache/auditui/books
```

Or the size of individual books:

```bash
du -h ~/.cache/auditui/books/*
```

Clean all the cache (if necessary) with:

```bash
rm -rf ~/.cache/auditui/books/*
```

## Authentication / credentials

Login is handled and credentials are stored in `~/.config/auditui/auth.json`.

When running `auditui configure`, you will be prompted for:

- **Email**: Your Audible account email address
- **Password**: Your Audible account password (input is hidden)
- **Marketplace locale**: The regional marketplace you want to connect to (defaults to `US` if left empty)

The marketplace locale determines which Audible region you access, affecting available audiobooks in your library. Common marketplace codes include:

- `US` - United States (default)
- `UK` - United Kingdom
- `DE` - Germany
- `FR` - France
- `CA` - Canada
- `AU` - Australia
- `IT` - Italy
- `ES` - Spain
- `JP` - Japan

To change your marketplace after initial configuration, simply run `auditui configure` again and select a different locale when prompted. But you should probably just stick with the marketplace you used when you first created your Audible account.

OTP is supported if you use a two-factor authentication device.

## Hacking

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# install dependencies (creates .venv)
$ uv sync
# modify the code...
# ...and run the TUI
$ uv run python -m auditui.cli
```

## Testing

WIP.

## License

This project is licensed under the GPLv3+ License. See the [LICENSE](LICENSE) file for details.
