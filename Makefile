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

MINIKUBE ?= true
CI_JOB_ID ?= local##pipeline job id
TANGO_HOST ?= tango-databaseds:10000## TANGO_HOST connection to the Tango DS
K8S_TEST_RUNNER = test-runner-$(CI_JOB_ID)##name of the pod running the k8s-test

# Single image in root of project
OCI_IMAGES = ska-pst-lmc
TANGO_HOST ?= databaseds-tango-base-test:10000

ifneq ($(CI_REGISTRY),)
K8S_TEST_TANGO_IMAGE = --set ska_pst_lmc.ska_pst_lmc.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA) \
        --set ska_pst_lmc.ska_pst_lmc.image.registry=$(CI_REGISTRY)/ska-telescope/pst/ska-pst-lmc
K8S_TEST_IMAGE_TO_TEST = $(CI_REGISTRY)/ska-telescope/pst/ska-pst-lmc/ska-pst-lmc:$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
else
K8S_TEST_TANGO_IMAGE = --set ska_pst_lmc.ska_pst_lmc.image.tag=$(VERSION)
K8S_TEST_IMAGE_TO_TEST = $(CAR_OCI_REGISTRY_HOST)/$(NAME):$(VERSION)
endif

PROXY_VALUES ?= --env="HTTPS_PROXY=$(HTTPS_PROXY)" --env="HTTP_PROXY=$(HTTP_PROXY)" --env="NO_PROXY=$(NO_PROXY)"  \
	--env="https_proxy=$(HTTPS_PROXY)" --env="http_proxy=$(HTTP_PROXY)" --env="no_proxy=$(NO_PROXY)"

SMRB ?= true
K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set ska-tango-base.display=$(DISPLAY) \
	--set ska-tango-base.xauthority=$(XAUTHORITY) \
	--set ska-tango-base.jive.enabled=$(JIVE) \
	--set ska-pst-smrb.enabled=$(SMRB) \
	${K8S_TEST_TANGO_IMAGE}

k8s_test_command = /bin/bash -o pipefail -c "\
	mkfifo results-pipe && tar zx --warning=all && \
        ( if [[ -f pyproject.toml ]]; then poetry export --format requirements.txt --output poetry-requirements.txt --without-hashes --dev; echo 'k8s-test: installing poetry-requirements.txt';  pip install -Ur poetry-requirements.txt; else if [[ -f $(k8s_test_folder)/requirements.txt ]]; then echo 'k8s-test: installing $(k8s_test_folder)/requirements.txt'; pip install -Ur $(k8s_test_folder)/requirements.txt; fi; fi ) && \
		echo \"Dev python packages installed.\" && \
		export PYTHONPATH=${PYTHONPATH}:/app/src$(k8s_test_src_dirs) && \
		mkdir -p build && \
		echo \"Executing: \$$(K8S_TEST_TEST_COMMAND)\" && \
	( \
	$(K8S_TEST_TEST_COMMAND) \
	); \
	echo \$$? > build/status; pip list > build/pip_list.txt; \
	echo \"k8s_test_command: test command exit is: \$$(cat build/status)\"; \
	tar zcf results-pipe build;"
