import sys, os, json, glob, gzip, pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FormatStrFormatter
import util

from treeck import *
from treeck.xgb import addtree_from_xgb_model

plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['text.usetex'] = False
plt.rcParams['font.size'] = 9
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['xtick.major.width'] = 0.5
plt.rcParams['ytick.major.width'] = 0.5
plt.rcParams['xtick.minor.width'] = 0.5
plt.rcParams['ytick.minor.width'] = 0.5
plt.rcParams['axes.unicode_minus'] = False

#import seaborn as sns

RESULT_DIR = "tests/experiments/scale"

def plot_output1(*args):
    filenames = [os.path.basename(f) for f in args]
    jsons = []
    for f in args:
        if f.endswith(".gz"):
            with gzip.open(f, "r") as fh:
                jsons.append(json.load(fh))
        else:
            with open(f) as fh:
                jsons.append(json.load(fh))

    k = 0
    for oos in zip(*jsons):
        n = len(oos)

        fig, axs = plt.subplots(n, 1, figsize=(8, 5*n), sharey=True, sharex=True)

        try: axs[0]
        except:
            axs = np.array([axs])

        oot_pos = 0
        for oo, ax, name in zip(oos, axs, filenames):
            print(f"\n== {name}: num_trees {oo['num_trees']}, depth {oo['depth']} ==")

            # A*
            tb0 = oo["a*"]["bounds_times"]
            b0  = [x[1]-x[0] for x in oo["a*"]["bounds"]]
            ts0 = oo["a*"]["sol_times"]
            s0  = [x[1]-x[0] for x in oo["a*"]["solutions"]]

            if len(s0) > 0:
                print("A* optimal:", s0[0])
                ax.axhline(s0[0], color="gray", linestyle=(0, (2, 4)), linewidth=1, label="Solution")
                b0.append(s0[0])
                tb0.append(ts0[0])
                b0 = [x for x in b0 if x >= s0[0]]
                tb0 = [y for x, y in zip(b0, tb0) if x >= s0[0]]
            else:
                print("A* best:", min(b0))
                ax.axhline(min(b0), color="gray", linestyle=(0, (2, 4)), linewidth=1, label="A* best")
            ax.plot(tb0, b0, label="A* upper")
            #if "best_solution_box" in oo["a*"]:
            #    print("A* sol: ", oo["a*"]["best_solution_box"])

            # ARA*
            tb1 = oo["ara*"]["bounds_times"]
            if len(oo["ara*"]["solutions"]) > 0:
                b1  = [x[1]-x[0] for x in oo["ara*"]["bounds"]]
                ts1 = oo["ara*"]["sol_times"]
                s  = [x[1]-x[0] for x in oo["ara*"]["solutions"]]
                s10  = [x[0] for x in oo["ara*"]["solutions"]]
                s11  = [x[1] for x in oo["ara*"]["solutions"]]
                e1  = oo["ara*"]["epses"]
                d1 = oo["ara*"]["total_time"]
                #s10f, s11f, ts1f, e1f = util.filter_solutions(s10, s11, ts1, e1)
                #s1f = [b-a for a, b in zip(s10f, s11f)]
                #b1f = util.flatten_ara_upper(s1f, e1f)

                l1, = ax.plot(ts1, s, ".-", label="ARA* lower")
                #ax.plot(ts1f, b1f, label="ARA* upper", ls=(0, (2, 2)), c=l1.get_color())
                #ylim_lo, ylim_hi = ax.get_ylim()
                #ax.plot(tb1, b1, ".", markersize=1.5, c=l1.get_color())
                #ax.set_ylim(bottom=ylim_lo)
                print("ARA* best:", max(s), "eps:", max(e1))
                #if "best_solution_box" in oo["ara*"]:
                #    print("ARA* sol: ", oo["ara*"]["best_solution_box"])
                if len(s0) == 0:
                    ax.axhline(max(s), color="gray", ls=(4, (2, 4)), lw=1, label="ARA* best")

            # merge
            if "merge" in oo:
                b2 = [x[1][1]-x[0][0] for x in oo["merge"]["bounds"]]
                t2 = oo["merge"]["times"]
                oot = oo["merge"]["oot"]
                oom = oo["merge"]["oom"]
                tt = oo["merge"]["total_time"]
                mt = oo["max_time"]
                mm = oo["max_memory"]
                l2, = ax.plot(t2, b2, "x-", label="Merge")
                if oot or oom:
                    label = f"OOM ({mm/(1024*1024*1024):.1f}gb, {tt:.0f}s)" if oom else f"OOT ({mt}s)"
                    oot_pos = max(oot_pos, max(tb0), max(tb1), max(t2))
                    ax.plot([t2[-1], oot_pos], [b2[-1], b2[-1]], ":", color=l2.get_color())
                    ax.text(oot_pos, b2[-1], label, horizontalalignment='right',
                            verticalalignment='bottom', color=l2.get_color())

                print("merge best:", min(b2), "OOT:", oot, "OOM:", oom, "optimal", oo["merge"]["optimal"])

            # plot details
            ax.set_title(f"num_trees={oo['num_trees']}, depth={oo['depth']} ({name}, {k})")
            ax.legend()
            ax.set_xlabel("time");
            ax.set_ylabel("model output");
            ax.set_ylim(top=1.1*max(b0));
            ax.xaxis.set_tick_params(which='both', labelbottom=True)

            k+=1

        plt.show()

