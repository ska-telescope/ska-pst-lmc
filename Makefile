#
# Project makefile for a SAT.LMC project. 

PROJECT = ska-pst-lmc

HELM_CHARTS_TO_PUBLISH = ska-pst-lmc

# E203 and W503 conflict with black
PYTHON_SWITCHES_FOR_FLAKE8 = --extend-ignore=BLK,T --enable=DAR104 --ignore=E203,FS003,W503,N802 --max-complexity=10 \
    --max-line-length=110 --rst-roles=py:attr,py:class,py:const,py:exc,py:func,py:meth,py:mod
PYTHON_SWITCHES_FOR_BLACK = --line-length=110
PYTHON_SWITCHES_FOR_ISORT = --skip-glob=*/__init__.py -w=110
PYTHON_TEST_FILE = tests
PYTHON_LINT_TARGET = src tests  ## Paths containing python to be formatted and linted
PYTHON_SWITCHES_FOR_PYLINT = --disable=W,C,R
DOCS_SOURCEDIR=./docs/src

K8S_CHART ?= test-parent
K8S_CHARTS ?= $(K8S_CHART)
K8S_UMBRELLA_CHART_PATH ?= charts/$(K8S_CHART)/

TANGO_HOST ?= databaseds-tango-base-test:10000

ifeq ($(strip $(firstword $(MAKECMDGOALS))),k8s-test)
# need to set the PYTHONPATH since the ska-cicd-makefile default definition 
# of it is not OK for the alpine images
PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=/app/src:/usr/local/lib/python3.9/site-packages TANGO_HOST="$(TANGO_HOST)"
PYTHON_VARS_AFTER_PYTEST := -m 'integration' --disable-pytest-warnings --forked
endif

# include OCI support
include .make/oci.mk

# include k8s support
include .make/k8s.mk

# include Helm Chart support
include .make/helm.mk

# include Python support
include .make/python.mk

# include core make support
include .make/base.mk

# define private overrides for above variables in here
-include PrivateRules.mak

.DEFAULT_GOAL := help

# Add this for typehints & static type checking
python-post-format:
	$(PYTHON_RUNNER) docformatter -r -i --wrap-summaries 88 --wrap-descriptions 72 --pre-summary-newline src/ tests/

python-post-lint:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini src/ tests/

.PHONY: python-post-format python-post-lint
