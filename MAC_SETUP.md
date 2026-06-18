# PolarAs Mac Setup

This version is ready to run on macOS. It uses only the Python standard library, so there are no packages to install.

## Quick Start

1. Move the `PolarAs AI` folder to your Mac.
2. Open the folder.
3. Double-click `run_mac.command`.
4. The first time, it will create `.env` from `.env.example` and open it in TextEdit.
5. Replace `your_api_key_here` with your OpenAI API key.
6. Save `.env`.
7. Double-click `run_mac.command` again.
8. Open:

```text
http://127.0.0.1:8001
```

## If macOS Blocks The File

Open Terminal, drag the project folder into Terminal after typing `cd `, then run:

```bash
chmod +x run_mac.command
./run_mac.command
```

## Environment File

Your `.env` should look like this:

```text
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.4-mini
PORT=8001
```

Do not upload `.env` to GitHub. It contains your API key.

## Stop The Server

Press `Control + C` in the Terminal window running PolarAs.