def plot_output2(f, i):
    fig, ax = plt.subplots(1, 1, figsize=(4, 2.5), sharey=True, sharex=True)
    with open(f) as fh:
        oo = json.load(fh)[i]

    print(list(oo["a*"].keys()))

    # A*
    tb0 = oo["a*"]["bounds_times"]
    b0  = [x[1]-x[0] for x in oo["a*"]["bounds"]]
    ts0 = oo["a*"]["sol_times"]
    s0  = [x[1]-x[0] for x in oo["a*"]["solutions"]]

    if len(s0) > 0:
        print("A* optimal:", s0[0])
        ax.axhline(s0[0], color="gray", linestyle=(0, (2, 4)), linewidth=1, label="Solution")
        b0.append(s0[0])
        tb0.append(ts0[0])
        b0 = [x for x in b0 if x >= s0[0]]
        tb0 = [y for x, y in zip(b0, tb0) if x >= s0[0]]
    else:
        print("A* best:", min(b0))
        ax.axhline(min(b0), color="gray", linestyle=(0, (2, 4)), linewidth=1, label="A* best")
    ax.plot(tb0, b0, label="A* upper")
    if "best_solution_box" in oo["a*"]:
        print("A* sol: ", oo["a*"]["best_solution_box"])

    # ARA*
    tb1 = oo["ara*"]["bounds_times"]
    if len(oo["ara*"]["solutions"]) > 0:
        b1  = [x[1]-x[0] for x in oo["ara*"]["bounds"]]
        ts1 = oo["ara*"]["sol_times"]
        s10  = [x[0] for x in oo["ara*"]["solutions"]]
        s11  = [x[1] for x in oo["ara*"]["solutions"]]
        e1  = oo["ara*"]["epses"]
        d1 = oo["ara*"]["total_time"]
        s10f, s11f, ts1f, e1f = util.filter_solutions(s10, s11, ts1, e1)
        s1f = [b-a for a, b in zip(s10f, s11f)]
        b1f = util.flatten_ara_upper(s1f, e1f)

        l1, = ax.plot(ts1f, s1f, ".-", label="ARA* lower")
        #ax.plot(ts1f, b1f, label="ARA* upper", ls=(0, (2, 2)), c=l1.get_color())
        #ylim_lo, ylim_hi = ax.get_ylim()
        #ax.plot(tb1, b1, ".", markersize=1.5, c=l1.get_color())
        #ax.set_ylim(bottom=ylim_lo)
        print("ARA* best:", max(s1f), "eps:", max(e1))
        if "best_solution_box" in oo["ara*"]:
            print("ARA* sol: ", oo["ara*"]["best_solution_box"])
        if len(s0) == 0:
            ax.axhline(max(s1f), color="gray", ls=(4, (2, 4)), lw=1, label="ARA* best")

    # merge
    if "merge" in oo:
        b2 = [x[1][1]-x[0][0] for x in oo["merge"]["bounds"]]
        t2 = oo["merge"]["times"]
        oot = oo["merge"]["oot"]
        oom = oo["merge"]["oom"]
        tt = oo["merge"]["total_time"]
        mt = oo["max_time"]
        mm = oo["max_memory"]
        l2, = ax.plot(t2, b2, "x-", label="Merge")
        oot_pos = 0
        if oot or oom:
            label = f"OOM ({mm/(1024*1024*1024):.1f}gb, {tt:.0f}s)" if oom else f"OOT ({mt}s)"
            oot_pos = max(oot_pos, max(tb0), max(tb1), max(t2))
            ax.plot([t2[-1], oot_pos], [b2[-1], b2[-1]], ":", color=l2.get_color())
            ax.text(oot_pos, b2[-1], label, horizontalalignment='right',
                    verticalalignment='bottom', color=l2.get_color())

        print("merge best:", min(b2), "OOT:", oot, "OOM:", oom, "optimal", oo["merge"]["optimal"])

    # plot details
    ax.set_title(f"num_trees={oo['num_trees']}, depth={oo['depth']} ({os.path.basename(f)})")
    ax.legend()
    ax.set_xlabel("time");
    ax.set_ylabel("model output");
    #ax.set_ylim(bottom=min(b1), top=1.1*max(b0));
    ax.xaxis.set_tick_params(which='both', labelbottom=True)
    plt.show()

