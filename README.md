## Readerbot

Local agentic LLM to read docx files

## Running on an NVIDIA GPU (optional)

By default llama-cpp-python is built for the CPU and readerbot runs the model
there. With an NVIDIA GPU, part of the model (or all of it, if it fits) can run
on the GPU instead. That is faster and needs less system RAM.

**1. Build llama-cpp-python with CUDA.** This needs the CUDA Toolkit (its
`bin\x64` folder on `PATH`, which the installer sets up) and the Visual Studio
C++ tools. In PowerShell, in the repo folder; the paths are for Visual Studio
2026 Community, so adjust them for your installation:

```powershell
& "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\Launch-VsDevShell.ps1" -Arch amd64 -HostArch amd64 -SkipAutomaticLocation
$vsc = "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake"
$env:PATH = "$vsc\CMake\bin;$vsc\Ninja;$env:PATH"
$env:CMAKE_GENERATOR = "Ninja"
$env:CC = "cl"; $env:CXX = "cl"
$env:CMAKE_BUILD_PARALLEL_LEVEL = "8"
$env:CMAKE_ARGS = "-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=120"
uv cache clean llama-cpp-python
uv sync --reinstall-package llama-cpp-python
```

- `120` is the GPU's compute capability without the dot (12.0 is Blackwell);
  `nvidia-smi --query-gpu=compute_cap --format=csv` shows yours.
- `uv cache clean` is needed because uv would otherwise reinstall the CPU
  build it has cached.
- The VS CMake and Ninja go first on `PATH` so that no older CMake or other
  compiler that happens to be installed (e.g. with Strawberry Perl) is used.
  Ninja compiles the CUDA code on all cores: about 6 minutes here.
- To go back to the CPU build, run the same commands without the
  `CMAKE_ARGS` line. Keep the CPU build on machines without CUDA: the CUDA
  build needs the CUDA libraries to start at all.

**2. Set `GPU_LAYERS` in `config.py`.** It is the number of model layers that
run on the GPU (`-1` = all of them). Start-up then shows, for example,
`GPU: 20 of 48 layers`. Raise it until video memory is almost full: watch
`nvidia-smi` while a question runs, and keep a few hundred MB free.

| Model | Context | `GPU_LAYERS` on 8 GB | Video memory |
|---|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 Q3_K_M | 32768 | 20 | 7.4 GB |

Even with `GPU_LAYERS = 0`, a CUDA build still uses the GPU to speed up reading
long prompts (about 0.75 GB of video memory). To keep the GPU completely free,
start readerbot with `$env:CUDA_VISIBLE_DEVICES = "-1"`.

**Too many layers?** When video memory runs out, the Windows NVIDIA driver
does not report an error; it quietly moves data to system RAM, which is very
slow. In the NVIDIA Control Panel, set *Manage 3D settings → CUDA - Sysmem
Fallback Policy* to *Prefer No Sysmem Fallback* to get an error instead, then
lower `GPU_LAYERS`.
