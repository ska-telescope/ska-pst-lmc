#
# Project makefile for a PST LMC project.

PROJECT = ska-pst-lmc

HELM_CHARTS_TO_PUBLISH = ska-pst-lmc

# E203 and W503 conflict with black
PYTHON_TEST_FILE = tests
## Paths containing python to be formatted and linted
PYTHON_LINT_TARGET = src/ tests/
PYTHON_LINE_LENGTH = 110

PYTHON_SWITCHES_FOR_FLAKE8 = --extend-ignore=BLK,T --enable=DAR104 --ignore=E203,FS003,W503,N802 --max-complexity=10 \
    --rst-roles=py:attr,py:class,py:const,py:exc,py:func,py:meth,py:mod \
		--rst-directives deprecated,uml --exclude=src/ska_pst_lmc_proto
PYTHON_SWITCHES_FOR_BLACK = --force-exclude=src/ska_pst_lmc_proto
PYTHON_SWITCHES_FOR_ISORT = --skip-glob="*/__init__.py" --py 39 --thirdparty=ska_pst_lmc_proto
PYTHON_SWITCHES_FOR_PYLINT = --disable=W,C,R --ignored-modules="ska_pst_lmc_proto"
PYTHON_SWITCHES_FOR_AUTOFLAKE ?= --in-place --remove-unused-variables --remove-all-unused-imports --recursive --ignore-init-module-imports
PYTHON_SWITCHES_FOR_DOCFORMATTER ?= -r -i --black --style sphinx --wrap-summaries $(PYTHON_LINE_LENGTH) --wrap-descriptions $(PYTHON_LINE_LENGTH) --pre-summary-newline

DOCS_SOURCEDIR=./docs/src
PYTHON_VARS_AFTER_PYTEST = --cov-config=$(PWD)/.coveragerc

K8S_CHART ?= test-parent
K8S_CHARTS ?= $(K8S_CHART)
K8S_UMBRELLA_CHART_PATH ?= charts/$(K8S_CHART)/

PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=$(PWD)/src:$(PWD)/generated

ifeq ($(strip $(firstword $(MAKECMDGOALS))),k8s-test)
# need to set the PYTHONPATH since the ska-cicd-makefile default definition
# of it is not OK for the alpine images
PYTHON_VARS_BEFORE_PYTEST = TANGO_HOST="$(TANGO_HOST)"
PYTHON_VARS_AFTER_PYTEST := -m 'integration' --disable-pytest-warnings --forked
endif

PROTOBUF_DIR=$(PWD)/protobuf
GENERATED_PATH=$(PWD)/generated

PROTOBUF_IMAGE ?= $(SKA_PST_COMMON_PROTOBUF_IMAGE)

OCI_BUILD_ADDITIONAL_ARGS=--build-arg PROTOBUF_IMAGE=$(PROTOBUF_IMAGE)

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

# Variables populated for local development and oci build.
# 	Overriden by CI variables. See .gitlab-cy.yml#L7
SKA_RELEASE_REGISTRY=artefact.skao.int
PST_DEV_REGISTRY=registry.gitlab.com/ska-telescope/pst

SKA_TANGO_PYTANGO_BUILDER_REGISTRY=$(SKA_RELEASE_REGISTRY)
SKA_TANGO_PYTANGO_BUILDER_IMAGE=ska-tango-images-pytango-builder
SKA_TANGO_PYTANGO_BUILDER_TAG=9.4.3
SKA_PST_PYTHON_BUILDER_IMAGE=$(SKA_TANGO_PYTANGO_BUILDER_REGISTRY)/$(SKA_TANGO_PYTANGO_BUILDER_IMAGE):$(SKA_TANGO_PYTANGO_BUILDER_TAG)

SKA_TANGO_PYTANGO_RUNTIME_REGISTRY=$(SKA_RELEASE_REGISTRY)
SKA_TANGO_PYTANGO_RUNTIME_IMAGE=ska-tango-images-pytango-runtime
SKA_TANGO_PYTANGO_RUNTIME_TAG=9.4.3
SKA_PST_PYTHON_RUNTIME_IMAGE=$(SKA_TANGO_PYTANGO_RUNTIME_REGISTRY)/$(SKA_TANGO_PYTANGO_RUNTIME_IMAGE):$(SKA_TANGO_PYTANGO_RUNTIME_TAG)

PST_COMMON_TAG=0.10.2

PST_OCI_COMMON_BUILDER_REGISTRY=$(PST_DEV_REGISTRY)/ska-pst-common
PST_OCI_COMMON_BUILDER_IMAGE=ska-pst-common-builder
PST_OCI_COMMON_BUILDER_TAG?=$(PST_COMMON_TAG)
SKA_PST_COMMON_BUILDER_IMAGE=$(PST_OCI_COMMON_BUILDER_REGISTRY)/$(PST_OCI_COMMON_BUILDER_IMAGE):$(PST_OCI_COMMON_BUILDER_TAG)

