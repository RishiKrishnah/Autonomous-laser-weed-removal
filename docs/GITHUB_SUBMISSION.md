# GitHub Submission Checklist

Before pushing:

- [ ] Dataset is not committed.
- [ ] No API keys or passwords are present.
- [ ] `pip install -r requirements.txt` works.
- [ ] `pytest -q` passes.
- [ ] A trained `best.pt` is available locally.
- [ ] `scripts/train_detector.py` completes.
- [ ] `scripts/evaluate_detector.py` completes.
- [ ] Camera inference works in safe mode.
- [ ] Targeting calibration has been measured rather than assumed.
- [ ] Experimental metrics are entered into `docs/EXPERIMENTS.md`.
- [ ] Final report cites MH-Weed16 Version 1 and its paper.
- [ ] Hardware safety documentation is included.
- [ ] Laser is not enabled by default.

Recommended Git commands:

```bash
git add .
git status
git commit -m "Initial submission-ready implementation"
git branch -M main
git push -u origin main
```
