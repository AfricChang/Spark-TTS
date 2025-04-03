# Spark-TTS GUI Documentation

This document describes how to set up and use the Spark-TTS GUI (`tts_gui.py`) for voice cloning using the Spark-TTS model.

## 1. Setup

### 1.1. Dependencies

Make sure you have the following Python libraries installed. You can typically install them using pip:

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cuXXX # Replace cuXXX with your CUDA version (e.g., cu118) or cpu
pip install soundfile transformers PyQt5 qfluentwidgets sip
```

*(Note: `sip` might be installed automatically with PyQt5)*

### 1.2. Spark-TTS Model

- Download or ensure you have the `pretrained_models/Spark-TTS-0.5B` directory in your project's root folder.
- The GUI currently expects the model to be in this specific location.

### 1.3. Resources Directory

The GUI uses a `Resources` directory for icons and output files. Ensure this directory exists or the application will attempt to create it.
- Output audio files will be saved in `Resources/output/`.

## 2. Running the GUI

Navigate to the project directory in your terminal (make sure your Python environment with the dependencies is activated) and run:

```bash
python tts_gui.py
```

## 3. Using the GUI for Voice Cloning

The GUI interface has been modified for Spark-TTS voice cloning:

![GUI Layout Sketch (Conceptual)](placeholder_for_gui_sketch.png) 
*Replace with an actual screenshot if possible*

- **Left Panel (Synthesis Inputs):**
    - **参考音频 (.wav / .mp3):** Click "浏览" to select a `.wav` or `.mp3` file containing the voice you want to clone. (Note: MP3 support depends on having necessary system audio libraries like ffmpeg installed).
    - **参考音频文本:** Enter the exact transcript (text content) corresponding to the selected reference audio file.
    - **合成文本:** Enter the text you want the cloned voice to speak.
    - **开始合成:** Click this button to start the voice cloning process.

- **Right Panel (Original UI - Ignored):** The voice selection grid, filters, and sliders on the right are part of the original Tencent TTS interface and are **not used** for Spark-TTS synthesis. You can ignore this panel.

- **Bottom Panel (Log & Player):**
    - **Log Area:** Shows progress messages, timings, and any errors during the synthesis process.
    - **Player Area:** Once synthesis is successful, controls will appear here to play the generated audio file (`sparktts_YYYYMMDD_HHMMSS.wav`).

### Workflow:

1.  Run `python tts_gui.py`.
2.  Click "浏览" under "参考音频" to select your `.wav` or `.mp3` voice sample.
3.  Enter the matching transcript for the reference audio in the "参考音频文本" field.
4.  Enter the desired output text in the "合成文本" field.
5.  Click "开始合成".
6.  Monitor the progress in the log area.
7.  If successful, use the player controls in the bottom right to listen to the output saved in `Resources/output/`.

## 4. Notes

- **Device:** The GUI automatically tries to use `cuda:0` if available, otherwise falls back to `cpu`. This is logged at startup.
- **Model Path:** The path `pretrained_models/Spark-TTS-0.5B` is hardcoded for now.
- **Error Handling:** Errors during synthesis will be displayed in the log area. Check the logs carefully if synthesis fails.
- **Original UI:** The right-hand panel with voice selection is currently unused and could be removed in future versions for clarity.
