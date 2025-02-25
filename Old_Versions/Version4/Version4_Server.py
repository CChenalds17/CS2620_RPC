#!/usr/bin/env python3
import os
import socket
import sys
import multiprocessing as mp
import selectors

from Modules.DatabaseManager import DatabaseManager
from Modules.DataObjects import DataObject, MessageObject
from Modules.SelectorData import SelectorData
from Modules.Flags import Request, Status

def database_request_handler(db : DatabaseManager, 
                             request : DataObject, 
                             key : selectors.SelectorKey, 
                             online_username : dict[str, selectors.SelectorKey], 
                             online_address : dict[str, str]) -> DataObject:
    address_string = f"{key.data.address}"

    # Confirm Login should reject already logged-in users. Otherwise, mark the user as now logged-in
    if request.request == Request.CONFIRM_LOGIN:
        if request.user == "":
            request.update(status=Status.ERROR)
        elif request.user in online_username:
            request.update(status=Status.MATCH)
        else:
            online_username[request.user] = key
            online_address[address_string] = request.user
            request = db.handler(request)

    # Return the list of users that are currently logged-in
    elif request.request == Request.GET_ONLINE_USERS:
        user_list = list(online_username.keys())
        request.update(status=Status.SUCCESS, datalen=len(user_list), data=user_list)

    # Check if the recipient is logged-in. If so, send them an alert
    elif request.request == Request.SEND_MESSAGE:
        message_raw = request.data[0]
        message = MessageObject(method="serial", serial = message_raw.encode("utf-8"))
        print(f"Database Processing Message: {message.to_string()}")
        
        request = db.handler(request)
        print(request.to_string())
        if request.status == Status.SUCCESS and message.recipient in online_username:
            target_key = online_username[message.recipient]
            request.update(request=Request.ALERT_MESSAGE, status=Status.PENDING)
            target_key.data.outbound.put(request.serialize())
            request.update(request=Request.SEND_MESSAGE, status=Status.SUCCESS)
    
    elif request.request == Request.CONFIRM_LOGOUT:
        request.update(status=Status.SUCCESS)
    
    # All other requests can go directly to the DatabaseManager's handler
    else:
        request = db.handler(request)
        print(f"Handler Responds with {request.to_string()}")
    return request
    
if __name__ == "__main__":
    """
    Handle all requests to the database
    """
    # Confirm validity of commandline arguments
    if len(sys.argv) != 3:
        print("Usage: python server.py HOSTNAME DATABASE_PORTNAME")
        sys.exit(1)
    host, database_port = sys.argv[1], int(sys.argv[2])

    print(f"Database process started")

    database_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    database_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    database_socket.bind((host, database_port))
    database_socket.listen(5)
    print(f"Database listening on {(host, database_port)}")
    database_socket.setblocking(False)

    selector = selectors.DefaultSelector()
    selector.register(database_socket, selectors.EVENT_READ, data=None)

    db = DatabaseManager()

    # bi-directional {username : address} and {address : username} for who is online
    online_username = {}
    online_address = {}

    try:
        while True:
            events = selector.select(timeout=None)
            for key, mask in events:
                # Add new connection from new User Processes
                if key.data is None:
                    connection, address = key.fileobj.accept()
                    print(f"Database accepted connection from {address}")
                    connection.setblocking(False)
                    events = selectors.EVENT_READ | selectors.EVENT_WRITE
                    selector.register(connection, events, data=SelectorData(f"{address}", address))
                else:
                    cur_socket = key.fileobj
                    address_string = f"{key.data.address}"

                    # Communications From User Processes to the Database
                    if mask & selectors.EVENT_READ:
                        recieve = cur_socket.recv(1024)
                        if recieve:
                            key.data.inbound += recieve
                            serial, key.data.inbound = DataObject.get_one(key.data.inbound)
                            print(serial, key.data.inbound)

                            # Once a full communication is read from the socket, deserialize and handle it
                            if serial != b"":
                                request = DataObject(method="serial", serial=serial)
                                print(f"Database recieved Request: {request.to_string()}")
                                response = database_request_handler(db, request, key, online_username, online_address)
                                key.data.outbound.put(response.serialize())
                        else:
                            print(f"Database closing connection to {key.data.address}")
                            if address_string in online_address:
                                del online_username[online_address[address_string]]
                                del online_address[address_string]
                            selector.unregister(cur_socket)
                            cur_socket.close()

                    # Communications From the Database To User Processes
                    if mask & selectors.EVENT_WRITE:
                        if not key.data.outbound.empty():
                            message = key.data.outbound.get()
                            cur_socket.sendall(message)
    except Exception as e:
        print(f"Database process encountered error {e}")
    finally:
        print("Closing Database Process")
        selector.close()
