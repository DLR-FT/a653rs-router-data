# Measurements

## TODO

## RTT
- [X] RTT delays echo -> log (is pretty large, depends on schedule)
Depends on schedule. Usually multiple of mayor frame. (10XX or 20XX ms)

## echo_server
- [X] internal delays of io part. echo_server -> GPIO + UART
- [ ] UART AXI write -> UART frame start

### Logical
- Channel 0-7 -> GPIO LSB->MSB from GPIO 0
- Channel 8 -> UART TX
- Channel 9 -> UART RX

### Physical
| Channel | IO |
|---------|----|
| 0       | 26 |
| 1       | 27 |
| 2       | 28 |
| 3       | 29 |
| 4       | 30 |
| 5       | 31 |
| 6       | 32 |
| 7       | 33 |
| 8       | 12 |
| 9       | 13 |

## echo client
- [ ] internal delays of io part. echo_client -> GPIO + UART
  - neccessary because using queueing ports instead of sampling ports
  - apply fix that removes copying of queueing port message

## XNG internal delay
- [ ] Apex write <-> Apex read
  - TODO: measure

## Derive
For client and server and each consecutive event:
- Distribution of delays
- Mean deviation and max deviation -> jitter

For echo-server and echo-client apps:
- RTT delay
- transmission delay APEX write <-> APEX read

## Throughput

- max = 256 * 8KiByte * (MF / source_t)
- direct = 13 MByte/s
- local = 7.3 MByte/s -> direct * (MF / io_t)
- remote = 
