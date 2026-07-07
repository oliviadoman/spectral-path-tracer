import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable
import numpy as np
import slangpy as spy

from cs248a_renderer.model.bounding_box import BoundingBox3D
from cs248a_renderer.model.primitive import Primitive
from tqdm import tqdm


logger = logging.getLogger(__name__)


@dataclass
class BVHNode:
    # The bounding box of this node.
    bound: BoundingBox3D = field(default_factory=BoundingBox3D)
    # The index of the left child node, or -1 if this is a leaf node.
    left: int = -1
    # The index of the right child node, or -1 if this is a leaf node.
    right: int = -1
    # The starting index of the primitives in the primitives array.
    prim_left: int = 0
    # The ending index (exclusive) of the primitives in the primitives array.
    prim_right: int = 0
    # The depth of this node in the BVH tree.
    depth: int = 0

    def get_this(self) -> Dict:
        return {
            "bound": self.bound.get_this(),
            "left": self.left,
            "right": self.right,
            "primLeft": self.prim_left,
            "primRight": self.prim_right,
            "depth": self.depth,
        }

    @property
    def is_leaf(self) -> bool:
        """Checks if this node is a leaf node."""
        return self.left == -1 and self.right == -1


class BVH:
    def __init__(
        self,
        primitives: List[Primitive],
        max_nodes: int,
        min_prim_per_node: int = 1,
        num_thresholds: int = 16,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        """
        Builds the BVH from the given list of primitives. The build algorithm should
        reorder the primitives in-place to align with the BVH node structure.
        The algorithm will start from the root node and recursively partition the primitives
        into child nodes until the maximum number of nodes is reached or the primitives
        cannot be further subdivided.
        At each node, the splitting axis and threshold should be chosen using the Surface Area Heuristic (SAH)
        to minimize the expected cost of traversing the BVH during ray intersection tests.

        :param primitives: the list of primitives to build the BVH from
        :type primitives: List[Primitive]
        :param max_nodes: the maximum number of nodes in the BVH
        :type max_nodes: int
        :param min_prim_per_node: the minimum number of primitives per leaf node
        :type min_prim_per_node: int
        :param num_thresholds: the number of thresholds per axis to consider when splitting
        :type num_thresholds: int
        """
        self.nodes: List[BVHNode] = []

        # TODO: Student implementation starts here.

        if len(primitives) == 0:
            return
        
        # Root node
        root = BVHNode(
            bound=self._compute_bounds(primitives, 0, len(primitives)),
            prim_left=0,
            prim_right=len(primitives),
            depth=0
        )
        self.nodes.append(root)
        
        if on_progress:
            on_progress(len(self.nodes), max_nodes)
        
        # Build BVH 
        queue = queue = [(0, 0, len(primitives))] 
        
        while queue and len(self.nodes) < max_nodes:
            node_idx, prim_left, prim_right = queue.pop(0)  # FIFO
            node = self.nodes[node_idx]
            num_prims = prim_right - prim_left
            
            # leaf node?
            if num_prims <= min_prim_per_node or len(self.nodes) >= max_nodes - 1:
                # Leaf node and no splitting
                continue
            
            # Find the best split with SAH
            best_axis, best_threshold, best_cost = self._find_best_split(
                primitives, prim_left, prim_right, num_thresholds
            )
            
            # If no good split, make it a leaf
            if best_axis == -1:
                continue
            
            # Seperate primitives on the best split
            mid = self._partition_primitives(
                primitives, prim_left, prim_right, best_axis, best_threshold
            )
            
            # Nake sure primitives on both sides
            if mid <= prim_left or mid >= prim_right:
                continue
            
            # Create left child
            left_bound = self._compute_bounds(primitives, prim_left, mid)
            left_node = BVHNode(
                bound=left_bound,
                prim_left=prim_left,
                prim_right=mid,
                depth=node.depth + 1
            )
            left_idx = len(self.nodes)
            self.nodes.append(left_node)
            node.left = left_idx
            
            if on_progress:
                on_progress(len(self.nodes), max_nodes)
            
            # Check if we can create right child
            if len(self.nodes) >= max_nodes:
                break
            
            # Create right child
            right_bound = self._compute_bounds(primitives, mid, prim_right)
            right_node = BVHNode(
                bound=right_bound,
                prim_left=mid,
                prim_right=prim_right,
                depth=node.depth + 1
            )
            right_idx = len(self.nodes)
            self.nodes.append(right_node)
            node.right = right_idx
            
            if on_progress:
                on_progress(len(self.nodes), max_nodes)
            
            # Push children onto queue (breadth-first)
            queue.append((left_idx, prim_left, mid))
            queue.append((right_idx, mid, prim_right))
    
    def _compute_bounds(
        self, primitives: List[Primitive], left: int, right: int
    ) -> BoundingBox3D:
        """Compute the bounding box for primitives in range [left, right)."""
        if left >= right:
            return BoundingBox3D()
        
        bounds = primitives[left].bounding_box
        for i in range(left + 1, right):
            bounds =  BoundingBox3D.union(bounds, (primitives[i].bounding_box))
        
        return bounds
    
    def _find_best_split(
        self,
        primitives: List[Primitive],
        left: int,
        right: int,
        num_thresholds: int
    ) -> Tuple[int, float, float]:
        """Find best split using SAH. Returns (axis, threshold, cost)."""
        bounds = self._compute_bounds(primitives, left, right)
        area = bounds.area
        
        if area <= 0:
            return -1, 0.0, float('inf')
        
        best_axis = -1
        best_threshold = 0.0
        best_cost = float('inf')
        
        # Try each axis (x, y, z)
        for axis in range(3):
            # Get centroid range along this axis
            min_centroid = float('inf')
            max_centroid = float('-inf')
            
            for i in range(left, right):
                centroid = primitives[i].bounding_box.center[axis]
                min_centroid = min(min_centroid, centroid)
                max_centroid = max(max_centroid, centroid)
            
            if min_centroid >= max_centroid:
                continue
            
            # Try different threshold positions
            for t in range(num_thresholds):
                threshold = min_centroid + (max_centroid - min_centroid) * (t + 1) / (num_thresholds + 1)
                
                # Compute SAH cost for this split
                left_box = BoundingBox3D()
                right_box = BoundingBox3D()
                n_left = 0
                n_right = 0
                
                for i in range(left, right):
                    box = primitives[i].bounding_box
                    centroid = box.center[axis]
                    
                    if centroid < threshold:
                        if n_left == 0:
                            left_box = box
                        else:
                            left_box = BoundingBox3D.union(left_box, box)
                        n_left += 1
                    else:
                        if n_right == 0:
                            right_box = box
                        else:
                            right_box = BoundingBox3D.union(right_box, box)
                        n_right += 1
                
                # Skip if all primitives go to one side
                if n_left == 0 or n_right == 0:
                    continue
                
                # SAH cost formula
                cost = (left_box.area * n_left + right_box.area * n_right) / area
                
                if cost < best_cost:
                    best_cost = cost
                    best_axis = axis
                    best_threshold = threshold
        
        return best_axis, best_threshold, best_cost
    
    def _partition_primitives(
        self,
        primitives: List[Primitive],
        left: int,
        right: int,
        axis: int,
        threshold: float
    ) -> int:
        """Partition primitives in-place. Returns partition index."""
        i = left
        j = right - 1
        
        while i <= j:
            # Find primitive on left that should be on right
            while i <= j and primitives[i].bounding_box.center[axis] < threshold:
                i += 1
            
            # Find primitive on right that should be on left
            while i <= j and primitives[j].bounding_box.center[axis] >= threshold:
                j -= 1
            
            # Swap if needed
            if i < j:
                primitives[i], primitives[j] = primitives[j], primitives[i]
                i += 1
                j -= 1
        
        return i

        # TODO: Student implementation ends here.


def create_bvh_node_buf(module: spy.Module, bvh_nodes: List[BVHNode]) -> spy.NDBuffer:
    device = module.device
    node_buf = spy.NDBuffer(
        device=device, dtype=module.BVHNode.as_struct(), shape=(max(len(bvh_nodes), 1),)
    )
    cursor = node_buf.cursor()
    for idx, node in enumerate(bvh_nodes):
        cursor[idx].write(node.get_this())
    cursor.apply()
    return node_buf
