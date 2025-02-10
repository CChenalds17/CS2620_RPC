from typing import Literal
import time
import json

from Modules.Flags import Request, Status, EncodeType

def byte_encode(input : bytes) -> bytes:
    '''
    Encode the string by replacing b"\n" with b"%1" and b"%" with b"%0"
    '''
    encoded = bytearray()  
    for byte in input:
        if byte == ord("\n"):
            encoded.extend(b"%1")
        elif byte == ord("%"):
            encoded.extend(b"%0")
        else:
            encoded.append(byte)
    return bytes(encoded)

def byte_decode(input : bytes) -> bytes:
    '''
    Encode the bytestring by replacing b"%1" with b"\n" and b"%0" with b"%" 
    '''
    special = False
    decoded = bytearray()
    for byte in input:
        if byte == ord("%"):
            special = True
        elif special:
            special = False
            if byte == ord("1"):
                decoded.extend(b"\n")
            elif byte == ord("0"):
                decoded.extend(b"%")
            else:
                raise Exception("Invalid Encoding")
        else:
            decoded.append(byte)
    return bytes(decoded)

class DataObject:
    def __init__(self, 
                 method : Literal["args", "serial"] = "args", 
                 encode_type : EncodeType = EncodeType.CUSTOM,
                 serial : bytes = b"", 
                 request : Request = Request.EMPTY, 
                 status : Status = Status.PENDING, 
                 sequence : int = 0,
                 user: str = "",
                 datalen: int = 0,
                 data: list[str] = []):
        if method == "serial":
            self.encode_type = encode_type
            self.deserialize(serial)
            self.typecheck()
        elif method == "args":
            # Have 0 be the indicator for assigning a sequence number by the time of the current system
            sequence = int(time.time()) if sequence == 0 else sequence

            self.encode_type = encode_type
            self.request = request
            self.status = status
            self.sequence = sequence
            self.user = user
            self.datalen = datalen
            self.data = data

            self.typecheck()
        else:
            raise Exception("Invalid DataObject Instantiation Method")
    
    def typecheck(self):
        '''
        Checks typing and basic assertions for each property
        '''
        if not self.encode_type or not isinstance(self.encode_type, EncodeType):
            raise Exception("Invalid DataObject encoding method Detected")
        if not self.request or not isinstance(self.request, Request):
            raise Exception("Invalid DataObject request Detected")
        if not self.status or not isinstance(self.status, Status):
            raise Exception("Invalid DataObject status Detected")
        if self.sequence == None or not isinstance(self.sequence, int):
            raise Exception("Invalid DataObject sequence Detected")
        if self.user == None or not isinstance(self.user, str):
            raise Exception("Invalid DataObject user Detected")
        if (self.datalen == None or not isinstance(self.datalen, int) or self.data == None
            or not isinstance(self.data, list) or self.datalen != len(self.data)):
            raise Exception("Invalid DataObject datalen and data Detected")
    
    def update(self, 
                 method : Literal["args", "serial"] = "args", 
                 encode_type : EncodeType = None,
                 serial : bytes = b"", 
                 request : Request = None, 
                 status : Status = None, 
                 sequence : int = None,
                 user: str = None,
                 datalen: int = None,
                 data: list[str] = None):
        if method == "serial":
            self.encode_type = encode_type if encode_type else self.encode_type
            self.deserialize(serial)
            self.typecheck()
        elif method == "args":
            self.encode_type = encode_type if encode_type else self.encode_type
            self.request = request if request else self.request
            self.status = status if status else self.status
            self.sequence = sequence if sequence else self.sequence
            self.user = user if user else self.user
            self.datalen = datalen if datalen else self.datalen
            self.data = data if data else self.data
            self.typecheck()
        else:
            raise Exception("Invalid DataObject Update Method")

    def serialize(self, use_encode_type : EncodeType = None):
        '''
        Serialize the object first removing "\n" from each field via encode, 
        joining feilds with "\n", removing "\n" once again via encode,
        then surrounding the entire bytestring with "\n"
        '''
        self.typecheck()

        use_encode_type = use_encode_type if use_encode_type else self.encode_type
        if use_encode_type == EncodeType.CUSTOM:
            serial_list = [
                str(self.request.value).encode("utf-8"),
                str(self.status.value).encode("utf-8"),
                str(self.sequence).encode("utf-8"),
                self.user.encode("utf-8"),
                str(self.datalen).encode("utf-8")
            ]

            serial_data = bytearray()  
            if self.datalen != 0:
                serial_data.extend(byte_encode(self.data[0].encode("utf-8")))
                for entry in self.data[1:]:
                    serial_data.extend(b"\n")
                    serial_data.extend(byte_encode(entry.encode("utf-8")))
            else:
                serial_data = b"0"
            serial_list.append(bytes(serial_data))
            
            serialized = bytearray()  
            serialized.extend(byte_encode(serial_list[0]))
            for entry in serial_list[1:]:
                serialized.extend(b"\n")
                serialized.extend(byte_encode(entry))

            final = b"\n" + str(EncodeType.CUSTOM.value).encode("utf-8") + byte_encode(bytes(serialized)) + b"\n"
            return final
        if use_encode_type == EncodeType.JSON:
            payload = {
                "request": self.request.value,
                "status": self.status.value,
                "sequence": self.sequence,
                "user": self.user,
                "datalen": self.datalen,
                "data": self.data
            }
            final = b"\n" + str(EncodeType.JSON.value).encode("utf-8") + json.dumps(payload).encode("utf-8") + b"\n"
            return final

    def deserialize(self, input : bytes):
        '''
        update the object with the arguments provided in deserialize by reversing
        the steps used to serialize
        '''
        if input[0] != ord("\n") or input[-1] != ord("\n"):
            raise Exception("Invalid encoding: Newline Wrapper Missing")
        
        input = input[1:-1]
        
        decode_type = None
        if input[0] == ord(str(EncodeType.CUSTOM.value)):
            decode_type = EncodeType.CUSTOM
        elif input[0] == ord(str(EncodeType.JSON.value)):
            decode_type = EncodeType.JSON
        else:
            raise Exception("Invalid encoding: Encode Type Flag missing")
    
        input = input[1:]

        if decode_type == EncodeType.CUSTOM:
            input = byte_decode(input)
            lines = input.split(b"\n")

            if len(lines) != 6:
                raise Exception("Invalid encoding: Incorrect Fields")

            self.request = Request(int(lines[0].decode("utf-8")))
            self.status = Status(int(lines[1].decode("utf-8")))
            self.sequence = int(lines[2].decode("utf-8"))
            self.user = lines[3].decode("utf-8")
            self.datalen = int(lines[4].decode("utf-8"))
            self.data = []

            if self.datalen == 0:
                if lines[5] != b"0":
                    raise Exception("Invalid encoding: Incorrect Fields")
            else:
                data = byte_decode(lines[5])
                data = data.split(b"\n")
                if len(data) != self.datalen:
                    raise Exception("Invalide encoding: Incorrect Data")
                for item in data:
                    self.data.append(byte_decode(item).decode("utf-8"))
                    
        elif decode_type == EncodeType.JSON:
            data = json.loads(input.decode("utf-8"))
            self.request = Request(data["request"])
            self.status = Status(data["status"])
            self.sequence = data["sequence"]
            self.user = data["user"]
            self.datalen = data["datalen"]
            self.data = data["data"]

        self.typecheck()
    
    def to_string(self):
        return (f"\nDataObject uses {self.encode_type}, and contains:\n" +
                f"\t{self.request}\n" +
                f"\t{self.status}\n" +
                f"\tSequence: {self.sequence}\n" +
                f"\tUser: {self.user}\n" +
                f"\tData Length: {self.datalen}\n" +
                f"\tData: {self.data}\n")

