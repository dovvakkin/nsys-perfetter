import os
import pathlib
import shutil

import streamlit as st

from app.opener_component import perfetto_opener
from lib import nsys_perfetter

STREAMLIT_CACHE = os.environ["STREAMLIT_CACHE"]
NSYS_BIN_PATH = os.environ.get("NSYS_BIN_PATH")


def open_perfetto(perfetto_proto_file):
    with open(perfetto_proto_file, "rb") as f:
        with st.spinner("Opening profile in ui.perfetto.dev"):
            byte_array = [i for i in f.read()]
            _ = perfetto_opener(byte_array=byte_array)
            st.toast("Wait for perfetto tab open and load", icon="⏳")


def stem_filename(filename):
    return pathlib.Path(filename).stem


def make_sqlite_report(local_report):
    if local_report.endswith(".sqlite"):
        return local_report

    if shutil.which("nsys") is None:
        raise RuntimeError("Cannot process .nsys-rep reports without nsys in PATH")

    sqlite_report = local_report[: local_report.rfind(".")] + ".sqlite"
    print(sqlite_report)
    os.system(f"nsys export {local_report} --type sqlite --force-overwrite true --output {sqlite_report}")

    return sqlite_report


st.title("Nsys Perfetter")


uploaded_file = st.file_uploader("Upload file", accept_multiple_files=False)

if uploaded_file is not None:
    local_report = os.path.join(STREAMLIT_CACHE, uploaded_file.name)
    with open(local_report, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if local_report not in st.session_state:
        with st.spinner("Converting to Perfetto TrackEvent"):
            local_sqlite_report = make_sqlite_report(local_report)
            print(local_sqlite_report)
            nsys_report = nsys_perfetter.NsysReport(local_sqlite_report)
            local_converted_report = os.path.join(
                STREAMLIT_CACHE, f"{stem_filename(uploaded_file.name)}.perfetto-proto"
            )
            nsys_report.save_trace(local_converted_report)
        st.session_state[local_report] = local_converted_report

    with open(st.session_state[local_report], "rb") as f:
        report_bytes = f.read()

    btn = st.download_button(
        "Download Perfetto Profile", report_bytes, os.path.basename(st.session_state[local_report])
    )

    st.button(
        "Open trace in Perfetto UI",
        key="open_trace_button",
        on_click=lambda: open_perfetto(st.session_state[local_report]),
    )
