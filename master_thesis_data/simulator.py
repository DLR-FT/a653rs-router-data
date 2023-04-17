from enum import Enum
from typing import Iterator, List
from dataclasses import dataclass


class Partition(Enum):
    client = 1
    server = 2
    io = 3


@dataclass
class PartitionWindow:
    partition: Partition
    offset: int  # us
    duration: int  # us


@dataclass
class Schedule:
    major_frame: int  # us
    partition_windows: List[PartitionWindow]
    inter_mf_delay: int  # us


@dataclass
class Simulation:
    client: Schedule
    server: Schedule
    transmission_delay: int  # us
    apex_delay: int  # us
    client_start: int  # us
    server_start: int  # us
    step: int  # us
    duration: int  # us
    echo_period: int  # us


class EventType(Enum):
    client_apex_send = 1
    client_apex_receive = 2

    server_apex_send = 3
    server_apex_receive = 4

    client_io_apex_receive = 5
    client_io_apex_send = 6
    client_io_network_send = 7
    client_io_network_receive = 8

    server_io_apex_receive = 9
    server_io_apex_send = 10
    server_io_network_send = 11
    server_io_network_receive = 12

    round_trip_complete = 13
    echo_timer = 14


@dataclass
class Event:
    type: EventType
    time: int  # us


# TODO rewrite using generators (yield)


def client_partition(t: int, sim: Simulation, event: Event) -> Iterator[Event]:
    if event.type == EventType.client_apex_receive:
        yield Event(EventType.round_trip_complete, t)
    elif event.type == EventType.client_io_apex_send:
        yield Event(EventType.client_apex_receive, t + sim.apex_delay)
    elif event.type == EventType.echo_timer:
        yield Event(EventType.client_apex_send, t + sim.apex_delay)


def client_io_partition(t: int, sim: Simulation, event: Event) -> Iterator[Event]:
    if event.type == EventType.client_apex_send:
        yield Event(EventType.client_io_apex_receive, t + sim.apex_delay)
    elif event.type == EventType.client_io_apex_receive:
        yield Event(EventType.client_io_network_send, t + sim.transmission_delay)
    elif event.type == EventType.server_io_network_send:
        yield Event(
            EventType.client_io_network_receive, t
        )  # TODO pretty much instantaneous?
    elif event.type == EventType.client_io_network_receive:
        yield Event(EventType.client_io_apex_send, t + sim.apex_delay)


def client(t: int, sim: Simulation, event: Event) -> Iterator[Event]:
    t_c = t % (sim.client.major_frame + sim.client.inter_mf_delay)
    partition: None | Partition = None
    for pw in sim.client.partition_windows:
        pw_start = pw.offset
        pw_end = pw.offset + pw.duration
        if pw_start <= t_c < pw_end:
            partition = pw.partition
    if partition == Partition.client:
        return client_partition(t, sim, event)
    elif partition == Partition.io:
        return client_io_partition(t, sim, event)
    else:
        return iter([])


def server_partition(t: int, sim: Simulation, event: Event) -> Iterator[Event]:
    if event.type == EventType.server_apex_receive:
        yield Event(EventType.server_apex_send, t + sim.apex_delay)
    elif event.type == EventType.server_io_apex_send:
        yield Event(EventType.server_apex_receive, t + sim.apex_delay)


def server_io_partition(t: int, sim: Simulation, event: Event) -> Iterator[Event]:
    if event.type == EventType.server_apex_send:
        yield Event(EventType.server_io_apex_receive, t + sim.apex_delay)
    elif event.type == EventType.server_io_apex_receive:
        yield Event(EventType.server_io_network_send, t + sim.transmission_delay)
    elif event.type == EventType.client_io_network_send:
        yield Event(
            EventType.server_io_network_receive, t
        )  # TODO pretty much instantaneous?
    elif event.type == EventType.server_io_network_receive:
        yield Event(EventType.server_io_apex_send, t + sim.apex_delay)


def server(t: int, sim: Simulation, event: Event) -> Iterator[Event]:
    t_c = t % (sim.server.major_frame + sim.server.inter_mf_delay)
    partition: None | Partition = None
    for pw in sim.server.partition_windows:
        pw_start = pw.offset
        pw_end = pw.offset + pw.duration
        if pw_start <= t_c < pw_end:
            partition = pw.partition
    if partition == Partition.server:
        return server_partition(t, sim, event)
    elif partition == Partition.io:
        return server_io_partition(t, sim, event)
    else:
        return iter([])


# Duration in seconds
def simulate(sim: Simulation) -> Iterator[int]:
    t_echo: int = 0
    t: int = 0
    # Initial event to get things started
    events: List[Event] = [Event(EventType.client_apex_send, 0)]
    while t < sim.duration:
        t += sim.step
        if 0 <= (t % sim.echo_period) <= sim.step:
            t_echo = t
            events.append(Event(EventType.echo_timer, t_echo))
        out: List[Event] = []
        for event in events:
            if event.time <= t:
                n_client: Iterator[Event] = client(t, sim, event)
                n_server: Iterator[Event] = server(t, sim, event)
                next = list(n_client) + list(n_server)
                if event.type == EventType.round_trip_complete:
                    # There is no action for a completed RTT besides returning the measured time
                    yield (event.time - t_echo)
                elif not next:
                    # Nothing reacted to event. Keep the event
                    next = [event]
                out = out + next
            else:
                # Time of event not reached
                out = out + [event]
        events = out
