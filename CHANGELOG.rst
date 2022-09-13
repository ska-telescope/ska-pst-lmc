###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

0.2.1 (2022-08-26)
------------------
- AT3-262 ensure updating alpine packages as part of build [Will Gauvin]
- AT3-262 ensure poetry is available in builder [Will Gauvin]
- AT3-262 update base pytango images [Will Gauvin]
- AT3-262 rename tango devices to match ADR-9 [Will Gauvin]
- AT3-262 update deployment using released ska-pst-recv [Will Gauvin]
- AT3-262 update helm configuration for test-parent to use recv and smrb [Will Gauvin]
- AT3-262 update test request fixtures [Will Gauvin]
- AT3-262 use exclusive range for start/end channels [Will Gauvin]
- AT3-241 ensure RECV can handle abort/reset/restart commands [Will Gauvin]


0.2.1 (2022-08-26)
------------------
- REL-217 update CHANGELOG.rst [Will Gauvin]
- REL-217 bump patch version to 0.2.1. [Will Gauvin]

0.2.0 (2022-08-24)
------------------
- REL-217: bumped version to 0.2.0. [Andrew Jameson]
- AT3-242 integrate RECV Tango and component manager for monitoring.
  [Will Gauvin]
- AT3-243 refactor out common simulated monitoring task. [Will Gauvin]
- AT3-243 implement monitoring callback for RECV gRPC API. [Will Gauvin]
- AT3-243 remove relative weights from RECV monitored properties. [Will
  Gauvin]
- AT3-243 update poetry. [Will Gauvin]
- AT3-242 improve test coverage for SMRB component manager. [Will
  Gauvin]
- AT3-242 implement end scan for RECV. [Will Gauvin]
- AT3-242 refactor test scan request out as a test fixture. [Will
  Gauvin]
- AT3-242 implement deconfigure for RECV gRPC call. [Will Gauvin]
- AT3-242 add tests for RECV and SMRB component manager for configure
  scan. [Will Gauvin]
- AT3-242 implement configure scan for RECV. [Will Gauvin]
- AT3-242 add method to convert configure request to RECV parameters.
  [Will Gauvin]
- AT3-242 disable moniotring values for RECV. [Will Gauvin]
- AT3-242 add tests for gRPC get methods. [Will Gauvin]
- AT3-242 implement gRPC deconfigure for SMRB. [Will Gauvin]
- AT3-242 refactor out scan configure as fixture for tests. [Will
  Gauvin]
- AT3-240 implement gRPC configure for SMRB. [Will Gauvin]
- AT3-242 use component manager submit_task for configure/deconfigure.
  [Will Gauvin]
- AT3-242 split SMRB process API tests to simulator and gRPC. [Will
  Gauvin]
- AT3-240 add data_host and data_port for RECV. [Will Gauvin]
- AT3-240 add tests for calculating tsamp. [Will Gauvin]
- AT3-240 ensure RECV switches to gRPC API when simulation mode changes.
  [Will Gauvin]
- AT3-240 fix RECV device test to use assign_resources fixture. [Will
  Gauvin]
- AT3-240 add tests of RECV component manager for API calls. [Will
  Gauvin]
- AT3-240 add utility to calc RECV subband assign resources. [Will
  Gauvin]
- AT3-240 extract out generating of data and weights keys. [Will Gauvin]
- AT3-240 add tests for release resources. [Will Gauvin]
- AT3-240 implement assign_resources gRPC call for RECV. [Will Gauvin]
- AT3-240 update test assign_resources_request. [Will Gauvin]
- AT3-240 create base gRPC API for RECV. [Will Gauvin]
- AT3-240 refactor SMRB gRPC API out to a common class. [Will Gauvin]
- AT3-219 add tests over calculating SMRB monitoring data. [Will Gauvin]
- AT3-219 fix merge request comments. [Will Gauvin]
- AT3-234 fix calculation of total utilisation. [Will Gauvin]
- AT3-219 implement the restart command for SMRB. [Will Gauvin]
- AT3-219 implement the ObsReset command for SMRB. [Will Gauvin]
- AT3-219 implement abort in device/component manager. [Will Gauvin]
- AT3-219 add abort to gRPC API. [Will Gauvin]
- AT3-219 refactor out creating gRPC API for tests. [Will Gauvin]
- AT3-223 fix monitoring callback back for real mode. [Will Gauvin]
- AT3-219 fix issue with monitoring found during test refactoring. [Will
  Gauvin]
