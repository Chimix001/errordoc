# Python Error Doctor 🩺

Python Error Doctor is an AI-powered command-line tool that helps
developers identify Python errors, understand what went wrong, and get
suggested fixes. It can check Python syntax and optionally run a script
to detect runtime errors. When an error is found, it can use an LLM to
explain the issue and recommend a correction.

**Safety first:** Python Error Doctor suggests fixes; it does not
automatically overwrite your original source file. Use `--run` only with
code you trust, because it executes the target script.

## Screenshot

The screenshot below shows Python Error Doctor being used from a VS Code
terminal.

![Python Error Doctor running in the VS Code
<img width="867" height="454" alt="image" src="https://github.com/user-attachments/assets/1973c3e3-9820-4088-b3aa-77ebe7c38029" />

## Features

-   **Syntax checking** to catch invalid Python syntax.
-   **Optional runtime analysis** by executing a target script.
-   **AI-powered explanations and fix suggestions** through Groq, with
    Google Gemini configured as a fallback provider.
-   **Command-line workflow** that fits into a developer's terminal.
-   **Non-destructive suggestions** that leave the original source file
    unchanged.

> Runtime detection depends on executing the script. A script that runs
> successfully may still contain logical bugs that are not triggered by
> that run.

## Project structure

``` text
cli_tool/
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
├── example.py
└── src/
    └── errodoc/
        ├── __init__.py
        ├── main.py
        ├── error_analyzer.py
        └── llm.py
```

Your exact structure may differ slightly depending on how you organize
tests and documentation.

## Requirements

-   Python 3.10 or newer
-   `pip`
-   A Groq API key
-   A Google Gemini API key if you want to use the Gemini fallback

## Installation

### 1. Clone the repository

``` bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

Replace the URL with your GitHub repository URL.

### 2. Create and activate a virtual environment

**Windows PowerShell**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the project

From the folder containing `pyproject.toml`, run:

``` bash
python -m pip install -e .
```

This installs the CLI in editable mode, so changes to your source files
are available without reinstalling the package.

## Configuration

Create a local `.env` file in the project root. You can start by copying
`.env.example`:

**Windows PowerShell**

``` powershell
Copy-Item .env.example .env
```

**macOS / Linux**

``` bash
cp .env.example .env
```

Add your API keys to `.env`:

``` dotenv
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

Use your real keys only in `.env`. Never commit `.env` or publish API
keys to GitHub. Commit `.env.example` with empty values instead.

## Usage

### Show available commands

``` powershell
errodoc --help
```

### Check a Python file for syntax errors

``` powershell
errodoc example.py
```

This checks syntax without executing the target file. It does not detect
runtime errors in this mode.

### Check syntax and run the script

``` powershell
errodoc example.py --run
```

This executes `example.py`. If execution fails, the tool can report the
runtime error and, when configured, request an AI explanation and
suggested fix.

**Warning:** Only run code you trust. A Python script can read, modify,
or delete files, access environment variables, or perform network
operations using your current permissions.

### Try an example

Create `example.py`:

``` python
def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count


def main():
    values = [10, 20, 30, 40]
    print("Average:", calculate_average(values))
    print("Empty list average:", calculate_average([]))


if __name__ == "__main__":
    main()
```

Run syntax analysis:

``` powershell
errodoc example.py
```

Then run the script to trigger a `ZeroDivisionError`:

``` powershell
errodoc example.py --run
```

The example intentionally divides by zero when the list is empty. A
suitable fix is to handle empty input before dividing, for example:

``` python
def calculate_average(numbers):
    if not numbers:
        return None

    return sum(numbers) / len(numbers)
```

Python Error Doctor is intended to **suggest** a fix; review any
suggestion and apply changes yourself.

## Troubleshooting

### `errodoc` is not recognized

Make sure your virtual environment is activated and install the project
from the directory containing `pyproject.toml`:

``` powershell
python -m pip install -e .
```

Then try:

``` powershell
errodoc --help
```

### `ModuleNotFoundError`

Check that your package files are under `src/errodoc/`, that
`src/errodoc/__init__.py` exists, and that internal imports use the
package path, for example:

``` python
from errodoc.error_analyzer import analyze_file
```

### AI suggestions are unavailable

-   Confirm that `.env` exists in the project root and contains valid
    API keys.
-   Check that `llm.py` loads the same variable names: `GROQ_API_KEY`
    and `GEMINI_API_KEY`.
-   Check the provider's API limits and the error printed by the
    application.

### Runtime errors are not reported

Confirm the script really raises an error when run directly:

``` powershell
python example.py
```

Then compare that result with:

``` powershell
errodoc example.py --run
```

## Security and privacy

-   Keep `.env` out of version control.
-   Do not run untrusted scripts with `--run`.
-   Review AI-generated suggestions before applying them.
-   Do not send secrets, credentials, or private source code to an LLM
    provider unless you are comfortable with that provider's
    data-handling terms.

## Current limitations

-   Runtime analysis only observes errors triggered during that
    execution.
-   Passing syntax and runtime checks does not guarantee that code is
    logically correct.
-   AI suggestions can be incomplete or incorrect and should be
    reviewed.
-   The tool is an experimental developer utility, not a replacement for
    tests, code review, static analysis, or security review.

## Contributing

Contributions and suggestions are welcome. For changes, consider opening
an issue first, then submitting a pull request with a clear description
and relevant tests.

Built as an experimental Python developer tool using Python, Groq, and
Google Gemini.
