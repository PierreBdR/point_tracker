#!/bin/bash
cur_dir=$(dirname $0)
pushd ${cur_dir}
# Not needed anymore:
# make -C src
if [[ "$1" == "-i" ]]; then
  ipython tracking.py "$@";
elif [[ "$1" == "interactive" ]]; then
  ipython -q4thread tracking.py "$@";
else
  case "$(uname)" in
    Darwin)
      PYTHON_EXE=python2.6
      ;;
    *)
      PYTHON_EXE=python
      ;;
  esac
  $PYTHON_EXE tracking.py "$@";
fi
popd
