import time
import sys
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

    def close(self):
        self.passwords.close()
        self.messages.close()

    def _signal_handler(self, signum, frame):
        self.close()
        sys.exit(0) 

    # User Account Management
    
    def CheckUsername(self, request, context):
        if not request.username:
            return chat_pb2.CheckUsernameResponse(status=chat_pb2.Status.ERROR)
        self.passwords_cursor.execute("SELECT Username FROM Passwords WHERE Username = ?", (request.username,))
        result = self.passwords_cursor.fetchone()
        status = chat_pb2.Status.MATCH if result else chat_pb2.Status.NO_MATCH
        return chat_pb2.CheckUsernameResponse(status=status)

    def CheckPassword(self, request, context):
        if not request.username or not request.password:
            return chat_pb2.CheckPasswordResponse(status=chat_pb2.Status.ERROR)
        self.passwords_cursor.execute("SELECT Password FROM Passwords WHERE Username = ?", (request.username,))
        result = self.passwords_cursor.fetchone()
        status = chat_pb2.Status.MATCH if (result == request.password) else chat_pb2.Status.NO_MATCH
        return chat_pb2.CheckPasswordResponse(status=status)

    def CreateUser(self, request, context):
        if not request.username or not request.password:
            return chat_pb2.CreateUserResponse(status=chat_pb2.Status.ERROR)
        try:
            self.passwords_cursor.execute("INSERT INTO Passwords (Username, Password) VALUES (?, ?)", (request.username, request.password))
            self.passwords.commit()
            return chat_pb2.CreateUserResponse(status=chat_pb2.Status.SUCCESS)
        except sqlite3.IntegrityError:
            return chat_pb2.CreateUserResponse(status=chat_pb2.Status.MATCH)

    def ConfirmLogin(self, request, context):
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
        if request.username in self.online_username:
            del self.online_username[request.username]
        return chat_pb2.ConfirmLogoutResponse(status=chat_pb2.Status.SUCCESS)

    def GetOnlineUsers(self, request, context):
        return chat_pb2.GetOnlineUsersResponse(status=chat_pb2.Status.SUCCESS, users=list(self.online_username.keys()))

    def GetUsers(self, request, context):
        self.passwords_cursor.execute("SELECT Username FROM Passwords WHERE Username Like ?", (request.query, ))
        result = self.passwords_cursor.fetchall()
        final_result = [username[0] for username in result]
        return chat_pb2.GetUsersResponse(status=chat_pb2.Status.SUCCESS, users=final_result)
    
    # Messages

    def SendMessage(self, request, context):
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
        return chat_pb2.GetMessageResponse(status=chat_pb2.Status.SUCCESS, message=messages)

    def ConfirmRead(self, request, context):
        if not request.username or not request.message_id:
            return chat_pb2.ConfirmReadResponse(status=chat_pb2.Status.ERROR)
        self.messages_cursor.execute(f"UPDATE Messages SET Read = 1 WHERE Recipient = ? AND Id = ?", request.username, request.message_id)
        self.messages.commit()
        return chat_pb2.ConfirmReadResponse(status=chat_pb2.Status.SUCCESS)

    def DeleteMessage(self, request, context):
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

    def SubscribeAlerts(self, request, context):
        alert_queue = self.online_username[request.message.recipient]
        while True:
            try:
                alert = alert_queue.get(timeout=0.5)
                yield alert
            except queue.Empty:
                if context.is_active():
                    continue
                else:
                    break

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
'''
Below is an updated version of the server’s SendMessage and SubscribeAlerts implementations along with an explanation of the step‐by‐step logic. In this design, every message is stored in the database regardless of the recipient’s status. However, if the recipient is online (that is, logged in and with an active alert subscription), the server immediately pushes a real‑time alert to that user. If the recipient is offline, no alert is sent; the unread message will simply be retrieved by the recipient when they log in.

Step‑by‑Step Logic
    1    Storing the Message:
When a user (User A) calls the SendMessage RPC, the server converts the incoming message into a dictionary and calls a database function (e.g. store_message()) to store it. The database assigns a new message ID.
    2    Checking Recipient Status:
The server maintains two in‑memory structures:
    ◦    online_users: A dictionary mapping usernames to a truthy value (or more detailed metadata) to indicate they’re logged in.
    ◦    alert_subscribers: A dictionary mapping logged‑in usernames to a Queue that holds pending alert notifications.
    3    After storing the message, the server checks whether the intended recipient is currently online by checking if their username exists in both dictionaries.
    4    Pushing a Live Alert (if online):
If the recipient is online and subscribed to alerts, the server creates an alert message (wrapping the stored message details and the assigned message ID) and enqueues it in the recipient’s alert Queue. This alert is then sent to the recipient via the SubscribeAlerts streaming RPC.
    5    Retrieving Alerts via SubscribeAlerts:
When a client calls SubscribeAlerts, the server enters a loop in which it waits (with a timeout) for an alert to appear in that user’s alert Queue. When an alert is available, it’s yielded to the client in real time. If no alert appears, the loop periodically checks whether the client is still connected.
    6    Offline Behavior:
If the recipient is not online (i.e. they aren’t in the online_users dictionary or haven’t subscribed for alerts), no real‑time notification is pushed. The message is still stored, so the recipient can later retrieve all unread messages upon logging in.

Updated Server Code Snippet
Below is the relevant portion of the gRPC server implementation reflecting these changes:
import time
import queue
from concurrent import futures

import grpc
import chat_pb2
import chat_pb2_grpc

# For demonstration, we use a dummy database manager.
class DummyDatabaseManager:
    def __init__(self):
        self.users = {}      # username -> password
        self.messages = {}   # message_id -> message dict
        self.next_msg_id = 1

    def store_message(self, message):
        message['id'] = self.next_msg_id
        self.messages[self.next_msg_id] = message
        self.next_msg_id += 1
        return message['id']

    def get_message(self, message_id, username):
        return self.messages.get(message_id)

    def mark_message_read(self, message_id):
        if message_id in self.messages:
            self.messages[message_id]['read'] = True
            return True
        return False

    def delete_message(self, message_id):
        if message_id in self.messages:
            del self.messages[message_id]
            return True
        return False

    def create_user(self, username, password):
        if username in self.users:
            return False
        self.users[username] = password
        return True

    def check_username(self, username):
        return username in self.users

    def check_password(self, username, password):
        return self.users.get(username) == password

    def delete_user(self, username):
        if username in self.users:
            del self.users[username]
            return True
        return False

# The gRPC service implementation.
class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        self.db = DummyDatabaseManager()
        # Track online users: { username: True }
        self.online_users = {}
        # For alert notifications: { username: Queue }
        self.alert_subscribers = {}

    # --- Messaging RPCs ---
    def SendMessage(self, request, context):
        msg_obj = request.message
        print(f"Received message from {msg_obj.sender} to {msg_obj.recipient}: {msg_obj.body}")
        # Convert the MessageObject into a dict for the database.
        msg_dict = {
            "sender": msg_obj.sender,
            "recipient": msg_obj.recipient,
            "time_sent": msg_obj.time_sent,
            "read": msg_obj.read,
            "subject": msg_obj.subject,
            "body": msg_obj.body,
        }
        # Store the message in the database.
        msg_id = self.db.store_message(msg_dict)
        print(f"Stored message with id {msg_id}")

        # If the recipient is online and subscribed to alerts, push a real-time alert.
        if (msg_obj.recipient in self.online_users and 
            msg_obj.recipient in self.alert_subscribers):
            alert = chat_pb2.AlertNotification(
                message=chat_pb2.MessageObject(
                    id=msg_id,
                    sender=msg_obj.sender,
                    recipient=msg_obj.recipient,
                    time_sent=msg_obj.time_sent,
                    read=msg_obj.read,
                    subject=msg_obj.subject,
                    body=msg_obj.body
                )
            )
            self.alert_subscribers[msg_obj.recipient].put(alert)
            print(f"Pushed alert to {msg_obj.recipient}")
        else:
            print(f"{msg_obj.recipient} is offline. No alert pushed.")

        return chat_pb2.SendMessageResponse(
            base=chat_pb2.BaseResponse(status=chat_pb2.Status.SUCCESS, message="Message sent and stored.")
        )

    # --- Streaming RPC for Alert Notifications ---
    def SubscribeAlerts(self, request, context):
        username = request.username
        # Verify that the user is subscribed for alerts.
        if username not in self.alert_subscribers:
            context.set_details("User not subscribed for alerts.")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return

        alert_queue = self.alert_subscribers[username]
        # Continuously yield alerts as they become available.
        while True:
            try:
                # Wait for an alert (with a timeout to check for client cancellation).
                alert = alert_queue.get(timeout=5)
                yield alert
            except queue.Empty:
                if context.is_active():
                    continue
                else:
                    break

    # --- Account management RPCs (ConfirmLogin example) ---
    def ConfirmLogin(self, request, context):
        username = request.username.strip()
        if username == "":
            return chat_pb2.ConfirmLoginResponse(
                base=chat_pb2.BaseResponse(status=chat_pb2.Status.ERROR, message="Empty username not allowed.")
            )
        if username in self.online_users:
            return chat_pb2.ConfirmLoginResponse(
                base=chat_pb2.BaseResponse(status=chat_pb2.Status.MATCH, message="User already logged in.")
            )
        # Mark user as online and initialize their alert subscription.
        self.online_users[username] = True
        self.alert_subscribers[username] = queue.Queue()
        return chat_pb2.ConfirmLoginResponse(
            base=chat_pb2.BaseResponse(status=chat_pb2.Status.SUCCESS, message="Login confirmed.")
        )

    # (Other RPCs such as CheckUsername, CheckPassword, CreateUser, etc. would be implemented similarly.)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC ChatService server started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()

Explanation of the Updated Functionality
    •    Message Storage (SendMessage):
    ◦    Every incoming message is converted into a dictionary and stored in the database.
    ◦    The database returns a new message ID, which is then included in any alert sent to the recipient.
    •    Recipient Alerting:
    ◦    After storing the message, the server checks if the recipient is online by verifying that their username exists in both online_users and alert_subscribers.
    ◦    If the recipient is online, an alert notification is created and enqueued in that user’s alert queue.
    ◦    If the recipient is offline, nothing extra is done (the message remains stored in the database).
    •    Live Alerts (SubscribeAlerts):
    ◦    A client calls SubscribeAlerts with their username.
    ◦    The server checks for an active subscription (i.e., that the user is logged in and has an alert queue).
    ◦    In a loop, the server waits (with a timeout) for alerts to become available in the queue. When an alert is available, it’s yielded to the client immediately.
    ◦    This loop continues as long as the client is connected, providing near real-time notifications.
This design meets your requirement: unread messages are stored in the database for later retrieval, but if a recipient is online when a message is sent, they also receive a live alert in real time.
'''