#!/usr/bin/env python

import sys, json, traceback
from collections import OrderedDict
from StringIO import StringIO


class Node:
    """A tree node identified by a string ID and a name

    Names are unique across siblings, and siblings are traversed by name lexicographically
    (in ascending order), so internally they are arranged in a treeset. IDs are globally unique
    NOTE: equality and comparison only operate on names, this is intended to only scope those operations
    for siblings. Generally, IDs should be compared to determine equality"""

    def __init__(self, nid, name):
        self._name = name
        self._id = nid
        self._children_by_id = {}  # for more efficient removal
        self._depth = 0

        self.children = []
        self.parent = None

    def id(self):
        return self._id

    def name(self):
        return self._name

    def depth(self):
        return self._depth

    def __eq__(self, other):
        return self.name() == other.name()

    def __lt__(self, other):
        return self.name() < other.name()

    def __str__(self):
        if self.parent:
            return "(%s, %s) => parent %s, depth %d" % (self._id, self._name, self.parent.id(), self._depth)
        else:
            return "(%s, %s) => root" % (self._id, self._name)

    def is_leaf(self):
        return False if self.children else True

    def last_preorder_child(self):
        node = self

        while node and node.children:
            node = node.children[len(node.children) - 1]

        return node

    def preorder_predecessor(self):
        """Returns the direct pre-order predecessor (i.e. the rightmost successor of the subtree
        formed by the nearest left sibling), or None if this node is the root"""

        if not self.parent:
            return None

        idx = self.parent.children.index(self)

        if idx == 0:
            return self.parent

        pred = self.parent.children[idx - 1]

        while pred.children:
            pred = pred.children[len(pred.children) - 1]

        return pred

    def set_depth(self, new_depth):
        """Recursively updates the depth of this node's subtree"""

        self._depth = new_depth
        for child in self.children:
            child.set_depth(new_depth + 1)

    def add_child(self, node):
        """Adds a child node if a child with the same name does not exist yet"""

        if not node or node in self.children:
            return False

        self.children.append(node)
        self.children.sort()
        self._children_by_id[node.id()] = node
        node.parent = self
        node.set_depth(self._depth + 1)
        return True

    def remove_child(self, nid, force=False):
        """Deletes the child with the specified ID.
        Non-leaf nodes can't be deleted unless the force flag is set (off by default)"""

        if nid not in self._children_by_id:
            return False

        node = self._children_by_id[nid]

        if not node.is_leaf() and not force:
            return False

        self._children_by_id.pop(nid)
        self.children.remove(node)
        return True