class MessageObject:
    def __init__(self, 
                 method : Literal["args", "serial"] = "args", 
                 encode_type : EncodeType = EncodeType.CUSTOM,
                 serial : bytes = b"", 
                 id : int = 0,
                 sender : str = "",
                 recipient : str = "",
                 time : str = "",
                 read : bool = False,
                 subject : str = "",
                 body : str = ""):
        if method == "serial":
            self.encode_type = encode_type
            self.deserialize(serial)
            self.typecheck()
        elif method == "args":
            self.encode_type = encode_type
            self.id = id
            self.sender = sender
            self.recipient = recipient
            self.time_sent = time
            self.read = read
            self.subject = subject
            self.body  = body

            self.typecheck()
        else:
            raise Exception("Invalid MessageObject Instantiation Method")
    
    def typecheck(self):
        '''
        Checks typing and basic assertions for each property
        '''       
        if not self.encode_type or not isinstance(self.encode_type, EncodeType):
            raise Exception("Invalid MessageObject encoding method Detected")
        if self.id == None or not isinstance(self.id, int):
            raise Exception("Invalid MessageObject id Detected")
        if self.sender == None or not isinstance(self.sender, str) or len(self.sender) < 1:
            raise Exception("Invalid MessageObject sender Detected")
        if self.recipient == None or not isinstance(self.recipient, str) or len(self.recipient) < 1:
            raise Exception("Invalid MessageObject recipient Detected")
        if self.time_sent == None or not isinstance(self.time_sent, str):
            raise Exception("Invalid MessageObject time Detected")
        if self.read == None or not isinstance(self.read, bool):
            raise Exception("Invalid MessageObject read Detected")
        if self.subject == None or not isinstance(self.subject, str):
            raise Exception("Invalid MessageObject subject Detected")
        if self.body == None or not isinstance(self.body, str):
            raise Exception("Invalid MessageObject body Detected")

    
    def update(self, 
                 method : Literal["args", "serial"] = "args", 
                 encode_type : EncodeType = None,
                 serial : bytes = b"", 
                 id : int = None,
                 sender : str = None,
                 recipient : str = None,
                 time_sent : str = None,
                 read : bool = None,
                 subject : str = None,
                 body : str = None):
        if method == "serial":
            self.encode_type = encode_type if encode_type else self.encode_type
            self.deserialize(serial)
            self.typecheck()
        elif method == "args":
            self.encode_type = encode_type if encode_type else self.encode_type
            self.id = id if id else self.id
            self.sender = sender if sender else self.sender
            self.recipient = recipient if recipient else recipient
            self.time_sent = time_sent if time_sent else self.time_sent
            self.read = read if read else self.read
            self.subject = subject if subject else self.subject
            self.body  = body if body else self.body
            self.typecheck()
        else:
            raise Exception("Invalid DataObject Update Method")
    

    def serialize(self, use_encode_type : EncodeType = None):
        '''
        Serialize the object first removing "\n" from each field via encode, 
        joining feilds with "\n", removing "\n" once again via encode,
        then surrounding the entire bytestring with "\n"
        '''
        self.typecheck()

        use_encode_type = use_encode_type if use_encode_type else self.encode_type
        if use_encode_type == EncodeType.CUSTOM:
            serial_list = [
                str(self.id).encode("utf-8"),
                self.sender.encode("utf-8"),
                self.recipient.encode("utf-8"),
                self.time_sent.encode("utf-8"),
                str(self.read).encode("utf-8"),
                self.subject.encode("utf-8"),
                self.body.encode("utf-8")
            ]
            
            serialized = bytearray()  
            serialized.extend(byte_encode(serial_list[0]))
            for entry in serial_list[1:]:
                serialized.extend(b"\n")
                serialized.extend(byte_encode(entry))

            final = b"\n" + str(EncodeType.CUSTOM.value).encode("utf-8") + byte_encode(bytes(serialized)) + b"\n"
            return final
        if use_encode_type == EncodeType.JSON:
            payload = {
                "id": self.id,
                "sender": self.sender,
                "recipient": self.recipient,
                "time_sent": self.time_sent,
                "read": self.read,
                "subject": self.subject,
                "body": self.body
            }
            final = b"\n" + str(EncodeType.JSON.value).encode("utf-8") + json.dumps(payload).encode("utf-8") + b"\n"
            return final

    def deserialize(self, input : bytes):
        '''
        update the object with the arguments provided in deserialize by reversing
        the steps used to serialize
        '''
        if input[0] != ord("\n") or input[-1] != ord("\n"):
            raise Exception("Invalid encoding: Newline Wrapper Missing")
        
        input = input[1:-1]
        
        decode_type = None
        if input[0] == ord(str(EncodeType.CUSTOM.value)):
            decode_type = EncodeType.CUSTOM
        elif input[0] == ord(str(EncodeType.JSON.value)):
            decode_type = EncodeType.JSON
        else:
            raise Exception("Invalid encoding: Encode Type Flag missing")
    
        input = input[1:]

        if decode_type == EncodeType.CUSTOM:
            input = byte_decode(input)
            lines = input.split(b"\n")

            if len(lines) != 7:
                raise Exception("Invalid encoding: Incorrect Fields")
            
            self.id = int(lines[0].decode("utf-8"))
            self.sender = lines[1].decode("utf-8")
            self.recipient = lines[2].decode("utf-8")
            self.time_sent = lines[3].decode("utf-8")
            self.read = bool(lines[4].decode("utf-8"))
            self.subject = lines[5].decode("utf-8")
            self.body  = lines[6].decode("utf-8")
                    
        elif decode_type == EncodeType.JSON:
            data = json.loads(input.decode("utf-8"))
            self.id = data["id"]
            self.sender = data["sender"]
            self.recipient = data["recipient"]
            self.time_sent = data["time_sent"]
            self.read = data["read"]
            self.subject = data["subject"]
            self.body = data["body"]

        self.typecheck()
    
    def to_string(self):
        return (f"\nMessageObject uses {self.encode_type}, and contains:\n" +
                f"\tID: {self.id}\n"
                f"\tFrom: {self.sender}\n" +
                f"\tTo: {self.recipient}\n" +
                f"\tTime Sent: {self.time_sent}\n" +
                f"\tIs Read: {self.read}\n" +
                f"\tSubject: {self.subject}\n" +
                f"\tBody: {self.body}\n")