PST_COMMON_PROTO_REGISTRY=$(PST_DEV_REGISTRY)/ska-pst-common
PST_COMMON_PROTO_IMAGE=ska-pst-common-proto
PST_COMMON_PROTO_TAG?=$(PST_COMMON_TAG)
SKA_PST_COMMON_PROTOBUF_IMAGE=$(PST_COMMON_PROTO_REGISTRY)/$(PST_COMMON_PROTO_IMAGE):$(PST_COMMON_PROTO_TAG)
OCI_BUILD_ADDITIONAL_ARGS = --build-arg BUILD_IMAGE=$(SKA_PST_PYTHON_BUILDER_IMAGE) --build-arg BASE_IMAGE=$(SKA_PST_PYTHON_RUNTIME_IMAGE) --build-arg PST_COMMON_BUILDER_IMAGE=$(SKA_PST_COMMON_BUILDER_IMAGE) --build-arg PROTOBUF_IMAGE=$(SKA_PST_COMMON_PROTOBUF_IMAGE)

# define private overrides for above variables in here
-include PrivateRules.mak

.DEFAULT_GOAL := help

# Add this for typehints & static type checking
mypy:
	$(PYTHON_RUNNER) mypy --config-file mypy.ini $(PYTHON_LINT_TARGET)

flake8:
	$(PYTHON_RUNNER) flake8 --show-source --statistics $(PYTHON_SWITCHES_FOR_FLAKE8) $(PYTHON_LINT_TARGET)

python-post-format:
	$(PYTHON_RUNNER) autoflake $(PYTHON_SWITCHES_FOR_AUTOFLAKE) $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) docformatter $(PYTHON_SWITCHES_FOR_DOCFORMATTER) $(PYTHON_LINT_TARGET)

python-post-lint: mypy

.PHONY: python-post-format, notebook-format, notebook-post-format, python-post-lint, mypy, flake8

local-oci-scan:
	docker run -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image $(strip $(OCI_IMAGE)):$(VERSION)

python-pre-generate-code:
	@echo "Installing dev dependencies for Python gRPC/Protobuf code generation."
	poetry install --with dev
	@echo "Ensuring generated path $(GENERATED_PATH) exists"
	mkdir -p $(GENERATED_PATH)

python-do-generate-code:
	@echo "Generating Python gRPC/Protobuf code."
	@echo "PROTOBUF_DIR=$(PROTOBUF_DIR)"
	@echo "GENERATED_PATH=$(GENERATED_PATH)"
	@echo
	@echo "List of protobuf files: $(shell find "$(PROTOBUF_DIR)" -iname "*.proto")"
	@echo
	$(PYTHON_RUNNER) python3 -m grpc_tools.protoc --proto_path="$(PROTOBUF_DIR)" \
			--python_out="$(GENERATED_PATH)" \
			--init_python_out="$(GENERATED_PATH)" \
			--init_python_opt=imports=protobuf+grpcio \
			--grpc_python_out="$(GENERATED_PATH)" \
			$(shell find "$(PROTOBUF_DIR)" -iname "*.proto")
	@echo
	@echo "Files generated. $(shell find "$(GENERATED_PATH)" -iname "*.py")"

python-post-generate-code:

python-generate-code: python-pre-generate-code python-do-generate-code python-post-generate-code

local_generate_code:
	@echo "Generating Python gRPC/Protobuf code."
	@echo "PROTOBUF_DIR=$(PROTOBUF_DIR)"
	@echo "GENERATED_PATH=$(GENERATED_PATH)"
	@echo
	@echo "List of protobuf files: $(shell find "$(PROTOBUF_DIR)" -iname "*.proto")"
	@echo
	@echo "Ensuring generated path $(GENERATED_PATH) exists"
	mkdir -p $(GENERATED_PATH)
	@echo
	python -m grpc_tools.protoc --proto_path="$(PROTOBUF_DIR)" \
			--python_out="$(GENERATED_PATH)" \
			--init_python_out="$(GENERATED_PATH)" \
			--init_python_opt=imports=protobuf+grpcio \
			--grpc_python_out="$(GENERATED_PATH)" \
			$(shell find "$(PROTOBUF_DIR)" -iname "*.proto")
	@echo
	@echo "Files generated. $(shell find "$(GENERATED_PATH)/ska_pst_lmc_proto" -iname "*.py")"

.PHONY: local_generate_code python-pre-build python-generate-code python-pre-generate-code python-do-generate-code python-post-generate-code

DEV_IMAGE=artefact.skao.int/ska-tango-images-pytango-builder-alpine:9.3.30
local-dev-env:
	docker run -ti --rm -v $(PWD):/mnt/$(PROJECT) -w /mnt/$(PROJECT) $(DEV_IMAGE) bash

.PHONY: local-dev-env

MINIKUBE ?= true
CI_JOB_ID ?= local##pipeline job id
TANGO_HOST ?= tango-databaseds:10000## TANGO_HOST connection to the Tango DS
K8S_TEST_RUNNER = test-runner-$(CI_JOB_ID)##name of the pod running the k8s-test

# Single image in root of project
OCI_IMAGES = ska-pst-lmc
TANGO_HOST ?= databaseds-tango-base-test:10000

ifneq ($(CI_REGISTRY),)
K8S_TEST_TANGO_IMAGE = --set ska-pst-lmc.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA) \
        --set ska-pst-lmc.image.registry=$(CI_REGISTRY)/ska-telescope/pst/ska-pst-lmc
K8S_TEST_IMAGE_TO_TEST = $(CI_REGISTRY)/ska-telescope/pst/ska-pst-lmc/ska-pst-lmc:$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
else
K8S_TEST_TANGO_IMAGE = --set ska-pst-lmc.image.tag=$(VERSION)
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
