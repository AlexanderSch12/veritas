import graphviz as gv

class TreePlot:

    def __init__(self, fontsize=10):
        self.g = gv.Graph(format="svg")
        self.g.attr(fontsize=str(fontsize), fontname="monospace")
        self.g.attr("node", fontsize=str(fontsize), fontname="monospace")
        self.index = 0

    def name(self, node):
        return "{}x{}".format(self.index, node)

    def nodes_eq(self, btree, stree, bnode, snode):
        return btree.is_internal(bnode) == stree.is_internal(snode) \
                and (not btree.is_internal(bnode) or \
                        (btree.get_split(bnode) == stree.get_split(snode))) \
                and (not btree.is_leaf(bnode) or \
                        (btree.get_leaf_value(bnode) == stree.get_leaf_value(snode)))

    def add_tree(self, tree):
        g = gv.Graph()
        self.index += 1
        stack = [tree.root()]
        while len(stack) > 0:
            node = stack.pop()
            if tree.is_leaf(node):
                g.node(self.name(node), "{:.3f}".format(tree.get_leaf_value(node)))
            else:
                feat_id, split_value = tree.get_split(node)
                g.node(self.name(node), "X{} < {:.3f}".format(feat_id, split_value))
                stack.append(tree.right(node))
                stack.append(tree.left(node))

            if not tree.is_root(node):
                g.edge(self.name(tree.parent(node)), self.name(node))
        self.g.subgraph(g)

    def add_tree_cmp(self, btree, stree):
        self.index += 1
        stack = [(btree.root(), stree.root())] # (big node, small node)
        while len(stack) > 0:
            bnode, snode = stack.pop()
            if self.nodes_eq(btree, stree, bnode, snode):
                if btree.is_leaf(bnode):
                    self.g.node(self.name(bnode), "{:.3f}".format(btree.get_leaf_value(bnode)),
                            style="bold", color="darkgreen")
                else:
                    feat_id, split_value = btree.get_split(bnode)
                    self.g.node(self.name(bnode), "X{} < {:.3f}".format(feat_id, split_value),
                            style="bold", color="darkgreen")
                    stack.append((btree.right(bnode), stree.right(snode)))
                    stack.append((btree.left(bnode), stree.left(snode)))

                if not btree.is_root(bnode):
                    self.g.edge(self.name(btree.parent(bnode)), self.name(bnode),
                            style="bold", color="darkgreen")
            else:
                if btree.is_leaf(bnode):
                    self.g.node(self.name(bnode), "{:.3f}".format(btree.get_leaf_value(bnode)),
                            color="gray", fontcolor="gray")
                else:
                    feat_id, split_value = btree.get_split(bnode)
                    self.g.node(self.name(bnode), "X{} < {:.3f}".format(feat_id, split_value),
                            color="gray", fontcolor="gray")
                    stack.append((btree.right(bnode), snode))
                    stack.append((btree.left(bnode), snode))

                if not btree.is_root(bnode):
                    self.g.edge(self.name(btree.parent(bnode)), self.name(bnode), color="gray")

    def add_splittree_leaf(self, tree, splittree_leaf):
        g = gv.Graph()
        self.index += 1
        stack = [tree.root()]
        while len(stack) > 0:
            node = stack.pop()

            is_reachable = splittree_leaf.is_reachable(tree.index(), node)
            c = "darkgreen" if is_reachable else "gray"
            s = "bold" if is_reachable else ""

            if tree.is_leaf(node):
                g.node(self.name(node), "{:.3f}".format(tree.get_leaf_value(node)),
                        style=s, color=c, fontcolor=c)
            else:
                feat_id, split_value = tree.get_split(node)
                g.node(self.name(node), "X{} < {:.3f}".format(feat_id, split_value),
                        style=s, color=c, fontcolor=c)
                stack.append(tree.right(node))
                stack.append(tree.left(node))

            if not tree.is_root(node):
                g.edge(self.name(tree.parent(node)), self.name(node), color=c)
        self.g.subgraph(g)

    def add_domains(self, domains):
        text = ""
        for i, dom in enumerate(domains):
            if dom.is_everything(): continue
            text += "X{}: {}\\l".format(i, dom)
        self.g.attr(label=text)

    def render(self, f):
        self.g.render(f)
