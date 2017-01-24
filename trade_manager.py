from trade import *
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

class TradeBook(object):
    def __init__(self, tick_size = 0.1):
        self.bids = TradeTree()
        self.asks = TradeTree()

    def add_trade(self, xtrade):        
        pass

    def process_trade(self, xtrade):
        direction = 'bid' if xtrade.vol > 0 else 'ask'
        if direction == 'bid':
            while abs(xtrade.filled_vol - xtrade.vol)!= 0 and self.asks:
                best_price_asks = self.asks.min_price_list()
                self.process_trade_list('ask', best_price_asks, xtrade)
        elif direction == 'ask':
            while abs(xtrade.filled_vol - xtrade.vol)!= 0 and self.bids:
                best_price_bids = self.bids.max_price_list()
                self.process_trade_list('bid', best_price_bids, xtrade)
        return

    def process_trade_list(self, side, trade_list, xtrade):
        quantity_to_trade = xtrade.remaining_vol
        while len(trade_list) > 0 and abs(quantity_to_trade) > 0:
            head_item = trade_list.get_head_item()
            head_trade = head_item.data
            traded_price = head_trade.limit_price
            if quantity_to_trade < head_order.quantity:
                traded_quantity = quantity_to_trade
                # Do the transaction
                new_book_quantity = head_order.quantity - quantity_to_trade
                head_order.update_quantity(new_book_quantity, head_order.timestamp)
                quantity_to_trade = 0
            elif quantity_to_trade == head_order.quantity:
                traded_quantity = quantity_to_trade
                if side == 'bid':
                    self.bids.remove_order_by_id(head_order.order_id)
                else:
                    self.asks.remove_order_by_id(head_order.order_id)
                quantity_to_trade = 0
            else: # quantity to trade is larger than the head order
                traded_quantity = head_order.quantity
                if side == 'bid':
                    self.bids.remove_order_by_id(head_order.order_id)
                else:
                    self.asks.remove_order_by_id(head_order.order_id)
                quantity_to_trade -= traded_quantity
            if verbose:
                print(("TRADE: Time - {}, Price - {}, Quantity - {}, TradeID - {}, Matching TradeID - {}".format(self.time, traded_price, traded_quantity, counter_party, quote['trade_id'])))

            transaction_record = {
                    'timestamp': self.time,
                    'price': traded_price,
                    'quantity': traded_quantity,
                    'time': self.time
                    }

            if side == 'bid':
                transaction_record['party1'] = [counter_party, 'bid', head_order.order_id, new_book_quantity]
                transaction_record['party2'] = [quote['trade_id'], 'ask', None, None]
            else:
                transaction_record['party1'] = [counter_party, 'ask', head_order.order_id, new_book_quantity]
                transaction_record['party2'] = [quote['trade_id'], 'bid', None, None]

            self.tape.append(transaction_record)
            trades.append(transaction_record)
        return quantity_to_trade, trades

