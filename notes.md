# DEV notes

create something equivalent to `condor_config_val -dump`

- use `cconfig -c <config>` with plumbum
- support "--host" parameter as cconfig (-h)
- check what other parameters areallowed
- combine with xrd env
- can we use [cppyy](https://cppyy.readthedocs.io/en/latest/starting.html) to
  extract more info (e.g. default values?)
- output formats: plain (sorted), json

extended features: xrdconfig diff
