# CS 248A Assignment 2

## Environment Setup

Please read the [top level README.md](../README.md) for instructions on how to set up the environment for this assignment.

## Migrate from Assignment 1

This assignment builds upon the ray caster you implemented in Assignment 1. To migrate your code from Assignment 1 to Assignment 2, please follow the migration guide in [asst2-migration-guide.md](./asst2-migration-guide.md).

## Download 3D Models

This assignment uses several 3D models and volumes for testing and rendering. Please download the models from [this google drive link](https://drive.google.com/drive/folders/1biYrBrNYx1sBlkcuyx3RARH9g9PaVHgL?usp=share_link)

Place all the files under the `resources` folder in the root of the repository. Note that this folder is ignored by `.gitignore`, so if you are collaborating with your partner, please make sure both of you download the models.

## What you will do

In this assignment you will extend your basic ray caster from Assignment 1 to support texture mapping and volumetric rendering. The assignment is divided into two parts which will be released in two steps.

In __Part 1__ of the assignment you will implement texture mapping for triangle meshes as well as volumetric rendering with absorption and emission volumes.

In __Part 2__ of the assignment (which will be released on week 5), you'll learn to recover volume data from a set of 2D images using differentiable rendering techniques.

### Getting started on Part 1

To get started on part 1, you'll work in two Python notebooks.

1. Please open [the texture mapping notebook](../notebooks/assignment2-part1/texture-mapping.ipynb) and follow the instructions in the notebook.
2. Please open [the volumetric rendering notebook](../notebooks/assignment2-part1/volumetric-rendering.ipynb) and follow the instructions in the notebook.

The texture mapping and volumetric rendering notebooks does not depend on each other, so you can work on them in any order.

The starter code also comes with an interactive renderer that allows you to move around and render 3D scenes in real time. Follow the [interactive renderer guide](../docs/interactive-renderer.md) to learn how to use it.

### Getting started on Part 2

There're two tasks in part 2 of the assignment. The first one is training a neural texture. The second one is implementing a differentiable volume renderer that can be used to recover volume data from 2D images.

These two tasks are independent, so you can work on them in any order.

1. Please open [the neural texture notebook](../notebooks/assignment2-part2/neural-texture/neural-texture.ipynb) and follow the instructions in the notebook.
2. For the differentiable volume renderer, there're two notebooks that you should follow that **IS** dependent on each other.
    1. Please open [the differentiable texture notebook](../notebooks/assignment2-part2/volume-recovery/diff-texture.ipynb) and follow the instructions in the notebook. We'll walk you through the basics of automatic differentiation in Slang and how to implement a differentiable texture.
    2. Please open [the volume recovery notebook](../notebooks/assignment2-part2/volume-recovery/volume-recovery.ipynb) and follow the instructions in the notebook. In this notebook, you'll implement a differentiable volume renderer and use it to recover volume data from a set of 2D images.

### Grading and Handin

Assignment handin will be done on Gradescope.

All programming assignments in CS248A will be graded via a 15 minute in-person conversation with a course CA.  The CAs will ask you to render various scenes, and ask you questions about your code.  Your grade will be a function of both your ability to demonstrate correct code and your team's ability to answer CA questions about the code.