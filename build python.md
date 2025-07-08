##  Python 3.15+ Installation

This guide explains how to **download, build, and install Python 3.15 or later** from source on a development machine.
---

### Prerequisites

Install required system packages:

```bash
sudo apt update
sudo apt install -y wget build-essential libssl-dev zlib1g-dev \
  libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
  libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev \
  tk-dev libffi-dev uuid-dev
```

---

### Download Python Source Code

Visit the official Python website: [https://www.python.org/downloads/](https://www.python.org/downloads/)

Then download the latest `.tar.xz` source package, for example:

```bash
cd /usr/src
sudo wget https://www.python.org/ftp/python/3.15.0/Python-3.13.5.tar.xz
sudo tar -xf Python-3.13.5.tar.xz
cd Python-3.15.0
```

---

###  Build and Install

```bash
sudo ./configure --enable-optimizations
sudo make -j$(nproc)
sudo make altinstall
```

> ⚠ Use `make altinstall` instead of `make install` to avoid overwriting the system's default Python.

---

###  Verify Installation

```bash
python3.13 --version
```

Expected output:

```
Python 3.13.5
```
