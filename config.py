import os
from dataclasses import dataclass

# Create .env file with these variables:
# BOT_TOKEN=your_bot_token_here
# DATABASE_URL=sqlite:///recipe_bot.db
# ADMIN_IDS=123456789,987654321
# ALLOWED_USERS=123456789,987654321

@dataclass
class Config:
   BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
   DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///recipe_bot.db")
   ADMIN_IDS: list = None
   ALLOWED_USERS: list = None

   def __post_init__(self):
       if self.ADMIN_IDS is None:
           admin_ids_str = os.getenv("ADMIN_IDS", "")
           self.ADMIN_IDS = [int(id_) for id_ in admin_ids_str.split(",")
                             if id_.strip().isdigit()]\
                             if admin_ids_str\
               else []

       if self.ALLOWED_USERS is None:
           allowed_users_str = os.getenv("ALLOWED_USERS", "")
           self.ALLOWED_USERS = [int(id_) for id_ in allowed_users_str.split(",")
                                 if id_.strip().isdigit()] if allowed_users_str else []

       if not self.BOT_TOKEN:
           raise ValueError("BOT_TOKEN is required")

config = Config()
