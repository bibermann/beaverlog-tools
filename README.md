# Beaverlog Tools

In this repository you find various scripts for interacting with the beaverlog API. For example to back up your data.

## Requirements

Install [direnv](https://direnv.net/docs/installation.html), [pyenv](https://github.com/pyenv/pyenv#installation)
and [poetry](https://python-poetry.org/docs/#installation).

When entering the root directory of this repository, direnv will ask you to run `direnv allow`.
This is necessary once to configure poetry.

## Usage

Run the python scripts as follows:

```bash
poetry run -- COMMAND
```

### API v1 ([beaverlog.cc](https://beaverlog.cc/api/swagger-ui))

Use the scripts in the `v1` directory, f.ex.:

```bash
poetry run -- v1/upload.py --help
```

### API v0 ([time.nevees.org](http://time.nevees.org/api/swagger-ui))

Use the scripts in the `v0` directory, f.ex.:

```bash
poetry run -- v0/download.py --help
```

## Example

To migrate your data from [time.nevees.org](http://time.nevees.org) to [beaverlog.cc](https://beaverlog.cc), run:

```bash
poetry run -- v0/download.py data.json -e YOUR_EMAIL
poetry run -- v1/upload.py   data.json -e YOUR_EMAIL
```
