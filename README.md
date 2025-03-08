# IPTV M3U Editor

This is a simple IPTV M3U playlist editor built with Python and PySide6. The application provides an easy-to-use graphical interface for editing and managing M3U playlists.

## Features

- Load and parse M3U playlist files
- Edit stream names and URLs
- Add or remove channels
- Save playlists back to M3U format
- Watchdog for real-time file monitoring

## Installation

### Prerequisites

Ensure you have the following installed:

- Python 3.x
- pip
- Virtual environment (optional but recommended)

### Setup

1. Clone this repository:
   ```sh
   https://github.com/chesko21/iptv_edit.git
   cd iptv_edit
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Running the Application

To start the IPTV M3U Editor, run:

```sh
python main.py
```

## Project Structure

```
├── __pycache__/         # Compiled Python files
├── .venv/               # Virtual environment
├── build/               # Build output (if using PyInstaller or Buildozer)
├── dist/                # Distribution files
├── icons/               # Icons and images
├── .gitignore           # Git ignore file
├── buildozer.spec       # Buildozer configuration (for mobile deployment)
├── editor_ui.py         # UI design and handling
├── main.py              # Main application entry point
├── main.spec            # PyInstaller spec file
├── menu.py              # Menu handling logic
├── requirements.txt     # Project dependencies
├── utils.py             # Utility functions
├── watchdog_runner.py   # File monitoring
```

## Packaging the Application

If you want to package the application into an executable:

```sh
pyinstaller --onefile --windowed main.py
```

or

```sh
pyinstaller --onefile --add-data "icons;icons" main.py
```


For mobile deployment using Buildozer:

```sh
buildozer -v android debug
```

## Contributing

Feel free to fork and contribute to this project by submitting pull requests.

## License

This project is licensed under the MIT License.
