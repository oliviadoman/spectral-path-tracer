# CS 248A Assignment 3: Path Tracer (Due Mar 2, 11:59 PM PST)

## Environment Setup

Please read the [top level README.md](../README.md) for instructions on how to set up the environment for this assignment.

## Migrate from Assignment 2

This assignment builds upon the ray caster and texture functionality you implemented as part of last 2 assignments. To migrate your code from Assignment 2 to Assignment 3, please follow the migration guide in [asst3-migration-guide.md](./asst3-migration-guide.md). You need to change only 3 functions, and we've provided a script that takes path of your assignment 2 directory and copies the unmodified files directly to assignment 3.

## Download 3D Models

This assignment uses several 3D models for testing and rendering. Please download the models from [this google drive link](https://drive.google.com/drive/folders/1kT2JPlwDfBr8oHNwdRPJnOsRY1iFvcUD?usp=drive_link)

Place all the files under the `resources` folder in the root of the repository. Note that this folder is ignored by `.gitignore`, so if you are collaborating with your partner, please make sure both of you download the models.

## What you will do

In this assignment you will add lights, BRDF's to the scene. Then you'll implement a path tracer with global illumination to render photorealistic images of a scene.

### Getting started 

Please open [the path tracer notebook](../notebooks/assignment3/pathtracer.ipynb) and follow the instructions in the notebook.


The starter code also comes with an interactive renderer that allows you to move around and render 3D scenes in real time. Follow the [interactive renderer guide](../docs/interactive-renderer.md) to learn how to use it.

### Grading
Total 100 points
- Correctness: 80 Points
- Interview: 20 Points

The 80 points for correctness are divided as follows:
* Shadows (10 points)
  * Shadow Ray (5 points)
  * LightOcclusion (5 points)
* Rectangular Light’s PDF (20 points)
* Indirect Illumination (30 points)
  * Lambertian Uniform Sampling+PDF (20 points)
  * Throughput update (5 points)
  * Ray update (5 points)
  * EC: Lambertian Cosine Sampling+PDF (2 points)
* Mirror BRDF (10 points)
* Glass BRDF (10 points)
  * EC: Fresnel Effect with Russian Roulette (2 points)
* EC: Make your own scene (1 point)

### Handin

Assignment handin will be done on Gradescope.

To create your submission, run the `create_submission.sh` script from the root of the repository:

```bash
./create_submission.sh
```

This will generate a `submission.zip` file containing all the required source files.

If you have completed extra credit scene, you can include your extra credit scene and/or rendered image using the optional arguments:

```bash
./create_submission.sh --extra-credit-scene <path_to_scene> --extra-credit-image <path_to_image>
```

The `--extra-credit-scene` argument accepts either a file or a directory. Both arguments are OPTIONAL. The extra credit files will be placed under the `extra_credit` folder in the submission.

Upload `submission.zip` to Gradescope.

All programming assignments in CS248A will be graded via a 15 minute in-person conversation with a course CA.  The CAs will ask you to render various scenes, and ask you questions about your code.  Your grade will be a function of both your ability to demonstrate correct code and your team's ability to answer CA questions about the code.
