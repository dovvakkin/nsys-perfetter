# nsys-perfetter (Nvidia Nsight Systems to Google Perfetto Converter)

This tool allows you to seamlessly convert Nvidia Nsight Systems profiles in SQLite format to the Google Perfetto visualizer Track Event protobuf format.

## 🌟 Features

- Tracks for all NVTX domains, kernels and memory operations on GPU, CUDA on CPU
- Multiple device profiles
- Links between CPU CUDA calls and GPU kernels
- Events info via Perfetto args window
- Streamlit application for easy profile conversion
- Supports profiles in SQLite (.sqlite) or .nsys-rep format
- Automatic conversion of .nsys-rep profiles to SQLite using nsys export (if nsys is available on the system)

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dovvakkin/nsys-perfetter
   ```

2. Build project docker image (uses last Nvidia nsight-systems-cli):
   ``` bash
   make docker-build
   ```

3. Run Streamlit in docker
   ```bash
   make docker-run
   ```

   App will be on `localhost:8501`

## 📚 API Reference
Converter is a `NsysReport` class from `lib/nsys_perfetter.py`. It accepts path to sqlite nsight report.

There is no complex track hiding in Perfetto, so in converted profile no tracks for threads that not intercat with devices and inactive (<0.1%) streams.

[Insert space for video demo here]

## 🐛 Known Issues
- Perfetto accepts profile via PostMessage from JavaScript, but passing little more than nothing (>50mb) is a problem for Streamlit. Maybe someday I'll implement more clean frontend in JS without Streamlit.
- There could be more info about memory operations.
- I could simply not collide with some profile details and, accordingly, not add them to the converter (CUDA Graphs for example).

