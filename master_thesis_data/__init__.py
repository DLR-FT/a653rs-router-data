from sys import argv, stdout
from pandas import DataFrame, Series, read_csv
from enum import Enum


class TraceEvent(Enum):
    Noop = 0
    NetworkSend = 1
    NetworkReceive = 2
    ApexSend = 3
    ApexReceive = 4
    ForwardFromNetwork = 5
    ForwardFromApex = 6
    ForwardToNetwork = 7
    ForwardToApex = 8
    VirtualLinkScheduled = 9
    Echo = 10

    @classmethod
    def try_from_int(cls, val):
        try:
            return cls(val)
        except:
            None


class EchoEvent(Enum):
    EchoRequestSend = 0
    EchoRequestReceived = 1
    EchoReplySend = 2
    EchoReplyReceived = 3

    @classmethod
    def try_from_int(cls, val):
        try:
            return cls(val)
        except:
            None


def decode(df: DataFrame) -> DataFrame:
    df = df.rename(columns={"Time [s]": "t"})
    df["data"] = df[channel_labels(0, 4)].apply(decode_bytes, axis=1)
    df["event"] = df[channel_labels(4, 8)].apply(decode_bytes, axis=1)
    df["event"] = df["event"].apply(TraceEvent.try_from_int)
    df["echo"] = df[["event", "data"]].apply(decode_echo, axis=1)
    # Eliminate duplicates
    df = df.loc[df["event"].shift() != df["event"]]
    df = df[["t", "event", "data", "echo"]]

    df["delay_echo_req_apex_recv"] = delay_echo_send(df, EchoEvent.EchoRequestSend, TraceEvent.ApexReceive)
    df["delay_echo_repl_apex_recv"] = delay_echo_send(df, EchoEvent.EchoReplySend, TraceEvent.ApexReceive)

    df["delay_apex_send_echo_req"] = delay_echo_send(df, TraceEvent.ApexSend, EchoEvent.EchoRequestReceived)
    df["delay_apex_send_echo_repl"] = delay_echo_send(df, TraceEvent.ApexSend, EchoEvent.EchoReplyReceived)

    df["delay_next"] = delay_next(df)

    return df


def delay_echo_send(df: DataFrame, echo: EchoEvent, event: TraceEvent) -> DataFrame:
    echos = df["t"].where(df["echo"] == echo)
    events = df["t"].where(df["event"] == event)
    return events.reindex_like(echos) - echos


def delay_echo_recv(df: DataFrame, event: TraceEvent, echo: EchoEvent) -> DataFrame:
    echos = df["t"].where(df["echo"] == echo)
    events = df["t"].where(df["event"] == event)
    return events.reindex_like(echos) - echos


# Gets delays from an event type to the next consecutive event.
def delay_next(df: DataFrame) -> DataFrame:
    return df["t"].shift(-1) - df["t"]


# Get delays between two consecutive event types
def delay_events(df: DataFrame, event_l: TraceEvent, event_r: TraceEvent) -> DataFrame:
    l = df["t"].where(df["event"] == event_l)
    r = df["t"].where(df["event"] == event_r)
    return r.reindex_like(l) - l


def decode_bytes(c: Series) -> int:
    return sum(x << i for i, x in enumerate(c))


def channel_labels(start, stop) -> [str]:
    return ["Channel %d" % c for c in range(start, stop)]


def decode_echo(df: Series) -> EchoEvent | None:
    if df[0] is TraceEvent.Echo:
        return EchoEvent.try_from_int(df[1])
    else:
        return None


# Entry functions
def decode_file():
    df = read_csv(argv[1])
    if len(argv) > 2:
        output = argv[2]
    else:
        output = stdout
    decode(df).to_csv(path_or_buf=output)
