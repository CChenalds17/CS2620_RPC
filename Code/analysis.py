import grpc
import threading
import time
from scapy.all import AsyncSniffer, TCP

# Import the generated gRPC modules.
import chat_pb2
import chat_pb2_grpc

# Callback function to process each captured packet
def packet_callback(packet):
    # We only care about TCP packets on our gRPC port
    if packet.haslayer(TCP):
        packet_size = len(packet)
        print(f"Captured packet: {packet.summary()} with size: {packet_size} bytes")

# Function to run packet sniffing on a separate thread
def sniff_packets():
    # We disable promiscuous mode by setting promisc=False.
    # Adjust the filter as needed; here we capture packets on TCP port 2620.
    sniffer = AsyncSniffer(filter="tcp port 2620", prn=packet_callback, store=False, promisc=False)
    sniffer.start()
    # Run for 10 seconds
    sniffer.join(timeout=10)
    sniffer.stop()

def main():
    # Start the packet sniffer in its own thread
    sniff_thread = threading.Thread(target=sniff_packets)
    sniff_thread.start()

    time.sleep(1)

    channel = grpc.insecure_channel(f"127.0.0.1:2620")
    stub = chat_pb2_grpc.ChatServiceStub(channel)

    # Send the gRPC request
    response = stub.CheckUsername(chat_pb2.CheckUsernameRequest(username="a"))
    print("gRPC response:", response)

    # Wait for the sniffer to finish
    sniff_thread.join()

if __name__ == '__main__':
    main()
