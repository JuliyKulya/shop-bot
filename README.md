# 🍽️ Recipe Bot

A powerful Telegram bot for managing recipes and creating smart shopping lists. Transform your meal planning experience with automated shopping list generation and intelligent recipe management.

## ✨ Features

### 🧾 Recipe Management
- **Create Recipes** - Add detailed recipes with ingredients and quantities
- **Edit & Update** - Modify existing recipes anytime
- **Smart Categories** - Organize ingredients by customizable categories
- **Recipe Library** - Browse and manage your complete recipe collection

### 🛒 Smart Shopping Lists  
- **Auto-Generation** - Create shopping lists from selected recipes
- **Menu Planning** - Select multiple recipes for weekly meal planning
- **Quantity Scaling** - Adjust portions for different group sizes
- **Additional Products** - Add extra items to your shopping list
- **Progress Tracking** - Mark items as purchased while shopping

### 🔒 Access Control
- **User Restrictions** - Control who can access your bot
- **Admin Features** - Special privileges for designated admins
- **Secure Configuration** - Environment-based security settings

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/recipe-bot.git
   cd recipe-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start the bot**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Required: Your Telegram Bot Token
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Database Configuration
DATABASE_URL=sqlite:///recipe_bot.db

# Access Control (comma-separated user IDs)
ADMIN_IDS=123456789,987654321
ALLOWED_USERS=123456789,987654321,555666777
```

### Getting User IDs
1. Start a chat with [@userinfobot](https://t.me/userinfobot)
2. Send any message to get your user ID
3. Add the ID to your `ALLOWED_USERS` list

## 🎯 How to Use

1. **Start the bot** - Send `/start` to initialize
2. **Create recipes** - Add your favorite recipes with ingredients
3. **Plan meals** - Select recipes for your weekly menu
4. **Generate lists** - Create smart shopping lists automatically
5. **Shop smart** - Use the organized list while shopping

## 📋 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and show main menu |

## 🏗️ Architecture

```
recipe-bot/
├── 📁 Core Files
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   └── models.py            # Database models
├── 📁 Database
│   └── database.py          # Database operations
├── 📁 Handlers
│   ├── handlers.py          # Main bot logic
│   ├── additional_handlers.py # Recipe management
│   ├── products_handlers.py   # Product management
│   └── saved_data_handlers.py # Data viewing
├── 📁 Interface
│   ├── keyboards.py         # Telegram keyboards
│   └── states.py           # FSM state management
└── 📁 Security
    └── access_middleware.py # Access control
```

## 💾 Database Schema

The bot uses SQLite with optimized schema:

- **Categories** - Product organization system
- **Products** - Comprehensive ingredient database  
- **Recipes** - User recipe storage with relationships
- **Shopping Lists** - Active shopping list management
- **Selected Recipes** - Temporary menu planning storage

## 🛡️ Security Features

- **Environment Variables** - All sensitive data externalized
- **Access Control Middleware** - User permission system
- **SQL Injection Prevention** - SQLAlchemy ORM protection
- **No Hardcoded Secrets** - GitHub-safe configuration

## 🔧 Development

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py
```

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 🤝 Support

- **Issues** - Report bugs via [GitHub Issues](https://github.com/yourusername/recipe-bot/issues)
- **Discussions** - Join conversations in [Discussions](https://github.com/yourusername/recipe-bot/discussions)


