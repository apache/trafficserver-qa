# TODO: rename from tsqa?
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


=================
Design Principles
=================
The goal of this design is to create a flexible framework to write tests in. Additionaly
we don't want to duplicate things that already exist. There are quite a few frameworks
out there that do more for you, but they all come with some restrictions. The idea
here is to enforce (in the framework) very few restrictions. Instead these restrictions
should be created as style/testing requirements of the project the tests are for.
This is done by effectively just creating a variety of helper classes that TestCases
can sub-class to get some common functionality for free.


============
Architecture
============
Due to the flexible design principles at play there is very little in terms of
architecture, but we'll go over the design of a few of the basic helper concepts.


Environment
============
One of the common use-cases of a test framework is to build and run the application.
The Environment is a directory (effectively a root dir) with the source code
installed in it. In addition to the code this root is also where configs live.
This means that the Environment object is responsible for maintining any daemons
or configs that the application needs while testing.

To reduce the amount of work to build environments there is an EnvironmentFactory.
This Factory class will create all unique builds of an application that it is asked
for. It will then return a copy of the requested environment to the caller. This
means that if N tests require the same base environment we only have to compile
once instead of N times.


Endpoint
========
Another common requirement for integration testing a proxy is an origin. Not only
do we need an origin, it is common to test the request/response on the origin as well
as the client (since the proxy will modify the request/response). To aid in these
sorts of tests we provide a DynamicHTTPEndpoint class which will create a Flask
server in a separate thread with APIs to register endpoints and track requests.


test_cases
==========
These are intended to be test cases that you would subclass to create your own test.
