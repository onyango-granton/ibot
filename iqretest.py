import time
from iqoptionapi.stable_api import IQ_Option
I_want_money = IQ_Option('grantononyango@gmail.com','password')
check = I_want_money.get_balances
if check:
    print(check)
else:
    print("####connect failed####")