def plot_output3(file):
    with open(file) as fh:
        oo = json.load(fh)

    c1 = (0.122, 0.467, 0.706)
    c2 = (0.173, 0.627, 0.173)

    m = {}
    for num_trees in [50, 100, 200, 400]:
        ooo = [o for o in oo if o["depth"] in [4, 6, 8] and o["num_trees"] == num_trees]
        if len(oo) == 0: continue
        m[num_trees] = ooo

    fig, axs = plt.subplots(1, len(m), sharey=True, figsize=(3.4, 1.4))

    for i, ((num_trees, oo), ax) in enumerate(zip(m.items(), axs)):
        xs = [o["depth"] for o in oo]
        A = [util.get_best_astar(o["a*"]) for o in oo]
        ARA = [max(map(lambda b: b[1], o["ara*"]["solutions"]))
                if len(o["ara*"]["solutions"]) > 0 else -np.inf
                for o in oo]
        ARAeps = [o["ara*"]["epses"][-1]
                if len(o["ara*"]["epses"]) > 0 else 0.0
                for o in oo]
        mergelo = [o["merge"]["bounds"][-1][1][0] for o in oo]
        mergehi = [o["merge"]["bounds"][-1][1][1] for o in oo]

        relA = [1.0 for a in A]
        relARA = [ara/a for a, ara in zip(A, ARA)]
        relmlo = [m/a for a, m in zip(A, mergelo)]
        relmhi = [m/a for a, m in zip(A, mergehi)]

        xxs = np.arange(len(xs))

        def interval_ours(ax, x, lo, hi, lw=1):
            ax.vlines(x, lo, hi, lw=lw, color=c1)
            ax.hlines(lo, x-0.1, x+0.1, lw=lw, color=c1)
            ax.hlines(hi, x-0.1, x+0.1, lw=lw, color=c1)

        def interval_merge(ax, x, lo, hi, lw=1):
            ax.vlines(x, lo, hi, lw=lw, color=c2, linestyles="dotted")
            ax.hlines(lo, x-0.1, x+0.1, lw=lw, color=c2)
            ax.hlines(hi, x-0.1, x+0.1, lw=lw, color=c2)

        for x, lo, hi in zip(xxs, ARA, A):
            interval_ours(ax, x-0.1, lo, hi, lw=0.8)

        for x, lo, hi in zip(xxs, mergelo, mergehi):
            interval_merge(ax, x+0.1, lo, hi, lw=0.8)

        #ax.set_xlabel("trees")
        ax.set_title(f"M = {num_trees}")

        ax.set_xticks(xxs)
        ax.set_yticks([-900, 0, 900])
        #ax.set_xticks(xxs, minor=True)

        #ax.xaxis.set_major_locator(FixedLocator(range(1, len(xs), 2)))
        #ax.xaxis.set_minor_locator(FixedLocator(range(0, len(xs), 2)))
        #ax.xaxis.set_minor_formatter(FormatStrFormatter("%d"))
        #ax.tick_params(which='major', pad=12, axis='x')
        ax.set_xticklabels([str(s) for i, s in enumerate(xs)])
        #ax.set_xticklabels([str(s) for i, s in enumerate(xs) if i%2==1])
        #ax.set_xticklabels([str(s) for i, s in enumerate(xs) if i%2==0], minor="True")

    #axs[0].set_ylabel("model output")
    axs[0].legend([
            Line2D([0], [0], color=c1, lw=1),
            Line2D([0], [0], ls=":", color=c2, lw=1.0)
        ], ["\\ouralg{}", "\\merge{}"],
        bbox_to_anchor=(0.8, 1.20, len(m)*1.08-0.5, 0.0), loc='lower left', ncol=2,
        mode="expand", borderaxespad=0.0, frameon=False)
    plt.figtext(0.01, 0.85, "model")
    plt.figtext(0.01, 0.78, "output")
    plt.figtext(0.5, 0.0, "tree depth", horizontalalignment="center")
    #plt.tight_layout()
    plt.subplots_adjust(top=0.75, bottom=0.22, left=0.15, right=0.95)
    plt.savefig("/tmp/unconstrained.svg")
    if "IMG_OUTPUT" in os.environ:
        plt.savefig(os.path.join(os.environ["IMG_OUTPUT"], "unconstrained.svg"))
        print(f"wrote svg to {os.environ['IMG_OUTPUT']}")
    plt.show()

