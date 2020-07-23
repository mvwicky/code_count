SHELL:=bash
.ONESHELL:
.SHELLFLAGS:=-eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

TMP_DIR=.tmp
CACHE_DIR=.cache
SRC_DIR=src
TESTS_DIR=tests
FIND_PY_ARGS=-type f -name '*.py'
SRC_FILES=$(shell find $(SRC_DIR) $(FIND_PY_ARGS))
TEST_FILES=$(shell find $(TESTS_DIR) $(FIND_PY_ARGS))
FLAKE8_SENTINEL=$(TMP_DIR)/flake8.sentinel
LIMIT?=100
CCOUNT_ARGS?=

.PHONY: flake8 clean watch test

flake8: $(FLAKE8_SENTINEL)

clean:
	-trash -v $(TMP_DIR)

$(FLAKE8_SENTINEL): $(SRC_FILES) $(TEST_FILES)
	@mkdir -p $(@D)
	flake8 $?
	date > $(FLAKE8_SENTINEL)

test:
	ccount -b dev --limit $(LIMIT) $(CCOUNT_ARGS) ../GitHub/main-resell

watch:
	watchexec -e py -d 500 -- $(MAKE) test