- AT3-219 refactor tests to use a common event assertions. [Will Gauvin]
- AT3-206 mark the BEAM device unit test as skipped. [Will Gauvin]
- AT3-206 attempt to avoid a TANGO testing race condition. [Will Gauvin]
- AT3-206 debugging failing test happening on GitLab. [Will Gauvin]
- AT3-206 debug MemoryError in tests. [Will Gauvin]
- AT3-206 add update the integration test to use events. [Will Gauvin]
- AT3-206 resolve issue with pytest-forked. [Will Gauvin]
- AT3-206 update BEAM tests to use events rather than timeouts. [Will
  Gauvin]
- AT3-206 update RECV tests to use events rather than timeouts. [Will
  Gauvin]
- AT3-206 update SMRB tests to use events rather than timeouts. [Will
  Gauvin]
- AT3-223 update header comment and license for util classes. [Will
  Gauvin]
- AT3-223 fix linting issue. [Will Gauvin]
- AT3-223 update generated documentation. [Will Gauvin]
- AT3-223 implement core logic for SMRB monitoring. [Will Gauvin]
- AT3-223 change SMRB data model classes to reflect subbands. [Will
  Gauvin]
- AT3-223 add monitor method to the gRPC LMC client. [Will Gauvin]
- AT3-223 add timeout iterator utility class. [Will Gauvin]
- AT3-223 add iPython for development purposes. [Will Gauvin]
- AT3-218 add sleeps in test for SMRB start communicating. [Will Gauvin]
- AT3-218 implement gRPC scan end scan commands for SMRB. [Will Gauvin]
- AT3-222 fix code review comments. [Will Gauvin]
- AT3-222 update pyproject.toml for path of generated code. [Will
  Gauvin]
- AT3-222 configure isort for protobuf generated code. [Will Gauvin]
- AT3-222 fix import sort order for protobuf/gRPC code. [Will Gauvin]
- AT3-222 update .make and poetry env. [Will Gauvin]
- AT3-222 implement assign/release resources using gRPC. [Will Gauvin]
- AT3-222 override script of oci-image-build to pass through protobuf
  image. [Will Gauvin]
- AT3-222 move oci build args before includes. [Will Gauvin]
- AT3-222 setup up CI to use env variable for common protobuf image.
  [Will Gauvin]
- AT3-226 setup test deployment with SMRB. [Will Gauvin]
- AT3-266 resolve issue with failing k8s-test. [Will Gauvin]
- AT3-226 have generated code put directly into src. [Will Gauvin]
- AT3-226 added linting override for ska_pst_lmc_proto. [Will Gauvin]
- AT3-226 implement connect in gRPC client for SMRB. [Will Gauvin]
- AT3-226 update python test to have correct Docker env. [Will Gauvin]
- AT3-226 update gitlab-ci.yaml to generate gRPC/Protobuf code. [Will
  Gauvin]
- AT3-226 use specific protobuf container to avoid cache issue. [Will
  Gauvin]
- AT3-226 debug the copy-protobuf step. [Will Gauvin]
- AT3-226 override python-lint to install deps via pip. [Will Gauvin]
- AT3-226 setup GitLab build to copy files from common. [Will Gauvin]
- AT3-226 add convinence make target for local oci scanning. [Will
  Gauvin]
- AT3-231 Updated job dependency  -  oci-image-build job needed by
  k8s-test to pull images from gitlab. [jesmigel]
- AT3-231 fixed smrb flag. [jesmigel]
- AT3-231 added smrb to test-parent chart  - Enabled smrb by default in
  test parent  - Added makefile flags to toggle smrb chart. [jesmigel]
- AT3-220 resolve security issue raised in OCI scan. [Will Gauvin]
- AT3-220 extend time for sleeping to wait for On command. [Will Gauvin]
- AT3-220 use gitlab runner for k8s-test. [Will Gauvin]
- AT3-220 set default simulation mode for Tango devices in helm. [Will
  Gauvin]
- AT3-220 update documentation. [Will Gauvin]
- AT3-220 update python dependencies. [Will Gauvin]
- AT3-220 add support of simulated and real mode in SMRB. [Will Gauvin]
- AT3-208 increase sleeps for integration test. [Will Gauvin]
- AT3-208 update project to new GitLab location. [Will Gauvin]


