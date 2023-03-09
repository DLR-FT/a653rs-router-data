from sys import argv, stdout, stdin
from pandas import DataFrame, Series, read_csv
from enum import Enum


class TraceType(Enum):
    Noop = 0
    NetworkSend = 1  # Occurs when send is started
    NetworkReceive = 2  # Occurs when receive is complete
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
    EchoRequestSend = 0  # Occurs when send is started
    EchoRequestReceived = 1  # Occurs when receive is complete
    EchoReplySend = 2  # Occurs when send is started
    EchoReplyReceived = 3  # Occurs when receive is complete

    @classmethod
    def try_from_int(cls, val):
        try:
            return cls(val)
        except:
            None

def decode_raw(df: DataFrame) -> DataFrame:
    df = df.rename(columns={"Time [s]": "t"})

    # Eliminate duplicates
    df["raw"] = df[channel_labels(0, 8)].apply(decode_bytes, axis=1)
    df = df.loc[df["raw"].shift() != df["raw"]]

    df["data"] = df[channel_labels(0, 3)].apply(decode_bytes, axis=1)
    df["type"] = df[channel_labels(3, 7)].apply(decode_bytes, axis=1)
    df["end"] = df[channel_labels(7, 8)]

    return df[["t", "end", "type", "data"]]


def decode(df: DataFrame) -> DataFrame:
    df = decode_raw(df)

    df["type"] = df["type"].apply(TraceType.try_from_int)
    df["echo"] = df.apply(decode_echo, axis=1)
    df["end"] = df.apply(boo, axis=1)
    df = df[["t", "end", "type", "echo", "data"]]

    return df


def delay_echo_send(df: DataFrame, echo: EchoEvent, event: TraceType) -> DataFrame:
    echos = df["t"].where(df["echo"] == echo)
    events = df["t"].where(df["type"] == event)
    return events.reindex_like(echos) - echos


def delay_echo_recv(df: DataFrame, event: TraceType, echo: EchoEvent) -> DataFrame:
    echos = df["t"].where(df["echo"] == echo)
    events = df["t"].where(df["type"] == event)
    return echos - events.reindex_like(echos)


# Gets the mean delay from the start to the end of an event.
def mean_delay_events(df: DataFrame) -> DataFrame:
    diff = delays_type(df)
    diff = diff.groupby(["type"], group_keys=False).mean()
    diff = diff[["delay"]]
    return diff


# Gets the jitter for each event.
def jitter_events(df: DataFrame) -> DataFrame:
    diff = delays_type(df)
    diff = diff.groupby(["type"], group_keys=False).var()
    diff = diff[["delay"]]
    return diff


# Gets the delays grouped by event type
def delays_type(df: DataFrame) -> DataFrame:
    diff = df.groupby(["type"], group_keys=False).apply(diff_start_stop)
    return diff


def diff_start_stop(r: DataFrame) -> DataFrame:
    end = r.where(r["end"] == 1).dropna()
    begin = r.where(r["end"] == 0).dropna().reindex_like(other=end, method="pad")
    r["delay"] = end["t"] - begin["t"]
    return r


def decode_bytes(c: Series) -> int:
    return sum(x << i for i, x in enumerate(c))


def channel_labels(start, stop) -> [str]:
    return ["Channel %d" % c for c in range(start, stop)]


def decode_echo(df: Series) -> EchoEvent | None:
    if df["type"] is TraceType.Echo:
        return EchoEvent.try_from_int(df["data"])
    else:
        return None


# Entry functions
def decode_file():
    if len(argv) > 1:
        input = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = stdout
    decode(df).to_csv(path_or_buf=output)


def jitter():
    if len(argv) > 1:
        input = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = stdout
    jitter_events(decode_raw(df)).to_csv(path_or_buf=output)


def mean_delay():
    if len(argv) > 1:
        input = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = stdout
    mean_delay_events(decode_raw(df)).to_csv(path_or_buf=output)
