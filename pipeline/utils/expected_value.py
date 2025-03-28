def expected_value(winPercenetage, odds):
    lossPercentage = 1 - winPercenetage
    winMoney = cashout(odds)
    return round((winPercenetage * winMoney) - (lossPercentage * 100), 2)

def cashout(odds):
    if odds > 0:
        return odds
    else:
        return (100 / (-1 * odds)) * 100