def plot_output4(file, depth):
    fig, ax = plt.subplots(1, 1)#, figsize=(4, 2.5))
    with open(file) as fh:
        oo = json.load(fh)
    oo = [o for o in oo if o["depth"] == depth]

    x = [o["num_trees"] for o in oo]
    #A = [max(o["a*"]["cliques"]) for o in oo]
    #ARA = [max(o["ara*"]["cliques"]) for o in oo]
    #merge = [max(o["merge"]["vertices"]) for o in oo]

    A = [max(o["a*"]["memory"]) / (1024*1024) for o in oo]
    ARA = [max(o["ara*"]["memory"]) / (1024*1024) for o in oo]
    merge = [max(o["merge"]["memory"]) / (1024*1024) for o in oo]

    At = [max(o["a*"]["bounds_times"]) for o in oo]
    ARAt = [max(o["ara*"]["bounds_times"]) for o in oo]
    merget = [max(o["merge"]["times"]) for o in oo]
    Apt = [a/t for a, t in zip(A, At)]
    ARApt = [a/t for a, t in zip(ARA, ARAt)]
    mergept = [a/t for a, t in zip(merge, merget)]

    print(Apt)
    print(mergept)

    #ax.semilogx(x, A, label="A*")
    #ax.semilogx(x, ARA, label="ARA*")
    #ax.semilogx(x, merge, label="merge")
    ax.loglog(x, Apt, label="A*")
    ax.loglog(x, ARApt, label="ARA*")
    ax.loglog(x, mergept, label="merge")

    ax.set_xticks(x)
    ax.set_xticks(x, minor=True)
    ax.set_xticklabels([str(s) for s in x])
    
    ax.set_xlabel("trees")
    ax.set_ylabel("Mb per sec.")
    ax.set_title("memory consumption per second")

    plt.legend()
    plt.show()

