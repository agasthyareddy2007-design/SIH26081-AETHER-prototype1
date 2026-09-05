import time
import requests

def wait_for_deploy():
    print("Waiting for Cloud Run deployment to expose explainability field...")
    for i in range(30):
        try:
            res = requests.post(
                "https://sih26081-aether-1050720405878.asia-south1.run.app/api/forecast",
                json={"lat":17.4400,"lon":78.3400,"valid_time":"2026-09-08 12:00:00","lead_time_hours":72},
                timeout=10
            )
            data = res.json()
            if 'explainability' in data and data['explainability'] is not None:
                print("Deployment successful! Explainability field is now available.")
                print(f"Logits keys: {list(data['explainability'].get('gating_scores', {}).keys())}")
                return True
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
    print("Wait timed out.")
    return False

wait_for_deploy()
