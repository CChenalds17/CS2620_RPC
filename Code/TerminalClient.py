import sys
import grpc
import hashlib
from datetime import datetime, timezone

# Import the generated gRPC modules.
import chat_pb2
import chat_pb2_grpc

def client_user(stub, username):
    # Confirm login via gRPC.
    try:
        login_response = stub.ConfirmLogin(chat_pb2.ConfirmLoginRequest(username=username))
    except grpc.RpcError as e:
        print("Error during ConfirmLogin:", e)
        return

    if login_response.status == chat_pb2.Status.SUCCESS:
        print("Logged In")
        print(f"Unread messages: {login_response.num_unread_msgs}, Total messages: {login_response.num_total_msgs}")
    elif login_response.status == chat_pb2.Status.MATCH:
        print("Already Logged In Elsewhere")
        return
    else:
        print("Login Failed")
        return

    # Main interactive loop.
    while True:
        command = input(f"Enter a message as User {username}: ")
        if command == "exit":
            break
        lines = command.split()
        if not lines:
            continue

        if lines[0] == "get":
            # Get online users.
            try:
                response = stub.GetOnlineUsers(chat_pb2.GetOnlineUsersRequest())
                if response.status == chat_pb2.Status.SUCCESS:
                    print("Online users:", response.users)
                else:
                    print("Failed to get online users.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        elif lines[0] == "msg":
            # Expected usage: msg <offset> <limit> <unread_only>
            if len(lines) < 4:
                print("Usage: msg <offset> <limit> <unread_only>")
                continue
            try:
                offset = int(lines[1])
                limit = int(lines[2])
                unread_only = (lines[3].lower() == "true")
                response = stub.GetMessage(chat_pb2.GetMessageRequest(
                    offset=offset,
                    limit=limit,
                    unread_only=unread_only,
                    username=username))
                if response.status == chat_pb2.Status.SUCCESS:
                    for msg in response.messages:
                        print(f"Message {msg.id} from {msg.sender} at {msg.time_sent}:\n {msg.subject}\n {msg.body}\n (Read: {msg.read})")
                else:
                    print("Failed to get messages.")
            except Exception as e:
                print("Error processing msg command:", e)

        elif lines[0] == "users":
            # Get all registered users.
            try:
                response = stub.GetUsers(chat_pb2.GetUsersRequest(query="All"))
                if response.status == chat_pb2.Status.SUCCESS:
                    print("Registered users:", response.users)
                else:
                    print("Failed to get users.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        elif lines[0] == "like":
            # Get users matching a pattern.
            if len(lines) < 2:
                print("Usage: like <pattern>")
                continue
            try:
                response = stub.GetUsers(chat_pb2.GetUsersRequest(query=lines[1]))
                if response.status == chat_pb2.Status.SUCCESS:
                    print("Users matching pattern:", response.users)
                else:
                    print("Failed to get users with pattern.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        elif lines[0] == "delete":
            # Delete the current user.
            try:
                response = stub.DeleteUser(chat_pb2.DeleteUserRequest(username=username))
                if response.status == chat_pb2.Status.SUCCESS:
                    print("User deleted successfully.")
                    return
                else:
                    print("Failed to delete user.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        elif lines[0] == "logout":
            # Logout.
            try:
                response = stub.ConfirmLogout(chat_pb2.ConfirmLogoutRequest(username=username))
                if response.status == chat_pb2.Status.SUCCESS:
                    print("Logged out successfully.")
                    return
                else:
                    print("Logout failed.")
            except grpc.RpcError as e:
                print("RPC error:", e)
                return

        elif lines[0] == "read":
            # Mark a message as read. (Expecting a single message_id.)
            if len(lines) < 2:
                print("Usage: read <message_id>")
                continue
            try:
                message_id = int(lines[1])
                response = stub.ConfirmRead(chat_pb2.ConfirmReadRequest(
                    message_id=message_id,
                    username=username))
                if response.status == chat_pb2.Status.SUCCESS:
                    print(f"Message {message_id} marked as read.")
                else:
                    print("Failed to mark message as read.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        elif lines[0] == "deletemsg":
            # Delete one or more messages by id.
            if len(lines) < 2:
                print("Usage: deletemsg <message_id1> [<message_id2> ...]")
                continue
            try:
                message_ids = [int(x) for x in lines[1:]]
                response = stub.DeleteMessage(chat_pb2.DeleteMessageRequest(message_id=message_ids))
                if response.status == chat_pb2.Status.SUCCESS:
                    print("Message(s) deleted successfully.")
                else:
                    print("Failed to delete messages.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        elif lines[0] == "message":
            # Compose and send a new message.
            recipient = input("Send Message To: ")
            subject = input("Enter Message Subject: ")
            body = input("Enter Message Body: ")
            current_time = datetime.now(timezone.utc)
            iso_time = current_time.isoformat(timespec='seconds')
            # Build a MessageObject for the RPC.
            message_obj = chat_pb2.MessageObject(
                id=0,
                sender=username,
                recipient=recipient,
                time_sent=iso_time,
                read=False,
                subject=subject,
                body=body
            )
            try:
                response = stub.SendMessage(chat_pb2.SendMessageRequest(message=message_obj))
                if response.status == chat_pb2.Status.SUCCESS:
                    print("Message sent successfully.")
                else:
                    print("Failed to send message.")
            except grpc.RpcError as e:
                print("RPC error:", e)

        else:
            print("Unknown command.")

def client_create_user(stub):
    while True:
        print("Create New User:")
        username = input("Enter Username: ")
        password = input("Enter Password: ")
        confirm_password = input("Confirm Password: ")
        if password != confirm_password:
            print("Passwords do not match. Try again.")
            continue
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            response = stub.CreateUser(chat_pb2.CreateUserRequest(username=username, password=hashed_password))
            if response.status == chat_pb2.Status.SUCCESS:
                print(f"Created User with Username: {username}")
                return username
            elif response.status == chat_pb2.Status.MATCH:
                print("User already exists.")
                return username
            else:
                print("Error creating user.")
        except grpc.RpcError as e:
            print("RPC error:", e)

def client_login(stub):
    while True:
        print("Login:")
        username = input("Enter Username: ")
        try:
            response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username=username))
            if response.status == chat_pb2.Status.MATCH:
                break
            elif response.status == chat_pb2.Status.NO_MATCH:
                print("No such username exists. Creating new user.")
                username = client_create_user(stub)
                break
            else:
                print("Error checking username.")
        except grpc.RpcError as e:
            print("RPC error:", e)
            return

    while True:
        password = input("Enter Password: ")
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            response = stub.CheckPassword(chat_pb2.CheckPasswordRequest(username=username, password=hashed_password))
            if response.status == chat_pb2.Status.MATCH:
                print("Logging In")
                client_user(stub, username)
                return
            elif response.status == chat_pb2.Status.NO_MATCH:
                print("Wrong Password.")
            else:
                print("Error checking password.")
        except grpc.RpcError as e:
            print("RPC error:", e)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py HOSTNAME PORT")
        exit(1)
    host, port = sys.argv[1], sys.argv[2]
    # Create a gRPC channel and stub.
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = chat_pb2_grpc.ChatServiceStub(channel)
    
    while True:
        client_login(stub)
        # After logout or deletion, you might want to allow another login.