def plot_output5(pattern):
    oo = []
    for f in glob.glob(f"tests/experiments/scale/{pattern}"):
        with open(f) as fh:
            oo += json.load(fh)
    print(len(oo), "records")
    
    fig, ax = plt.subplots(1, 1)#, figsize=(4, 2.5))

    print(list(oo[0]["a*"].keys()))
    print(list(oo[0]["ara*"].keys()))

    num_vertices = [o["a*"]["num_vertices0"] + o["a*"]["num_vertices1"] for o in oo]
    A = [util.get_best_astar(o["a*"]) for o in oo]
    ARA = [max(map(lambda b: b[1]-b[0], o["ara*"]["solutions"]))
            if len(o["ara*"]["solutions"]) > 0
            else -np.inf
            for o in oo]
    merge = [min(map(lambda b: b[1], o["merge"]["bounds"])) for o in oo]

    A, ARA, merge = np.array(A), np.array(ARA), np.array(merge)

    #l0, = ax.plot(num_vertices, [(a-ara)/a for a, ara in zip(A, ARA)], ".", alpha=0.2, zorder=-1, markersize=5)
    l1, = ax.plot(num_vertices, [(m-a) for a, m in zip(A, merge)], ".", alpha=0.5, zorder=-1, markersize=5)
    #l0, = ax.plot(num_vertices, [a-ara for a, ara in zip(A, ARA)], ".", alpha=0.05, zorder=-1, markersize=20)
    #l1, = ax.plot(num_vertices, [m-a for a, m in zip(A, merge)], ".", alpha=0.05, zorder=-1, markersize=20)

    #bins = np.linspace(min(num_vertices), max(num_vertices), 20)
    #bin_width = bins[1]-bins[0]
    #assignments = np.digitize(num_vertices, bins)
    #meanA = [np.mean(merge[assignments==int(bin)]-A[assignments==int(bin)]) for bin in range(len(bins))]
    #stdA = [np.std(merge[assignments==int(bin)]-A[assignments==int(bin)]) for bin in range(len(bins))]

    #ax.bar(bins, meanA, 0.45*bin_width, yerr=stdA, color=l1.get_color())

    #for x, a, ara in zip(num_vertices, A, ARA):
    #    ax.plot([x, x], [a, ara], ".-b", alpha=0.25)
    #for x, a, m in zip(num_vertices, A, merge):
    #    ax.plot([x, x], [a, m], "-b", alpha=0.25)

    ax.set_xlabel("number of reachable leafs")
    ax.set_ylabel("(merge - A*) bounds (> 0 means A* wins)")
    ax.set_title("merge vs A*: how do upper bounds compare")
    plt.show()

def time_to_beat_merge(o):
    A = [b[1]-b[0] for b in o["a*"]["bounds"]]
    At = o["a*"]["bounds_times"]
    merge = o["merge"]["bounds"][-1]
    merge = merge[1][1] - merge[0][0]

    #print(A)
    #print(At)
    #print(merge)

    try:
        return [at for a, at in zip(A, At) if a < merge][0]
    except:
        return np.inf

