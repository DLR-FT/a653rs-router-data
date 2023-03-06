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
    df["data"] = df[channel_labels(0, 4)].apply(decode_bytes, axis=1)
    df["event"] = df[channel_labels(4, 8)].apply(decode_bytes, axis=1)
    df["event"] = df["event"].apply(TraceEvent.try_from_int)
    df["echo"] = df[["event", "data"]].apply(decode_echo, axis=1)
    df = df[["Time [s]", "event", "data", "echo"]]
    df = df.loc[df["event"].shift() != df["event"]]
    return df


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
