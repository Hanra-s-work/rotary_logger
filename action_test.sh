#!/bin/bash
# 
# +==== BEGIN rotary_logger =================+
# LOGO: 
# ..........####...####..........
# ......###.....#.#########......
# ....##........#.###########....
# ...#..........#.############...
# ...#..........#.#####.######...
# ..#.....##....#.###..#...####..
# .#.....#.##...#.##..##########.
# #.....##########....##...######
# #.....#...##..#.##..####.######
# .#...##....##.#.##..###..#####.
# ..#.##......#.#.####...######..
# ..#...........#.#############..
# ..#...........#.#############..
# ...##.........#.############...
# ......#.......#.#########......
# .......#......#.########.......
# .........#####...#####.........
# /STOP
# PROJECT: rotary_logger
# FILE: action_test.sh
# CREATION DATE: 01-11-2025
# LAST Modified: 6:1:36 01-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is a file in charge of running the tests of the module as if it were in a github action environement.
# // AR
# +==== END rotary_logger =================+
# 

# Exit on error
set -euo pipefail

GLOBAL_STATUS=0
# Default python versions to test when no args are provided
DEFAULT_PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13")

# If arguments are provided they are treated as the list of python
# versions to run. This allows calling the script with a single
# version to reduce output: ./action_test.sh 3.12
if [ "$#" -gt 0 ]; then
    PYTHON_VERSIONS=("$@")
else
    PYTHON_VERSIONS=("${DEFAULT_PYTHON_VERSIONS[@]}")
fi

function update_global_status {
    if [ $1 -ne 0 ]; then
        GLOBAL_STATUS=$1
    fi
}

# If DOCKER_EXTRA_ARGS is not provided, and the script is being run via
# sudo, prefer running the container as the original user to reproduce
# GitHub Actions behaviour. The environment variables SUDO_UID and
# SUDO_GID are set by sudo and point to the invoking user's uid/gid.
if [ -z "${DOCKER_EXTRA_ARGS:-}" ] && [ -n "${SUDO_UID:-}" ]; then
    DOCKER_EXTRA_ARGS="--user ${SUDO_UID}:${SUDO_GID}"
    echo "Using DOCKER_EXTRA_ARGS='${DOCKER_EXTRA_ARGS}' to run container as the original user"
fi

function run_tests {
    start_time=$(date +%s)

    for version in "${PYTHON_VERSIONS[@]}"; do
        echo "=== Running tests with Python version: $version ==="

        # Use the official python slim image for a much smaller and
        # predictable environment. We mount the repository into /work
        # and run tests there. To reproduce GitHub Actions (non-root)
        # behaviour you can pass --user "$(id -u):$(id -g)" to docker
        # in the DOCKER_EXTRA_ARGS env var before calling this script.

        DOCKER_IMAGE="python:${version}-slim"

        sudo docker run --rm \
            -t \
            --name "python${version}_test" \
            -v "$(pwd)":/work \
            -w /work \
            ${DOCKER_EXTRA_ARGS:-} \
            "$DOCKER_IMAGE" \
            /bin/bash -c "set -euo pipefail \
                && python -V \
                && python -m venv .venv \
                && . .venv/bin/activate \
                && pip install --upgrade pip \
                && pip install -r requirements.txt \
                && pip install pytest \
                && pytest -q \
            "

        STATUS=$?
        update_global_status $STATUS
        echo "Finished tests with Python version: $version, status: $STATUS"
    done

    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    echo "Total elapsed time: ${elapsed} seconds"
}

echo "Running tests for rotary_logger module"

run_tests

echo "----------------------"
echo "Tests finished."
echo "All tests completed. Final status: $GLOBAL_STATUS"
exit $GLOBAL_STATUS
