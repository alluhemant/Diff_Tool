from locust import HttpUser, task, between
import json
from pathlib import Path
import os


"""
ComparisonUser class simulates a user who sends POST requests to /api/v1/compare.

@task — tells Locust to run this method.

params — includes test URLs and parameters.

catch_response=True — allows checking if the response is valid (status 200).
"""


class ComparisonUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def run_comparison(self):
        url1 = "https://jsonplaceholder.typicode.com/posts/1"
        url2 = "https://jsonplaceholder.typicode.com/posts/2"
        params = {
            "url1": url1,
            "url2": url2,
            "method": "get",
            "url1_params": json.dumps({}),
            "url2_params": json.dumps({})
        }

        with self.client.post(
                "/api/v1/compare",
                params=params,
                catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code} - {response.text}")
