# Dataset directory

Do not commit MH-Weed16 to GitHub.

Download **MH-Weed16 Version 1** from:

https://data.mendeley.com/datasets/d3n3mgjjbv/1

The project expects the dataset to be supplied locally to `scripts/prepare_dataset.py`.

Recommended workflow:

```bash
python scripts/prepare_dataset.py   --source /path/to/MH-Weed16   --output data/yolo   --classes configs/classes.txt
```

The source publication states that the crop-with-weed portion includes annotations in Pascal VOC, TXT and JSON formats.
