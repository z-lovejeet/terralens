# Test folder for Sort my photos

30 real EuroSAT satellite patches (64 × 64 px, Sentinel-2 RGB) for trying the **Sort my photos** page:
six each of forest, lake or sea, houses, crop fields and industrial areas, shuffled and renamed
`photo_01.jpg` … `photo_30.jpg` so the file names give nothing away.

All 30 come from the **held-out** cohort, so none of them were used to fit the scaler, PCA or
K-Means models — a fair test. `answer_key.csv` lists the true land type of each file so you can
check the groups afterwards.

## How to test

1. Open **Sort my photos**, click **Choose a folder** and pick this folder (or drag the photos in).
2. Leave **Number of groups** on **Auto** and click **Sort photos**.
3. Compare the groups with `answer_key.csv`.

## What to expect (measured)

With these exact files, Auto picks **5 groups** that are **83 % pure** (adjusted Rand index 0.68):
crop fields, houses and industrial areas each get their own group, while forest and water partly
share one (both look dark and smooth in RGB). Results on other random sets of five land types
average about 72 % purity.
