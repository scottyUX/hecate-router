# ARM64 rebuild of jyangballin/swesmith.x86_64.jd_1776_tenacity.0d40e76f (E10 G0b).
# Same layout: conda env "testbed" at /opt/miniconda3, Python 3.10.16, the x86
# image pip versions, /testbed copied verbatim (incl. .git with instance branches).
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
RUN apt-get update && apt-get install -y --no-install-recommends git wget ca-certificates bzip2 build-essential && rm -rf /var/lib/apt/lists/*
RUN wget -q https://github.com/conda-forge/miniforge/releases/download/24.11.3-0/Miniforge3-24.11.3-0-Linux-aarch64.sh -O /tmp/mf.sh \
 && bash /tmp/mf.sh -b -p /opt/miniconda3 && rm /tmp/mf.sh
ENV PATH=/opt/miniconda3/bin:$PATH
RUN conda create -y -n testbed python=3.10.16 pip=24.2 wheel=0.44.0 setuptools=75.1.0 && conda clean -afy
COPY requirements.txt /tmp/requirements.txt
RUN /opt/miniconda3/envs/testbed/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY testbed /testbed
RUN cd /testbed && /opt/miniconda3/envs/testbed/bin/pip install --no-cache-dir --no-deps -e . \
 && git config --global --add safe.directory /testbed
RUN echo "source /opt/miniconda3/etc/profile.d/conda.sh && conda activate testbed" >> /root/.bashrc
WORKDIR /testbed
CMD ["/bin/bash"]
