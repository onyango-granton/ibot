from iqoptionapi.stable_api import IQ_Option
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

api = IQ_Option("grantononyango@gmail.com", "0724600680@Gt")
status, reason = api.connect()
print(f"Connection status: {status}")
print(f"Reason: {reason}")