def plot_output6(pattern):
    oo = []
    for f in glob.glob(f"tests/experiments/scale/{pattern}"):
        with open(f) as fh:
            oo += json.load(fh)
    print(len(oo), "records")

    fig, (ax, ax2) = plt.subplots(2, 1, sharex=True,
            gridspec_kw={"height_ratios": [4, 1]})#, figsize=(4, 2.5))

    num_vertices = [o["a*"]["num_vertices0"] + o["a*"]["num_vertices1"] for o in oo]
    At = [util.get_best_astar(o["a*"]) for o in oo]
    mt = [o["merge"]["times"][-1] for o in oo]
    ms = [o["merge"]["vertices"][-1] for o in oo]
    Ab = [time_to_beat_merge(o) for o in oo]

    print("mean time to beat time", np.mean(Ab))

    ratio = np.array([m-a for a, m in zip(Ab, mt)])

    l0, = ax.plot(num_vertices, ratio, ".", alpha=0.5, zorder=20, markersize=5)
    ax.plot(num_vertices, Ab, ".", alpha=0.5, zorder=20, markersize=5)
    ax2.plot(num_vertices, [len(o["merge"]["bounds"]) for o in oo], ".", markersize=5,
            color="gray", zorder=10, alpha=0.5)

    #bins = np.linspace(min(num_vertices), max(num_vertices), 10)
    #bin_width = bins[1]-bins[0]
    #assignments = np.digitize(num_vertices, bins)

    #meanA = [np.mean(ratio[assignments==int(bin)]) for bin in range(len(bins))]
    #meanA = [sum(assignments==int(bin)) for bin in range(len(bins))]
    #stdA = [np.std(ratio[assignments==int(bin)]) for bin in range(len(bins))]

    #for b in range(5, len(bins)):
    #    data = ratio[assignments==int(b)]
    #    print(data)
    #    ax.boxplot(data)
    #    break

    #ax.bar(bins, meanA, 0.45*bin_width)

    #sns.set(style="whitegrid", palette="pastel", color_codes=True)
    #data = pd.DataFrame({"bin": assignments, "value": ratio})
    #sns.violinplot(x="bin", y="value", data=data)
    ax2.set_xlabel("number of reachable leafs")
    ax.set_ylabel("(merge - A*) time (> 0 means A* wins)")
    ax2.set_ylabel("merge level")
    ax2.set_yticks(range(4, 9))
    ax.set_title("merge vs A*: time for A* to get to best bound of merge")
    plt.show()

def plot_robust():
    cache_file = f"/tmp/temporary_mnist_robust_cache.h5"
    df = pd.read_hdf(cache_file) # created by scale-table.py

    dfg = df.groupby(["example_seed", "example_i", "source", "follow_a*", "target"])
    index = list(dfg.indices.keys())
    np.random.shuffle(index)

    def plotit(dfg, i0, ax=None):
        lw=0.7
        i1 = (i0[0], i0[1], i0[2], False, i0[4]) # follow merge
        g0 = dfg.get_group(i0)
        g1 = dfg.get_group(i1)

        n = len(g0)

        if ax is None:
            fig, ax = plt.subplots(1, 1)

        l0, = ax.plot(g0["delta"].values, label="ours", lw=lw, zorder=5)
        #ax.plot(g0["up"].values, ":", c=l0.get_color(), lw=1)
        #ax.plot(g0["lo"].values, ":", c=l0.get_color(), lw=1)
        ax.fill_between(range(n), g0["lo"].values, g0["up"].values, color=l0.get_color(), alpha=0.2, linewidth=0)

        l1, = ax.plot(g1["delta"].values, label="merge", lw=lw, zorder=2)
        #ax.plot(g1["up"].values, ":", c=l1.get_color(), lw=1)
        #ax.plot(g1["lo"].values, ":", c=l1.get_color(), lw=1)
        ax.fill_between(range(n), g1["lo"].values, g1["up"].values, color=l1.get_color(), alpha=0.2, linewidth=0)

        ax.set_title(f"{i0[2]} vs. {i0[4]}")
        ax.set_yticks(range(0, 21, 5))
        ax.set_xticks(range(0, n, 2))
        ax.set_xticks(range(0, n, 1), minor=True)

#    for i0 in index:
#        if not i0[3]: continue # only follow a*
#        print(i0)
#        plotit(dfg, i0)
#        plt.show()

    interesting = [
            #(11, 10137, 3, True, 0),
            #(11, 49735, 2, True, 1),
            (34, 40466, 8, True, 6),
            (34, 38435, 2, True, 1),
            ]

    # interesting ones
    fig, axs = plt.subplots(1, len(interesting), figsize=(3.5, 1.2), sharey=True)
    plt.subplots_adjust(top=0.8, bottom=0.28, left=0.1, right=0.95, wspace=0.1)
    for i0, ax in zip(interesting, axs):
        print(i0)
        plotit(dfg, i0, ax)
    plt.figtext(0.05, 0.85, "\$\\delta\$")
    plt.figtext(0.5, 0.00, "binary search step", horizontalalignment="center")
    axs[0].legend(frameon=False)
    if "IMG_OUTPUT" in os.environ:
        plt.savefig(os.path.join(os.environ["IMG_OUTPUT"], "robust.svg"))
    plt.show()

