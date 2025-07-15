'''Script to process shopify shipments'''

import csv
from os import listdir, path
import click
from itertools import groupby
from copy import deepcopy
from difflib import SequenceMatcher
from decimal import Decimal, ROUND_HALF_UP


class ShopifyCSVRow:
    '''Data contained within a row from a Shopify .csv export.'''
    def __init__(self, attribute_list, values):
        for attribute, value in zip(attribute_list, values):
            attribute = attribute.replace(' ', '_')
            setattr(self, attribute, value)


class ShopifyOrder():
    '''A Shopify order.'''
    order_code = None
    num_penny_placemats = 0
    num_nickel_placemats = 0
    num_silver_stacking_placemats = 0
    num_dollar_coin_placemats = 0
    num_hats = 0
    customer_name = None
    email_address = None
    mailing_address = None
    country = None
    retail_price = 0
    is_shop_order = False


class Package():
    '''A single package.'''
    order_code = None
    num_penny_placemats = 0
    num_nickel_placemats = 0
    num_silver_stacking_placemats = 0
    num_dollar_coin_placemats = 0
    num_hats = 0
    num_total_placemats = 0
    customer_name = None
    email_address = None
    mailing_address = None
    country = None
    shipping_cost = 0
    shipping_class = None
    is_shop_order = False


# the cost to ship a single hat varies, but is typically around $4
# NOTE: not accounting for Canadian shipping rates!
SINGLE_HAT_SHIPPING_COST_USA = 4.00
# NOTE: I do not know if the below price is actually accurate. I will need to ship one of these
# from the post office before I know for sure. This is pretty pricey!
SINGLE_HAT_SHIPPING_COST_CANADA = 14.85
NUM_PLACEMATS_TO_SHIPPING_COST = {
    'US': {
        '1': 2.44,
        '2': 3.28,
        '3': 3.84,
        '4': 4.74,
        # packages of 5 or 6 placemats must be sent via priority which doesn't
        # have a set price, but can cost up to $10
        '5': 10.00,
        '6': 10.00,
        '7': 10.00,
        '8': 10.00,
        '9': 10.00,
    },
    # FIXME: not sure if it shows up as "Canada" in csv, or something else. Will need
    # to fill this in once someone from Canada places an order
    'CA': {
        '1': 4.12,
        '2': 5.02,
        '3': 6.79,
        '4': 6.79,
        '5': 8.27,
        # 6 or more placemats to Canada cannot be done
    }
}


def get_address_similarity_ratio(a1, a2):
    return SequenceMatcher(None, a1, a2).ratio()


def update_order_product_quantities(order, sku, item_quantity):
    if sku == 'P1':
        order.num_penny_placemats += item_quantity
    elif sku == 'N1':
        order.num_nickel_placemats += item_quantity
    elif sku == 'S1':
        order.num_silver_stacking_placemats += item_quantity
    elif sku == 'D1':
        order.num_dollar_coin_placemats += item_quantity
    elif sku == 'M1':
        order.num_penny_placemats += item_quantity
        order.num_nickel_placemats += item_quantity
        order.num_silver_stacking_placemats += item_quantity
        order.num_dollar_coin_placemats += item_quantity
    elif sku == 'H1':
        order.num_hats += item_quantity
    else:
        raise Exception(f'Unknown sku: {sku}')


