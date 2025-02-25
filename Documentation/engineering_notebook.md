# Engineering Notebook

## 2/24

### Initial Thoughts
* Don't have to do much parsing &mdash; behaves more like JSON, where you can directly access variables, as opposed to coming up with an encoding and decoding scheme as part of processing
* The logic/logical structure gets handled in the `.proto` file instead of backend code. Our custom protocol handled all the logic in the backend, while using RPC abstracts much of the schema definition, etc to the `.proto` file.