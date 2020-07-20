# Beaverlog Tools

In this repository you find various scripts for interacting with the beaverlog API. For example to back up your data.

## Requirements

Install [poetry](https://python-poetry.org/docs/#installation):

```bash
# install:
sudo apt install -y python3-venv
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

# or update:
poetry self update
```

Install timetracker-tools locally (in a subfolder):

```bash
git clone https://git.nevees.org/fabianvss/timetracker-tools.git
cd timetracker-tools

source .envrc  # poetry configuration (mandatory if you have not installed direnv)
pyenv install --skip-existing  # optional (may remove some warnings; requires pyenv)

rm -rf .venv
poetry install
rm -rf beaverlog_tools.egg-info
```

## Usage

Run the python scripts as follows:

```bash
poetry run COMMAND
```

### API v1 ([beaverlog.cc](https://beaverlog.cc/api/swagger-ui))

Use the scripts in the `v1` directory, f.ex.:

```bash
poetry run v1/upload.py --help
```

### API v0 ([time.nevees.org](http://time.nevees.org/api/swagger-ui))

Use the scripts in the `v0` directory, f.ex.:

```bash
poetry run v0/download.py --help
```

## Example

To migrate your data from [time.nevees.org](http://time.nevees.org) to [beaverlog.cc](https://beaverlog.cc), run:

```bash
poetry run v0/download.py data-$(date --iso-8601).json -e YOUR_EMAIL
poetry run v1/upload.py   data-$(date --iso-8601).json -e YOUR_EMAIL
```
