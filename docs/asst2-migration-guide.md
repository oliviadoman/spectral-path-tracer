# Migration From Assignment 1 to Assignment 2
In the assignment 1, you implemented ray-surface interstion for different surfaces, such as mesh, volume and SDF. In Assignment 2, we are going to focus on coloring the surface, specifically those represented as meshes and volumes. As expected, a lot of functionality that you implemented in Assignment 1 will be reused. This document guides how to migrate your code to fit the structure of code in Assignment 2, which we've refactored to be more modular.

## What should you be doing?
The migration document is divided into 3 parts: low effort, medium effort, and high effort.

### Low Effort
Low effort requires you to simply copy some of the files that you submitted into the approproate directories in this repositiory.

```bash
asst1/
├── notebooks/
│   └── assignment1-part1/
│       └── shaders/
│           └── assignment1.slang
└── src/
    └── cs248a_renderer/
        ├── model/
        │   ├── bvh.py
        │   └── scene_object.py
        └── slang_shaders/
            ├── math/
            │   ├── bounding_box.slang
            │   └── ray.slang
            ├── model/
            │   ├── bvh.slang
            │   └── camera.slang
            ├── primitive/
            │   ├── sdf.slang
            │   └── volume.slang
```

### Medium Effort
Medium effort requires you to copy the code of specific functions that you implemented into the appropriate files.
- `src/cs248a_renderer/slang_shaders/texture/texture.slang`: Copy the `TODO` functions that you'd implemented for `SharedTexture3DBuffer`.
- `src/cs248a_renderer/slang_shaders/primitive/triangle.slang`: Copy the `hit` function that you'd implemented.
  
### High Effort
High effort requires you to _slightly_ modify a function that you'd implemented last time.  
*Why?* We've significantly refactored the `renderer.slang` and decoupled it into `renderer/triangle_renderer.slang` and `renderer/volume_renderer.slang`. The ray-mesh intersection that you implemented as part of `sample` function in `renderer.slang` of `asst1` is now migrated to `renderer/triangle_renderer.slang`.
To adapt to this change, all we ask you to do is:
- Copy the ray-mesh interseciton that you implemented in `sample` function into the `TODO` of `rayMeshIntersection` function in `renderer/triangle_renderer.slang`. 
- Then, along with the `closestHit` that you were tracking earlier in this function pleaase also track the triangle which is causing the `closestHit` in the `hitTriangle` object that's provided. Also, make this change in both parts of your code: the one using BVH and the one that's not. 

## Verification
Please run the [ray-triangle-intersection.ipynb](../notebooks/assignment1-part1/ray-triangle-intersection.ipynb) and [bvh.ipynb](../notebooks/assignment1-part2/bvh.ipynb). A successful migration should result in reproduction of the same results that you got in Assignment 1 for these notebooks.