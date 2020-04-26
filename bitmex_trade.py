#!/usr/bin/env python
# coding: utf-8



from sympy import symbols, Eq, solve
from bitmex import bitmex
import sys
import json
import os
clear = lambda: os.system('clear') #on Linux System
from datetime import datetime, timedelta
import time

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")




def mex_rounding(value):
    rounded_value = round(value, 8)
    return rounded_value




def readable_format(value):
    value = "{:.8f}".format(value)
    return value




def usd_rounding(value):
    rounded_value = "${:,.2f}".format(value)
    return rounded_value




def mex_positions():
    postions = []
    resp = bitmex_client.Position.Position_get(filter = json.dumps({'isOpen': True})).result()[0]
    for x in range(len(resp)):
        time.sleep(1)
        current_bitmex = bitmex_client.Position.Position_get(filter=json.dumps({'symbol': resp[x]['symbol']})).result()[0][0]    
        open_orders = bitmex_client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true'})).result()[0]
        time.sleep(1)
        if len(bitmex_client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Limit', 'MarketIfTouched', 'StopLimit', 'LimitIfTouched']})).result()[0]) != 0:
            close_order = bitmex_client.Order.Order_getOrders(symbol = resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Limit', 'MarketIfTouched', 'StopLimit', 'LimitIfTouched']})).result()[0]
            close_price = "${:,.2f}".format(close_order[0]['price'])
        else:
            close_order = 'No Close Order Set'
            close_price = 'No Close Order Set'
        time.sleep(1)
        if len(bitmex_client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Stop', 'TrailingStop']})).result()[0]) > 0:
            stop_order = bitmex_client.Order.Order_getOrders(symbol=resp[x]['symbol'], filter = json.dumps({'open': 'true', 'ordType': ['Stop', 'TrailingStop']})).result()[0]
            stop_price = "${:,.2f}".format(stop_order[0]['stopPx'])
        else:
            stop_order = 'NO STOP SET!!!'
            stop_price = 'NO STOP SET!!!'
        time.sleep(1)
        mex = {}
        mex['Contract'] = resp[x]['symbol']
        if current_bitmex['currentQty'] < 0:
            mex['Side'] = 'Short'
        elif current_bitmex['currentQty'] > 0:
            mex['Side'] = 'Long'
        else:
            mex['Side'] = 'None'
        if mex['Side'] == 'Short':
            mex['Size'] = current_bitmex['currentQty']*-1
        else:
            mex['Size'] = current_bitmex['currentQty']
        mex['Entry'] = current_bitmex['avgEntryPrice']
        mex['Target'] = close_price
        mex['Stop'] = stop_price
        mex['OpenValue'] = mex_rounding(mex['Size']*((1/mex['Entry'])-(1/mex['Entry'])*0.00075))
        mex['MarketPrice'] = current_bitmex['markPrice']
        mex['MarketValue'] = mex_rounding(mex['Size']*((1/mex['MarketPrice'])-(1/mex['MarketPrice'])*0.00075))
        mex['Entry'] = usd_rounding(current_bitmex['avgEntryPrice'])
        mex['MarketPrice'] = usd_rounding(current_bitmex['markPrice'])
        if mex['Side'] == 'Long':
            mex['UnrealisedPnL'] = readable_format(mex['OpenValue'] - mex['MarketValue'])
        else:
            mex['UnrealisedPnL'] = readable_format(mex['MarketValue'] - mex['OpenValue'])
        postions.append(mex)
    return postions




def position_size(entry, stop, balance, risk):
    x = symbols('x')
    if target > entry:
        target_value = (1/target)+((1/target)*takerFee)
        stop_value = (1/stop)+((1/stop)*takerFee)
        if order_type == 'Limit':
            entry_value = (1/entry)-((1/entry)*makerFee)
            eq1 = Eq((x*(entry_value - stop_value)) + (balance*risk)) 
        else:
            entry_value = (1/entry)-((1/entry)*takerFee)
            eq1 = Eq((x*(entry_value - stop_value)) + (balance*risk))
    elif target < entry:
        target_value = (1/target)-((1/target)*takerFee)
        stop_value = (1/stop)-((1/stop)*takerFee)
        if order_type == 'Limit':
            entry_value = (1/entry)+((1/entry)*makerFee)
            eq1 = Eq((x*(stop_value - entry_value)) - (balance*risk))
        else:
            entry_value = (1/entry)+((1/entry)*takerFee)
            eq1 = Eq((x*(stop_value - entry_value)) - (balance*risk))
    size = solve(eq1)
    size = [ '%.0f' % elem for elem in size ]
    size = size[0]
    return size, entry_value, stop_value, target_value




def risk_amount_XBT(entry_value, stop_value, size):
    risk_amount = (size*(entry_value - stop_value))
    risk_amount = float(round(risk_amount, 8))
    return risk_amount




def reward_amount_XBT(entry_value, target_value, size):
    reward_amount = (size*(target_value - entry_value))
    reward_amount = float(round(reward_amount, 8))
    return reward_amount




def r(reward_amount, risk_amount):
    r_r = reward_amount/risk_amount
    return r_r




def initiate_trade(contract, size, entry, target, stop):
    if order_type == order_types[0]:
        bitmex_client.Order.Order_cancelAll(symbol=contract).result()
        bitmex_client.Order.Order_new(symbol=contract, orderQty=size, ordType='Market').result()
        bitmex_client.Order.Order_new(symbol=contract, price=target, execInst='ReduceOnly', orderQty=(size*-1), ordType='Limit').result()
        bitmex_client.Order.Order_new(symbol=contract, stopPx=stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='Stop').result()

    else:
        bitmex_client.Order.Order_cancelAll(symbol=contract).result()
        bitmex_client.Order.Order_new(symbol=contract, orderQty=size, price=entry).result()
        if target < entry:
            stop_limit_trigger = float(float(entry)+0.5)
        else:
            stop_limit_trigger = float(float(entry)-0.5)
        bitmex_client.Order.Order_new(symbol=contract, stopPx=stop_limit_trigger, price=target, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='StopLimit').result()
        bitmex_client.Order.Order_new(symbol=contract, stopPx=stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(size*-1), ordType='Stop').result()




def close_position(contract_to_view):
    resp = bitmex_client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]
    if resp['currentQty'] > 0:
        bitmex_client.Order.Order_new(symbol=contract_to_view, execInst='Close', side='Sell').result()
    else:
        bitmex_client.Order.Order_new(symbol=contract_to_view, execInst='Close', side='Buy').result()
    bitmex_client.Order.Order_cancelAll(symbol=contract_to_view).result()
    return print(contract_to_view+' Position Closed')




def amend_orders(contract_to_view):
    if len(bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Stop'})).result()[0]) > 0:
        stop = bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Stop'})).result()[0][0]
    else:
        stop = []
    if len(bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'Close'})).result()[0]) > 0:
        close = bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'Close'})).result()[0][0]
    elif len(bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ParticipateDoNotInitiate,ReduceOnly'})).result()[0]) > 0:
        close = bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ParticipateDoNotInitiate,ReduceOnly'})).result()[0][0]
    elif len(bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ReduceOnly'})).result()[0]) > 0:
        close = bitmex_client.Order.Order_getOrders(symbol=contract_to_view, filter = json.dumps({'open': 'true', 'ordType': 'Limit', 'execInst': 'ReduceOnly'})).result()[0][0]
    else:
        close = []
    qty = bitmex_client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]['currentQty']
    orderQty = qty*-1
    if new_stop != 0:
        if len(stop) > 0:
            bitmex_client.Order.Order_amend(orderID=stop['orderID'], stopPx=new_stop).result()
            print('Stop for '+contract_to_view+' Amended to '+usd_rounding(new_stop))
        elif len(stop) == 0:
            bitmex_client.Order.Order_new(symbol=contract_to_view, stopPx=new_stop, execInst=str('LastPrice, ReduceOnly'), orderQty=orderQty, ordType='Stop').result()
            print('Stop for '+contract_to_view+' Set to '+usd_rounding(new_stop))
    else:
        print('Stop Unchanged')
    if new_target != 0 :
        if len(close) > 0:
            bitmex_client.Order.Order_amend(orderID=close['orderID'], price=new_target).result()
            print('Target for '+contract_to_view+' Amended to '+usd_rounding(new_target))
        elif len(close) == 0:
            bitmex_client.Order.Order_new(symbol=contract_to_view, price=new_target, execInst='ReduceOnly', orderQty=orderQty, ordType='Limit').result()
            print('Target for '+contract_to_view+' Set to '+usd_rounding(new_target))
    else:
        print('Target Unchanged')
    if new_stop != 0 or new_target != 0:
        print('\n'+'Updated '+contract_to_view+' Position')
        time.sleep(1)
        for x in range(len(mex_positions())):
            if mex_positions()[x]['Contract'] == contract_to_view:
                for k, v in mex_positions()[x].items():
                    print(k, ':', v)
    else:
        print('Returning to Start')




def take_profit(contract_to_view):
    while True:
        take_profit = float(input('Percent of '+contract_to_view+' position to close'+'\n'+'> '))
        if take_profit == 0:
            break
        else:
            resp = bitmex_client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]
            take_profit_size = round(((resp['currentQty']*(int(take_profit)/100))*-1), 0)
            bitmex_client.Order.Order_cancelAll(symbol=contract_to_view).result()
            bitmex_client.Order.Order_new(symbol=contract_to_view, orderQty=take_profit_size, ordType='Market').result()
            new_size = bitmex_client.Position.Position_get(filter = json.dumps({'isOpen': True, 'symbol': contract_to_view})).result()[0][0]['currentQty']
            while True:
                new_stop = input('Enter New Stop Price. Enter 0 to skip'+'\n'+'> ')

                if '.' not in new_stop and new_stop[-1] not in str({valid_ticks}) or '.' in new_stop and new_stop[-1] not in str({0, 5}):
                    print('Invalid Tick Size')
                    continue
                else:
                    new_stop = float(new_stop)
                    break
            while True:
                new_target = input('Enter New Target Price. Enter 0 to skip'+'\n'+'> ')

                if '.' not in new_target and new_target[-1] not in str({valid_ticks}) or '.' in new_target and new_target[-1] not in str({0, 5}):
                    print('Invalid Tick Size')
                    continue
                else:
                    new_target = float(new_target)
                    break
            bitmex_client.Order.Order_new(symbol=contract_to_view, price=new_target, execInst='ReduceOnly', orderQty=(new_size*-1), ordType='Limit').result()
            print('Target for '+contract_to_view+' Set to '+usd_rounding(new_target))
            bitmex_client.Order.Order_new(symbol=contract_to_view, stopPx=new_stop, execInst=str('LastPrice, ReduceOnly'), orderQty=(new_size*-1), ordType='Stop').result()
            print('Stop for '+contract_to_view+' Set to '+usd_rounding(new_stop))
            time.sleep(1)
            print('\n'+'Updated '+contract_to_view+' Position')
            for x in range(len(mex_positions())):
                if mex_positions()[x]['Contract'] == contract_to_view:
                    for k, v in mex_positions()[x].items():
                        print(k, ':', v)
            break




