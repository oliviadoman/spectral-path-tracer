# Migration From Assignment 2 to Assignment 3
We are going to reuse all the functionality that you've built so far straight up for this assignment. You simply need to run `./migrate-asst2-to-asst3.sh <PATH_TO_ASST2>` to copy all the functionality, except for 3 functions which are affected in the code refactoring for assignment 3.

First, check the mesh renderer in `asst3/src/cs248a_renderer/slang_shaders/renderer/mesh_renderer` directory. It contains 2/3 files that are to modified next. The last file is `asst3/src/cs248a_renderer/model/material.py`

1. `ray_mesh_intersection.slang` contains the functionality that you implemented in assignment 1. Please copy TODO block that you implemented in `rayMeshIntersection` function from assignment 2's `src/cs248a_renderer/slang_shaders/renderer/triangle_renderer.slang` file into the TODO block of `ray_mesh_intersection.slang`'s `rayMeshIntersection` function.
   
2. `mesh_material.slang` contains the functionality that you implemented in assignment 2. Please copy TODO block that you implemented for `getLevel` function in assignment 2's `src/cs248a_renderer/slang_shaders/renderer/triangle_renderer.slang` into TODO block of `mesh_material.slang`'s `getLevel` function.
   
3. The last function to be migrated is `generate_mipmaps` that you wrote in assignment 2's `src/cs248a_renderer/model/material.py` file. Please copy the TODO block that you implemented in it to `asst3/src/cs248a_renderer/model/material.py`.

If you migrate the code from assignment 2 succesfully, you should be able to run all the cells in `notebooks/assignment3/pathtracer.ipynb` successfully and render the scenes in the notebook with a very bright incorrect lighting. You'll implement lighting, BRDF, and global illumination in this assignment to produce the correct lighting.
