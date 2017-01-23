from bintrees import FastRBTree

class LinkedList(object):
    class Node(object):
        def __init__(self, data, prev, next):
            self.data = data
            self.prev = prev
            self.next = next

    def __init__(self):
        self.head_item = None  # first trade in the list
        self.tail_item = None  # last trade in the list
        self.length = 0  # number of Orders in the list
        self.last = None  # helper for iterating 

    def __len__(self):
        return self.length

    def __iter__(self):
        self.last = self.head_item
        return self

    def next(self):
        '''Get the next trade in the list. 

        Set self.last as the next trade. If there is no next trade, stop
        iterating through list.
        '''
        if self.last == None:
            raise StopIteration
        else:
            return_value = self.last
            self.last = self.last.next_item
            return return_value

    __next__ = next  # python3

    def get_head_item(self):
        return self.head_item

    def append_item(self, data):
        item = LinkedList.Node(data, None, None)
        if len(self) == 0:
            item.next_item = None
            item.prev_item = None
            self.head_item = item
            self.tail_item = item
        else:
            item.prev_trade = self.tail_item
            item.next_trade = None
            self.tail_item.next_item = item
            self.tail_item = item
        self.length += 1
        return item

    def remove_item(self, item):
        self.length -= 1
        if len(self) == 0:  # if there are no more Orders, stop/return
            return

        # Remove an Order from the TradeList. First grab next / prev trade
        # from the Order we are removing. Then relink everything. Finally
        # remove the Order.
        next_item = item.next_trade
        prev_item = item.prev_trade
        if next_item != None and prev_item != None:
            next_item.prev_trade = prev_item
            prev_item.next_trade = next_item
        elif next_item != None:  # There is no previous trade
            next_item.prev_item = None
            self.head_item = next_item  # The next trade becomes the first trade in the TradeList after this Order is removed
        elif prev_item != None:  # There is no next trade
            prev_item.next_item = None
            self.tail_item = prev_item  # The previous trade becomes the last trade in the TradeList after this Order is removed

    def move_to_tail(self, item):
        '''After updating the quantity of an existing Order, move it to the tail of the TradeList
        Check to see that the quantity is larger than existing, update the quantities, then move to tail.
        '''
        if item.prev_item != None:  # This Order is not the first Order in the TradeList
            item.prev_item.next_item = item.next_item  # Link the previous Order to the next Order, then move the Order to tail
        else:  # This Order is the first Order in the TradeList
            self.head_item = item.next_item  # Make next trade the first
        item.next_item.prev_item = item.prev_item
        # Move Order to the last position. Link up the previous last position Order.
        self.tail_item.next_item = item
        self.tail_item = item

class TradeTree(object):
    '''A red-black tree used to store TradeLists in price trade
    The exchange will be using the TradeTree to hold bid and ask data (one TradeTree for each side).
    Keeping the information in a red black tree makes it easier/faster to detect a match.
    '''

    def __init__(self):
        self.price_tree = FastRBTree()
        self.trade_map = {}
        self.num_trades = 0 # Contains count of Orders in tree
        self.depth = 0 # Number of different prices in tree (http://en.wikipedia.org/wiki/trade_book_(trading)#Book_depth)

    def __len__(self):
        return len(self.trade_map)

    def get_price_list(self, price):
        return self.price_tree.get(price, [])

    def get_trade(self, trade_id):
        return self.trade_map[trade_id]

    def create_price(self, price):
        self.depth += 1 # Add a price depth level to the tree
        new_list = LinkedList()
        self.price_tree.insert(price, new_list) # Insert a new price into the tree

    def remove_price(self, price):
        self.depth -= 1 # Remove a price depth level
        self.price_tree.remove(price)

    def price_exists(self, price):
        return self.price_tree.__contains__(price)

    def trade_exists(self, trade_id):
        return trade_id in self.trade_map

    def insert_trade(self, trade):
        if self.trade_exists(trade.id):
            return
        self.num_trades += 1
        if not self.price_exists(trade.limit_price):
            self.create_price(trade.limit_price) # If price not in Price Map, create a node in RBtree
        self.trade_map[trade.id] = self.price_tree[trade.limit_price].append_item(trade) # Add the trade to the TradeList in Price Map return the reference

    def remove_trade(self, trade):
        self.num_trades -= 1
        trade_node = self.trade_map[trade.id]
        self.price_tree[trade.limit_price].remove_item(trade_node)
        if len(trade.trade_list) == 0:
            self.remove_price(trade.limit_price)
        del self.trade_map[trade.id]

    def max_price(self):
        if self.depth > 0:
            return self.price_tree.max_key()
        else:
            return None

    def min_price(self):
        if self.depth > 0:
            return self.price_tree.min_key()
        else:
            return None

    def max_price_list(self):
        if self.depth > 0:
            return self.get_price_list(self.max_price())
        else:
            return None

    def min_price_list(self):
        if self.depth > 0:
            return self.get_price_list(self.min_price())
        else:
            return None