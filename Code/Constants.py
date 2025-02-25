'''
This file contains constants used by the GRPC Database Manager
'''

from pathlib import Path

PASSWORD_DATABASE = Path(__file__).parent / "User_Data/passwords.db"
MESSAGES_DATABASE = Path(__file__).parent / "User_Data/messages.db"
PASSWORD_DATABASE_SCHEMA = "Passwords (Username TEXT PRIMARY KEY, Password TEXT NOT NULL)"
MESSAGES_DATABASE_SCHEMA = ("Messages (Id INTEGER PRIMARY KEY AUTOINCREMENT, Sender TEXT NOT NULL, " +
                            "Recipient TEXT NOT NULL, Time_sent TEXT NOT NULL, Read BOOLEAN NOT NULL DEFAULT 0, " + 
                            "Subject TEXT, Body TEXT)")