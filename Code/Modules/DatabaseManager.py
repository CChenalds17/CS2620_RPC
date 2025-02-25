'''
This file contains the DatabaseManager Class, which is used by the Database_process 
to query and update the messages.db and passwords.db files
'''

import sqlite3
import atexit
import signal
import sys

from Modules.Flags import Request, Status
from Modules.DataObjects import DataObject, MessageObject
from Modules.Constants import PASSWORD_DATABASE, MESSAGES_DATABASE, PASSWORD_DATABASE_SCHEMA, MESSAGES_DATABASE_SCHEMA

class DatabaseManager:
    def __init__(self):
        self.passwords = sqlite3.connect(PASSWORD_DATABASE)
        self.passwords_cursor = self.passwords.cursor()
        self.passwords_cursor.execute(f"CREATE TABLE IF NOT EXISTS {PASSWORD_DATABASE_SCHEMA}")
        self.passwords.commit()

        self.messages = sqlite3.connect(MESSAGES_DATABASE)
        self.messages_cursor = self.messages.cursor()
        self.messages_cursor.execute(f"CREATE TABLE IF NOT EXISTS {MESSAGES_DATABASE_SCHEMA}")
        self.messages.commit()

        # Handle kills and interupts by closing
        atexit.register(self.close)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    # various handlers for supporting instantiation and deletion, particularly under adverse circumstances
    def close(self):
        self.passwords.close()
        self.messages.close()
            
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()
    
    def _signal_handler(self, signum, frame):
        self.close()
        sys.exit(0) 

    # Modularized functionalities that are needed to maintain and update the database info
    def insert_user(self, username : str, password : str) -> Status:
        if not username or not password:
            return Status.ERROR
        try:
            self.passwords_cursor.execute("INSERT INTO Passwords (Username, Password) VALUES (?, ?)", (username, password))
            self.passwords.commit()
            return Status.SUCCESS
        except sqlite3.IntegrityError:
            return Status.MATCH
    
    def delete_user(self, username: str) -> Status:
        if not username:
            return Status.ERROR
        self.messages_cursor.execute("UPDATE Messages SET Recipient = Sender, Subject = 'NOT SENT ' || Subject WHERE Recipient = ? AND Read = 0;", (username,))
        self.messages_cursor.execute("DELETE FROM Messages WHERE Recipient = ?", (username,))
        self.messages.commit()
        self.passwords_cursor.execute("DELETE FROM Passwords WHERE Username = ?", (username,))
        if self.passwords_cursor.rowcount == 0:
            return Status.ERROR
        self.passwords.commit()
        return Status.SUCCESS
    
    def get_password(self, username : str) -> tuple[Status, str]:
        if not username:
            return (Status.ERROR, None)
        self.passwords_cursor.execute("SELECT Password FROM Passwords WHERE Username = ?", (username,))
        result = self.passwords_cursor.fetchone()
        return (Status.MATCH, result[0]) if result else (Status.NO_MATCH, None)
    
    def get_users(self, command : str, search : str = None) -> tuple[Status, list[str]]:
        if command == "All":
            self.passwords_cursor.execute("SELECT Username FROM Passwords")
            result = self.passwords_cursor.fetchall()
        elif command == "Like":
            self.passwords_cursor.execute("SELECT Username FROM Passwords WHERE Username Like ?", (search, ))
            result = self.passwords_cursor.fetchall()
        else:
            return (Status.ERROR, None)
        final_result = [username[0] for username in result]
        print(final_result)
        return (Status.SUCCESS, final_result)
    
    def insert_message(self, message : MessageObject) -> tuple[Status, int]:
        try:
            self.messages_cursor.execute(
                "INSERT INTO Messages (Sender, Recipient, Time_sent, Read, Subject, Body) VALUES (?, ?, ?, ?, ?, ?)",
                (message.sender, message.recipient, message.time_sent, int(message.read), message.subject, message.body)
            )
            id = self.messages_cursor.lastrowid
            self.messages.commit()
            return (Status.SUCCESS, id)
        except sqlite3.IntegrityError:
            return (Status.ERROR, 0)
    
    def delete_message(self, ids: list[str]) -> Status:
        if len(ids) == 0:
            return Status.ERROR
        format = ','.join('?' for _ in ids)
        values = []
        for id in ids:
            values.append(int(id))
        self.messages_cursor.execute(f"DELETE FROM Messages WHERE Id IN ({format})", values)
        self.messages.commit()
        return Status.SUCCESS
    
    def get_message(self, username : str, offset : int, limit : int, unread_only : bool) -> tuple[Status, list[MessageObject]]:
        if unread_only:
            self.messages_cursor.execute(
                "SELECT * FROM Messages WHERE Recipient = ? AND Read = 0 ORDER BY Time_sent DESC LIMIT ? OFFSET ?;",
                (username, limit, offset)
            )
        else:
            self.messages_cursor.execute(
                "SELECT * FROM Messages WHERE Recipient = ? ORDER BY Time_sent DESC LIMIT ? OFFSET ?;",
                (username, limit, offset)
            )
        result = self.messages_cursor.fetchall()
        return (Status.SUCCESS, result)

    def confirm_read(self, username : str, ids : list[str]) -> Status:
        if len(ids) == 0:
            return Status.ERROR
        format = ','.join('?' for _ in ids)
        values = [username]
        for id in ids:
            values.append(int(id))
        self.messages_cursor.execute(f"UPDATE Messages SET Read = 1 WHERE Recipient = ? AND Id IN ({format})", values)
        self.messages.commit()
        return Status.SUCCESS

    def get_message_counts(self, username : str) -> tuple[Status, int, int]:
        self.messages_cursor.execute(
            "SELECT COUNT(*) FROM Messages WHERE Recipient = ? AND Read = 0;", (username,))
        unread = self.messages_cursor.fetchone()[0]
        self.messages_cursor.execute(
            "SELECT COUNT(*) FROM Messages WHERE Recipient = ?", (username,))
        total = self.messages_cursor.fetchone()[0]
        return (Status.SUCCESS, unread, total)

    # Overall handler that parses DataObject requests and calls the appropriate functionality
    def handler(self, request : DataObject) -> tuple[Status, str]:
        print(f"Handler Recieved {request.to_string()}")
        try:
            match request.request:
                case Request.CHECK_USERNAME:
                    status, true_password = self.get_password(request.data[0])
                    request.update(status=status)
                case Request.CHECK_PASSWORD:
                    username, password = request.data[0], request.data[1]
                    status, true_password = self.get_password(username)
                    if status == Status.MATCH:
                        if password == true_password:
                            request.update(status=Status.MATCH, datalen=1, data=[username])
                        else:
                            request.update(status=Status.NO_MATCH, datalen=1, data=[username])
                    else:
                        request.update(status=Status.ERROR, datalen=0, data=[])
                case Request.CREATE_USER:
                    username, password = request.data[0], request.data[1]
                    status, _password = self.get_password(username)
                    if status == Status.SUCCESS:
                        request.update(status=Status.MATCH, datalen=0, data=[])
                        return request
                    status = self.insert_user(request.data[0], request.data[1])
                    request.update(status=status, datalen=0, data=[])
                case Request.DELETE_USER:
                    status = self.delete_user(request.user)
                    request.update(status=status)
                case Request.GET_USERS:
                    command = request.data[0]
                    usernames = []
                    if command == "All":
                        status, usernames = self.get_users("All")
                        request.update(status=status, datalen=len(usernames), data=usernames)
                    elif command == "Like":
                        status, usernames = self.get_users("Like", request.data[1])
                        request.update(status=status, datalen=len(usernames), data=usernames)
                    else:
                        request.update(status=Status.ERROR, datalen=0, data=[])
                case Request.SEND_MESSAGE:
                    message = MessageObject(method="serial", serial = request.data[0].encode("utf-8"))
                    recipient = message.recipient
                    status, _password = self.get_password(recipient)
                    if status == Status.NO_MATCH:
                        request.update(status=Status.NO_MATCH)
                    else:
                        status, id = self.insert_message(message)
                        message.update(id=id)
                        request.update(status=status, data=[message.serialize().decode("utf-8")])
                        print(request.to_string())
                case Request.DELETE_MESSAGE:
                    status = self.delete_message(request.data)
                    request.update(status=status)
                case Request.GET_MESSAGE:
                    message_list = []
                    if request.datalen == 3 and request.data[2] == "Unread":
                        status, raw_list = self.get_message(request.user, int(request.data[0]), int(request.data[1]), True)
                    else:
                        status, raw_list = self.get_message(request.user, int(request.data[0]), int(request.data[1]), False)
                    print(raw_list)
                    for item in raw_list:
                        message_list.append(MessageObject(method='tuple', tuple=item).serialize().decode("utf-8"))
                    request.update(status=Status.SUCCESS, datalen = len(message_list), data=message_list)
                case Request.CONFIRM_READ:
                    status = self.confirm_read(request.user, request.data)
                    request.update(status=status)
                case Request.CONFIRM_LOGIN:
                    status, unread, total = self.get_message_counts(request.user)
                    request.update(status=status, datalen=2, data=[str(unread), str(total)])
                case _:
                    request.update(status=Status.ERROR, datalen=0, data=[])
            print(self.output())
            return request
        except Exception as e:
            print(f"Database Encountered Error {e}")
            request.update(status=Status.ERROR)
    

    # The below functionalities are useful for debugging and testing purposes
    def empty_table(self) -> Status:
        try:
            self.passwords_cursor.execute("DELETE FROM Passwords")
            self.passwords.commit()
            self.messages_cursor.execute("DELETE FROM Messages")
            self.messages.commit()
            return Status.SUCCESS
        except sqlite3.Error:
            return Status.ERROR
    
    def output(self) -> list[list[any]]:
        try:
            self.passwords_cursor.execute("SELECT * FROM Passwords")
            self.messages_cursor.execute("SELECT * FROM Messages")
        except sqlite3.OperationalError:
            return Status.ERROR
        rows_passwords = self.passwords_cursor.fetchall()
        rows_messages = self.messages_cursor.fetchall()
        return [rows_passwords, rows_messages]

