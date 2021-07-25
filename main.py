import datetime as DT
import yfinance as yf
import yahoo_fin.stock_info as si
from ta import add_all_ta_features


def getRecommendations():
    stock = yf.Ticker(ticker) # Tell Yahoo finance what we want
    recommendations = stock.recommendations # Get the recommendations
    recommendations = recommendations.loc[startDate:endDate] # Trim the recommendations to fit within the timeframe
    return recommendations


def getStockData():
    import warnings
    warnings.filterwarnings("ignore")
    data = si.get_data(ticker)
    data = add_all_ta_features(
        data, open="open", high="high", low="low", close="close", volume="volume")
    return data


def smartPricing(date):
    travelBackwards = 1 # Don't iterate backwards
    if date == endDate:
        travelBackwards = -1 # Iterate backwards
    elif date is not startDate:
        date = date.date()

    buyPrice = data["close"].get(str(date))
    while buyPrice is None: # In case the analyst recommendation comes out on a none trading day...
        date = date + travelBackwards * DT.timedelta(1)
        buyPrice = data["open"].get(str(date)) # Assume we buy the next available open
    return buyPrice


# Grab all the recommendations for a given date, if theres more positive analyst sentiment then we buy, otherwise
# we sell (assuming it's not neutral in nature)
def determineBuySell(date, recommendations):
    date = date.date()
    allRecommendations = recommendations.get(str(date))
    if len(allRecommendations) is 0:
        allRecommendations = [allRecommendations]
    rating = 0
    for recommendation in allRecommendations:
        recommendation = str(recommendation)
        if recommendation == "Buy" or recommendation == "Strong Buy" or recommendation == "Outperform" or recommendation == "Overweight":
            rating += 1
        elif recommendation == "Sell" or recommendation == "Strong Sell" or recommendation == "Underperform" or recommendation == "Underweight":
            rating -= 1
    return rating


# We want to make sure we're not trading any recommendations that take place after market hours,
# otherwise that would lead to bias in our buying and selling.
def fixDates(dates):
    newDates = []
    for date in dates:
        marketClose = DT.datetime(year=date.year, month=date.month, day=date.day, hour=16, minute=0, second=0)
        if date > marketClose:  # Make sure we're not buying after market closes
            date = date + DT.timedelta(1)
            date = DT.datetime(year=date.year, month=date.month, day=date.day, hour=9, minute=0, second=0) # Market open
        newDates.append(date)
    return newDates


def tradeAllRecommendations(recommendations):
    capital = 1000
    stockCapital = 0
    numBought = 0
    bought = False
    numWins = 0
    numTrades = 0
    dates = recommendations.index
    dates = fixDates(dates)
    recommendations = recommendations['To Grade']
    for x in range(len(recommendations)): # Can't do a for each otherwise we lose the date aspect
        recommendation = recommendations[x]
        date = dates[x]
        rating = determineBuySell(date, recommendations)
        if not bought and rating > 0:
            # print("Buying")
            buyPrice = smartPricing(date)
            numBought = int(capital/buyPrice)
            stockCapital = buyPrice * numBought
            capital = capital - stockCapital
            bought = True
        elif bought and rating < 0:
            # print("Selling")
            sellPrice = smartPricing(date)
            newStockCapital = numBought * sellPrice
            if newStockCapital > stockCapital:
                numWins += 1
            numTrades += 1
            stockCapital = 0
            capital = capital + newStockCapital
            bought = False
    if bought:
        # print("Selling at the end")
        date = endDate
        sellPrice = smartPricing(date)
        newStockCapital = numBought * sellPrice
        if newStockCapital > stockCapital:
            numWins += 1
        numTrades += 1
        capital = capital + newStockCapital
    if numTrades is 0:
        winPercentage = 100
    else:
        winPercentage = (numWins/numTrades) * 100
    return capital, winPercentage, numTrades


def buyAndHold():
    capital = 1000
    # Buying at the start
    buyPrice = smartPricing(startDate)
    numBought = int(capital / buyPrice)
    stockCapital = buyPrice * numBought
    capital = capital - stockCapital
    # Selling today
    sellPrice = smartPricing(endDate)
    stockCapital = numBought * sellPrice
    capital = capital + stockCapital

    return capital


if __name__ == "__main__":
    ticker = str(input("Enter a a stock (AAPL, TSLA, etc.): "))
    numYears = int(input("Enter the number of years you would like to analyze for: "))
    endDate = DT.date.today()
    startDate = endDate - DT.timedelta(days=365*numYears)
    data = getStockData()
    recommendations = getRecommendations()
    newCapital, winPercentage, numTrades = tradeAllRecommendations(recommendations)
    buyAndHoldCapital = buyAndHold()
    print("If you were to listen to analyst recommendations, assuming you started with $1000 in capital, you would end up with $%s capital or "
          "a percent change of %s%%, with a win percentage of %s%% with %s trades.\nOn the other hand, if you were to buy "
          "and hold you would end up with $%s capital or a percent change of %s%%." % (newCapital, (newCapital-1000)/1000 * 100, winPercentage, numTrades, buyAndHoldCapital, (buyAndHoldCapital-1000)/1000 * 100))