class Storage:
    """Container class for the tree storage

    Exposes methods for querying and manipulating the underlying structure,
    also enforces the global ID uniqueness constraint. NOT thread safe."""

    def __init__(self):
        self._nodes = {}
        self._root = None

        # this is the list of node IDs for pre-order traversal
        # it is updated on every operation and serves as a slightly faster
        # alternative to a recursive approach (using slicing and list comprehensions)
        self._preorder = []

    def add(self, node, parent=None):
        """Adds the specified node either as the root or under the parent with the (optionally) specified ID"""

        if not node or node.id() in self._nodes:
            return False

        if not parent:
            if self._nodes:
                return False  # can't have more than one root

            self._nodes[node.id()] = node
            self._root = node
            self._root.set_depth(0)
            self._preorder.append(node.id())
            return True
        else:
            if parent not in self._nodes:
                return False

            if self._nodes[parent].add_child(node):
                self._nodes[node.id()] = node

                # update the cached pre-order list by inserting the new node after its predecessor
                # no null checks here since the predecessor must exist
                pred = node.preorder_predecessor()
                self._preorder.insert(self._preorder.index(pred.id()) + 1, node.id())
                return True

            return False

    def delete(self, nid):
        """Deletes the node with the specified ID"""

        if nid not in self._nodes:
            return False

        parent = self._nodes[nid].parent

        if parent and parent.remove_child(nid):
            self._nodes.pop(nid)

            # we're only deleting a single node here so no need to include children
            self._preorder.remove(nid)

            return True
        elif not parent and len(self._nodes) == 1:
            self._nodes.clear()
            self._preorder = []
            return True

        return False

    def move(self, nid, to):
        """Moves the node with the specified ID to the parent with the specified ID

        Fails if
         - provided IDs are not found
         - a node is moved to itself, its parent or any node in its subtree (which would create a loop)"""

        if nid not in self._nodes or to not in self._nodes or nid == to:
            return False

        target = self._nodes[nid]

        if not target.parent or target.parent.id() == to:
            return False

        item = self._nodes[to].parent

        while item:
            if item.id() == nid:
                return False

            item = item.parent

        old_parent = target.parent

        if not self._nodes[to].add_child(target):
            return False

        old_parent.remove_child(nid, True)
        pred = target.preorder_predecessor()
        new_preorder_position = self._preorder.index(pred.id()) + 1

        if target.is_leaf():
            # special case: only the leaf node changes its pre-order position
            self._preorder.remove(nid)
            self._preorder.insert(new_preorder_position, nid)
        else:
            # the node is moved with its children, so its entire sub-list must be repositioned
            # this is done in-place: https://stackoverflow.com/a/10272358

            node = target.last_preorder_child()
            range_start = self._preorder.index(target.id())
            range_size = self._preorder.index(node.id()) - range_start + 1

            if new_preorder_position > range_start + range_size:
                a, b, c = range_start, range_start + range_size, new_preorder_position
            elif new_preorder_position < range_start:
                a, b, c = new_preorder_position, range_start, range_start + range_size

            span1, span2 = b - a, c - b
            if span1 < span2:
                tmp = self._preorder[a:b]
                self._preorder[a:a + span2] = self._preorder[b:c]
                self._preorder[c - span1:c] = tmp
            else:
                tmp = self._preorder[b:c]
                self._preorder[a + span2:c] = self._preorder[a:b]
                self._preorder[a:a + span2] = tmp

        return True

    def query(self, ids=None, names=None, roots=None, min_depth=0, max_depth=0):
        """Queries the underlying structure

        Parameters
        ----------
        ids: list of string IDs (optional)
            Filter query by the list of IDs. Narrows the criteria if used together with `names`.
            Non-existent IDs are ignored.
            Takes precedence over `roots` if specified.
        names: list of names (optional)
            Behaves similarly to `ids`. Both `ids` and `names` return the results of a pre-order DFS.
        roots: list of root IDs (optional)
            Query the subtrees of the specified nodes. Subtrees are traversed in pre-order
            and the resulting lists are merged in the order their root IDs were specified.
            Takes no effect if `ids` or `names` are specified.
            Ignores non-existent IDs (if none exist, the result is an empty list).
            Depth range filters (see below) are applied individually to every subtree.
        min_depth: minimum relative depth to include in the query result (optional)
            If used together with `roots`, will only return children nodes at or below the specified depth,
            ignored if `ids` or `names` are set.
        max_depth: maximum relative depth to include in the query result (optional)
            If used together with `roots`, will only return children nodes at or above the specified depth,
            ignored if `ids` or `names` are set.

        If neither `ids`, `names` or `roots` are used, the entire tree is queried and depth range filters
        take effect as described."""

        result = []

        if not self._nodes or (min_depth and max_depth and max_depth < min_depth):
            return result

        if not min_depth:
            min_depth = 0

        if not max_depth:
            max_depth = len(self._preorder)  # can't go deeper than the tree size

        if names:
            names = list(OrderedDict.fromkeys(names))  # uniq(names)

        if ids:
            ids = [nid for nid in self._preorder if nid in list(OrderedDict.fromkeys(ids))]
            result = [self._nodes[k] for k in ids]
            return result if not names else [i for i in result if i.name() in names]
        elif names:
            return [self._nodes[nid] for nid in self._preorder if self._nodes[nid].name() in names]

        if roots:
            roots = [self._nodes[nid] for nid in list(OrderedDict.fromkeys(roots)) if nid in self._nodes]
        else:
            roots = [self._root]

        for root in roots:
            # depth ranges are relative, set them for each root
            dmin, dmax = min_depth + root.depth(), max_depth + root.depth()

            if root.id() == self._root.id():
                # special case: if it's THE root, no need to compute the subtree index range
                subtree = [self._nodes[nid] for nid in self._preorder if dmin <= self._nodes[nid].depth() <= dmax]
            else:
                # only need to walk the subtree starting at the current root and ending with its last pre-order child
                start = self._preorder.index(root.id())
                end = self._preorder.index(root.last_preorder_child().id()) + 1
                subtree = [self._nodes[nid] for nid in self._preorder[start:end]
                           if dmin <= self._nodes[nid].depth() <= dmax]

            result += subtree

        return result


def add_node(stg, body):
    for attr in ['id', 'name']:
        if attr not in body or not body[attr]:
            return False

    return stg.add(Node(body['id'], body['name']), body.get('parent_id'))


def delete_node(stg, body):
    if 'id' not in body or not body['id']:
        return False

    return stg.delete(body['id'])


def move_node(stg, body):
    for attr in ['id', 'new_parent_id']:
        if attr not in body or not body[attr]:
            return False

    return stg.move(body['id'], body['new_parent_id'])


def query(stg, body):
    nodes = stg.query(body.get('ids'), body.get('names'), body.get('root_ids'),
                      body.get('min_depth'), body.get('max_depth'))
    return [{'id': n.id(), 'name': n.name(), 'parent_id': n.parent.id() if n.parent else ""} for n in nodes]


def main():
    stg = Storage()

    while True:
        line = sys.stdin.readline()

        if not line:
            return

        sys.stderr.writelines(["request : ", line, '\n'])

        try:
            req = json.load(StringIO(line))
        except:
            traceback.print_exc()
            continue

        if not req.keys() or len(req.keys()) > 1:
            sys.stderr.write("invalid request format")
            continue

        func = req.keys()[0]
        result = globals()[func](stg, req[func])
        result = json.dumps({'nodes' if func == 'query' else 'ok': result})

        sys.stdout.write(result)
        sys.stdout.flush()


if __name__ == '__main__':
    main()