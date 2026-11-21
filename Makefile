# SnakTUI — Makefile
# Python + Textual Snake game. The game core (game.py / models.py / theme.py /
# storage.py) must stay importable without Textual — pytest covers both.
#
#   make run      launch the game (needs a TTY)
#   make test     headless pytest suite (106 tests, no TTY needed)
#   make lint     ruff
#   make check    lint + test
#   make clean    remove caches

PYTHON ?= python3
export TMPDIR ?= /data/data/com.termux/files/usr/tmp
SNAKTUI_DATA_DIR ?= $(TMPDIR)/snaktui-test-state

.PHONY: run test lint check clean

run:
	$(PYTHON) -m snaktui

lint:
	ruff check .

test:
	SNAKTUI_DATA_DIR="$(SNAKTUI_DATA_DIR)" $(PYTHON) -m pytest -q

check: lint test
	$(PYTHON) -m snaktui --help >/dev/null

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info "$(SNAKTUI_DATA_DIR)"