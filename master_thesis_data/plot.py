import seaborn as sb
import matplotlib.pyplot as plt
import matplotlib
from sys import argv, stdin, stdout
from typing import TextIO

from master_thesis_data import *


def plot_delays() -> None:
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
    df = df.where(df["delay"].between(0, 0.005) & (df["type"] != TraceType.Echo.value))
    df["type"] = df["type"].apply(trace_type_name)
    print(len(df))
    sb.boxplot(data=df, x="delay", y="type")
    plt.subplots_adjust(left=0.3)
    plt.savefig(output)
