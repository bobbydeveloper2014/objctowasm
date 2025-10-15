import os
import subprocess
import sys
from pathlib import Path

# ==============================
# CONFIG
# ==============================
LLVM_PATH = "/usr/local/opt/llvm/bin"       # Brew LLVM path
WASI_SYSROOT = "/opt/wasi-sysroot"          # WASI sysroot
OUTPUT_DIR = "./build"
DOCKER_IMAGE = "ghcr.io/webassembly/wasi-sdk:latest"  # fallback

# ==============================
# FUNCTION RUN COMMAND
# ==============================
def run(cmd, stop_on_fail=True):
    print(f"\n⚙️  Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ Error:")
        print(res.stderr)
        if stop_on_fail:
            sys.exit(1)
        return False
    print("✅ Done")
    return True

# ==============================
# MAIN PIPELINE
# ==============================
def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <file.m>")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"❌ File not found: {src}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ll_file = Path(OUTPUT_DIR) / (src.stem + ".ll")
    o_file = Path(OUTPUT_DIR) / (src.stem + ".o")
    wasm_file = Path(OUTPUT_DIR) / (src.stem + ".wasm")

    # ---------------------------------
    # 1️⃣ Compile Objective-C -> LLVM IR (.ll)
    # ---------------------------------
    run([
        f"{LLVM_PATH}/clang",
        "-S", "-emit-llvm",
        str(src),
        "-o", str(ll_file),
        "-fobjc-arc", "-framework", "Foundation"
    ])

    # ---------------------------------
    # 2️⃣ LLVM IR -> Object file (.o)
    # ---------------------------------
    run([
        f"{LLVM_PATH}/llc",
        str(ll_file),
        "-filetype=obj",
        "-o", str(o_file)
    ])

    # ---------------------------------
    # 3️⃣ Object -> WebAssembly (.wasm)
    # ---------------------------------
    ok = run([
        f"{LLVM_PATH}/clang",
        "--target=wasm32-unknown-wasi",
        f"--sysroot={WASI_SYSROOT}",
        "-O2", "-s",
        "-o", str(wasm_file),
        str(o_file)
    ], stop_on_fail=False)

    # ---------------------------------
    # 4️⃣ Fallback Docker nếu clang fail
    # ---------------------------------
    if not ok:
        print("\n⚠️ clang failed — fallback sang Docker WASI-SDK...")
        run([
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}:/src", "-w", "/src",
            DOCKER_IMAGE,
            "/wasi-sdk/bin/clang",
            "--target=wasm32-wasi",
            "-O2", "-o", str(wasm_file),
            str(o_file)
        ])

    print(f"\n🎉 Build hoàn tất → {wasm_file}")

if __name__ == "__main__":
    main()
