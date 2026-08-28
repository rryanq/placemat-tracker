# Placemat Tracker

## Getting Started
1. Install pipenv:
```bash
python3 -m pip install --user pipenv
```
2. Sync to the exact versions of the packages required for this project:
```bash
pipenv sync
```
3. Run the program:
```bash
pipenv run python3 process_shipment_v7.py
```

## Summary
placemat-tracker is a small project that I have created to help me with accounting for the sales of my Quin's Coins Coin Roll Hunting Placemats.
These placemats are sold via shopify which allows me to retrieve receipts from each and every purchase.
Once I retrieve these receipts, I can use this program to extract information from them to aide me with both packaging and accounting for each order.

This project has one file that does the majority of the work:
  - process_shipment_v<X>.py: a python script that extracts data from shopify orders and outputs statistics used in packaging and accounting
