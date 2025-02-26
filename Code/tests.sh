# May need to run chmod +x tests.sh
# Exit immediately if a command fails
set -e  

# Clear the databases by deleting them
rm -f User_Data/messages.db
rm -f User_Data/passwords.db
touch User_Data/messages.db
touch User_Data/passwords.db

# Start the GRPC server in the background
python GRPCServer.py 127.0.0.1 2620 &
SERVER_PID=$!
sleep 2

# Run pytest on tests.py
pytest tests.py

# After tests finish, stop the GRPC server
kill $SERVER_PID

# Clear the databases by deleting them
rm -f User_Data/messages.db
rm -f User_Data/passwords.db
touch User_Data/messages.db
touch User_Data/passwords.db