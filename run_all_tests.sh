#!/bin/bash
export PYTHONPATH="/home/agasthya/ai models"
export AETHER_LLM_PROVIDER="external"
export EXTERNAL_LLM_API_KEY="dummy"

pass_count=0
fail_count=0

for test_file in /home/agasthya/ai\ models/test_*.py; do
    echo "=================================="
    echo "Running $test_file"
    /home/agasthya/ai\ models/.venv/bin/python "$test_file"
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "PASS: $test_file"
        pass_count=$((pass_count+1))
    else
        echo "FAIL: $test_file"
        fail_count=$((fail_count+1))
    fi
done

echo "=================================="
echo "SUMMARY:"
echo "Tests Passed: $pass_count"
echo "Tests Failed: $fail_count"
