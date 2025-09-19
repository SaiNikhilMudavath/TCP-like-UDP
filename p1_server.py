import socket
import time
import argparse
import random
import logging
import json


logging.basicConfig(
    filename="server.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants
MSS = 1400  # Maximum Segment Size for each packet
WINDOW_SIZE = 30  # Number of packets in flight
DUP_ACK_THRESHOLD = 3  # Threshold for duplicate ACKs to trigger fast recovery
FILE_PATH = "file.txt"
TIMEOUT = 1.0  # Timeout for retransmitting unacknowledged packets

def send_file(server_ip, server_port, enable_fast_recovery):
    """
    Send a predefined file to the client, ensuring reliability over UDP.
    """
    # Initialize UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    # #print(f"Server listening on {server_ip}:{server_port}")

    # Wait for client to initiate connection
    client_address = None
    with open(FILE_PATH, 'rb') as file:
        seq_num = 0
        window_base = 0
        unacked_packets = {}
        duplicate_ack_count = 0
        last_ack_received = 0
        duplicate_ack_map={}
        end_of_file = False  # Flag to mark end of file
        retransmit=False
        dup_3_bool=False
        is_dup_acks=False 
        rtt_map={}
        rto=1.0
        srtt=1.0
        rttvar=1.0
        G=1.0
        drop=0
        past_time=time.time()
        deadline=time.time()
        # Wait for client connection
        while not client_address:
            # #print("Waiting for client connection...")
            try:
                json_data, client_address = server_socket.recvfrom(1024)
                data=json.loads(json_data.decode())["message"]
                if data == "START":
                    # #print(f"Connection established with client {client_address}")
                    pass 
            except socket.timeout:
                pass
        
        logging.info('connection established with client')
        logging.getLogger().handlers[0].flush()

        logging.info(f'end of file is {end_of_file} and the command value is {((not end_of_file) or (len(unacked_packets) > 0))}')
        logging.getLogger().handlers[0].flush()
       
        while ((not end_of_file) or (len(unacked_packets) > 0)):
            # Start sending the file in chunks
            logging.info('in server while')
            logging.getLogger().handlers[0].flush()
            if dup_3_bool:
                fast_recovery(server_socket, client_address, unacked_packets,rtt_map)
            elif not is_dup_acks:
                seq_num=window_base
                past_time = time.time()
                # check if it is retransmission or not
                if retransmit:
                    for number in range(0,WINDOW_SIZE):
                        if seq_num in unacked_packets:
                            (a,b,c)=unacked_packets[seq_num]
                            a=modify_packet(a)
                            rtt_map[seq_num]=time.time()
                            server_socket.sendto(a, client_address)
                            logging.info(f"Sent packet in retransmission {seq_num} with {len(chunk)} bytes and {chunk}")
                            logging.getLogger().handlers[0].flush()
                            #print(f"Sent packet in retransmission {seq_num} with {c} bytes")
                            seq_num += c
                else:
                    for number in range(0,WINDOW_SIZE):
                        if (seq_num not in unacked_packets):
                            chunk = file.read(MSS)
                            if (not chunk):
                                # End of file reached, break out and stop sending new packets
                                if not end_of_file:
                                    #print("End of file reached, sending END signal")
                                    packet=create_packet(seq_num,b'EOF',time.time())
                                    rtt_map[seq_num]=time.time()
                                    server_socket.sendto(packet, client_address)
                                    unacked_packets[seq_num]=(packet,time.time(),len(b'EOF'))
                                    end_of_file = True
                                    logging.info(f"Sent end")
                                    logging.getLogger().handlers[0].flush()
                                break

                            # Create and send the packet
                            packet = create_packet(seq_num, chunk, time.time())
                            rand_num=random.randint(1,10)
                            if rand_num<11:
                                rtt_map[seq_num]=time.time()
                                server_socket.sendto(packet, client_address)
                                #print(f"Sent packet {seq_num} with {len(chunk)} bytes")
                                logging.info(f"sent packet {seq_num} with {len(chunk)} bytes")
                                logging.getLogger().handlers[0].flush()
                            else:
                                rtt_map[seq_num]=time.time()
                                #print(f"not sending packet {seq_num} with {len(chunk)} bytes")
                            unacked_packets[seq_num] = (packet, time.time(),len(chunk))
                            
                            seq_num += len(chunk)
                        else:
                            (a,b,c)=unacked_packets[seq_num]
                            seq_num+=c 
            # acknowledgments receiving part
            is_dup_acks=False
            dup_3_bool=False
            retransmit=False
            # received=False
            # past_time=time.time()
            
            if rto<0.1:
                rto=0.1
            # print("rto is ",rto)
            if rto>60.0:
                rto=60.0
            # while((time.time()-past_time<rto) and (not received)):
            try:
                server_socket.settimeout((past_time+rto)-time.time())
                ack_packet, _ = server_socket.recvfrom(1024)
                data=json.loads(ack_packet.decode())["message"]
                if data == "START":
                    is_dup_acks=True
                    continue
                
                
                receiving_time=time.time()
                ack_seq_num,time_stamp = get_seq_no_from_ack_pkt(ack_packet)
                if ack_seq_num==-1:
                    unacked_packets={}
                    # received=True
                    #print('sending CLOSE')
                    packet=create_packet(-1,b'CLOSE',time.time())
                    server_socket.sendto(packet, client_address)
                    logging.info('sent close')
                    logging.getLogger().handlers[0].flush()
                elif ack_seq_num > last_ack_received:
                    #print(f"Received cumulative ACK for packet {ack_seq_num}")
                    logging.info(f"received cumulative ACK for packet {ack_seq_num}")
                    logging.getLogger().handlers[0].flush()
                    # has to change the R calculation as i am considering the old packet
                    R=receiving_time-time_stamp
                    logging.info(f"rtt is  {R}")
                    logging.getLogger().handlers[0].flush()
                    if last_ack_received==0:
                        srtt=R
                        rttvar=R/2
                        rto=srtt+4*rttvar
                    else:
                        rttvar=(0.75*rttvar)+0.25*abs(srtt-R)
                        srtt=0.875*srtt+0.125*R 
                        # rto=srtt+max(G,4*rttvar)
                        rto=srtt+4*rttvar
                        
                        
                    last_ack_received = ack_seq_num
                    # Slide the window forward
                    for key in list(unacked_packets.keys()):
                        if key < ack_seq_num:
                            unacked_packets.pop(key)
                    window_base = last_ack_received  # Update the window base
                    # received=True
                elif ack_seq_num == last_ack_received:
                    # Duplicate ACK received
                    if ack_seq_num not in duplicate_ack_map:
                        duplicate_ack_map[ack_seq_num]=0
                    duplicate_ack_map[ack_seq_num]+=1
                    #print(f"Received duplicate ACK for packet {ack_seq_num}, count={duplicate_ack_map[ack_seq_num]}")
                    logging.info(f"Received duplicate ACK for packet {ack_seq_num}, count={duplicate_ack_map[ack_seq_num]}")
                    logging.getLogger().handlers[0].flush()
                    
                    is_dup_acks=True
                    if duplicate_ack_map[ack_seq_num]==3 and enable_fast_recovery:
                        dup_3_bool=True
                        # received=True
                        duplicate_ack_map[ack_seq_num]=0
                        #print(f"Received 3 duplicate ACK for packet {ack_seq_num}")
                        logging.info(f"Received 3 duplicate ACK for packet {ack_seq_num}")
                        logging.getLogger().handlers[0].flush()
                        
            except socket.timeout:
                # if not received:
                rto*=2.0
                #print("Timeout occurred, retransmitting unacknowledged packets")
                logging.info("Timeout occurred, retransmitting unacknowledged packets")
                logging.getLogger().handlers[0].flush()
                # retransmit_unacked_packets(server_socket, client_address, unacked_packets)
                retransmit=True

            logging.info(f'timeout is {rto}')
            logging.getLogger().handlers[0].flush()
            # If file is fully sent and acknowledged, break the loop
            if end_of_file and len(unacked_packets) == 0:
                # #print("File transfer complete.")
                break

def modify_packet(packet):
    packet_dict = json.loads(packet.decode())
    packet_dict["timestamp"] = time.time()
    return json.dumps(packet_dict).encode()

def create_packet(seq_num, data, time_stamp):
    """
    Create a packet with the sequence number and data.
    """
    packet = {
        "sequence_number": seq_num,
        "num_bytes": len(data),
        "data": data.decode(),  # Convert data to string for JSON serialization
        "timestamp": time.time()
    }
    return json.dumps(packet).encode()

def retransmit_unacked_packets(server_socket, client_address, unacked_packets):
    """
    Retransmit all unacknowledged packets.
    """
    for seq_num, (packet, _) in unacked_packets.items():
        server_socket.sendto(packet, client_address)
        # #print(f"Retransmitted packet {seq_num}")
        logging.info(f"Retransmitted packet {seq_num}")
        logging.getLogger().handlers[0].flush()

def fast_recovery(server_socket, client_address, unacked_packets,rtt_map):
    """
    Retransmit the earliest unacknowledged packet (fast recovery).
    """
    #print("entered the fast recovery mode")
    earliest_seq_num = min(unacked_packets.keys())
    packet,b,c = unacked_packets[earliest_seq_num]
    packet=modify_packet(packet)
    server_socket.sendto(packet, client_address)
    #print(f"Fast retransmit for packet {earliest_seq_num}")
    logging.info(f"Fast retransmit for packet {earliest_seq_num}")
    logging.getLogger().handlers[0].flush()

def get_seq_no_from_ack_pkt(ack_packet):
    """
    Extract the sequence number from the ACK packet.
    """
    # #print(ack_packet.decode())
    json_packet=json.loads(ack_packet.decode())
    seq_num=json_packet["sequence_number"] 
    time_stamp=json_packet["timestamp"]
    return int(seq_num),float(time_stamp)

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reliable file transfer server over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')
parser.add_argument('fast_recovery', type=int, help='Enable fast recovery')

args = parser.parse_args()

# Run the server
send_file(args.server_ip, args.server_port, args.fast_recovery)