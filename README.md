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

## 📹 Demo
GPT2-Medium from TensorRT-LLM examples profile

https://github.com/dovvakkin/nsys-perfetter/assets/40765059/c45d8df5-177b-4fcf-b671-be8356a5bde4

<img width="1060" alt="gpt2_nsys" src="https://github.com/dovvakkin/nsys-perfetter/assets/40765059/e0a7f100-7cee-4871-8f60-2acc7e331963">

<img width="1128" alt="gpt2_perfetto" src="https://github.com/dovvakkin/nsys-perfetter/assets/40765059/b3f9751a-162d-4213-bfa7-da52505023bf">



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

There is no complex track hiding in Perfetto, so in converted profile no tracks for threads that not interact with devices and inactive (<0.1%) streams.

## 🐛 Known Issues
- Perfetto accepts profile via PostMessage from JavaScript, but passing little more than nothing (>50mb) is a problem for Streamlit. Maybe someday I'll implement more clean frontend in JS without Streamlit.
- There could be more info about memory operations.
- I could simply not collide with some profile details and, accordingly, not add them to the converter (CUDA Graphs for example).
- Compatibility between SQLite exported profiles is not guaranteed. Project tested with schema version **3.11.1**

