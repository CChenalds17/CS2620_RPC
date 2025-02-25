import grpc

# Import the generated gRPC modules.
import chat_pb2
import chat_pb2_grpc

def test_login():
    channel = grpc.insecure_channel(f"127.0.0.1:2620")
    stub = chat_pb2_grpc.ChatServiceStub(channel)

    # User does not exist
    response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username="a"))
    assert response.status == chat_pb2.Status.NO_MATCH

    # Create a user
    response = stub.CreateUser(chat_pb2.CreateUserRequest(username="a", password="b"))
    assert response.status == chat_pb2.Status.SUCCESS

    # Create the same user again
    response = stub.CreateUser(chat_pb2.CreateUserRequest(username="a", password="b"))
    assert response.status == chat_pb2.Status.MATCH

    # Check user exists
    response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username="a"))
    assert response.status == chat_pb2.Status.MATCH

    # User does not exist
    response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username="b"))
    assert response.status == chat_pb2.Status.NO_MATCH

    # Bad login attempt
    response = stub.CheckPassword(chat_pb2.CheckPasswordRequest(username="a", password="a"))
    assert response.status == chat_pb2.Status.NO_MATCH

    # Good login attempt
    response = stub.CheckPassword(chat_pb2.CheckPasswordRequest(username="a", password="b"))
    assert response.status == chat_pb2.Status.MATCH

    channel.close()

def test_logging_in():
    channel = grpc.insecure_channel(f"127.0.0.1:2620")
    stub = chat_pb2_grpc.ChatServiceStub(channel)

    # Confirm login
    response = stub.ConfirmLogin(chat_pb2.ConfirmLoginRequest(username="a"))
    assert response.status == chat_pb2.Status.SUCCESS
    assert response.num_unread_msgs == 0
    assert response.num_total_msgs == 0

    # Confirm double login
    response = stub.ConfirmLogin(chat_pb2.ConfirmLoginRequest(username="a"))
    assert response.status == chat_pb2.Status.MATCH

    # Logout
    response = stub.ConfirmLogout(chat_pb2.ConfirmLogoutRequest(username="a"))
    assert response.status == chat_pb2.Status.SUCCESS

    # Confirm login
    response = stub.ConfirmLogin(chat_pb2.ConfirmLoginRequest(username="a"))
    assert response.status == chat_pb2.Status.SUCCESS
    assert response.num_unread_msgs == 0
    assert response.num_total_msgs == 0

    channel.close()

def test_messages():
    channel = grpc.insecure_channel(f"127.0.0.1:2620")
    stub = chat_pb2_grpc.ChatServiceStub(channel)
    message1 = chat_pb2.MessageObject(id=0, sender="a", recipient="b", time_sent="now", read=False, subject="subject", body="body")

    # Send a message to non-user
    response = stub.SendMessage(chat_pb2.SendMessageRequest(message=message1))
    assert response.status == chat_pb2.Status.NO_MATCH

    # Create a user
    response = stub.CreateUser(chat_pb2.CreateUserRequest(username="b", password="b"))
    assert response.status == chat_pb2.Status.SUCCESS

    # Send 2 messages
    response = stub.SendMessage(chat_pb2.SendMessageRequest(message=message1))
    assert response.status == chat_pb2.Status.SUCCESS
    response = stub.SendMessage(chat_pb2.SendMessageRequest(message=message1))
    assert response.status == chat_pb2.Status.SUCCESS

    # Confirm login
    response = stub.ConfirmLogin(chat_pb2.ConfirmLoginRequest(username="b"))
    assert response.status == chat_pb2.Status.SUCCESS
    assert response.num_unread_msgs == 2
    assert response.num_total_msgs == 2

    # Get message
    response = stub.GetMessage(chat_pb2.GetMessageRequest(offset=0, limit=10, unread_only=True, username="b"))
    assert response.status == chat_pb2.Status.SUCCESS
    assert len(response.messages) == 2
    one_id = response.messages[0].id
    next_id = response.messages[1].id

    # Delete message
    response = stub.DeleteMessage(chat_pb2.DeleteMessageRequest(message_id=[one_id]))
    assert response.status == chat_pb2.Status.SUCCESS

    # Mark Read message
    response = stub.ConfirmRead(chat_pb2.ConfirmReadRequest(message_id=next_id, username="b"))
    assert response.status == chat_pb2.Status.SUCCESS

    # Get Unread message
    response = stub.GetMessage(chat_pb2.GetMessageRequest(offset=0, limit=10, unread_only=True, username="b"))
    assert response.status == chat_pb2.Status.SUCCESS
    assert len(response.messages) == 0

    # Get Read message
    response = stub.GetMessage(chat_pb2.GetMessageRequest(offset=0, limit=10, unread_only=False, username="b"))
    assert response.status == chat_pb2.Status.SUCCESS
    assert len(response.messages) == 1

    channel.close()

def test_delete_user():
    channel = grpc.insecure_channel(f"127.0.0.1:2620")
    stub = chat_pb2_grpc.ChatServiceStub(channel)

    response = stub.DeleteUser(chat_pb2.DeleteUserRequest(username="a"))
    assert response.status == chat_pb2.Status.SUCCESS

    # User does not exist
    response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username="a"))
    assert response.status == chat_pb2.Status.NO_MATCH

    # Create a user
    response = stub.CreateUser(chat_pb2.CreateUserRequest(username="a", password="b"))
    assert response.status == chat_pb2.Status.SUCCESS

    # Create the same user again
    response = stub.CreateUser(chat_pb2.CreateUserRequest(username="a", password="b"))
    assert response.status == chat_pb2.Status.MATCH

    # Check user exists
    response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username="a"))
    assert response.status == chat_pb2.Status.MATCH


    










