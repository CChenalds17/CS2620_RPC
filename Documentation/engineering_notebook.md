# Engineering Notebook

## 2/24

### Initial Thoughts
* Don't have to do much parsing &mdash; behaves more like JSON, where you can directly access variables, as opposed to coming up with an encoding and decoding scheme as part of processing
* The logic/logical structure gets handled in the `.proto` file instead of backend code. Our custom protocol handled all the logic in the backend, while using RPC abstracts much of the schema definition, etc to the `.proto` file.
* More specific error messages

### Structural/Design Differences
* Instead of having an operation code and the server parsing every operation and associated data, we essentially define an RPC function for every operation (along with associated message structures to standardize across systems)
* Simplified client-side code: instead of needing a lot of logic to handle sending a message to the server and waiting for confirmation, all we need to do is make the object(s) and call the RPC function to send it to the server (and get the response)
* Client-side logic for requests seems to be divided in a much more intuitive way. Relevant code that should be executed following confirmation of a successful request now lives in the same function as the request, as opposed to our original implementation, which handled all of them in the event handler function and needed to verify by keeping a dictionary of pending requests and generating unique IDs.

### Delivering Messages to Online Users in Real Time
* With sockets, we were able to add a TKinter event listener on the server socket to handle incoming messages. This meant the client could always receive a message from the server in real time, so the server could just send a message to an online user whenever one came in. However, with gRPC, we can't have this sort of asynchronous behavior. Instead, we make a client thread solely for subscribing to alerts from the server via blocking. (We stream these alerts from the server to the client so they aren't limited to immediately when the client requests/subscribes &mdash; they can come in to the client whenever, as long as the connection is still open).

### Testing
* Since we chose to remove the database class and instead chose to integrate it directly into the RPC function implementations, we cannot test the database on its own, and must instead test solely through RPC function calls. If we wanted to also test the database on its own, we could have abstracted it away into its own class and made those function calls within the RPC functions.