def plot_examples():
    lw=0.7
    examples = [
            #("tests/experiments/scale/covtype/all4g120s", 9),
            ("tests/experiments/scale/covtype/rnd4g30s10N_1", 152),
            ("tests/experiments/scale/covtype/rnd4g30s10N_1", 165)
            ]
    fig, axs = plt.subplots(1, len(examples), figsize=(3.4, 1.2), sharey=False, sharex=False)
    oo = []
    for f, i in examples:
        with open(f) as fh:
            o = json.load(fh)[i]
            oo.append(o)

    for o, ax in zip(oo, axs):
        # A*
        tb0 = o["a*"]["bounds_times"]
        b0  = [x[1]-x[0] for x in o["a*"]["bounds"]]
        ts0 = o["a*"]["sol_times"]
        s0  = [x[1]-x[0] for x in o["a*"]["solutions"]]

        if len(s0) > 0:
            print("A* optimal:", s0[0])
            ax.axhline(s0[0], color="gray", linestyle=":", linewidth=lw, label="Solution")
            b0.append(s0[0])
            tb0.append(ts0[0])
            b0 = [x for x in b0 if x >= s0[0]]
            tb0 = [y for x, y in zip(b0, tb0) if x >= s0[0]]
        else:
            print("A* best:", min(b0))
            ax.axhline(min(b0), color="gray", linestyle=":", linewidth=lw, label="A* best")
        l0, = ax.plot(tb0, b0, lw=lw, label="A* upper")
        #if "best_solution_box" in o["a*"]:
        #    print("A* sol: ", o["a*"]["best_solution_box"])

        # ARA*
        tb1 = o["ara*"]["bounds_times"]
        if len(o["ara*"]["solutions"]) > 0:
            b1  = [x[1]-x[0] for x in o["ara*"]["bounds"]]
            ts1 = o["ara*"]["sol_times"]
            s10  = [x[0] for x in o["ara*"]["solutions"]]
            s11  = [x[1] for x in o["ara*"]["solutions"]]
            e1  = o["ara*"]["epses"]
            d1 = o["ara*"]["total_time"]
            s10f, s11f, ts1f, e1f = util.filter_solutions(s10, s11, ts1, e1)
            s1f = [b-a for a, b in zip(s10f, s11f)]
            b1f = util.flatten_ara_upper(s1f, e1f)

            l1, = ax.plot(ts1f, s1f, ".-", lw=lw, ms=2.0, label="ARA* lower")
            #ax.plot(ts1f, b1f, label="ARA* upper", ls=(0, (2, 2)), c=l1.get_color())
            #ylim_lo, ylim_hi = ax.get_ylim()
            #ax.plot(tb1, b1, ".", markersize=1.5, c=l1.get_color())
            #ax.set_ylim(bottom=ylim_lo)
            print("ARA* best:", max(s1f), "eps:", max(e1))
            #if "best_solution_box" in o["ara*"]:
            #    print("ARA* sol: ", o["ara*"]["best_solution_box"])
            if len(s0) == 0:
                ax.axhline(max(s1f), color="gray", ls=":", lw=lw, label="ARA* best")

        # merge
        if "merge" in o:
            b2 = [x[1][1]-x[0][0] for x in o["merge"]["bounds"]]
            t2 = o["merge"]["times"]
            oot = o["merge"]["oot"]
            oom = o["merge"]["oom"]
            tt = o["merge"]["total_time"]
            mt = o["max_time"]
            mm = o["max_memory"]
            l2, = ax.plot(t2, b2, "x-", lw=lw, ms=3.0, label="Merge")
            oot_pos = 0
            if oot or oom:
                label = f"OOM ({mm/(1024*1024*1024):.1f}gb, {tt:.0f}s)" if oom else f"OOT ({mt}s)"
                oot_pos = max(oot_pos, max(tb0), max(tb1), max(t2))
                ax.plot([t2[-1], oot_pos], [b2[-1], b2[-1]], ":", color=l2.get_color(), lw=lw)
                ax.text(oot_pos, b2[-1]*1.1, label, horizontalalignment='right',
                        verticalalignment='bottom', color=l2.get_color())

            print("merge best:", min(b2), "OOT:", oot, "OOM:", oom, "optimal", o["merge"]["optimal"])

    # plot details
    #ax.set_title(f"num_trees={o['num_trees']}, depth={o['depth']} ({os.path.basename(f)})")
    #ax.legend()
    #ax.set_xlabel("time");
    #ax.set_ylabel("model output");
    ##ax.set_ylim(bottom=min(b1), top=1.1*max(b0));
    #ax.xaxis.set_tick_params(which='both', labelbottom=True)
    plt.subplots_adjust(top=0.8, bottom=0.16, left=0.15, right=0.95,wspace=0.4)
    axs[0].legend([l0, l1, l2], ["up", "lo", "merge"],
        bbox_to_anchor=(0.4, 1.0, 2.0, 1.0), loc='lower left',
        ncol=3, mode="expand", borderaxespad=0.0, frameon=False)
    plt.figtext(0.0, 0, "Time [s]")
    plt.figtext(0.0, 0.85, "Output")
    plt.savefig("/tmp/examples.svg")
    if "IMG_OUTPUT" in os.environ:
        plt.savefig(os.path.join(os.environ["IMG_OUTPUT"], "examples.svg"))
    plt.show()