0.1.1 (2022-06-01)
------------------
- REL-110 release 0.1.1. [Will Gauvin]
- AT3-147 update CI/CD to use k8srunner-psi-low for stop-k8s-test. [Will
  Gauvin]


0.1.0 (2022-06-01)
------------------
- REL-110 initial release. [Will Gauvin]
- AT3-147 remove use-context in k8s-test task. [Will Gauvin]
- AT3-147 retry using k8srunner-psi-low. [Will Gauvin]
- AT3-147 revert to k8srunner. [Will Gauvin]
- AT3-147 add kubectl config to k8s-test. [Will Gauvin]
- AT3-147 increase verbosity of k8s_test_command. [Will Gauvin]
- AT3-147 add PROXY_VALUES which is used by k8s-test. [Will Gauvin]
- AT3-147 use k8srunner-psi-low. [Will Gauvin]
- AT3-147 enable CI running of k8s-test on GitLab. [Will Gauvin]
- AT3-147 add integration test for BEAM. [Will Gauvin]
- AT3-147 reenable most Python and docs tasks for branch builds. [Will
  Gauvin]
- AT3-147 enable Helm and k8s steps in CI/CD pipeline. [Will Gauvin]
- AT3-147 remove duplicated import of k8s.mk file. [Will Gauvin]
- AT3-146 update TANGO install instructions. [Will Gauvin]
- AT3-146 update documentation. [Will Gauvin]
- AT3-146 fix linting issue due Python version. [Will Gauvin]
- AT3-146 add k8s/helm configuration for BEAM/RECV/SMRB. [Will Gauvin]
- AT3-146 update PstBeam to use component manager. [Will Gauvin]
- AT3-146 update PstBeam TANGO device to be a SKASubarray device. [Will
  Gauvin]
- AT3-146 add a component manager for BEAM. [Will Gauvin]
- AT3-146 add handling of remote device tasks. [Will Gauvin]
- AT3-146 refactor out non-api based component manager. [Will Gauvin]
- AT3-146 create PstDeviceProxy. [Will Gauvin]
- AT3-193 attempt to remove false Pipeline Checks errors. [jesmigel]
- AT3-193 attempt to remove false Pipeline Checks errors. [jesmigel]
- AT3-193 added dependency between oci-image-build and oci-image-scan.
  [jesmigel]
- AT3-193 removed ci job. [jesmigel]
- AT3-193 removed ci template. [jesmigel]
- AT3-193 enforce nested manual trigger. [jesmigel]
- AT3-193 updated .make library. [jesmigel]
- AT3-193 enforce nested manual trigger. [jesmigel]
- AT3-193 nested manual trigger. [jesmigel]
- AT3-193 test manual trigger. [jesmigel]
- AT3-193 test manual trigger. [jesmigel]
- AT3-193 updated skip logic. [jesmigel]
- AT3-193 updated skip logic. [jesmigel]
- AT3-193 updated from manual to never. [jesmigel]
- AT3-193 enforce manual trigger through rules. [jesmigel]
- AT3-193 testing inherited k8s-test job. [jesmigel]
- AT3-193 updated tag from k8srunner-psi-low to k8srunner. [jesmigel]
- AT3-193 moved job to gitlab/ci/all.yml. [jesmigel]
- AT3-193 commented enforced k8s context. [jesmigel]
- AT3-193 updated conditions. [jesmigel]
- AT3-193 updated regular expression. [jesmigel]
- AT3-193 moved jobs to .gitlab/ci/all.yml. [jesmigel]
- AT3-193 updated tag. [jesmigel]
- AT3-193 added k8s test support. [jesmigel]
- AT3-193 initial branch based build logic. [jesmigel]
- AT3-189 update README.md. [Will Gauvin]
- AT3-189 update to get test server working for k8s. [Will Gauvin]
- AT3-189 add test device. [Will Gauvin]
- AT3-189 update pytango docker versions. [Will Gauvin]
- AT3-145 update poetry.lock. [Will Gauvin]
- AT3-145 update CI/CD make submodule. [Will Gauvin]
- AT3-145 fix comments caused by copying. [Will Gauvin]
- AT3-145 update documentation for SMRB device. [Will Gauvin]
- AT3-145 implement PstSmrb device. [Will Gauvin]
- AT3-145 add tests for SMRB Component Manager. [Will Gauvin]
- AT3-145 Update RECV Component Manager test for properties. [Will
  Gauvin]
- AT3-145 add SMRB component manager. [Will Gauvin]
- AT3-145 refactor out common component manager calls to base. [Will
  Gauvin]
