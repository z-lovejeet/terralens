# Test image for Map my image

`demo-scene.jpg` is a 512 × 512 px scene built from 64 real **held-out** EuroSAT patches (8 × 8 tiles) in four blobs: forest, lake or sea, houses and crop fields. The patches never took part in fitting the scaler, PCA or K-Means models, so it is a fair test.

## How to test

1. Open **Map my image** and drop `demo-scene.jpg` into the upload box (or click it and choose the file).
2. Leave **Number of regions** on *Auto* and read the result.

## What to expect (measured)

Auto finds **4 regions** that match the four blobs closely (adjusted Rand index **0.93**): trees about 37 %, water about 25 %, buildings about 19 % and fields about 18 %. Because this scene is built from patches of the same kind as the training data, the regions are named by the 30-group land model.

The scene is the clearest of 40 randomly drawn four-blob scenes, chosen to give a readable demonstration. Typical results are lower: over 30 random scenes of 2–5 blobs the average agreement is about 0.51 (see the benchmark table in the main README).
