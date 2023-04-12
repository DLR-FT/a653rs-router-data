from sys import argv, stdout, stdin
from pandas import DataFrame, Series, read_csv
from enum import Enum
from typing import TextIO, TypeVar, Type

import matplotlib.pyplot as plt
import seaborn as sb
import pandas as pd
import numpy as np

Tt = TypeVar("Tt", bound="TraceType")


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
    def try_from_int(cls: Type[Tt], val: int) -> Tt | None:
        try:
            return cls(val)
        except:
            return None


Ee = TypeVar("Ee", bound="EchoEvent")


class EchoEvent(Enum):
    EchoRequestSend = 0  # Occurs when send is started
    EchoRequestReceived = 1  # Occurs when receive is complete
    EchoReplySend = 2  # Occurs when send is started
    EchoReplyReceived = 3  # Occurs when receive is complete

    @classmethod
    def try_from_int(cls: Type[Ee], val: int) -> Ee | None:
        try:
            return cls(val)
        except:
            return None


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
    df["end"] = df["end"].apply(bool)
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
    diff = diff.reset_index()
    diff["type"] = diff["type"].apply(TraceType.try_from_int)
    return diff


# Gets the jitter for each event.
def jitter_events(df: DataFrame) -> DataFrame:
    diff = delays_type(df)
    diff = diff.groupby(["type"], group_keys=False).var()
    diff = diff[["delay"]]
    diff = diff.reset_index()
    diff["type"] = diff["type"].apply(TraceType.try_from_int)
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


def channel_labels(start: int, stop: int) -> list[str]:
    return ["Channel %d" % c for c in range(start, stop)]


def decode_echo(df: Series) -> EchoEvent | None:
    if df["type"] is TraceType.Echo:
        return EchoEvent.try_from_int(df["data"])
    else:
        return None


def events_raw_delays(df: DataFrame) -> DataFrame:
    df = delays_type(decode_raw(df))
    df = df[["type", "delay"]]
    return df.dropna()


def parse_throughput_log(path: str | TextIO) -> Series:
    data = read_csv(path, sep=" ", header=None, usecols=[3], dtype=np.int64)
    throughput = data[3]
    return throughput

# Entry functions
def decode_file() -> None:
    if len(argv) > 1:
        input: TextIO | str = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output: TextIO | str = argv[2]
    else:
        output = stdout
    decode(df).to_csv(path_or_buf=output)


def jitter() -> None:
    if len(argv) > 1:
        input: TextIO | str = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output: TextIO | str = argv[2]
    else:
        output = stdout
    jitter_events(decode_raw(df)).to_csv(path_or_buf=output)


def mean_delay() -> None:
    if len(argv) > 1:
        input: TextIO | str = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output: TextIO | str = argv[2]
    else:
        output = stdout
    mean_delay_events(decode_raw(df)).to_csv(path_or_buf=output)


def raw_delays() -> None:
    if len(argv) > 1:
        input: TextIO | str = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output: TextIO | str = argv[2]
    else:
        output = stdout
    df = events_raw_delays(df)
    df["type"] = df["type"].apply(TraceType.try_from_int)
    df.to_csv(path_or_buf=output)


def throughput() -> None:
    direct = argv[1]
    output = "out.png"
    direct = parse_throughput_scenario(direct, "Direct")
    print(direct)

    local = argv[2]
    local = parse_throughput_scenario(local, "Local")
    df = pd.concat([direct, local])

    #local = parse_rtt_scenario(input, "Local")
    sb.relplot(data=df, x="Time", y="Throughput", hue="Scenario")
    plt.ylabel("Throughput [Byte/s]")
    plt.xlabel("Time [s]")
    plt.savefig(output)


def parse_rtt(path: str | TextIO) -> Series:
    df = DataFrame(columns=["Scenario", "RTT"])
    data = read_csv(path, sep=" ", header=None, usecols=[8], dtype=np.float64)
    return data[8]


def parse_throughput_scenario(path: str | TextIO, scenario: str) -> DataFrame:
    df = DataFrame(columns=["Scenario", "Throughput"])
    tp = parse_throughput_log(path)
    tp = tp - tp.shift()
    tp = tp.shift(-1).dropna()
    df["Throughput"] = tp
    df["Time"] = Series(range(1, len(tp) + 1))
    df["Scenario"] = scenario
    return df


def parse_rtt_scenario(path: str | TextIO, name: str) -> DataFrame:
    df = DataFrame(columns=["Scenario", "RTT"])
    rtt = parse_rtt(path)
    df["RTT"] = rtt.where(rtt < 250000.0, np.nan).dropna()
    df["Scenario"] = name
    return df


def rtt() -> None:
    data = DataFrame(columns=["Scenario", "RTT"])
    direct = parse_rtt_scenario(argv[1], "Direct")
    local = parse_rtt_scenario(argv[2], "Local")
    remote = parse_rtt_scenario(argv[3], "Remote")
    data = pd.concat([direct, local, remote])
    sb.catplot(data=data, x="Scenario", y="RTT", kind="strip")
    plt.savefig("out.png")
