import seaborn as sb
import matplotlib.pyplot as plt
import matplotlib
from sys import argv, stdin, stdout

from master_thesis_data import *


def plot_delays():
    if len(argv) > 1:
        input = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = "out.png"
    df = events_raw_delays(df)
    print(df)
    df = df.where(df["type"] == TraceType.NetworkSend)
    print(df)
    sb.boxplot(x=df["delay"])

    plt.savefig(output)

