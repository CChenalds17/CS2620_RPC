import sys
import time
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import hashlib
import threading
import signal

import grpc
import chat_pb2, chat_pb2_grpc

# run python client.py HOSTNAME PORTNAME

class LoginClient:
    def __init__(self, stub):
        self.stub = stub
        self.window = tk.Tk()
        self.window.geometry("500x200")
        self.window.title("Login")
        self.create_login_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.close_connection)
        self.window.mainloop()
    
    def create_login_ui(self):
        """Create the login UI"""
        self.username_label = tk.Label(self.window, text="Username:")
        self.username_label.grid(row=0, column=0, pady=5, padx=2)
        self.username_entry = tk.Entry(self.window)
        self.username_entry.grid(row=0, column=1, pady=5, padx=2) 
        self.username_button = tk.Button(self.window, text="Submit Username", command=self.send_username)
        self.username_button.grid(row=0, column=2, pady=5, padx=2)

        self.password_label = tk.Label(self.window, text="Password:")
        self.password_entry = tk.Entry(self.window, show="*")
        self.password_button = tk.Button(self.window, text="Submit Password", command=self.send_password)

        self.window.update_idletasks()
    
    def send_username(self):
        """Send username to server"""
        username = self.username_entry.get()
        if not username:
            messagebox.showwarning("Input Error", "Username cannot be empty!")
            return
        
        # Call CheckUsername RPC
        try:
            response = self.stub.CheckUsername(chat_pb2.CheckUsernameRequest(username=username))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return
        
        # If username exists, allow password entry
        if response.status == chat_pb2.MATCH:
            self.username_entry.config(state=tk.DISABLED)
            self.username_button.config(state=tk.DISABLED)
            self.password_label.grid(row=1, column=0, pady=5, padx=2)
            self.password_entry.grid(row=1, column=1, pady=5, padx=2)
            self.password_button.grid(row=1, column=2, pady=5, padx=2)
            self.window.update_idletasks()
        elif response.status == chat_pb2.NO_MATCH:
            messagebox.showerror("Login Failed", "No such username exists! Please register for an account.")
            self.window.destroy()
            RegisterClient(self.stub)
        else:
            messagebox.showerror("Error", "Unexpected server response.")
            return

    def send_password(self):
        """Send password to server"""
        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("Input Error", "Password cannot be empty!")
            return
        username = self.username_entry.get()
        if not username:
            messagebox.showwarning("Input Error", "Username cannot be empty!")
            return
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            response = self.stub.CheckPassword(chat_pb2.CheckPasswordRequest(username=username, password=hashed_password))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return
        
        if response.status == chat_pb2.MATCH:
            messagebox.showinfo("Success", "Currently Logging In")
            self.window.destroy()
            UserClient(self.stub, username)
        elif response.status == chat_pb2.NO_MATCH:
            messagebox.showerror("Login Failed", "Wrong password!")
            return
        else:
            messagebox.showerror("Error", "Unexpected server response.")

    def close_connection(self):
        """Specifies behavior upon closing the window"""
        self.window.destroy()


