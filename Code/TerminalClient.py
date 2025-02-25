import socket
import sys
import selectors
from datetime import datetime, timezone
import hashlib

from Modules.Flags import Request, Status
from Modules.DataObjects import DataObject, MessageObject
from Modules.SelectorData import SelectorData

# run python client.py HOSTNAME PORTNAME

def client_user(server_socket, username):
    # Send a message to the database, confirming Login
    try:
        request = DataObject(request=Request.CONFIRM_LOGIN, user=username)
        server_socket.sendall(request.serialize())
    except Exception as e:
        print(f"Error in Client when sending Login to database:", e)
        server_socket.close()
        return
    data_buffer = b""
    logged_in = False
    while not logged_in:
        data = server_socket.recv(1024)
        if not data:
            print("Connection closed by the server.")
            return
        data_buffer += data
        serial, data_buffer = DataObject.get_one(data_buffer)
        if serial != b"":
            logged_in = True
            response = DataObject(method="serial", serial=serial)
            print(f"{response.to_string()}")
            if response.request != Request.CONFIRM_LOGIN:
                print("Unexpected Communication, Login Failed")
                return
            if response.status == Status.SUCCESS:
                print("Logged In")
            elif response.status == Status.MATCH:
                print("Already Logged In Elsewhere")
                return
            else:
                print("Login Failed")
                return
    
    # Use selectors to allow for polling instead of blocking
    client_selector = selectors.DefaultSelector()
    client_selector.register(server_socket, selectors.EVENT_READ, data=SelectorData("User"))
    server_socket.setblocking(False)

    while logged_in:
        # Send user input to database
        command = input(f"Enter a message as User {username}: ")
        if command == "exit":
            break
        lines = command.split()
        request = DataObject(user=username)
        if lines[0] == "get":
            request.update(request=Request.GET_ONLINE_USERS)
        if lines[0] == "msg":
            request.update(request=Request.GET_MESSAGE, datalen=3, data=[lines[1], lines[2], lines[3]])
            # start index, # messages, read/unread
        elif lines[0] == "users":
            request.update(request=Request.GET_USERS, datalen=1, data = ["All"])
        elif lines[0] == "like":
            request.update(request=Request.GET_USERS, datalen=2, data = ["Like", lines[1]])
        elif lines[0] == "delete":
            request.update(request=Request.DELETE_USER)
        elif lines[0] == "logout":
            request.update(request=Request.CONFIRM_LOGOUT)
            logged_in = False
        elif lines[0] == "read":
            request.update(request=Request.CONFIRM_READ, datalen=len(lines[1:]), data=lines[1:])
        elif lines[0] == "deletemsg":
            request.update(request=Request.DELETE_MESSAGE, datalen=len(lines[1:]), data=lines[1:])
        elif lines[0] == "message":
            recipient = input("Send Message To: ")
            subject = input("Enter Message Subject: ")
            body = input("Enter Message Body: ")
            current_time = datetime.now(timezone.utc)
            iso_time = current_time.isoformat(timespec='seconds')
            message = MessageObject(sender=username, recipient=recipient, time=iso_time, subject=subject, body=body)
            message_string = message.serialize().decode("utf-8")
            print(message.to_string())
            request.update(request=Request.SEND_MESSAGE, datalen=1, data=[message_string])
        else:
            request.update(request=Request.ALERT_MESSAGE, datalen=1, data=[command])
        
        print(f"Sending {request.to_string()}")

        server_socket.sendall(request.serialize())

        # Get response(s)
        events = client_selector.select(timeout=None)
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                data = key.fileobj.recv(1024)
                if not data:
                    print("Connection closed by the server.")
                    return
                key.data.inbound += data
                serial, key.data.inbound = DataObject.get_one(key.data.inbound)
                while serial != b"":
                    response = DataObject(method="serial", serial=serial)
                    if response.request in [Request.DELETE_USER, Request.CONFIRM_LOGOUT] :
                        return
                    print(response.to_string()) 
                    serial, key.data.inbound = DataObject.get_one(key.data.inbound)
                    

def client_create_user(server_socket):
    username = ""
    while True:
        print("Create New User:")
        username = input("Enter Username: ")
        password = input("Enter Password: ")
        confirm_password = input("Confirm Password: ")
        if password == confirm_password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            request = DataObject(request=Request.CREATE_USER, datalen=2, data=[username, hashed_password])
            server_socket.sendall(request.serialize())
        else:
            continue

        recieved = False
        data_buffer = b""
        while not recieved:
            data = server_socket.recv(1024)
            if not data:
                print("Connection closed by the server.")
                return
            data_buffer += data
            serial, data_buffer = DataObject.get_one(data_buffer)
            if serial != b"":
                recieved = True
                response = DataObject(method="serial", serial=serial)
                if response.status == Status.SUCCESS:
                    print(f"Created User with Username: {username}, Password: {password}")
                    return
                elif response.status == Status.MATCH:
                    print("User Exists.")
                    return
                else:
                    print("Error")

def client_login(server_socket):
    data_buffer = b""
    username = ""
    in_login = True
    while in_login:
        print("Login:")
        username = input("Enter Username: ")
        print(username)
        request = DataObject(request=Request.CHECK_USERNAME, datalen=1, data=[username])
        print(f"Sending: {request.to_string()}")
        server_socket.sendall(request.serialize())
        recieved = False
        while not recieved:
            data = server_socket.recv(1024)
            if not data:
                print("Connection closed by the server.")
                return
            data_buffer += data
            serial, data_buffer = DataObject.get_one(data_buffer)
            if serial != b"":
                recieved = True
                response = DataObject(method="serial", serial=serial)
                # print(f"Recieved {response.to_string()}")
                if response.status == Status.MATCH:
                    in_login = False
                elif response.status == Status.NO_MATCH:
                    print("No such username exists")
                    client_create_user(server_socket)
                else:
                    print("Error")
    
    password = ""
    while True:
        password = input("Enter Password: ")
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        request = DataObject(request=Request.CHECK_PASSWORD, datalen = 2, data = [username, hashed_password])
        server_socket.sendall(request.serialize())
        recieved = False
        while not recieved:
            data = server_socket.recv(1024)
            if not data:
                print("Connection closed by the server.")
                return
            data_buffer += data
            serial, data_buffer = DataObject.get_one(data_buffer)
            if serial != b"":
                recieved = True
                response = DataObject(method="serial", serial=serial)
                if response.status == Status.MATCH:
                    print("Logging In")
                    client_user(server_socket, username)
                    return
                elif response.status == Status.NO_MATCH:
                    print("Wrong Password")
                else:
                    print("Error")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py HOSTNAME PORTNAME")
        exit(1)
    host, port = sys.argv[1], int(sys.argv[2])

    while True:
        # Connect to the server
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, int(port)))

        # Start the login process
        client_login(server_socket)

        server_socket.close()
