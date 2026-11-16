# TechApplications Telegram Bot

A role-based Telegram bot for reporting and tracking technical issues across
multiple restaurants. Managers submit requests, technicians process them, and
administrators manage users and review activity.

## Features

- Role-based access for administrators, managers, and technicians.
- Create issue reports for configured restaurants, with text and optional
  photos.
- Notify administrators and technicians about new reports.
- Let technicians accept, complete, or reject requests and track pending and
  in-progress work.
- Store request data in a local SQLite database and synchronize reports and
  status updates with Google Sheets through Google Apps Script.
- Provide administrator tools for user and role management, statistics, and
  spreadsheet exports.

## Requirements

- Python 3.10 or newer.
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- Redis, used for Telegram conversation state.
- A deployed Google Apps Script web app connected to the target spreadsheet.

## Getting started

1. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/QuietLoud1/TechApplications-Telegram-Bot.git
   cd TechApplications-Telegram-Bot
   python -m venv .venv
   ```

2. Activate the virtual environment and install dependencies:

   ```bash
   # macOS / Linux
   source .venv/bin/activate

   # Windows PowerShell
   .venv\Scripts\Activate.ps1

   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and replace example values with your
   configuration. In particular, set `BOT_TOKEN`, the role passwords,
   `GOOGLE_SCRIPT_URL`, and any storage or integration settings required by
   `config/config.py`. The Google Apps Script URL must be the deployed web app
   URL ending in `/exec`. Do not commit `.env` or put real credentials in source
   control.

4. Start Redis locally, then run the bot:

   ```bash
   python main.py
   ```

The bot creates its SQLite tables when it starts. Make sure the configured
database path is writable. Requests and status changes are also sent to the
configured Google Apps Script, so its deployment must be available and allow
the bot's requests.

## Configuration

See `.env.example` for the configuration template. `RESTAURANTS` is an optional,
comma-separated list; if omitted, the built-in default list is used:

```env
RESTAURANTS=Restaurant One,Restaurant Two
```

The configured names are used both in the bot's restaurant-selection menus and
when validating reports received through the Google integration.

## License

No license file is currently included in this repository.