def youtube(file):
    result_dir = "tests/experiments/scale/youtube"
    with open(os.path.join(result_dir, file)) as f:
        oo = json.load(f)

    for i, o in enumerate(oo):
        num_trees, depth = o["num_trees"], o["depth"]
        model_name = f"youtube-{num_trees}-{depth}.xgb"
        meta_name = f"youtube-{num_trees}-{depth}.meta"
        with open(os.path.join(result_dir, model_name), "rb") as f:
            model = pickle.load(f)
        with open(os.path.join(result_dir, meta_name), "r") as f:
            meta = json.load(f)

        columns = meta["columns"]
        at = addtree_from_xgb_model(model)
        #print("at", at)
        #print("splits", at.get_splits())
        at.base_score = 0.0
        feat2id_dict = {v: i for i, v in enumerate(columns)}
        feat2id = lambda x: feat2id_dict[x]
        id2feat = lambda i: columns[i]
        featinfo = FeatInfo(AddTree(), at, set(), True)
        fixed_feat_ids = [feat2id(w) for w in o["fixed_words"]]
        fixed_ids = [featinfo.get_id(1, i) for i in fixed_feat_ids]

        used_feat_ids = featinfo.feat_ids1()
        asol = {int(k) : v for k, v in o["ara*"]["best_solution_box"].items()}
        for i in set(fixed_ids).difference(set(asol.keys())):
            asol[i] = (1.0, np.inf)
        asol = [used_feat_ids[i] for i, v in asol.items() if v[0] == 1.0]
        asol_txt = [columns[i] for i in asol]

        example = [0.0 for x in columns]
        for i in asol:
            example[i] = 1.0
        example0 = example.copy()
        for i in set(asol).difference(fixed_feat_ids):
            example0[i] = 0.0
        print(at.predict_single(example), util.get_best_astar(o["a*"]), o["ara*"]["solutions"][-1][1])
        print(at.predict_single(example0))

        print(asol_txt)
    



if __name__ == "__main__":
    if sys.argv[1] == "1":
        plot_output1(sys.argv[2])
    if sys.argv[1] == "2":
        plot_output2(sys.argv[2], int(sys.argv[3]))
    if sys.argv[1] == "bounds":
        plot_output3(sys.argv[2])
    if sys.argv[1] == "4":
        plot_output4(sys.argv[2], int(sys.argv[3]))
    if sys.argv[1] == "5":
        plot_output5(sys.argv[2])
    if sys.argv[1] == "6":
        plot_output6(sys.argv[2])
    if sys.argv[1] == "robust":
        plot_robust()
    if sys.argv[1] == "examples":
        plot_examples()
    if sys.argv[1] == "youtube":
        youtube(sys.argv[2])
