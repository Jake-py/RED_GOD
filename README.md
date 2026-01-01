# OSINT Telegram Bot

A comprehensive OSINT (Open Source Intelligence) Telegram bot that allows users to gather information from various public sources in a legal and ethical manner.

## 🌟 Features

- **Multi-source OSINT gathering**
- **Modular architecture**
- **Rate limiting**
- **Caching**
- **Comprehensive logging**
- **User-friendly interface**

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd RED_GOD
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot**
   - Copy `.env.example` to `.env`
   - Edit `.env` with your configuration:
     ```
     BOT_TOKEN=your_telegram_bot_token_here
     ADMIN_IDS=[123456789]  # Your Telegram user ID
     ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## 🛠️ Available Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show help message
- `/osint` - Show OSINT tools menu
  - 👤 Person - Search by name
  - 🌐 Username - Search by username
  - 📱 Phone - Analyze phone number
  - 📧 Email - Analyze email
  - 🌍 Domain/IP - Analyze domain or IP address

## 📂 Project Structure

```
RED_GOD/
├── config/               # Configuration files
├── data/                 # Data storage
│   ├── cache/            # Cached data
│   └── logs/             # Log files
├── src/                  # Source code
│   ├── core/             # Core bot functionality
│   ├── modules/          # OSINT modules
│   └── utils/            # Utility functions
├── .env                  # Environment variables
├── main.py               # Entry point
└── requirements.txt      # Python dependencies
```

## ⚠️ Legal Notice

This tool is intended for legal and ethical use only. Users are responsible for ensuring they have proper authorization before conducting any OSINT activities. The developers are not responsible for any misuse of this tool.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
