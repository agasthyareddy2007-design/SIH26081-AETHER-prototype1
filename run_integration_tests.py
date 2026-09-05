import os
import sys

# Hack for simple running of the pytest scripts
from test_location_time_parsing import *

if __name__ == "__main__":
    tests = [
        test_integration_pipeline_gachibowli,
        test_integration_pipeline_secunderabad,
        test_integration_pipeline_explicit_date,
        test_integration_pipeline_non_weather
    ]
    
    for t in tests:
        try:
            print(f"Running {t.__name__}...", end=" ")
            
            # Since patches are decorators we can just call the function!
            # Wait, patch creates mocks, pytest runs them injecting args. But if called manually we don't get the args injected automatically unless we use the wrapper correctly. Wait - patch as decorator injects automatically if called without arguments!
            t()
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
            
    print("All tests passed!")
