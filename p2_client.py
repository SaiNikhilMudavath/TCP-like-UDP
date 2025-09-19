import socket
import argparse
import logging
import random
import time
import json


# Constants
MSS = 1400  # Maximum Segment Size

def receive_file(server_ip, server_port, pref_outfile):
    logging.basicConfig(
    filename=f"client{pref_outfile}.log",
    filemode='w',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
    )
    """
    Receive the file from the server with reliability, handling packet loss
    and reordering.
    """
    # Initialize UDP socket
    
    ## Add logic for handling packet loss while establishing connection
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2)  # Set timeout for server response

    server_address = (server_ip, server_port)
    expected_seq_num = 0
    output_file_path = f"{pref_outfile}received_file.txt"  # Default file name

    out_of_order_packets = {}
    isconnectionEstablished=False
    # Send initial connection request
    while True:
        try:
            start_json = {
            "sequence_number": -1,
            "timestamp": "0.0",
            "message":"START"}
            
            start_packet=json.dumps(start_json).encode()
            client_socket.sendto(start_packet, server_address)
            # ##print('connected to roy')
            break
        except socket.timeout:
            ##print("Retrying connection to server...")
            pass

    check_close=False
    close_timer=float('inf')

    with open(output_file_path, 'wb') as file:
        while True:
            
            if time.time()-close_timer>30 and check_close:
                # #print('timer expired, closing the connection')
                logging.info('timer expired closing connection')
                logging.getLogger().handlers[0].flush()
                return
            elif check_close:
                # #print('current time is',time.time())
                pass

            try:
                packet, _ = client_socket.recvfrom(2*MSS)  # Allow room for headers
                ##print('start of while loop')

                if not isconnectionEstablished:
                    logging.info('connection established with server')
                    logging.getLogger().handlers[0].flush()
                    isconnectionEstablished=True

                seq_num, data, time_stamp = parse_packet(packet)
                logging.info(f'seq is {seq_num} and expected seq is {expected_seq_num} and received data is {data}')
                logging.getLogger().handlers[0].flush()
                # print('received data is',data,'and seq is',seq_num,'and expected seq is',expected_seq_num)
                
                rand_num=random.randint(1,10)
                if rand_num>11:
                    # print('ignoring seq no',seq_num)
                    pass
                
                else:

                    if seq_num == expected_seq_num:

                        if b"EOF" in data:
                            # print('got eof')
                            logging.info('got eof')
                            logging.getLogger().handlers[0].flush()
                            # with open('client_status.txt','w') as filen:
                            #     filen.write('EOF received. closed the program')
                            check_close=True
                            expected_seq_num=-1
                            send_ack(client_socket, server_address,-1,time_stamp)
                            close_timer=time.time()
                            # #print('close_timer', close_timer)
                            continue

                        elif b'CLOSE' in data:
                            logging.info('received close')
                            logging.getLogger().handlers[0].flush()
                            # print('received CLOSE')
                            break
                        
                        file.write(data)
                        file.flush()
                        # print(f"Received packet {seq_num}, writing to file")
                        
                        '''
                        check this:
                        '''
                        expected_seq_num += len(data)
                        # send_ack(client_socket, server_address, expected_seq_num)
                
                        if expected_seq_num not in out_of_order_packets: 
                            send_ack(client_socket, server_address, expected_seq_num,time_stamp)

                        else:
                            while expected_seq_num in out_of_order_packets:
                                ##print('received advance packets')
                                this_data=out_of_order_packets.pop(expected_seq_num)
                                if b'EOF' in this_data:
                                    # print('found eof in buffer')
                                    logging.info('got eof in buffer')
                                    logging.getLogger().handlers[0].flush()
                                    check_close=True
                                    expected_seq_num=-1
                                    close_timer=time.time()

                                elif b'CLOSE' in this_data:
                                    # print('found close in buffer')
                                    logging.info('received close in buffer')
                                    logging.getLogger().handlers[0].flush()
                                    return
                                
                                else:
                                    # print(f'found {expected_seq_num} in buffer and data is {this_data}')
                                    logging.info(f'found {expected_seq_num} in buffer and data is {this_data}')
                                    logging.getLogger().handlers[0].flush()
                                    file.write(this_data)
                                    expected_seq_num += len(this_data)

                                if expected_seq_num not in out_of_order_packets:
                                    send_ack(client_socket, server_address, expected_seq_num,time_stamp)

                    elif seq_num < expected_seq_num:
                        # Duplicate or old packet, send ACK again
                        # print('received dup or old packet so sending ack again')
                        logging.info('received dup or old packet so sending ack again')
                        logging.getLogger().handlers[0].flush()
                        send_ack(client_socket, server_address, expected_seq_num, time_stamp)

                    else:
                        # packet arrived out of order
                        out_of_order_packets[seq_num]=data
                        # print(f"Received out-of-order packet {seq_num}")
                        logging.info(f"Received out-of-order packet {seq_num}")
                        logging.getLogger().handlers[0].flush()
                        if check_close:
                            send_ack(client_socket, server_address,-1, time_stamp)
                            expected_seq_num=-1

                        send_ack(client_socket, server_address, expected_seq_num, time_stamp)

            except socket.timeout:
                # #print("Timeout waiting for data")
                if not isconnectionEstablished:
                    start_json = {
                    "sequence_number": -1,
                    "timestamp": "0.0",
                    "message":"START"}
                    
                    start_packet=json.dumps(start_json).encode()
                    client_socket.sendto(start_packet, server_address)

def parse_packet(packet):
    """
    Parse the packet to extract the sequence number and data.
    """
    packet_dict = json.loads(packet.decode())
    seq_num=packet_dict["sequence_number"]
    data=packet_dict["data"]
    time_stamp=packet_dict["timestamp"]
    return int(seq_num), data.encode(), time_stamp


def send_ack(client_socket, server_address, seq_num, time_stamp):
    """
    Send a cumulative acknowledgment for the received packet.
    """
    ack_json = {
        "sequence_number": seq_num,
        "timestamp": time_stamp,
        "message":"ACK"
    }
    ack_packet=json.dumps(ack_json).encode()
    client_socket.sendto(ack_packet, server_address)
    logging.info(f"Sent cumulative ACK {seq_num} and ack is {seq_num}|ACK")
    logging.getLogger().handlers[0].flush()

file_start=time.time()
# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reliable file receiver over UDP.')
parser.add_argument('server_ip', help='IP address of the server')
parser.add_argument('server_port', type=int, help='Port number of the server')
parser.add_argument('--pref_outfile', default='', help='Prefix for the output file')

args = parser.parse_args()
# print(args.pref_outfile)

# Run the client
receive_file(args.server_ip, args.server_port, args.pref_outfile)
