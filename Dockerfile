FROM ubuntu:24.04

WORKDIR /app

RUN apt update
RUN apt install -y --no-install-recommends gnupg
RUN echo "deb http://developer.download.nvidia.com/devtools/repos/ubuntu2404/amd64 /" | tee /etc/apt/sources.list.d/nvidia-devtools.list
RUN apt-key adv --fetch-keys http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/7fa2af80.pub
RUN apt update
RUN apt install -y nsight-systems-cli

RUN apt install -y python3.12 python3-pip && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

COPY . /app

ENV STREAMLIT_CACHE=/tmp

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "app/streamlit_app.py"]

