import codecs
from io import StringIO

from .pytreeck import *

def __realdomain__str(self):
    return "[{:.3g}, {:.3g})".format(self.lo, self.hi)

def __realdomain__eq(self, o):
    return self.lo == o.lo and self.hi == o.hi

def __realdomain__hash(self):
    return hash((self.lo, self.hi))

RealDomain.__str__ = __realdomain__str
RealDomain.__eq__ = __realdomain__eq

def __tree_predict_single(self, example):
    node = self.root()
    while not self.is_leaf(node):
        fid, sv = self.get_split(node)
        go_left = example[fid] < sv
        node = self.left(node) if go_left else self.right(node)
    return self.get_leaf_value(node)

def __tree_predict(self, examples):
    return list(map(self.predict_single, examples))

Tree.predict_single = __tree_predict_single
Tree.predict = __tree_predict

def __addtree_iter(self):
    for i in range(len(self)):
        yield self[i]

def __addtree_predict_single(self, example):
    result = self.base_score
    for tree in self:
        result += tree.predict_single(example)
    return result

def __addtree_predict(self, examples):
    predictions = []
    print("predicting...", end="")
    for i, example in enumerate(examples):
        print("\rpredicting...", i, "/", len(examples), end="")
        predictions.append(self.predict_single(example))
    print("\rdone                    ")
    return predictions

def __addtree_write(self, f):
    with open(f, "w") as fh:
        json = self.to_json()
        fh.write(json)

def __addtree_read(f):
    with open(f, "r") as fh:
        json = fh.read()
        return AddTree.from_json(json)

AddTree.__iter__ = __addtree_iter
AddTree.predict_single = __addtree_predict_single
AddTree.predict = __addtree_predict
AddTree.write = __addtree_write
AddTree.read = __addtree_read

def __splittree_leaf_getstate(self):
    b = bytes(self.to_json(), "ascii")
    return codecs.encode(b, encoding="zlib")

def __splittree_leaf_setstate(self, b):
    json = codecs.decode(b, encoding="zlib").decode("ascii")
    self.update_from_json(json)

SplitTreeLeaf.__getstate__ = __splittree_leaf_getstate
SplitTreeLeaf.__setstate__ = __splittree_leaf_setstate

