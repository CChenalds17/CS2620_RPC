'''
Generate various timing and message size metrics. 
'''

import grpc
import chat_pb2
import chat_pb2_grpc

import sys

import pandas as pd
import matplotlib.pyplot as plt

from Analytics.Analytics_test_data import SHORT_ENGLISH_MESSAGE, SHORT_CHINESE_MESSAGE

OUTPUT_FILE = "Analytics/results.txt"
WIRE_PROTOCOL_FILE = "Analytics/wire_protocol_results.txt"
PLOT_PATH = "Analytics/Plots/"

def generate_timing():
    '''
    Establish a test socket for sending messages, and check how long it takes to send 
    messages of various length
    '''
    with open("Analytics/results.txt", "a") as file:
        file.write(f"LENGTH\tENCODING_TYPE\tMESSAGE_TYPE\tMESSAGE_SIZE\n")

    messages = [SHORT_ENGLISH_MESSAGE, SHORT_CHINESE_MESSAGE]
    names = ["ENGLISH_MESSAGE", "CHINESE_MESSAGE"]
    for datalen in range(10, 510, 10):
        for index, message in enumerate(messages):
            message1 = chat_pb2.MessageObject(id=0, sender="a", recipient="b", time_sent="now", read=False, subject=message, body=message)

            request = chat_pb2.GetMessageResponse(status=chat_pb2.Status.SUCCESS, messages=[message1]*datalen)

            message = request.SerializeToString()
            
            with open(OUTPUT_FILE, "a") as file:
                file.write(f"{datalen}\tGRPC\t{names[index]}\t{len(message)}\n")

def plot_graph(data, data_wire, metric, message_type, ylabel, title, filename):
    plt.figure(figsize=(8, 6))
    for encoding in ['EncodeType.CUSTOM', 'EncodeType.JSON']:
        # Filter by message type and encoding type
        subset = data_wire[(data_wire['MESSAGE_TYPE'] == message_type) &
                      (data_wire['ENCODING_TYPE'] == encoding)]
        if not subset.empty:
            subset = subset.sort_values(by='LENGTH')
            plt.plot(subset['LENGTH'], subset[metric], marker='o', label=encoding)
    subset = data[(data['MESSAGE_TYPE'] == message_type)]
    if not subset.empty:
        subset = subset.sort_values(by='LENGTH')
        plt.plot(subset['LENGTH'], subset[metric], marker='o', label="Grpc")
    plt.xlabel('Number of Messages in Response')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(PLOT_PATH + filename, format='png')
    plt.close()

def analyze():
    data = pd.read_csv(OUTPUT_FILE, sep='\t')
    data['LENGTH'] = pd.to_numeric(data['LENGTH'])
    data['MESSAGE_SIZE'] = pd.to_numeric(data['MESSAGE_SIZE']) / 1024

    data_wire = pd.read_csv(WIRE_PROTOCOL_FILE, sep='\t')
    data_wire['LENGTH'] = pd.to_numeric(data_wire['LENGTH'])
    data_wire['MESSAGE_SIZE'] = pd.to_numeric(data_wire['MESSAGE_SIZE']) / 1024

    language_label = {"ENGLISH_MESSAGE" : "English Messages", "CHINESE_MESSAGE" : "Chinese (Special Character) Messages"}

    for language in ["ENGLISH_MESSAGE", "CHINESE_MESSAGE"]:
        plot_graph( data, data_wire, "MESSAGE_SIZE", language,
            ylabel=f"Size of Serialized message (kB)",
            title=f"Size of Serialized message (kB) for\n{language_label[language]} as a function of the\nNumber of Messages in the Response",
            filename=f"{language}_MESSAGE_SIZE.png")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "Generate":
        generate_timing()
    elif len(sys.argv) == 2 and sys.argv[1] == "Analyze":
        analyze()
    elif len(sys.argv) == 2 and sys.argv[1] == "Size":
        print("English: ", len(SHORT_ENGLISH_MESSAGE.encode('utf-8')), "bytes\n")
        print("Chinese: ", len(SHORT_CHINESE_MESSAGE.encode('utf-8')), "bytes\n")
    else:
        print("Usage: python Analytics.py Analyze OR python Analytics.py Generate")
        sys.exit(1)
        