print('Welcome to MEXecutioner'+'\n')
while True:
    valid_ticks = tuple(list(range(10)))
    bitmex_client = bitmex(test=False, api_key='XXX', api_secret='YYY') #Input your API Credentials
    xbt_contracts = []
    for x in range(len(bitmex_client.Instrument.Instrument_getActive().result()[0])):
        if bitmex_client.Instrument.Instrument_getActive().result()[0][x]['symbol'][:3] == 'XBT':
            xbt_contracts.append(bitmex_client.Instrument.Instrument_getActive().result()[0][x]['symbol'])
    step1_options = ['View/Manage Open Positions', 'Plan New Trade']
    while True:
        try:
            time.sleep(1)
            bitmex_client = bitmex(test=False, api_key='umogf4zoIFqtLssQvl-pvEe2', api_secret='M8QutdE3f89lybuZc21Onsilpob1vcBtoyJlnfqQvztdmEnw')
            for (x, y) in enumerate(step1_options):
                print(str(x)+': '+y)
            step1 = step1_options[int(input('Choose Option'+'\n'+'> '))]
        except (IndexError):
            print('Selection Invalid')
            time.sleep(1)
            continue
        else:
            break
    if step1 == 'View/Manage Open Positions':
        print('\n'+'Your Current Open Positions'+'\n')
        active_contracts = []
        for x in range(len(mex_positions())):
            for k, v in mex_positions()[x].items():
                print(k, ':', v)
            print('\n')
            active_contracts.append(mex_positions()[x]['Contract'])
        active_contracts.append('Return To Start')
        step2_options = ['Close Position', 'Amend Orders', 'Take Profit', 'Return to Start']
        while True:
            try:
                for (x, y) in enumerate(step2_options):
                    print(str(x)+': '+y)
                step2 = step2_options[int(input('Choose Option'+'\n'+'> '))]
            except (IndexError):
                print('Selection Invalid')
                time.sleep(1)
                continue
            else:
                if step2 != 'Return to Start':
                    while True:
                        try:
                            print('Choose a Position to Manage')
                            my_contracts = []
                            for l in range(len(mex_positions())):
                                temp_contracts = [x for x in active_contracts if x in mex_positions()[l]['Contract']]
                                my_contracts.append(temp_contracts[0])
                            my_contracts.append('Return to Start')
                            for (x, y) in enumerate(my_contracts):
                                print(str(x)+': '+y)
                            contract_to_view = my_contracts[int(input('> '))]
                        except IndexError:
                            print('Selection Invalid')
                            time.sleep(1)
                            continue
                        else:
                            if contract_to_view == 'Return to Start':
                                break
                            if step2 == 'Close Position':
                                close_position(contract_to_view)
                                break
                            elif step2 == 'Amend Orders':
                                while True:
                                        new_stop = input('Enter New Stop Price. Enter 0 to skip'+'\n'+'> ')
                                        
                                        if '.' not in new_stop and new_stop[-1] not in str({valid_ticks}) or '.' in new_stop and new_stop[-1] not in str({0, 5}):
                                            print('Invalid Tick Size')
                                            time.sleep(1)
                                            continue
                                        else:
                                            new_stop = float(new_stop)
                                            break
                                while True:
                                        new_target = input('Enter New Target Price. Enter 0 to skip'+'\n'+'> ')
                                            
                                        if '.' not in new_target and new_target[-1] not in str({valid_ticks}) or '.' in new_target and new_target[-1] not in str({0, 5}):
                                            print('Invalid Tick Size')
                                            time.sleep(1)
                                            continue
                                        else:
                                            new_target = float(new_target)
                                            break
                                amend_orders(contract_to_view)
                                break
                            elif step2 == 'Take Profit':
                                take_profit(contract_to_view)
                                break
                            break
                        break
                else:
                    break
                break
    
    elif step1 == 'Plan New Trade':
        while True:
            try:
                print('Available XBT Contracts'+'\n')
                for (x, y) in enumerate(xbt_contracts):
                    print(str(x)+': '+y)
                contract = xbt_contracts[int(input('Choose Contract'+'\n'+'> '))]
                order_types = ['Market', 'Limit']
                for (x, y) in enumerate(order_types):
                    print(str(x)+': '+y)
                order_type = order_types[int(input('Choose Order Type for Entry'+'\n'+'> '))]
            except (IndexError, ValueError):
                print('Entry Order Type selection must be a number 0-1. Try Again')
                continue
            else:
                break
        while True:
            stop = str(input('Stop Market Price'+'\n'+'> '))
            if '.' not in stop and stop[-1] not in str({valid_ticks}) or '.' in stop and stop[-1] not in str({0, 5}):
                print('Invalid Tick Size')
                continue
            else:
                stop = float(stop)
                break
        while True:
            target = str(input('Target Price'+'\n'+'> '))
            if '.' not in target and target[-1] not in str({valid_ticks}) or '.' in target and target[-1] not in str({0, 5}):
                print('Invalid Tick Size')
                continue
            else:
                target = float(target)
                break
        while True:
                contract_data = bitmex_client.Instrument.Instrument_getActive().result()[0] 
                contract_data = next(item for item in contract_data if item["symbol"] == contract)
                bidPrice = float(contract_data['bidPrice'])
                askPrice = float(contract_data['askPrice'])
                makerFee = float(contract_data['makerFee'])
                takerFee = float(contract_data['takerFee'])
                if order_type == 'Limit':
                    entry = str(input('Limit Entry Price'+'\n'+'> '))
                    if '.' not in entry and entry[-1] not in str({valid_ticks}) or '.' in entry and entry[-1] not in str({0, 5}):
                        print('Invalid Tick Size')
                        continue
                    else:
                        entry = float(entry)
                        break
                else:
                    if stop > target:
                        entry = bidPrice
                        break
                    else:
                        entry = askPrice
                        break
        while True:
            try:
                risk = float(input('BTC Risk Percentage. Or 0 for 1x Short'+'\n'+'> '))/100
                if risk == 0:
                    risk = (stop - entry) / entry
                else:
                    None
            except ValueError:
                print('Risk must be expressed as integer or float. I.e. 3% is 3. 0.5% is 0.5. Or choose 0 for 1x Short')
                continue
            else:
                break
        balance = bitmex_client.User.User_getWalletHistory().result()[0][0]['walletBalance']/100000000
        position_size_1 = position_size(entry, stop, balance, risk)
        size = int(position_size_1[0])
        entry_value = float(position_size_1[1])
        stop_value = float(position_size_1[2])
        target_value = float(position_size_1[3])

        risk_amount = risk_amount_XBT(entry_value, stop_value, size)*-1

        reward_amount = reward_amount_XBT(entry_value, target_value, size)*-1

        r_r = r(reward_amount, risk_amount)
        r_r = format(r_r, '.2f')


        loss_final_balance = balance - risk_amount
        loss_final_balance = round(loss_final_balance, 8)
        win_final_balance = balance + reward_amount
        win_final_balance = round(win_final_balance, 8)
        starting_usd = balance*entry
        starting_usd = round(starting_usd, 2)
        winning_usd = win_final_balance*target
        winning_usd = round(winning_usd, 2)
        losing_usd = loss_final_balance*stop
        losing_usd = round(losing_usd, 2)
        risk_amount = format(risk_amount, '.8f')
        reward_amount = format(reward_amount, '.8f')

        if target < entry:
            direction = 'Short'
        else:
            direction = 'Long'

        risk_percentage = str(round(risk*100, 1))+'%'

        trade_details = f"""
Contract: {contract}
Direction: {direction}
BTC Percent Risk: {risk_percentage}
Size: {size}
Entry: {entry}
Stop: {stop}
Target: {target}
Risk: {risk_amount} BTC
Reward: {reward_amount} BTC
R: {r_r}
Starting Balance: {balance} / ${starting_usd}
Winning Balance: {win_final_balance} / ${winning_usd}
Losing Balance: {loss_final_balance} / ${losing_usd}
"""
        print(trade_details)

        while True:
            try:
                trade_execution = int(input('Do you wish to take this trade?'+'\n'+'All existing orders for '+str(contract)+' will be cancelled'+'\n'+'0:Yes, 1:No' + '\n'))
                if trade_execution == 0:
                    if len(bitmex_client.Position.Position_get(filter = json.dumps({'symbol': str(contract)})).result()[0]) != 0:
                        if bitmex_client.Position.Position_get(filter = json.dumps({'symbol': str(contract)})).result()[0][0]['currentQty'] < 0:
                            bitmex_client.Order.Order_new(symbol=contract, execInst='Close', side='Buy').result()
                        else:
                            bitmex_client.Order.Order_new(symbol=contract, execInst='Close', side='Sell').result()
                        initiate_trade(contract, size, entry, target, stop)
                    else:
                        initiate_trade(contract, size, entry, target, stop)
                    print('TRADE EXECUTED')
                else:
                    print('TRADE NOT EXECUTED')
            except ValueError:
                print('Selection must be a number 0-1. Try Again')
                continue
            else:
                break