class TradeManager(object):
    def __init__(self, agent):
        self.agent = agent
        self.tradebooks = {}
        self.ref2trade = {}

    def initialize(self):
        self.ref2trade = self.load_trade_list(self.agent.scur_day, self.agent.folder)
        for trade_id in self.ref2trade:
            xtrade = self.ref2trade[trade_id]
            orderdict = xtrade.order_dict
            for inst in orderdict:
                xtrade.order_dict[inst] = [ self.agent.ref2order[order_ref] for order_ref in orderdict[inst] ]
            xtrade.update()

    def get_trade(self, trade_id):
        return self.ref2trade[trade_id]

    def get_trades_by_strat(self, strat_name):
        return [xtrade for xtrade in self.ref2trade.values() if xtrade.strategy == strat_name]

    def save_pfill_trades(self):
        pfilled_dict = {}
        for trade_id in self.ref2trade:
            xtrade = self.ref2trade[trade_id]
            xtrade.update()
            if xtrade.status == TradeStatus.Pending or xtrade.status == TradeStatus.OrderSent:
                xtrade.status = TradeStatus.Cancelled
                strat = self.agent.strategies[xtrade.strategy]
                strat.on_trade(xtrade)
            elif xtrade.status == TradeStatus.PFilled:
                xtrade.status = TradeStatus.Cancelled
                self.agent.logger.warning('Still partially filled after close. trade id= %s' % trade_id)
                pfilled_dict[trade_id] = xtrade
        if len(pfilled_dict)>0:
            file_prefix = self.agent.folder + 'PFILLED_'
            self.save_trade_list(self.agent.scur_day, pfilled_dict, file_prefix)

    def add_trade(self, xtrade):
        if xtrade.id not in self.ref2trade:
            self.ref2trade[xtrade.id] = xtrade
        if xtrade.status in Alive_Trade_Status:
            key = xtrade.underlying.name
            self.working_trades[key].append(xtrade)

    def remove_trade(self, xtrade):
        key = xtrade.name
        self.working_trades[key].remove(xtrade, None)

    def process_trades(self, instID):
        pass

    def match_trade(self):
        pass

    def save_trade_list(self, curr_date, trade_list, file_prefix):
        filename = file_prefix + 'trade_' + curr_date.strftime('%y%m%d')+'.csv'
        with open(filename,'wb') as log_file:
            file_writer = csv.writer(log_file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL);
            file_writer.writerow(['id', 'insts', 'units', 'price_unit', 'vol', 'limitprice',
                                  'filledvol', 'filledprice', 'order_dict', 'aggressive',
                                  'start_time', 'end_time', 'strategy','book', 'status'])
            for xtrade in trade_list.values():
                insts = ' '.join(xtrade.instIDs)
                units = ' '.join([str(i) for i in xtrade.units])
                if len(xtrade.order_dict)>0:
                    order_dict = ' '.join([inst +':'+'_'.join([str(o.order_ref) for o in trade.order_dict[inst]])
                                        for inst in trade.order_dict])
                else:
                    order_dict = ''
                file_writer.writerow([trade.id, insts, units, xtrade.price_unit, xtrade.vol, xtrade.limit_price,
                                      xtrade.filled_vol, xtrade.filled_price, order_dict, xtrade.aggressive_level,
                                      xtrade.start_time, xtrade.end_time, xtrade.strategy, xtrade.book, xtrade.status])

    def load_trade_list(self, curr_date, file_prefix):
        logfile = file_prefix + 'trade_' + curr_date.strftime('%y%m%d')+'.csv'
        if not os.path.isfile(logfile):
            return {}
        trade_dict = {}
        with open(logfile, 'rb') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if idx > 0:
                    instIDs = row[1].split(' ')
                    units = [ int(n) for n in row[2].split(' ')]
                    price_unit = float(row[3])
                    vol = int(row[4])
                    limit_price = float(row[5])
                    filled_vol = int(row[6])
                    filled_price = float(row[7])
                    aggressiveness = float(row[9])
                    start_time = int(row[10])
                    end_time = int(row[11])
                    order_dict = {}
                    if ':' in row[8]:
                        str_dict =  dict([tuple(s.split(':')) for s in row[8].split(' ')])
                        for inst in str_dict:
                            if len(order_dict[inst])>0:
                                order_dict[inst] = [int(o_id) for o_id in str_dict[inst].split('_')]
                    strategy = row[10]
                    book = row[11]
                    xtrade = XTrade(instIDs, units, vol, limit_price, price_unit = price_unit, strategy = strategy, book = book, \
                                    agent = self.agent, start_time = start_time, end_time = end_time, aggressiveness = aggressiveness)
                    xtrade.id = int(row[0])
                    xtrade.status = int(row[12])
                    xtrade.order_dict = order_dict
                    xtrade.filled_vol = filled_vol
                    xtrade.filled_price = filled_price
                    xtrade.refresh_status()
                    trade_dict[xtrade.id] = xtrade
        return trade_dict
