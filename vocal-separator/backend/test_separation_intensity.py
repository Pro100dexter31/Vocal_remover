#!/usr/bin/env python3
"""
Test script for separation_intensity parameter.
Tests the integration at multiple intensity levels: 0.0, 0.25, 0.5, 0.75, 1.0
"""

import json
import logging
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"
SAMPLE_AUDIO_PATH = Path("test_audio.mp3")  # Replace with actual test audio file


def test_separation_intensity():
    """Test separation_intensity parameter at different levels."""

    intensity_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    test_results = {}

    if not SAMPLE_AUDIO_PATH.exists():
        logger.error(f"Test audio file not found: {SAMPLE_AUDIO_PATH}")
        logger.info("Please provide a test audio file at: test_audio.mp3")
        return

    logger.info("Starting separation intensity tests...")
    logger.info(f"Test audio: {SAMPLE_AUDIO_PATH}")

    for intensity in intensity_levels:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing intensity level: {intensity} ({int(intensity*100)}%)")
        logger.info(f"{'='*60}")

        try:
            # Upload file with separation_intensity
            with open(SAMPLE_AUDIO_PATH, 'rb') as f:
                files = {'file': f}
                data = {'separation_intensity': intensity}

                logger.info(f"Uploading file with intensity={intensity}...")
                response = requests.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data,
                    timeout=30
                )

            if response.status_code != 202:
                logger.error(f"Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                continue

            upload_data = response.json()
            task_id = upload_data['task_id']
            logger.info(f"✓ Upload successful - Task ID: {task_id}")

            # Poll for completion
            import time
            max_wait = 300  # 5 minutes max
            poll_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                status_response = requests.get(f"{API_BASE_URL}/api/status/{task_id}")
                status_data = status_response.json()

                logger.info(f"  Status: {status_data['status']} ({status_data['progress']}%)")

                if status_data['status'] == 'SUCCESS':
                    logger.info("✓ Processing complete!")

                    # Store results
                    test_results[intensity] = {
                        'status': 'SUCCESS',
                        'task_id': task_id,
                        'vocals_url': status_data.get('vocals_url'),
                        'accompaniment_url': status_data.get('accompaniment_url'),
                    }

                    # Download samples
                    logger.info("Downloading audio samples...")

                    # Download vocals
                    vocals_url = f"{API_BASE_URL}{status_data.get('vocals_url')}"
                    vocals_response = requests.get(vocals_url)
                    if vocals_response.status_code == 200:
                        output_path = Path(f"test_results/vocals_{int(intensity*100)}.mp3")
                        output_path.parent.mkdir(exist_ok=True)
                        output_path.write_bytes(vocals_response.content)
                        logger.info(f"  ✓ Vocals saved: {output_path} ({len(vocals_response.content)} bytes)")

                    # Download accompaniment
                    accomp_url = f"{API_BASE_URL}{status_data.get('accompaniment_url')}"
                    accomp_response = requests.get(accomp_url)
                    if accomp_response.status_code == 200:
                        output_path = Path(f"test_results/accompaniment_{int(intensity*100)}.mp3")
                        output_path.parent.mkdir(exist_ok=True)
                        output_path.write_bytes(accomp_response.content)
                        logger.info(f"  ✓ Accompaniment saved: {output_path} ({len(accomp_response.content)} bytes)")

                    break

                elif status_data['status'] == 'FAILURE' or status_data['status'] == 'FAILED':
                    logger.error(f"✗ Processing failed: {status_data.get('error')}")
                    test_results[intensity] = {
                        'status': 'FAILURE',
                        'error': status_data.get('error'),
                    }
                    break

                time.sleep(poll_interval)
                elapsed += poll_interval

            if elapsed >= max_wait:
                logger.error(f"✗ Processing timeout after {max_wait} seconds")
                test_results[intensity] = {'status': 'TIMEOUT'}

        except Exception as e:
            logger.exception(f"✗ Test failed with exception: {e}")
            test_results[intensity] = {'status': 'EXCEPTION', 'error': str(e)}

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    for intensity, result in test_results.items():
        status = result['status']
        symbol = '✓' if status == 'SUCCESS' else '✗'
        logger.info(f"{symbol} Intensity {intensity} ({int(intensity*100)}%): {status}")

    # Save results
    results_file = Path("test_results/results.json")
    results_file.parent.mkdir(exist_ok=True)
    results_file.write_text(json.dumps(test_results, indent=2))
    logger.info(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    test_separation_intensity()
