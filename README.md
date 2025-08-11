# CSK-SNIFFER DEMO

CSK-SNIFFER is a demo project for detecting object detection errors using commonsense knowledge. This repository provides all the necessary code and setup instructions to run the demo locally.

---

## 1. Download CSK-SNIFFER Repo

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/anuragg1209/CSK-SNIFFER.git
cd CSK-SNIFFER
```

---

## 2. Installing CSK-SNIFFER Environment

We recommend using **Python 3.7** and a **MacOSX/Linux** OS for best compatibility. Follow the steps below to set up your environment:

```bash
python3.7 -m venv csk-env
source csk-env/bin/activate
pip install -r requirements.txt  # You might get a warning to upgrade pip or Python version. Do NOT upgrade, as our dependencies require the older version.
```

---

## 3. Installing Darkflow Implementation of YOLO

We use [Darkflow](https://github.com/thtrieu/darkflow) to set up the YOLO model. Install it as follows:

```bash
cd yolo
git clone https://github.com/thtrieu/darkflow.git
cd darkflow
python3 setup.py build_ext --inplace
pip install .
```

---

## 4. Running the App

Return to the home directory (`CSK-SNIFFER`) and run the demo locally:

```bash
cd ../..
python flask_app.py
```

---

## 5. Model Weights

Model weights are included inside the folder `yolo/bin/`. Please download them using [git lfs](https://git-lfs.github.com/):

```bash
git lfs pull
```

---

## Citation

If you use this codebase or ideas from this work, please cite the following papers:

```
@article{Garg_Tandon_Varde_2020,
  title={I Am Guessing You Can’t Recognize This: Generating Adversarial Images for Object Detection Using Spatial Commonsense (Student Abstract)},
  volume={34},
  url={https://ojs.aaai.org/index.php/AAAI/article/view/7166},
  DOI={10.1609/aaai.v34i10.7166},
  number={10},
  journal={Proceedings of the AAAI Conference on Artificial Intelligence},
  author={Garg, Anurag and Tandon, Niket and Varde, Aparna S.},
  year={2020},
  month={Apr.},
  pages={13789-13790}
}

@inproceedings{Garg2022CSKSniffer,
  author    = {Anurag Garg and Niket Tandon and Aparna S. Varde},
  title     = {{CSK{-}SNIFFER}: Commonsense Knowledge for Sniffing Object Detection Errors},
  booktitle = {Proceedings of the EDBT/ICDT 2022 Joint Conference Workshops (BigVis)},
  year      = {2022},
  publisher = {CEUR-WS},
  volume    = {3135},
  address   = {Edinburgh, UK},
  url       = {https://ceur-ws.org/Vol-3135/bigvis_short2.pdf}
}
```

---

For any questions or issues, please open an issue on the [GitHub repository](https://github.com/anuragg1209/CSK-SNIFFER).
