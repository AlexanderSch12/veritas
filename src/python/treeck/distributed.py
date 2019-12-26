import codecs, time, io, json

from enum import Enum
from dask.distributed import wait, get_worker

from .pytreeck import AddTree, RealDomain, SplitTreeLeaf
from .verifier import Verifier, VerifierTimeout


class DistributedVerifier:

    def __init__(self,
            client,
            splittree,
            verifier_factory,
            check_paths = True,
            saturate_workers_from_start = True,
            saturate_workers_factor = 1.0,
            stop_when_sat = False,
            timeout_start = 60,
            timeout_max = 3600,
            timeout_grow_rate = 1.5):

        self._timeout_start = timeout_start
        self._timeout_max = timeout_max
        self._timeout_rate = timeout_grow_rate

        self._client = client # dask client
        self._st = splittree
        self._at = splittree.addtree()
        self._at_fut = client.scatter(self._at, broadcast=True) # distribute addtree to all workers
        self._verifier_factory = verifier_factory # (addtree, splittree_leaf) -> Verifier

        self._check_paths_opt = check_paths
        self._saturate_workers_opt = saturate_workers_from_start
        self._saturate_workers_factor_opt = saturate_workers_factor
        self._stop_when_sat_opt = stop_when_sat

        self.results = dict() # domtree_node_id => result info
        self._stop_flag = False

    def check(self):
        l0 = self._st.get_leaf(0)

        # TODO add domain constraints to verifier

        # 1: loop over trees, check reachability of each path from root
        if self._check_paths_opt:
            l0 = self._check_paths(l0)

        # 2: splits until we have a piece of work for each worker
        if self._saturate_workers_opt:
            nworkers = sum(self._client.nthreads().values())
            ntasks = int(round(self._saturate_workers_factor_opt * nworkers))
            ls = self._generate_splits(l0, ntasks)
        else:
            ls = [l0]

        # 3: submit verifier 'check' tasks for each
        fs = [self._client.submit(DistributedVerifier._verify_fun,
            self._at_fut, lk, self._timeout_start, self._verifier_factory)
            for lk in ls]

        # 4: wait for future to complete, act on result
        # - if sat/unsat -> done (finish if sat if opt set)
        # - if new split -> schedule two new tasks
        while len(fs) > 0: # while task are running...
            if self._stop_flag:
                print("Stop flag: cancelling remaining tasks")
                for f in fs:
                    f.cancel()
                    self._stop_flag = False
                break

            wait(fs, return_when="FIRST_COMPLETED")
            next_fs = []
            for f in fs:
                if f.done(): next_fs += self._handle_done_future(f)
                else:        next_fs.append(f)
            fs = next_fs

    def _check_paths(self, l0):
        # update reachabilities in splittree_leaf 0 in parallel
        fs = []
        for tree_index in range(len(self._at)):
            f = self._client.submit(DistributedVerifier._check_tree_paths,
                self._at_fut,
                tree_index,
                l0,
                self._verifier_factory)
            fs.append(f)
            pass
        wait(fs)
        for f in fs:
            assert f.done()
            assert f.exception() is None
        return SplitTreeLeaf.merge(list(map(lambda f: f.result(), fs)))

    def _generate_splits(self, l0, ntasks):
        # split and collects splittree_leafs
        l0.find_best_domtree_split(self._at)
        ls = [l0]
        while len(ls) < ntasks:
            max_score = 0
            max_lk = None
            for lk in ls:
                if lk.split_score > max_score:
                    max_score = lk.split_score
                    max_lk = lk

            ls.remove(max_lk)
            nid = max_lk.domtree_node_id()

            #print("splitting domtree_node_id", nid, max_lk.get_best_split())
            self._st.split(max_lk)

            domtree = self._st.domtree()
            l, r = domtree.left(nid), domtree.right(nid)
            ll, lr = self._st.get_leaf(l), self._st.get_leaf(r)
            ll.find_best_domtree_split(self._at)
            lr.find_best_domtree_split(self._at)
            ls += [ll, lr]

        return ls

    def _handle_done_future(self, f):
        t = f.result()
        status = t[0]

        # We're finished with this branch!
        if status != Verifier.Result.UNKNOWN:
            model, domtree_node_id, check_time = t[1:]
            print(f"{status} for {domtree_node_id} in {check_time}s!")
            self.results[domtree_node_id] = {"status": status, "check_time": check_time}
            if status.is_sat() and self._stop_when_sat_opt:
                self._stop_flag = True
            return []

        # We timed out, split and try again
        lk, check_time, timeout = t[1:]
        domtree_node_id = lk.domtree_node_id()
        split = lk.get_best_split()
        score, balance = lk.split_score, lk.split_balance

        self._st.split(lk)

        domtree = self._st.domtree()
        domtree_node_id_l = domtree.left(domtree_node_id)
        domtree_node_id_r = domtree.right(domtree_node_id)
        self.results[domtree_node_id]["check_time"] = check_time
        self.results[domtree_node_id_l] = {}
        self.results[domtree_node_id_r] = {}

        print(f"UNKNOWN for {domtree_node_id} in {check_time}s with timeout {timeout}")
        print(f"> splitting {domtree_node_id} into {domtree_node_id_l} and {domtree_node_id_r}")
        print(f"> with score {score} and balance {balance}")

        next_timeout = min(self._timeout_max, self._timeout_rate * timeout)

        fs = [self._client.submit(DistributedVerifier._verify_fun,
            self._at_fut, lk, next_timeout, self._verifier_factory)
            for lk in [self._st.get_leaf(domtree_node_id_l),
                       self._st.get_leaf(domtree_node_id_r)]]
        return fs





    # - WORKERS ------------------------------------------------------------- #

    @staticmethod
    def _check_tree_paths(at, tree_index, l0, vfactory):
        tree = at[tree_index]
        stack = [(tree.root(), True)]
        v = vfactory(at, l0)

        while len(stack) > 0:
            node, path_constraint = stack.pop()

            l, r = tree.left(node), tree.right(node)
            feat_id, split_value = tree.get_split(node)
            xvar = v.xvar(feat_id)

            if tree.is_internal(l) and l0.is_reachable(tree_index, l):
                path_constraint_l = (xvar < split_value) & path_constraint;
                if v.check(path_constraint_l).is_sat():
                    stack.append((l, path_constraint_l))
                else:
                    print(f"unreachable  left: {tree_index} {l}")
                    l0.mark_unreachable(tree_index, l)

            if tree.is_internal(r) and l0.is_reachable(tree_index, r):
                path_constraint_r = (xvar >= split_value) & path_constraint;
                if v.check(path_constraint_r).is_sat():
                    stack.append((r, path_constraint_r))
                else:
                    print(f"unreachable right: {tree_index} {r}")
                    l0.mark_unreachable(tree_index, r)

        return l0

    @staticmethod
    def _verify_fun(at, lk, timeout, vfactory):
        v = vfactory(at, lk)
        v.set_timeout(timeout)
        v.add_all_trees()
        try:
            status = v.check()
            model = {}
            if status.is_sat():
                model = v.model()
            return status, model, lk.domtree_node_id(), v.check_time
        except VerifierTimeout as e:
            print(f"timeout after {e.unk_after} (timeout = {timeout}) -> splitting l{lk.domtree_node_id()}")
            lk.find_best_domtree_split(at)
            return Verifier.Result.UNKNOWN, lk, v.check_time, timeout