@click.command()
def main():

    shopify_orders = []
    packages = []
    total_revenue = 0

    SHOPIFY_ORDERS_CSV_DIR = "current_shopify_orders_csv"
    current_shopify_orders_files = listdir("./" + SHOPIFY_ORDERS_CSV_DIR)
    csv_files = [f for f in current_shopify_orders_files if f.endswith('.csv')]
    if len(csv_files) != 1:
        raise Exception(f"Only one .csv file should exist under '{SHOPIFY_ORDERS_CSV_DIR}'")
    csv_file = path.dirname(path.realpath(__file__)) + '/' + SHOPIFY_ORDERS_CSV_DIR + '/' + csv_files[0]

    with open(csv_file, newline='') as f:
        reader = csv.reader(f, delimiter=',')
        attribute_names = next(reader)
        csv_rows = [ShopifyCSVRow(attribute_names, r) for r in reader]
    
    previous_order_name = None
    for row in csv_rows:
        current_order_name = row.Name
        if current_order_name == previous_order_name:
            # update the previous order
            previous_order = shopify_orders[-1]
            sku = row.Lineitem_sku
            item_quantity = int(row.Lineitem_quantity)
            previous_order.order_code = previous_order.order_code + sku
            update_order_product_quantities(previous_order, sku, item_quantity)
            shopify_orders[-1] = previous_order
        else:
            # create a new order
            order = ShopifyOrder()
            sku = row.Lineitem_sku
            item_quantity = int(row.Lineitem_quantity)
            order.is_shop_order = 'Shop Cash' in row.Payment_Method

            order.order_code = sku
            order.customer_name = row.Shipping_Name
            order.email_address = row.Email
            # shipping zip codes begin with single quotes for some unknown reason, so they
            # have to be removed
            shipping_zip = row.Shipping_Zip.replace("'", "")
            address_parts = [
                row.Shipping_Address1,
                row.Shipping_Address2,
                f"{row.Shipping_City}, {row.Shipping_Province} {shipping_zip}"
            ]
            order.mailing_address = '\n'.join([p for p in address_parts if p])
            order.country = row.Shipping_Country
            order.retail_price = Decimal(row.Total)

            total_revenue += order.retail_price

            update_order_product_quantities(order, sku, item_quantity)
            shopify_orders.append(order)
        previous_order_name = current_order_name

     # DEBUG
    #for shopify_order in shopify_orders:
    #    print(shopify_order.__dict__)
    

    # NOTE: consider grouping by name instead because grouping by address is 
    # looking like it will be too complicated
    # group shopify orders by address
    grouped_shopify_orders = groupby(
        sorted(shopify_orders, key = lambda p: p.mailing_address),
        key = lambda p: p.mailing_address,
    )

    for mailing_address, orders in grouped_shopify_orders:
        orders = list(orders)
        
        # DEBUG
        #print(mailing_address)
        #for order in orders:
        #    print(order.__dict__)

        package = Package()
        package.mailing_address = mailing_address
        for o in orders:
            package.country = o.country
            package.customer_name = o.customer_name
            package.email_address = o.email_address
            package.is_shop_order = o.is_shop_order
            package.num_penny_placemats += o.num_penny_placemats
            package.num_nickel_placemats += o.num_nickel_placemats
            package.num_silver_stacking_placemats += o.num_silver_stacking_placemats
            package.num_dollar_coin_placemats += o.num_dollar_coin_placemats
            package.num_hats += o.num_hats
        num_total_placemats = package.num_penny_placemats + package.num_nickel_placemats + package.num_silver_stacking_placemats + package.num_dollar_coin_placemats
        package.num_total_placemats = num_total_placemats
        # hats get shipped in packages that are separate from placemats
        if package.num_hats > 0:
            # each hat needs its own package because the boxes are too small
            # to fit more than one in a box
            hat_package = deepcopy(package)
            hat_package.num_penny_placemats = 0
            hat_package.num_nickel_placemats = 0
            hat_package.num_silver_stacking_placemats = 0
            hat_package.num_dollar_coin_placemats = 0
            hat_package.num_total_placemats = 0
            hat_package.order_code = 'H1'
            if hat_package.country == 'USA' or hat_package.country == 'US':
                hat_package.shipping_cost = SINGLE_HAT_SHIPPING_COST_USA
            elif hat_package.country == 'Canada':
                hat_package.shipping_cost = SINGLE_HAT_SHIPPING_COST_CANADA
            else:
                raise Exception('Unknown Country: %s' % hat_package.country)
            num_hats = hat_package.num_hats
            hat_package.num_hats = 1
            # NOTE: untested so far since no one has bought two hats at once
            for i in range(num_hats):
                packages.append(hat_package)
        if package.num_total_placemats > 0:
            placemat_package = deepcopy(package)
            placemat_package.num_hats = 0
            if placemat_package.country == 'USA' and placemat_package.num_total_placemats > 9:
                # NOTE: what to do in this scenario? Should probably divide placemats
                # into separate packages in this case
                raise Exception('unable to ship more than 9 placemats in a single package within USA')
            if placemat_package.country == 'Canada' and placemat_package.num_total_placemats > 5:
                # NOTE: should handle this situation better by splitting the shipment up
                raise Exception('unable to ship more than 5 placemats in a single package to Canada')
            placemat_package.shipping_cost = NUM_PLACEMATS_TO_SHIPPING_COST.get(placemat_package.country, {}).get(str(placemat_package.num_total_placemats))
            if placemat_package.shipping_cost is None:
                raise Exception('Unable to retrieve shipping cost for %s placemats to %s' % (
                    placemat_package.num_total_placemats, placemat_package.country
                ))
            placemat_package.order_code = '%s%s%s%s' % (
                ('P' + str(placemat_package.num_penny_placemats)) if placemat_package.num_penny_placemats else '',
                ('N' + str(placemat_package.num_nickel_placemats)) if placemat_package.num_nickel_placemats else '',
                ('S' + str(placemat_package.num_silver_stacking_placemats)) if placemat_package.num_silver_stacking_placemats else '',
                ('D' + str(placemat_package.num_dollar_coin_placemats)) if placemat_package.num_dollar_coin_placemats else '',
            )

            if (not placemat_package.is_shop_order) and \
               placemat_package.num_total_placemats < 5 or \
               (placemat_package.num_total_placemats == 5 and placemat_package.country == 'CA'):
                # first class mail
                placemat_package.shipping_class = 'first_class'
            else:
                # priority mail
                placemat_package.shipping_class = 'priority'
                placemat_package.shipping_cost = 10.00
            packages.append(placemat_package)
    
    # DEBUG
    #for package in packages:
    #    print(package.__dict__)

    untracked_emails = [p.email_address for p in packages if (p.shipping_class == 'first_class' and p.num_hats == 0)]
    tracked_emails = [p.email_address for p in packages if p.shipping_class == 'priority' or p.num_hats > 0]

    # calculate numbers of items needed
    penny_placemats_needed = sum([p.num_penny_placemats for p in packages])
    nickel_placemats_needed = sum([p.num_nickel_placemats for p in packages])
    silver_stacking_placemats_needed = sum([p.num_silver_stacking_placemats for p in packages])
    dollar_coin_placemats_needed = sum([p.num_dollar_coin_placemats for p in packages])
    hats_needed = sum([p.num_hats for p in packages])

    # approximate cost of shipping
    shipping_cost = sum([p.shipping_cost for p in packages])

    # sort packages primarily by number of placemats in ascending order, then by alphebtical order
    sorted_packages = sorted(packages, key = lambda p: (p.num_total_placemats, p.order_code))

    # debug
    #for p in sorted_packages:
    #    print(p.__dict__)

    duplicate_name_packages = {}
    for i in sorted_packages:
        for j in sorted_packages:
            if i.customer_name == j.customer_name and i.mailing_address != j.mailing_address:
                if duplicate_name_packages.get(i.customer_name):
                    duplicate_name_packages[i.customer_name].extend([i.mailing_address, j.mailing_address])
                else:
                    duplicate_name_packages[i.customer_name] = [i.mailing_address, j.mailing_address]
    for name in duplicate_name_packages.keys():
        duplicate_name_packages[name] = list(set(duplicate_name_packages[name]))

    print("\nADDRESSES\n=============================")
    for p in sorted_packages:
        print(  
"""
Order Type: %s%s
%s
%s
""" %       (
                p.order_code,
                ' (tracked)' if (p.shipping_class == 'priority' or p.num_hats > 0) else '',
                p.customer_name,
                p.mailing_address
            )
        )
    print("=============================\n")

    # print out all important stats
    print(
"""
TOTAL REVENUE: ${:,.2f}

IMPORTANT STATS
=============================
Penny Placemats Needed: {}
Nickel Placemats Needed: {}
Silver Stacking Placemats Needed: {}
Dollar Coin Placemats Needed: {}
Hats Needed: {}
Total Packages: {}

Shipping Cost: ${:,.2f}
=============================
""".format(total_revenue, penny_placemats_needed, nickel_placemats_needed, 
           silver_stacking_placemats_needed, dollar_coin_placemats_needed, hats_needed,
           len(packages), shipping_cost)
    )

    if not all(isinstance(e, str) for e in untracked_emails):
        print("WARNING: not all untracked emails were parsed properly. See warnings above for more info\n")
        untracked_emails = [e for e in untracked_emails if isinstance(e, str)]
    print('untracked emails: %s\n' % ', '.join(untracked_emails))
    if not all(isinstance(e, str) for e in tracked_emails):
        print("WARNING: not all tracked emails were parsed properly. See warnings above for more info\n")
        tracked_emails = [e for e in tracked_emails if isinstance(e, str)]
    print('tracked emails: %s\n' % ', '.join(tracked_emails))

    if duplicate_name_packages:
        for name, mailing_addresses in duplicate_name_packages.items():
            if len(mailing_addresses) == 2:
                address_similarity_ratio = get_address_similarity_ratio(mailing_addresses[0], mailing_addresses[1])
                if address_similarity_ratio > 0.7:
                    print(f"WARNING: mailing addresses for customer '{name}' have a high similarity ratio ({address_similarity_ratio:.2f}) indicating that these orders may need to be combined into a single package.")
            else:
                print(f"WARNING: customer '{name}' has more than 2 mailing addresses that are different. Be sure to analyze this case carefully.")


if __name__ == "__main__":
    main()
