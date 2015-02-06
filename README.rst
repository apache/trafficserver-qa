=============
What is TSQA?
=============

TSQA is an integration testing framework for Apache TrafficServer. While working
with ATS we've noticed that there little to no integration tests (functional tests)
of ATS, the tests are primarily unit or regression tests-- but none of which actually
start traffic-server. There was some work done on the initial tsqa (which is a
collection of bash scripts). The intent here is to create a more useful and
friendly testing harness for trafficserver and it's plugins. This comes with a
secondary goal of being generic enough to test other proxies-- this has come up
since after writing the majority of code is not ATS specific.



Environment Variables
=====================
TSQA_LAYOUT_PREFIX: Prefix to create layouts for each test execution (defaults to /tmp)
TSQA_LOG_LEVEL: Log level for TSQA (defaults to INFO)
TSQA_TMP_DIR: temp directory for building of source (environment factory)