- AT3-145 add SMRB Process API. [Will Gauvin]
- AT3-145 move background_task_processor fixture to conftest.py. [Will
  Gauvin]
- AT3-145 logger and component_state_callback to base API. [Will Gauvin]
- AT3-145 create background task decorator. [Will Gauvin]
- AT3-145 update file headers. [Will Gauvin]
- AT3-145 refactor out PstProcessApi from RECV. [Will Gauvin]
- AT3-145 add SMRB simulator. [Will Gauvin]
- AT3-145 add SMRB model class. [Will Gauvin]
- AT3-144 fix doc-build by ignoring readerwriterlock. [Will Gauvin]
- AT3-144 update README.md based off RECV work. [Will Gauvin]
- AT3-144 update sphinx documentation. [Will Gauvin]
- AT3-144 refactor out a RECV API. [Will Gauvin]
- AT3-144 use SKASubarray for RECV device. [Will Gauvin]
- AT3-144 build out RECV device. [Will Gauvin]
- AT3-144 move tests to tests/unit. [Will Gauvin]
- AT3-144 fix doc linting issue. [Will Gauvin]
- AT3-144 remove Hello. [Will Gauvin]
- AT3-144 update documentation. [Will Gauvin]
- AT3-144 update RECV component manager to use simulator. [Will Gauvin]
- AT3-144 add RECV simulator. [Will Gauvin]
- AT3-144 update editorconfig to use tabs for make files. [Will Gauvin]
- AT3-144 add a util class for background tasks. [Will Gauvin]
- AT3-144 base classes for RECV component. [Will Gauvin]
- AT3-140 rename master to management. [Will Gauvin]
- AT3-140 rename capacity to ring_buffer_size. [Will Gauvin]
- AT3-140 update the read the docs. [Will Gauvin]
- AT3-140 add always_executed_hook and delete_device. [Will Gauvin]
- AT3-140 Add PstSmrb stub. [Will Gauvin]
- AT3-140 Add PstReceive stub. [Will Gauvin]
- AT3-140 rename dsp.py to dsp_device.py for consistency. [Will Gauvin]
- AT3-140 update the __init__.py for all submodules. [Will Gauvin]
- AT3-140 Add PstDsp stub. [Will Gauvin]
- AT3-140 Add PstBeam stub. [Will Gauvin]
- AT3-140 Add PstMaster stub. [Will Gauvin]
- AT3-139 add PrivateRules.mak to .gitignore. [Will Gauvin]
- AT3-139 Port pst-lmc validation and util code. [Will Gauvin]
- AT3-139 update ska-telmodel to 1.3.2. [Will Gauvin]
- AT3-141 revert add CI post steps to get badges. [Will Gauvin]
- AT3-141 add CI post steps to get badges. [Will Gauvin]
- AT3-141 disable k8s and helm build steps. [Will Gauvin]
- AT3-141 add more GitLab templates. [Will Gauvin]
- AT3-141 use default python3 runner in Makefile. [Will Gauvin]
- AT3-141 update Dockerfile. [Will Gauvin]
- AT3-141 fix build for linting and docs. [Will Gauvin]
- AT3-141 add .dockerignore to not copy certain files to Docker. [Will
  Gauvin]
- AT3-141 Add GitLab CI/CD integration. [Will Gauvin]
- AT3-138 add Dockerfile to run Hello World. [Will Gauvin]
- AT3-138 run black over code. [Will Gauvin]
- AT3-138 add read the docs generation. [Will Gauvin]
- AT3-138 add simple hello world. [Will Gauvin]
- AT3-138 add .editorconfig. [Will Gauvin]
- AT3-138 update README.md for latest project details. [Will Gauvin]
- AT3-138 add CHANGELOG.rst to capture changes. [Will Gauvin]
- AT3-138 add .gitignore. [Will Gauvin]
- AT3-138 setup VS Code docker environment. [Will Gauvin]
- AT3-138 add initial python dependencies. [Will Gauvin]
- AT3-138 add pypoetry.toml. [Will Gauvin]
- AT3-138 add CODEOWNERS file. [Will Gauvin]
- AT3-138 add ska-cicd-makefile submodule. [Will Gauvin]
- AT3-138 add initial VS Code devcontainer. [Will Gauvin]
- Add LICENSE. [Ugur Yilmaz]
- Initial commit. [Ugur Yilmaz]
