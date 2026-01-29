*** Settings ***
Documentation     Coinbase BTC Prediction Bot - Automated Test Suite
...               Tests all components of the prediction market bot
Library           Process
Library           OperatingSystem
Library           String

*** Variables ***
${PYTHON}         python
${PROJECT_DIR}    c:\\CryptoAI
${TIMEOUT}        30s

*** Test Cases ***
Test 1: Verify Python Installation
    [Documentation]    Check if Python is installed and accessible
    [Tags]    setup
    ${result}=    Run Process    ${PYTHON}    --version
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Python 3
    Log    Python version: ${result.stdout}

Test 2: Verify Dependencies Installed
    [Documentation]    Check if all required packages are installed
    [Tags]    dependencies
    ${packages}=    Create List    pandas    numpy    requests    ta    plotly    dash
    FOR    ${package}    IN    @{packages}
        ${result}=    Run Process    ${PYTHON}    -c    import ${package}
        Should Be Equal As Integers    ${result.rc}    0
        Log    ✓ ${package} installed
    END

Test 3: Verify ML Libraries Available
    [Documentation]    Check if machine learning libraries are installed
    [Tags]    ml
    ${result}=    Run Process    ${PYTHON}    -c    import sklearn; import xgboost
    Log    ML Libraries Check: RC=${result.rc}
    Run Keyword If    ${result.rc} == 0    Log    ✓ ML libraries available
    Run Keyword If    ${result.rc} != 0    Log    ⚠ ML libraries missing - install with: pip install scikit-learn xgboost    WARN

Test 4: Test Market Data Fetcher
    [Documentation]    Test if market data fetcher can retrieve BTC price
    [Tags]    fetcher
    ${result}=    Run Process    ${PYTHON}    ${PROJECT_DIR}\\prediction_market_fetcher.py
    ...    timeout=${TIMEOUT}    cwd=${PROJECT_DIR}
    Log    ${result.stdout}
    Should Contain    ${result.stdout}    Mid Price
    Should Not Contain    ${result.stdout}    Error

Test 5: Test ML Prediction Engine
    [Documentation]    Test ML prediction engine initialization
    [Tags]    ml    engine
    ${result}=    Run Process    ${PYTHON}    ${PROJECT_DIR}\\ml_prediction_engine.py
    ...    timeout=${TIMEOUT}    cwd=${PROJECT_DIR}
    Log    ${result.stdout}
    Should Contain Any    ${result.stdout}    features    prediction    Warning

Test 6: Test Prediction Market Analyzer
    [Documentation]    Test prediction market analyzer
    [Tags]    analyzer
    ${result}=    Run Process    ${PYTHON}    ${PROJECT_DIR}\\prediction_market_analyzer.py
    ...    timeout=${TIMEOUT}    cwd=${PROJECT_DIR}
    Log    ${result.stdout}
    Should Contain Any    ${result.stdout}    Price    Signal    Confidence

Test 7: Test Trading Bot Initialization
    [Documentation]    Test if trading bot can initialize without errors
    [Tags]    bot
    ${code}=    Set Variable    from prediction_trading_bot import PredictionTradingBot; bot = PredictionTradingBot(auto_trade=False); print(bot.get_status())
    ${result}=    Run Process    ${PYTHON}    -c    ${code}
    ...    timeout=${TIMEOUT}    cwd=${PROJECT_DIR}
    Log    ${result.stdout}
    Should Be Equal As Integers    ${result.rc}    0

Test 8: Test Portfolio Integration
    [Documentation]    Test if bot integrates with existing portfolio
    [Tags]    portfolio
    ${code}=    Set Variable    from portfolio import Portfolio; p = Portfolio(); print(f"Value: ${p.get_total_value()}")
    ${result}=    Run Process    ${PYTHON}    -c    ${code}
    ...    timeout=${TIMEOUT}    cwd=${PROJECT_DIR}
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Value

Test 9: Test API Connectivity
    [Documentation]    Test if external APIs are accessible
    [Tags]    api
    ${code}=    Set Variable    import requests; r = requests.get('https://api.coingecko.com/api/v3/ping', timeout=10); print(r.status_code)
    ${result}=    Run Process    ${PYTHON}    -c    ${code}
    ...    timeout=${TIMEOUT}
    Should Contain    ${result.stdout}    200

Test 10: Run Complete Component Test Suite
    [Documentation]    Run the comprehensive test_prediction_bot.py script
    [Tags]    integration
    ${result}=    Run Process    ${PYTHON}    ${PROJECT_DIR}\\test_prediction_bot.py
    ...    timeout=60s    cwd=${PROJECT_DIR}
    Log    ${result.stdout}
    Log    ${result.stderr}
    Should Contain Any    ${result.stdout}    passed    PASS    ✓

Test 11: Verify Dashboard Can Initialize
    [Documentation]    Test if dashboard can be created (doesn't start server)
    [Tags]    dashboard
    ${code}=    Set Variable    from dashboard_predictions import app; print("Dashboard OK" if app else "Failed")
    ${result}=    Run Process    ${PYTHON}    -c    ${code}
    ...    timeout=${TIMEOUT}    cwd=${PROJECT_DIR}
    Should Contain    ${result.stdout}    Dashboard OK

Test 12: Test Prediction Summary
    [Documentation]    Get a quick prediction summary
    [Tags]    prediction
    ${code}=    Set Variable    from prediction_market_analyzer import PredictionMarketAnalyzer; a = PredictionMarketAnalyzer(auto_train=False); s = a.get_prediction_summary(); print(f"Signal: {s['signal']}, Score: {s['score']}")
    ${result}=    Run Process    ${PYTHON}    -c    ${code}
    ...    timeout=60s    cwd=${PROJECT_DIR}
    Log    ${result.stdout}
    Should Contain Any    ${result.stdout}    Signal    Score

*** Keywords ***
Should Contain Any
    [Arguments]    ${text}    @{expected}
    ${found}=    Set Variable    ${False}
    FOR    ${item}    IN    @{expected}
        ${contains}=    Run Keyword And Return Status    Should Contain    ${text}    ${item}
        ${found}=    Set Variable If    ${contains}    ${True}    ${found}
    END
    Should Be True    ${found}    Text does not contain any of: ${expected}
