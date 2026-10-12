import random

import matplotlib
matplotlib.use("Agg")  # render straight to file, no GUI window needed
import matplotlib.pyplot as plt
import networkx as nx

LAYOUTS = {
    "circle": nx.circular_layout,
    "random": nx.random_layout,
    "kamada_kawai": nx.kamada_kawai_layout,
    "spring": nx.spring_layout,
    "spectral": nx.spectral_layout,
}
MENU = list(LAYOUTS) + ["randomize"]  # "randomize" = pick a random layout

START_SIZE = 8.0      # figure size in inches
GROWTH = 1.3          # figure grows by this factor every few failed attempts
MAX_ATTEMPTS = 30
LABEL_PADDING = 1.15  # labels must keep ~15% breathing room around them


def draw_graph(graph, pos, size):
    """Draw the graph and return (fig, {node: Text})."""
    fig, ax = plt.subplots(figsize=(size, size))
    ax.margins(0.15)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color="blue", node_size=1)
    nx.draw_networkx_edges(
        graph, pos, ax=ax, arrows=True, arrowstyle="-|>", arrowsize=13,
        width=3, edge_color="#a9a9a9",
    )
    texts = nx.draw_networkx_labels(
        graph, pos, ax=ax, font_size=8, font_color="black"
    )
    ax.set_axis_off()
    fig.canvas.draw()  # needed so text extents can be measured
    return fig, texts


def find_overlaps(fig, texts):
    """Return pairs of node names whose labels overlap on the rendered canvas."""
    renderer = fig.canvas.get_renderer()
    boxes = {
        name: t.get_window_extent(renderer).expanded(LABEL_PADDING, LABEL_PADDING)
        for name, t in texts.items()
    }
    names = list(boxes)
    return [
        (a, b)
        for i, a in enumerate(names)
        for b in names[i + 1:]
        if boxes[a].overlaps(boxes[b])
    ]


def nudge_apart(pos, overlaps, step):
    """Push each overlapping pair of nodes away from each other."""
    for a, b in overlaps:
        dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-9:  # same spot: pick a random direction
            dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
            dist = (dx * dx + dy * dy) ** 0.5 or 1.0
        dx, dy = dx / dist * step, dy / dist * step
        pos[a] = (pos[a][0] + dx, pos[a][1] + dy)
        pos[b] = (pos[b][0] - dx, pos[b][1] - dy)
    return pos


def chain_to_graph_png(chain: str, output_path: str, graph_layout: str):
    """Returns (layout_name, overlap_free)."""
    names = [part.strip() for part in chain.split("->") if part.strip()]
    if len(names) < 2:
        raise ValueError("Need at least two names separated by '->'")

    graph = nx.DiGraph()
    for src, dst in zip(names, names[1:]):
        graph.add_edge(src, dst)

    if graph_layout == "randomize":
        layout_func = random.choice(list(LAYOUTS.values()))
    else:
        layout_func = LAYOUTS[graph_layout]
    pos = {n: tuple(p) for n, p in layout_func(graph).items()}

    size = START_SIZE
    fig, overlap_free = None, False
    for attempt in range(MAX_ATTEMPTS):
        fig, texts = draw_graph(graph, pos, size)
        overlaps = find_overlaps(fig, texts)
        if not overlaps:
            overlap_free = True
            break
        if attempt == MAX_ATTEMPTS - 1:
            break  # keep this last figure and save it with a warning
        plt.close(fig)
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
        pos = nudge_apart(pos, overlaps, step=0.05 * span)
        if attempt % 3 == 2:  # labels are fixed-size, so a bigger canvas helps
            size *= GROWTH

    fig.savefig(output_path, pad_inches=0.1, transparent=False, bbox_inches="tight")
    plt.close(fig)
    return layout_func.__name__, overlap_free


def ask_layout() -> str:
    print("\nChoose a graph layout:")
    for i, name in enumerate(MENU, 1):
        print(f"  {i}. {name}")
    while True:
        choice = input(f"Layout [1-{len(MENU)} or name, default spectral]: ").strip().lower()
        if not choice:
            return "spectral"
        if choice.isdigit() and 1 <= int(choice) <= len(MENU):
            return MENU[int(choice) - 1]
        if choice in MENU:
            return choice
        print("Invalid choice, try again.")


def ask_chain() -> str:
    print("Enter the name chain, e.g.  a -> b -> c -> a")
    while True:
        chain = input("Chain: ").strip()
        if len([p for p in chain.split("->") if p.strip()]) >= 2:
            return chain
        print("Need at least two names separated by '->'.")


def main() -> None:
    while True:
        chain = ask_chain()
        layout = ask_layout()
        output = input("Output file [graph.png]: ").strip() or "graph.png"

        used, ok = chain_to_graph_png(chain, output, layout)
        print(f"Saved {output} using {used}")
        if not ok:
            print("Warning: some labels still overlap. Try a different layout.")

        if input("\nMake another? [y/N]: ").strip().lower() != "y":
            break


if __name__ == "__main__":
    main()