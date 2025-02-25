import time
from concurrent import futures
import queue
import sqlite3
import atexit
import signal
import sys

import grpc
import chat_pb2
import chat_pb2_grpc
from Constants import PASSWORD_DATABASE, MESSAGES_DATABASE, PASSWORD_DATABASE_SCHEMA, MESSAGES_DATABASE_SCHEMA

class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        self.online_username = {}

        self.passwords = sqlite3.connect(PASSWORD_DATABASE, check_same_thread=False)
        self.passwords_cursor = self.passwords.cursor()
        self.passwords_cursor.execute(f"CREATE TABLE IF NOT EXISTS {PASSWORD_DATABASE_SCHEMA}")
        self.passwords.commit()

        self.messages = sqlite3.connect(MESSAGES_DATABASE, check_same_thread=False)
        self.messages_cursor = self.messages.cursor()
        self.messages_cursor.execute(f"CREATE TABLE IF NOT EXISTS {MESSAGES_DATABASE_SCHEMA}")
        self.messages.commit()

        # Handle kills and interupts by closing
        atexit.register(self.close)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def close(self):
        self.passwords.close()
        self.messages.close()

    def _signal_handler(self, signum, frame):
        self.close()
        sys.exit(0) 

    # User Account Management
    
    def CheckUsername(self, request, context):
        print(f"Checking Username given {request}")
        if not request.username:
            return chat_pb2.CheckUsernameResponse(status=chat_pb2.Status.ERROR)
        self.passwords_cursor.execute("SELECT Username FROM Passwords WHERE Username = ?", (request.username,))
        result = self.passwords_cursor.fetchone()
        status = chat_pb2.Status.MATCH if result else chat_pb2.Status.NO_MATCH
        return chat_pb2.CheckUsernameResponse(status=status)

    def CheckPassword(self, request, context):
        print(f"Checking Password given {request}")
        if not request.username or not request.password:
            return chat_pb2.CheckPasswordResponse(status=chat_pb2.Status.ERROR)
        self.passwords_cursor.execute("SELECT Password FROM Passwords WHERE Username = ?", (request.username,))
        result = self.passwords_cursor.fetchone()
        print(f"Got: {result}")
        status = chat_pb2.Status.MATCH if (str(result[0]) == str(request.password)) else chat_pb2.Status.NO_MATCH
        return chat_pb2.CheckPasswordResponse(status=status)

    def CreateUser(self, request, context):
        print(f"Creating user given {request}")
        if not request.username or not request.password:
            return chat_pb2.CreateUserResponse(status=chat_pb2.Status.ERROR)
        try:
            self.passwords_cursor.execute("INSERT INTO Passwords (Username, Password) VALUES (?, ?)", (request.username, request.password))
            self.passwords.commit()
            return chat_pb2.CreateUserResponse(status=chat_pb2.Status.SUCCESS)
        except sqlite3.IntegrityError:
            return chat_pb2.CreateUserResponse(status=chat_pb2.Status.MATCH)

    def ConfirmLogin(self, request, context):
        print(f"Confirming Login given {request}")
        if not request.username:
            return chat_pb2.ConfirmLoginResponse(
            status=chat_pb2.Status.ERROR, 
            num_unread_msgs=0, 
            num_total_msgs=0)
        elif request.username in self.online_username:
            return chat_pb2.ConfirmLoginResponse(
            status=chat_pb2.Status.MATCH, 
            num_unread_msgs=0, 
            num_total_msgs=0)
        else:
            self.online_username[request.username] = queue.Queue()

            self.messages_cursor.execute(
            "SELECT COUNT(*) FROM Messages WHERE Recipient = ? AND Read = 0;", (request.username,))
            unread = self.messages_cursor.fetchone()[0]
            self.messages_cursor.execute(
                "SELECT COUNT(*) FROM Messages WHERE Recipient = ?", (request.username,))
            total = self.messages_cursor.fetchone()[0]
            return chat_pb2.ConfirmLoginResponse(
                status=chat_pb2.Status.SUCCESS, 
                num_unread_msgs=unread, 
                num_total_msgs=total
            )

    def ConfirmLogout(self, request, context):
        print(f"Confirming Logout given {request}")
        if request.username in self.online_username:
            del self.online_username[request.username]
        return chat_pb2.ConfirmLogoutResponse(status=chat_pb2.Status.SUCCESS)

    def GetOnlineUsers(self, request, context):
        print(f"Getting Online Users")
        return chat_pb2.GetOnlineUsersResponse(status=chat_pb2.Status.SUCCESS, users=list(self.online_username.keys()))

    def GetUsers(self, request, context):
        print(f"Getting Users given {request}")
        self.passwords_cursor.execute("SELECT Username FROM Passwords WHERE Username Like ?", (request.query, ))
        result = self.passwords_cursor.fetchall()
        final_result = [username[0] for username in result]
        return chat_pb2.GetUsersResponse(status=chat_pb2.Status.SUCCESS, users=final_result)
    
    # Messages

    def SendMessage(self, request, context):
        print(f"Sending Message given {request}")
        self.passwords_cursor.execute("SELECT Username FROM Passwords WHERE Username = ?", (request.message.recipient,))
        result = self.passwords_cursor.fetchall()
        if not result:
            return chat_pb2.SendMessageResponse(status=chat_pb2.Status.NO_MATCH)
        try:
            self.messages_cursor.execute(
                "INSERT INTO Messages (Sender, Recipient, Time_sent, Read, Subject, Body) VALUES (?, ?, ?, ?, ?, ?)",
                (request.message.sender, request.message.recipient, request.message.time_sent, 
                 int(request.message.read), request.message.subject, request.message.body)
            )
            request.message.id = self.messages_cursor.lastrowid
            self.messages.commit()
            if request.message.recipient in self.online_username:
                self.online_username[request.message.recipient].put(request.message)
            return chat_pb2.SendMessageResponse(status=chat_pb2.Status.SUCCESS)
        except sqlite3.IntegrityError:
            return chat_pb2.SendMessageResponse(status=chat_pb2.Status.ERROR)

    def GetMessage(self, request, context):
        print(f"Getting Message given {request}")
        if request.unread_only:
            self.messages_cursor.execute(
                "SELECT * FROM Messages WHERE Recipient = ? AND Read = 0 ORDER BY Time_sent DESC LIMIT ? OFFSET ?;",
                (request.username, request.limit, request.offset)
            )
        else:
            self.messages_cursor.execute(
                "SELECT * FROM Messages WHERE Recipient = ? ORDER BY Time_sent DESC LIMIT ? OFFSET ?;",
                (request.username, request.limit, request.offset)
            )
        result = self.messages_cursor.fetchall()
        messages = []
        for tuple in result:
            messages.append(chat_pb2.MessageObject(
            id = int(tuple[0]),
            sender = tuple[1],
            recipient = tuple[2],
            time_sent = tuple[3],
            read = bool(tuple[4]),
            subject = tuple[5],
            body = tuple[6]))
        return chat_pb2.GetMessageResponse(status=chat_pb2.Status.SUCCESS, messages=messages)

    def ConfirmRead(self, request, context):
        print(f"Confirming Read given {request}")
        if not request.username or not request.message_id:
            return chat_pb2.ConfirmReadResponse(status=chat_pb2.Status.ERROR)
        self.messages_cursor.execute(f"UPDATE Messages SET Read = 1 WHERE Recipient = ? AND Id = ?", (request.username, request.message_id,))
        self.messages.commit()
        return chat_pb2.ConfirmReadResponse(status=chat_pb2.Status.SUCCESS)

    def DeleteMessage(self, request, context):
        print(f"Deleting Message given {request}")
        if len(request.message_id) == 0:
            return chat_pb2.DeleteMessageResponse(status=chat_pb2.Status.ERROR)
        format = ','.join('?' for _ in request.message_id)
        values = []
        for id in request.message_id:
            values.append(int(id))
        self.messages_cursor.execute(f"DELETE FROM Messages WHERE Id IN ({format})", values)
        self.messages.commit()
        return chat_pb2.DeleteMessageResponse(status=chat_pb2.Status.SUCCESS)

    def DeleteUser(self, request, context):
        print(f"Deleting User given {request}")
        if not request.username:
            return chat_pb2.DeleteUserResponse(status=chat_pb2.Status.ERROR)
        self.messages_cursor.execute("UPDATE Messages SET Recipient = Sender, Subject = 'NOT SENT ' || Subject WHERE Recipient = ? AND Read = 0;", (request.username,))
        self.messages_cursor.execute("DELETE FROM Messages WHERE Recipient = ?", (request.username,))
        self.messages.commit()
        self.passwords_cursor.execute("DELETE FROM Passwords WHERE Username = ?", (request.username,))
        if self.passwords_cursor.rowcount == 0:
            return chat_pb2.DeleteUserResponse(status=chat_pb2.Status.ERROR)
        self.passwords.commit()
        return chat_pb2.DeleteUserResponse(status=chat_pb2.Status.SUCCESS)

if __name__ == '__main__':
     # Confirm validity of commandline arguments
    if len(sys.argv) != 3:
        print("Usage: python server.py HOSTNAME DATABASE_PORTNAME")
        sys.exit(1)
    host, port = sys.argv[1], sys.argv[2]

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServiceServicer(), server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    print(f"gRPC Server started on {host}:{port}")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)