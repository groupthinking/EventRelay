# FastVLM Integration Setup

Follow these steps whenever you need the Apple FastVLM repo for local vision-language processing.

## 1. Clone the upstream repository

```bash
git clone https://github.com/apple/ml-fastvlm.git external/ml-fastvlm
```

## 2. Download model checkpoints

```bash
cd external/ml-fastvlm
./get_models.sh  # pick the models you need per the upstream docs
```

## 3. Install the FastVLM Python dependencies

Run this from your active project virtualenv:

```bash
pip install -r external/ml-fastvlm/requirements.txt
```

## 4. Configure environment variables

Ensure the wrapper knows where to find the repo and checkpoints. Add these to `.env` or export them directly:

```env
FASTVLM_REPO_PATH=external/ml-fastvlm
FASTVLM_MODEL_PATH=external/ml-fastvlm/checkpoints/<model_dir>
```

## 5. Verify the setup

Run the smoke tests to confirm the wrapper loads correctly:

```bash
pytest tests/test_working_version.py -k fastvlm
```

## Troubleshooting

- If you see `FastVLM repository path not found`, check the `FASTVLM_REPO_PATH` value.
- On macOS, ensure your PyTorch build supports MPS. You can grab the CPU wheels with:
  ```bash
  pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
  ```
- For GPU acceleration, install the CUDA-compatible PyTorch build from the official instructions.
