
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("HIVEMQ_HOST")
PORT = int(os.getenv("HIVEMQ_PORT", "8883"))
USERNAME = os.getenv("HIVEMQ_USERNAME")
PASSWORD = os.getenv("HIVEMQ_PASSWORD")

TOPIC = "shellyemg3-d885ac0b67e8/#"

# Save data in the project root, regardless of the
# directory from which the script is launched.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = DATA_DIR / "shelly_mqtt_messages.jsonl"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logging.error("HiveMQ connection failed: %s", reason_code)
        return

    logging.info("Connected to HiveMQ Cloud successfully.")
    client.subscribe(TOPIC, qos=0)
    logging.info("Subscribed to: %s", TOPIC)
    logging.info("Saving incoming messages to: %s", OUTPUT_FILE)


def on_message(client, userdata, message):
    received_at = datetime.now(timezone.utc).isoformat()

    try:
        raw_payload = message.payload.decode("utf-8")
    except UnicodeDecodeError:
        raw_payload = message.payload.decode("utf-8", errors="replace")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        payload = None

    record = {
        "received_at_utc": received_at,
        "topic": message.topic,
        "qos": message.qos,
        "retain": message.retain,
        "payload": payload if payload is not None else raw_payload,
    }

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Append one complete JSON record per line.
        with OUTPUT_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            file.flush()

    except OSError:
        logging.exception("Could not save MQTT message")
        return

    logging.info("Saved message | topic=%s", message.topic)


def main():
    if not all((HOST, USERNAME, PASSWORD)):
        raise RuntimeError(
            "Missing HiveMQ credentials. Check HIVEMQ_HOST, "
            "HIVEMQ_USERNAME and HIVEMQ_PASSWORD in .env."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="wattwiser-home-consumer",
        protocol=mqtt.MQTTv311,
    )

    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()
    client.tls_insecure_set(False)

    client.on_connect = on_connect
    client.on_message = on_message

    logging.info("Connecting to HiveMQ Cloud at %s:%s", HOST, PORT)

    try:
        client.connect(HOST, PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info("Consumer stopped by user.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    main()
