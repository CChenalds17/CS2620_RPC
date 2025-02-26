# Engineering Notebook

## 2/25

### Client-Side Changes to Real Time Message Delivery
- We ran into bugs with the streaming method for receiving realtime notifications upon message deliveries, so we instead switched to a polling approach: Every .5 seconds, the client queries messages again to check if any new ones came in (and handles any new messages accordingly). With sockets and tkinter's event listener (which worked on sockets but does not work for gRPC), we could simply have the server send a message to the client at any time it chose to. However, just polling for new messages was by far the simpler solution with gRPC.
- This (among other things) exemplified the fact that while gRPC is a very useful abstraction in many ways, and it makes things like function calls and inter-system communication much simpler (i.e. things it is specifically fine-tuned to abstract away), it is much more difficult to implement features that gRPC was not designed to do.
- Spent a good amount of time just debugging new logic with gRPC implementation.
- Fixed bugs related to closing the client/server while the other is still running:
    - Prematurely closing the client: This caused the server to think the client was still logged in. To fix this, we added a logout message to the server when either the TKinter window closes or the user keyboard interrupts the program.
    - Prematurely closing the server: This caused every message the client sent to the server to raise a gRPC exception. This was a big problem because the client polls the server 2 times a second (which means they just receive a flood of errors). To fix this, we had to make 2 changes. First, we exit the client program if `query_messages()` raises an error when it is called by `check_incoming_messages()`. This way, we don't keep on querying the server for messages every 0.5 seconds when we know that it already raised an exception. Second, we also exit the client program even if it does not receive a logout confirmation from the server upon closing the window &mdash; this ensures the user doesn't get stuck in a loop of trying to close the window due to an error, which raises another error from telling the server that the client logged out.

### Structural Differences
- The ability to essentially treat server responses as local variables is very noticeable in the code. Instead of processing all the responses in one big conditional in the TKinter event handler, we can just treat the response like a local variable whose value is set right as the request is sent out. This makes the logic and struture of the client code much clearer.

### Ease of Use
- gRPC's abstractions make this an easier out-of-the-box solution than implementing our own custom wire protocol. However, we recognize that this is in part because we are implementing some very common and basic functionalities, and once we get into more custom uses/datatypes/etc, having to tailor our approach and structure to accomodate gRPC's supported features may likely end up being more work than just creating our own protocol.

## 2/24

### Initial Thoughts
- Don't have to do much parsing &mdash; behaves more like JSON, where you can directly access variables, as opposed to coming up with an encoding and decoding scheme as part of processing
- The logic/logical structure gets handled in the `.proto` file instead of backend code. Our custom protocol handled all the logic in the backend, while using RPC abstracts much of the schema definition, etc to the `.proto` file.
- More specific error messages

### Structural/Design Differences
- Instead of having an operation code and the server parsing every operation and associated data, we essentially define an RPC function for every operation (along with associated message structures to standardize across systems)
- Simplified client-side code: instead of needing a lot of logic to handle sending a message to the server and waiting for confirmation, all we need to do is make the object(s) and call the RPC function to send it to the server (and get the response)
- Client-side logic for requests seems to be divided in a much more intuitive way. Relevant code that should be executed following confirmation of a successful request now lives in the same function as the request, as opposed to our original implementation, which handled all of them in the event handler function and needed to verify by keeping a dictionary of pending requests and generating unique IDs.

### Delivering Messages to Online Users in Real Time
- With sockets, we were able to add a TKinter event listener on the server socket to handle incoming messages. This meant the client could always receive a message from the server in real time, so the server could just send a message to an online user whenever one came in. However, with gRPC, we can't have this sort of asynchronous behavior. Instead, we make a client thread solely for subscribing to alerts from the server via blocking. (We stream these alerts from the server to the client so they aren't limited to immediately when the client requests/subscribes &mdash; they can come in to the client whenever, as long as the connection is still open).

### Testing
- Since we chose to remove the database class and instead chose to integrate it directly into the RPC function implementations, we cannot test the database on its own, and must instead test solely through RPC function calls. If we wanted to also test the database on its own, we could have abstracted it away into its own class and made those function calls within the RPC functions.