from sys import argv, stdout, stdin
from pandas import DataFrame, Series, read_csv
from enum import Enum
from typing import TextIO, TypeVar, Type
from .simulator import Simulation, Schedule, Partition, PartitionWindow, simulate
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sb
import pandas as pd
import numpy as np

Tt = TypeVar("Tt", bound="TraceType")


def trace_type_name(val: int) -> str | None:
    t = TraceType.try_from_int(val)
    if t:
        return t.name
    else:
        return None


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

    sb.catplot(data=df, y="Throughput", x="Scenario", kind="bar")
    plt.ylabel("Throughput [Byte/s]")
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
    df["RTT"] = rtt.dropna()
    df["RTT"] = df["RTT"] / 1000
    df["Scenario"] = name
    print(df)
    return df


def rtt() -> None:
    data = DataFrame(columns=["Scenario", "RTT"])
    direct = parse_rtt_scenario(argv[1], "Direct")
    local = parse_rtt_scenario(argv[2], "Local")
    remote = parse_rtt_scenario(argv[3], "Remote")
    output = argv[4]
    data = pd.concat([direct, local, remote])
    sb.set_theme(style="whitegrid", palette="gray")
    sb.stripplot(data=data, x="Scenario", y="RTT", color="k", size=4, marker="D")
    plt.ylabel("RTT [ms]")
    plt.savefig(output, backend="pgf")


def plot_delays_apex_ports() -> None:
    if len(argv) > 1:
        input: TextIO | str = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = "out.png"
    df = events_raw_delays(df)
    df = df.where(
        (df["type"] == TraceType.ApexReceive.value)
        | (df["type"] == TraceType.ApexSend.value)
    )
    df = df.dropna()
    df["type"] = df["type"].apply(trace_type_name)
    print(df)
    sb.boxplot(data=df, x="delay", y="type")
    plt.subplots_adjust(left=0.3)
    plt.savefig(output)


def plot_delays_network() -> None:
    if len(argv) > 1:
        input: TextIO | str = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = "out.png"
    df = events_raw_delays(df)
    df = df.dropna()
    df = df.where(
        (df["type"] == TraceType.NetworkSend.value)
        | (df["type"] == TraceType.NetworkReceive.value)
    )
    df["type"] = df["type"].apply(trace_type_name)
    print(df)
    sb.boxplot(data=df, x="delay", y="type")
    plt.subplots_adjust(left=0.3)
    plt.savefig(output)


def rtt_var() -> None:
    input = argv[1]
    output = argv[2]
    direct = parse_rtt(argv[1]).var()
    local = parse_rtt(argv[2]).var()
    remote = parse_rtt(argv[3])
    remote = remote.where(remote < 20000).dropna().var()
    data = DataFrame(
        {"Scenario": ["Direct", "Local", "Remote"], "RTT": [direct, local, remote]}
    )
    g = sb.catplot(data=data, x="Scenario", y="RTT", kind="bar")
    plt.ylabel("Var(RTT)")
    plt.savefig("out.png")


def diff(s: Series) -> np.int64:
    return s - s.shift(-1)


def diff_scenario(s: Series, sc: str) -> DataFrame:
    df = DataFrame(columns=["Scenario", "IPDV"])
    df["IPDV"] = s
    df["Scenario"] = sc
    print(df)
    return df


def ipdv() -> None:
    input = argv[1]
    direct = diff_scenario(diff(parse_rtt(argv[1])), "Direct")
    local = diff_scenario(diff(parse_rtt(argv[2])), "Local")
    remote = parse_rtt(argv[3])
    remote = diff_scenario(diff(remote.where(remote < 20000).dropna()), "Remote")
    data = pd.concat([direct, local, remote])
    print(data)
    sb.catplot(data=data, y="Scenario", x="IPDV", kind="box")
    plt.xlabel("IPDV [us]")
    plt.savefig("out.png")


def rtt_timeline() -> None:
    remote = parse_rtt(argv[1])
    rtt = remote.where(remote < 20000).dropna() / 1000.0
    df = DataFrame({"t [s]": rtt.index, "RTT [ms]": rtt})
    print(df)
    sb.relplot(data=df, x="t [s]", y="RTT [ms]", kind="line", aspect=4)
    plt.savefig("out")


def create_simulation(
    duration: int,
    client_inter_mf_delay: int = 0,
    client_start: int = 0,
    server_inter_mf_delay: int = 0,
    server_start: int = 0,
) -> Simulation:
    return Simulation(
        client=Schedule(
            major_frame=2000,
            inter_mf_delay=client_inter_mf_delay,
            partition_windows=[
                PartitionWindow(partition=Partition.client, offset=0, duration=500),
                PartitionWindow(partition=Partition.io, offset=500, duration=1500),
            ],
        ),
        server=Schedule(
            major_frame=2000,
            inter_mf_delay=server_inter_mf_delay,
            partition_windows=[
                PartitionWindow(partition=Partition.server, offset=0, duration=500),
                PartitionWindow(partition=Partition.io, offset=500, duration=1500),
            ],
        ),
        transmission_delay=1000,
        apex_delay=250,
        client_start=client_start,
        server_start=server_start,
        step=1,
        duration=(duration * 1000**2),
        echo_period=1_000_000,
    )


def simulate_rtt(duration: int=300) -> DataFrame:
    normal = create_simulation(
        duration=duration,
        client_inter_mf_delay=0,
        client_start=0,
        server_inter_mf_delay=0,
        server_start=0,
    )

    large_rtt = create_simulation(
        duration=duration,
        client_inter_mf_delay=1111,
        server_inter_mf_delay=0,
        client_start=0,
        server_start=0,
    )
    level_jump = create_simulation(
        duration=duration,
        client_inter_mf_delay=0,
        server_inter_mf_delay=0,
        client_start=1111,
        server_start=0,
    )
    results = []
    for label, sim in [
        ("Normal", normal),
        ("Different Inter-MAF", large_rtt),
        ("Different starts", level_jump),
    ]:
        dfsim = DataFrame(
            data=zip(range(1, duration + 1), simulate(sim)),
            columns=["Time [s]", "RTT [us]"],
        )
        dfsim["Label"] = label
        results.append(dfsim)
    df = pd.concat(results)

    return df


def plot_simulate_rtt() -> None:
    out_path: Path = argv[1]
    if len(argv) > 2:
        duration = int(argv[2])
        df = simulate_rtt(duration)
    else:
        df = simulate_rtt()

    print("Done simulating. Plotting ...")
    sb.set_theme(style="whitegrid", palette="gray")
    ax = sb.relplot(
        data=df,
        x="Time [s]",
        y="RTT [us]",
        hue="Label",
        style="Label",
        kind="line",
        aspect=1,
        facet_kws=dict(legend_out=False),
    )
    sb.move_legend(
        ax, "lower right",
        bbox_to_anchor=(.7, .18),
        title=None,
        frameon=True,
    )
    plt.savefig(out_path, backend="pgf")

def csv_simulate_rtt() -> None:
    out_path: Path = argv[1]
    if len(argv) > 1:
        duration = int(argv[2])
        df = simulate_rtt(duration)
    else:
        df = simulate_rtt()

    return df.to_csv(out_path)