class RegisterClient:
    def __init__(self, stub):
        self.stub = stub
        self.window = tk.Tk()
        self.window.geometry("500x200")
        self.window.title("Register")
        self.create_register_ui()
        self.window.protocol("WM_DELETE_WINDOW", self.close_connection)
        self.window.mainloop()

    def create_register_ui(self):
        """Create the register UI"""
        self.username_label = tk.Label(self.window, text="Username:")
        self.username_label.grid(row=0, column=0, pady=5, padx=2)
        self.username_entry = tk.Entry(self.window)
        self.username_entry.grid(row=0, column=1, pady=5, padx=2)

        self.password_label = tk.Label(self.window, text="Password:")
        self.password_label.grid(row=1, column=0, pady=5, padx=2)
        self.password_entry = tk.Entry(self.window, show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=2)

        self.confirm_password_label = tk.Label(self.window, text="Confirm Password:")
        self.confirm_password_label.grid(row=2, column=0, pady=5, padx=2)
        self.confirm_password_entry = tk.Entry(self.window, show="*")
        self.confirm_password_entry.grid(row=2, column=1, pady=5, padx=2)

        self.confirm_password_button = tk.Button(self.window, text="Register", command=self.send_new_user)
        self.confirm_password_button.grid(row=3, column=1, sticky="W", pady=10)

    def send_new_user(self):
        """Sends the server a request to register new user upon submission"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        # Input validation checks
        if not username:
            messagebox.showwarning("Input Error", "Username cannot be empty!")
            return
        if " " in username:
            messagebox.showwarning("Input Error", "Username cannot contain spaces.")
            return
        if "%" in username:
            messagebox.showwarning("Input Error", "Username cannot contain '%'.")
            return
        if "_" in username:
            messagebox.showwarning("Input Error", "Username cannot contain '_'.")
            return
        if not password or not confirm_password:
            messagebox.showwarning("Input Error", "Password cannot be empty!")
            return
        if " " in password:
            messagebox.showwarning("Input Error", "Username cannot contain spaces.")
            return
        if password != confirm_password:
            messagebox.showwarning("Input Error", "Passwords must match!")
            return

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            response = self.stub.CreateUser(chat_pb2.CreateUserRequest(username=username, password=hashed_password))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return
        
        if response.status == chat_pb2.SUCCESS:
            messagebox.showinfo("Success", "Registration Successful!")
            self.window.destroy()
            LoginClient(self.stub)
        elif response.status == chat_pb2.MATCH:
            messagebox.showwarning("Error", "Username already exists.")
            return
        else:
            messagebox.showerror("Error", "Unexected server response.") 
            return

    def close_connection(self):
        self.window.destroy()


class UserClient:
    ACCOUNTS_LIST_LEN = 19

    def __init__(self, stub, username):
        self.stub = stub
        self.username = username
        self.accounts = []
        self.accounts_offset = 0
        self.unread_count = 0
        self.message_count = 0
        self.curr_displayed_msgs = []

        self.window = tk.Tk()
        self.window.geometry("1500x500")
        self.window.title(f"{username}'s Chat")

        signal.signal(signal.SIGINT, lambda sig, frame: self.close_connection())

        self.create_chat_ui()
        self.check_user_status()
        self.query_accounts()

        self.window.protocol("WM_DELETE_WINDOW", self.close_connection)
        self.check_incoming_messages()
        self.window.mainloop()
    
    def create_chat_ui(self):        
        """Generate Tkinter Widgets for GUI"""

        # Accounts column
        self.accounts_label = tk.Label(self.window, text="Accounts:")
        self.accounts_label.grid(row=0, column=0, sticky="W", padx=1, pady=5)
        self.accounts_searchbar = tk.Entry(self.window, width=20)
        self.accounts_searchbar.grid(row=0, column=1, padx=1, pady=5, sticky="W")
        self.accounts_search_button = tk.Button(self.window, text="Search", command=self.query_accounts)
        self.accounts_search_button.grid(row=0, column=2, padx=1, pady=5, sticky="W")
        self.accounts_list = tk.Text(self.window, wrap=tk.WORD, state=tk.DISABLED, height=20, width=50)
        self.accounts_list.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="W")
        self.accounts_back_button = tk.Button(self.window, text="<", command=self.prev_account)
        self.accounts_back_button.grid(row=2, column=0, pady=1, sticky="W")
        self.accounts_next_button = tk.Button(self.window, text=">", command=self.next_account)
        self.accounts_next_button.grid(row=2, column=2, pady=1, sticky="E")

        # Messages column
        self.message_count_label = tk.Label(self.window, text=f"You have {self.message_count} messages ({self.unread_count} unread). How many messages would you like to see?")
        self.message_count_label.grid(row=0, column=3, padx=2, pady=5, sticky="E")
        self.message_count_entry = tk.Entry(self.window, width=5)
        self.message_count_entry.grid(row=0, column=4, padx=2, pady=5, sticky="W")
        self.read_button = tk.Button(self.window, text="Show Messages", command=self.query_messages)
        self.read_button.grid(row=0, column=5, padx=2, pady=5, sticky="W")

        # Display messages
        self.chat_area = ttk.Treeview(self.window, columns=("ID", "Time", "Sender", "Subject", "Body"), show="headings", height=15)
        self.chat_area.heading("Time", text="Time", anchor="w")
        self.chat_area.heading("Sender", text="Sender", anchor="w")
        self.chat_area.heading("Subject", text="Subject", anchor="w")
        self.chat_area.column("ID", width=0, stretch=False)
        self.chat_area.column("Time", width=225, stretch=False)
        self.chat_area.column("Sender", width=150, anchor="w", stretch=False)
        self.chat_area.column("Subject", width=275, anchor="w", stretch=False)
        self.chat_area.column("Body", width=0, stretch=False)

        # Scrollbar for Chat Treeview
        self.chat_scroll = ttk.Scrollbar(self.window, orient="vertical", command=self.chat_area.yview)
        self.chat_area.configure(yscroll=self.chat_scroll.set)
        self.chat_area.grid(row=1, column=3, columnspan=3, padx=10, pady=5, sticky="W")
        self.chat_scroll.grid(row=1, column=6, sticky="NS")

        # Bind click event
        self.chat_area.bind("<Double-1>", self.open_message)

        # Send Message UI
        send_frame = tk.Frame(self.window)
        send_frame.grid(row=0, column=7, rowspan=3, padx=20, pady=10, sticky="N")
        tk.Label(send_frame, text="Send a Message").grid(row=0, column=0, columnspan=2, pady=10)
        tk.Label(send_frame, text="To:").grid(row=1, column=0, sticky="E", padx=5)
        self.recipient_entry = tk.Entry(send_frame, width=30)
        self.recipient_entry.grid(row=1, column=1, pady=2, sticky="W")
        tk.Label(send_frame, text="Subject:").grid(row=2, column=0, sticky="E", padx=5)
        self.subject_entry = tk.Entry(send_frame, width=30)
        self.subject_entry.grid(row=2, column=1, pady=2, sticky="W")
        tk.Label(send_frame, text="Body:").grid(row=3, column=0, sticky="NE", padx=5)
        self.body_text = tk.Text(send_frame, wrap=tk.WORD, height=15, width=39)
        self.body_text.grid(row=3, column=1, pady=2, sticky="W")
        self.send_button = tk.Button(send_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=4, column=1, pady=5, sticky="W")

        # Delete message
        self.delete_button = tk.Button(self.window, text="Delete Selected Messages", command=self.delete_selected_messages)
        self.delete_button.grid(row=2, column=3, columnspan=3, pady=5, padx=10, sticky="W")

        # Logout and Delete Account Buttons
        self.logout_button = tk.Button(self.window, text="Logout", command=self.logout)
        self.logout_button.grid(row=4, column=0, padx=5, pady=10, sticky="W")
        self.delete_account_button = tk.Button(self.window, text="Delete Account", command=self.delete_account)
        self.delete_account_button.grid(row=4, column=1, padx=5, pady=10, sticky="W")
        self.window.update_idletasks()

    def check_user_status(self):
        """Verifies this user is not currently logged in on another machine. Runs immediately upon login."""

        # Call ConfirmLogin RPC to verify status and get unread/total messages
        try:
            response = self.stub.ConfirmLogin(chat_pb2.ConfirmLoginRequest(username=self.username))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            self.close_connection()
            return

        if response.status == chat_pb2.SUCCESS:
            messagebox.showinfo("Sucess", "Logged In")
            self.unread_count = response.num_unread_msgs
            self.message_count = response.num_total_msgs
            self.message_count_label.config(text=f"You have {self.message_count} messages ({self.unread_count} unread). How many messages would you like to see?")
        elif response.status == chat_pb2.MATCH:
            messagebox.showerror("Error", "Already Logged In Elsewhere")
            self.window.destroy()
            LoginClient(self.stub)
            return
        else:
            messagebox.showerror("Server Error", "Unexpected login response.")
            self.window.destroy()
            LoginClient(self.stub)
            return

    def query_accounts(self):
        """Queries server user process for list of accounts matching wildcard pattern"""
        query = self.accounts_searchbar.get().strip()
        if not query:
            query = r"%"

        try:
            response = self.stub.GetUsers(chat_pb2.GetUsersRequest(query=query))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return

        if response.status == chat_pb2.SUCCESS:
            self.accounts = [account for account in response.users if account != self.username]
            self.display_accounts()
        else:
            messagebox.showerror("Error", "Error fetching users.")
    
    def display_accounts(self):
        """Displays list of requested accounts (not including user)"""
        self.accounts_list.config(state=tk.NORMAL)
        self.accounts_list.delete(1.0, tk.END)
        self.accounts_list.config(state=tk.DISABLED)
        
        if self.ACCOUNTS_LIST_LEN + self.accounts_offset >= len(self.accounts):
            self.accounts_next_button.config(state=tk.DISABLED)
        else:
            self.accounts_next_button.config(state=tk.NORMAL)
        if self.accounts_offset == 0:
            self.accounts_back_button.config(state=tk.DISABLED)
        else:
            self.accounts_back_button.config(state=tk.NORMAL)

        for i in range(self.accounts_offset, min(self.ACCOUNTS_LIST_LEN + self.accounts_offset, len(self.accounts))):
            self.accounts_list.config(state=tk.NORMAL)
            self.accounts_list.insert(tk.END, self.accounts[i] + "\n")
            self.accounts_list.config(state=tk.DISABLED)
    
    def next_account(self):
        """Displays next page of accounts"""
        self.accounts_offset += self.ACCOUNTS_LIST_LEN
        if self.ACCOUNTS_LIST_LEN + self.accounts_offset >= len(self.accounts):
            self.accounts_next_button.config(state=tk.DISABLED)
        else:
            self.accounts_next_button.config(state=tk.NORMAL)
        if self.accounts_offset == 0:
            self.accounts_back_button.config(state=tk.DISABLED)
        else:
            self.accounts_back_button.config(state=tk.NORMAL)
        self.display_accounts()
    
    def prev_account(self):
        """Displays previous page of accounts"""
        self.accounts_offset -= self.ACCOUNTS_LIST_LEN
        if self.ACCOUNTS_LIST_LEN + self.accounts_offset >= len(self.accounts):
            self.accounts_next_button.config(state=tk.DISABLED)
        else:
            self.accounts_next_button.config(state=tk.NORMAL)
        if self.accounts_offset == 0:
            self.accounts_back_button.config(state=tk.DISABLED)
        else:
            self.accounts_back_button.config(state=tk.NORMAL)
        self.display_accounts()

    def query_messages(self, active=True):
        """Queries server for all of user's messages"""

        limit = self.message_count_entry.get().strip()

        if active:
            # If no valid number is provided or the value is less than 1, default to 1.
            if not limit or not limit.isdigit() or int(limit) < 1:
                limit = 1
            elif int(limit) > self.message_count:
                limit = self.message_count
            else:
                limit = int(limit)
            # if we changed the number of messages to be displayed
            try:
                response = self.stub.GetMessage(chat_pb2.GetMessageRequest(
                    offset=0, limit=-1, unread_only=False, username=self.username
                ))
            except grpc.RpcError as e:
                messagebox.showerror("gRPC Error", str(e))
                return
            if response.status == chat_pb2.SUCCESS:
                # visually update limit
                self.message_count_entry.delete(0, tk.END)
                self.message_count_entry.insert(0, limit)
                num_new_messages = len(response.messages) - self.message_count
                self.unread_count += num_new_messages
                self.message_count = len(response.messages)
                self.message_count_label.config(text=f"You have {self.message_count} messages ({self.unread_count} unread). How many messages would you like to see?")
                self.display_messages(response.messages[-limit:])
            else:
                messagebox.showerror("Error", "Error fetching messages")
                return
        else:
            # Fetch all messages
            try:
                response = self.stub.GetMessage(chat_pb2.GetMessageRequest(
                    offset=0, limit=-1, unread_only =False, username=self.username
                ))
            except grpc.RpcError as e:
                messagebox.showerror("gRPC Error", str(e))
                self.close_connection()
                return
            if response.status == chat_pb2.SUCCESS:
                num_new_messages = len(response.messages) - self.message_count
                if num_new_messages == 0:
                    return
                # update unread_count and total count and increment limit (and ui)
                self.unread_count += num_new_messages
                self.message_count = len(response.messages)
                self.message_count_label.config(text=f"You have {self.message_count} messages ({self.unread_count} unread). How many messages would you like to see?")
            else:
                messagebox.showerror("Error", "Error fetching messages")
                return
            
    def display_messages(self, messages):
        """Displays user messages upon receipt"""
        for item in self.chat_area.get_children():
            self.chat_area.delete(item)
        for msg in messages:
            # formatted_datetime = datetime.fromisoformat(msg.time_sent).strftime("%-m/%-d/%y %-H:%M")
            formatted_datetime = msg.time_sent
            formatted_datetime += " (*)" if not msg.read else "    "  # 4 spaces to match (*)
            self.chat_area.insert("", "end", values=(msg.id, formatted_datetime, msg.sender, msg.subject, msg.body))

        self.curr_displayed_msgs = messages

    def open_message(self, event):
        """Open up a popup to view a message"""
        item = self.chat_area.identify_row(event.y)
        if item:
            message_id, time_sent, sender, subject, body = self.chat_area.item(item, "values") 

            # Popup window for message details
            message_window = tk.Toplevel(self.window)
            message_window.title(f"Message from {sender}: {subject}")
            message_window.geometry("600x400")
            message_textbox = tk.Text(message_window, wrap=tk.WORD, height=20, width=70)
            message_textbox.pack(expand=True, fill="both", padx=10, pady=10)
            message_textbox.config(state=tk.NORMAL)
            message_textbox.insert(
                tk.END,
                f"{'Time:':<8} {time_sent.strip().replace('(*)', '')}\n"
                f"{'From:':<8} {sender}\n"
                f"{'To:':<8} {self.username}\n\n"
                f"Subject: {subject}\n\n"
                f"Body:\n\n{body}"
            )
            message_textbox.config(state=tk.DISABLED)
            message_window.transient(self.window)
            message_window.grab_set()

            # Mark message as read
            try:
                response = self.stub.ConfirmRead(chat_pb2.ConfirmReadRequest(
                    message_id=int(message_id), username=self.username
                ))
                if response.status == chat_pb2.SUCCESS:
                    self.unread_count -= 1
                    self.query_messages()
            except grpc.RpcError as e:
                messagebox.showerror("gRPC Error", str(e))
                return
    
    def send_message(self):
        """Server request to send message"""
        recipient = self.recipient_entry.get().strip()
        subject = self.subject_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()  # Get text from Text widget
        # Client-side input validation
        if not recipient or not subject or not body:
            messagebox.showwarning("Warning", "All fields are required!")
            return
        # Message timestamp (different from request ID)
        current_time = datetime.now(timezone.utc).isoformat(timespec='seconds')
        
        # Create a MessageObject. ID is assigned by the server
        message_obj = chat_pb2.MessageObject(
            id=0,
            sender=self.username,
            recipient=recipient,
            time_sent=current_time,
            read=False,
            subject=subject,
            body=body
        )
        try:
            response = self.stub.SendMessage(chat_pb2.SendMessageRequest(message=message_obj))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return

        if response.status == chat_pb2.SUCCESS:
            messagebox.showinfo("Sent", "Your message has been sent")
        else:
            messagebox.showerror("Error", "An error has occurred while sending your message.")

        # Clear fields after sending
        self.recipient_entry.delete(0, tk.END)
        self.subject_entry.delete(0, tk.END)
        self.body_text.delete("1.0", tk.END)
    
    def delete_selected_messages(self):
        """Server request to delete messages selected in chat_area"""
        selected_items = self.chat_area.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a message to delete.")
            return
        
        message_ids = []
        num_messages = 0
        num_unread = 0
        for item in selected_items:
            values = self.chat_area.item(item, "values")
            msg_id = values[0]
            message_ids.append(int(msg_id))
            num_messages += 1
            if "(*)" in values[1]:
                num_unread += 1

        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {len(message_ids)} message(s)?")
        if not confirm:
            return
        
        # Remove from Treeview (UI)
        for item in selected_items:
            self.chat_area.delete(item)

        # Update text
        self.message_count -= num_messages
        self.unread_count -= num_unread
        num_to_read = self.message_count_entry.get().strip()

        # Update number of messages on UI
        if int(num_to_read) <= num_messages:
            self.message_count_entry.delete(0, tk.END)
            self.message_count_label.config(text=f"You have {self.message_count} messages ({self.unread_count} unread). How many messages would you like to see?")
        else:
            num_to_read = str(int(num_to_read) - num_messages)
            self.message_count_entry.delete(0, tk.END)
            self.message_count_entry.insert(0, num_to_read)
            self.message_count_label.config(text=f"You have {self.message_count} messages ({self.unread_count} unread). How many messages would you like to see?")
    
        try:
            response = self.stub.DeleteMessage(chat_pb2.DeleteMessageRequest(message_id=message_ids))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return
        if response.status != chat_pb2.SUCCESS:
            messagebox.showerror("Error", "An error has occurred while deleting messages.")

    def logout(self):
        """Sends server request to log user out"""
        try:
            response = self.stub.ConfirmLogout(chat_pb2.ConfirmLogoutRequest(username=self.username))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return
        if response.status == chat_pb2.SUCCESS:
            self.close_connection()
            LoginClient(self.stub)
        else:
            messagebox.showerror("Error", "Logout failed")
    
    def delete_account(self):
        """Sends server request to delete account. Waits for confirmation."""
        confirm = messagebox.askyesno("Confirm Account Deletion", "Are you sure you want to delete your account? This action is irreversible!")
        if not confirm:
            return

        try:
            response = self.stub.DeleteUser(chat_pb2.DeleteUserRequest(username=self.username))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            return
        if response.status == chat_pb2.SUCCESS:
            messagebox.showinfo("Account Deleted", "Your account has been deleted.")
            self.close_connection()
            LoginClient(self.stub)
        else:
            messagebox.showerror("Error", "Account deletion failed")

    def check_incoming_messages(self):
        self.query_messages(active=False)
        # Schedule check_incoming_messages to run again after 500 milliseconds
        self.window.after(500, self.check_incoming_messages)

    def close_connection(self):
        try:
            response = self.stub.ConfirmLogout(chat_pb2.ConfirmLogoutRequest(username=self.username))
        except grpc.RpcError as e:
            messagebox.showerror("gRPC Error", str(e))
            self.window.destroy()
            return
        if response.status == chat_pb2.SUCCESS:
            self.window.destroy()
        else:
            messagebox.showerror("Error", "Logout failed")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py HOSTNAME PORTNAME")
        exit(1)
    host, port = sys.argv[1], int(sys.argv[2])
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = chat_pb2_grpc.ChatServiceStub(channel)

    LoginClient(stub)
