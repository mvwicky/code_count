SHELL:=bash
.ONESHELL:
.SHELLFLAGS:=-eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

TMP_DIR=.tmp
CACHE_DIR=.cache
SRC_DIR=src
SRC_FILES=$(shell find $(SRC_DIR) -type f -name '*.py')
FLAKE8_SENTINEL=$(TMP_DIR)/flake8.sentinel

.PHONY: flake8 clean watch test

flake8: $(FLAKE8_SENTINEL)

clean:
	-trash -v $(TMP_DIR)

$(FLAKE8_SENTINEL): $(SRC_FILES)
	mkdir -p $(@D)
	flake8 --statistics $?
	date > $(FLAKE8_SENTINEL)

test:
	ccount -b dev --limit 100 ../GitHub/main-resell

watch:
	watchexec -e py -d 500 -- $(MAKE) test
