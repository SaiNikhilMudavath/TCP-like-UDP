# TCP-like-UDP

The server holds a text file that the client requests over a UDP connection. Since UDP (User Datagram Protocol) is inherently unreliable and lacks built-in congestion control, we implement these features at the application layer.

## Part 1: Reliability

To provide reliable data transfer, we implement mechanisms such as cumulative acknowledgments, retransmissions, fast recovery, and timeouts.

Run server: python3 p1_server.py <SERVER_IP> <SERVER_PORT> <FAST_RECOVERY_BOOL>

FAST_RECOVERY_BOOL={0,1}

Run client: python3 p1_client.py <SERVER_IP> <SERVER_PORT>

## Part 2: Congestion Control

We design a congestion control algorithm using a sliding window scheme, where the server can send multiple packets before receiving acknowledgments. The window size adapts dynamically to prevent network overload. The algorithm follows a TCP Reno-like strategy, including slow start, congestion avoidance, fast recovery, and timeout handling.

Run server: python3 p2_server.py <SERVER_IP> <SERVER_PORT>

Run client: python3 p2_client.py <SERVER_IP> <SERVER_PORT> --pref_outfile <PREF_FILENAME>

## Simulation

For testing, we use Ryu and Mininet with the p2_exp_fairness.py script, which sets up a dumbbell topology. By varying the delay and packet loss on the bottleneck link, we evaluate the effectiveness of the congestion control algorithm.

<img width="582" height="200" alt="image" src="https://github.com/user-attachments/assets/68a9de62-19e3-4054-b077-622d3bdde20c" />
