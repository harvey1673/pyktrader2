from trade import *
from eventType import *
from eventEngine import *
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
            item.prev_item = self.tail_item
            item.next_item = None
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
        return self.trade_map[trade_id] if trade_id in self.trade_map else None

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

    def insert_trade(self, xtrade):
        if self.trade_exists(xtrade.id):
            return
        self.num_trades += 1
        if not self.price_exists(xtrade.limit_price):
            self.create_price(xtrade.limit_price) # If price not in Price Map, create a node in RBtree
        self.trade_map[trade.id] = self.price_tree[xtrade.limit_price].append_item(xtrade) # Add the trade to the TradeList in Price Map return the reference

    def remove_trade(self, xtrade):
        self.num_trades -= 1
        trade_node = self.trade_map[trade.id]
        self.price_tree[trade.limit_price].remove_item(trade_node)
        if len(self.price_tree[trade.limit_price]) == 0:
            self.remove_price(trade.limit_price)
        self.trade_map.pop(trade.id, None)        

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

class FullTradeBook(object):
    def __init__(self, ee, inst_obj):
        self.bids = TradeTree()
        self.asks = TradeTree()
        self.eventEngine = ee
        self.instrument = inst_obj
    
    def get_all_trades(self):
        return self.bids.trade_map.keys() + self.asks.trade_map.keys()
        
    def remove_trade(self, xtrade):
        if xtrade.vol > 0:
            self.bids.remove_trade(xtrade)
        else:
            self.asks.remove_trade(xtrade)

    def add_trade(self, xtrade):
        direction = 'bid' if xtrade.vol > 0 else 'ask'
        if direction == 'bid':
            while self.asks and (xtrade.limit_price >= self.asks.min_price()) and (abs(xtrade.remaining_vol)!= 0):
                best_price_asks = self.asks.min_price_list()
                self.process_trade_list('ask', best_price_asks, xtrade)
        elif direction == 'ask':
            while self.bids and (xtrade.limit_price <= self.bids.max_price()) and (abs(xtrade.filled_vol - xtrade.vol)!= 0):
                best_price_bids = self.bids.max_price_list()
                self.process_trade_list('bid', best_price_bids, xtrade)
        if xtrade.status == TradeStatus.Done:
            event = Event(type=EVENT_XTRADESTATUS)
            event.dict['trade_ref'] = xtrade.id
            self.eventEngine.put(event)
        else:
            if direction == 'bid':
                self.bids.insert_trade(xtrade)
            else:
                self.asks.insert_trade(xtrade)
            return
        return

    def process_trade_list(self, side, trade_list, xtrade):
        curr_item = trade_list.get_head_item()
        while (curr_item != None) and (abs(xtrade.remaining_vol) > 0):
            next_item = curr_item.next_item
            curr_xtrade = curr_item.data
            traded_price = self.instrument.mid_price
            diff = abs(xtrade.remaining_vol) - abs(curr_xtrade.remaining_vol)
            if abs(xtrade.remaining_vol) - abs(curr_xtrade.remaining_vol) <= 0: 
                curr_xtrade.on_trade(traded_price, -xtrade.remaining_vol)
                xtrade.on_trade(traded_price, xtrade.remaining_vol)
            else:
                curr_xtrade.on_trade(traded_price, curr_xtrade.remaining_vol)
                xtrade.on_trade(traded_price, -curr_xtrade.remaining_vol)                                   
                if curr_xtrade.status == TradeStatus.Done:
                    event = Event(type=EVENT_XTRADESTATUS)
                    event.dict['trade_ref'] = xtrade.id
                    self.eventEngine.put(event)                    
                    if side == 'bid':
                        self.bids.remove_trade(curr_xtrade)
                    else:
                        self.asks.remove_trade(curr_xtrade)                            
            curr_item = next_item

class SimpleTradeBook(object):
    def __init__(self, ee, inst_obj):
        self.bids = []
        self.asks = []        
        self.eventEngine = ee
        self.instrument = inst_obj
    
    def get_all_trades(self):
        return [xtrade.id for xtrade in self.bids + self.asks if xtrade.status in trade.Alive_Trade_Status]
        
    def remove_trade(self, xtrade):
        if xtrade.vol > 0:
            self.bids = [ x for x in self.bids if x.id != xtrade.id ]
        else:
            self.asks = [ x for x in self.asks if x.id != xtrade.id ]

    def filter_alive_trades(self):
        self.bids = [ xtrade for xtrade in self.bids if xtrade.status in Alive_Trade_Status]
        self.asks = [xtrade for xtrade in self.asks if xtrade.status in Alive_Trade_Status]

    def add_trade(self, xtrade):
        if xtrade.vol > 0:
            self.bids.append(xtrade)
        else:
            self.asks.append(xtrade)
    
    def match_trades(self):
        nbid = len(self.bids)
        nask = len(self.asks)
        n = 0
        m = 0
        traded_price = self.instrument.mid_price
        while (n < nbid) and (m < nask):
            bid_trade = self.bids[n]
            ask_trade = self.asks[m]
            if bid_trade.remaining_vol == 0:
                n += 1
            elif ask_trade.remaining_vol == 0:
                m += 1
            else:
                if abs(bid_trade.remaining_vol) <= abs(ask_trade.remaining_vol):
                    ask_trade.on_trade(traded_price, -bid_trade.remaining_vol)
                    bid_trade.on_trade(traded_price, bid_trade.remaining_vol)
                    n += 1
                else:
                    ask_trade.on_trade(traded_price, ask_trade.remaining_vol)
                    bid_trade.on_trade(traded_price, -ask_trade.remaining_vol)
                    m += 1
            
class TradeManager(object):
    def __init__(self, agent):
        self.agent = agent        
        self.tradebooks = {}
        self.pending_trades = {}
        self.ref2trade = {}

    def initialize(self):
        self.ref2trade = self.load_trade_list(self.agent.scur_day, self.agent.folder)
        for trade_id in self.ref2trade:
            xtrade = self.ref2trade[trade_id]
            orderdict = xtrade.order_dict
            for inst in orderdict:
                xtrade.order_dict[inst] = [ self.agent.ref2order[order_ref] for order_ref in orderdict[inst] ]
            xtrade.refresh()
            self.add_trade(xtrade)

    def day_finalize(self, scur_day, file_prefix):
        pfilled_dict = {}
        for trade_id in self.ref2trade:
            xtrade = self.ref2trade[trade_id]
            xtrade.refresh()
            if xtrade.status in [TradeStatus.Pending, TradeStatus.Ready]:
                xtrade.status = TradeStatus.Done
                xtrade.order_dict = {}
                xtrade.filled_vol = 0
                xtrade.remaining_vol = xtrade.vol - xtrade.filled_vol
                strat = self.agent.strategies[xtrade.strategy]
                strat.on_trade(xtrade)
            elif xtrade.remaining_vol > 0:
                xtrade.status = TradeStatus.PFilled
                self.agent.logger.warning('Still partially filled after close. trade id= %s' % trade_id)
                pfilled_dict[trade_id] = xtrade
        if len(pfilled_dict)>0:
            file_prefix = self.agent.folder + 'PFILLED_'
            self.save_trade_list(self.agent.scur_day, pfilled_dict, file_prefix)
        self.save_trade_list(scur_day, self.ref2trade, file_prefix)
        self.tradebooks = {}
        self.pending_trades = {}
        self.ref2trade = {}

    def get_trade(self, trade_id):
        return self.ref2trade[trade_id] if trade_id in self.ref2trade else None

    def get_trades_by_strat(self, strat_name):
        return [xtrade for xtrade in self.ref2trade.values() if xtrade.strategy == strat_name]

    def add_trade(self, xtrade):
        if xtrade.id not in self.ref2trade:
            self.ref2trade[xtrade.id] = xtrade
        key = xtrade.underlying.name
        if xtrade.status == TradeStatus.Pending:
            if key not in self.pending_trades:
                self.pending_trades[key] = []
            self.pending_trades[key].append(xtrade)
        elif xtrade.status in Alive_Trade_Status:
            key = xtrade.underlying.name
            if key in self.agent.instruments:
                inst_obj = self.agent.instruments[key]
            else:
                inst_obj = self.agent.spread_data[key]
            if key not in self.tradebooks:
                self.tradebooks[key] = SimpleTradeBook(self.agent.eventEngine, inst_obj)
            self.tradebooks[key].add_trade(xtrade)

    def remove_trade(self, xtrade):
        key = xtrade.name
        if xtrade.status == TradeStatus.Pending:
            self.pending_trades[key].remove(xtrade, None)
        elif xtrade.status in Alive_Trade_Status:
            self.tradebooks[key].remove_trade(xtrade)

    def check_pending_trades(self, key):
        alive_trades = []
        if key not in self.pending_trades:
            return
        for xtrade in self.pending_trades[key]:
            curr_price = xtrade.underlying.ask_price1 if xtrade.vol > 0 else xtrade.underlying.ask_price1 
            if (curr_price - xtrade.limit_price) * xtrade.vol >= 0:
                xtrade.status = TradeStatus.Ready
                alive_trades.append(xtrade)
        self.pending_trades[key] = [xtrade for xtrade in self.pending_trades[key] if xtrade.status == TradeStatus.Pending]
        [self.add_trade(xtrade) for xtrade in alive_trades]
        if key in self.tradebooks:
            self.tradebooks[key].match_trades()

    def process_trades(self, key):
        if key not in self.tradebooks:
            return
        for trade_id in self.tradebooks[key].get_all_trades():
            xtrade = self.ref2trade[trade_id]
            xtrade.execute()
        self.tradebooks[key].filter_alive_trades()

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
                    order_dict = ' '.join([inst +':'+'_'.join([str(o.order_ref) for o in xtrade.order_dict[inst] if o.volume > 0])
                                        for inst in xtrade.order_dict])
                else:
                    order_dict = ''
                file_writer.writerow([xtrade.id, insts, units, xtrade.price_unit, xtrade.vol, xtrade.limit_price,
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
                    price_unit = None if len(row[3]) == 0 else float(row[3])
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
                            if len(str_dict[inst])>0:
                                order_dict[inst] = [int(o_id) for o_id in str_dict[inst].split('_')]
                    strategy = row[12]
                    book = row[13]
                    xtrade = XTrade(instIDs, units, vol, limit_price, price_unit = price_unit, strategy = strategy, book = book, \
                                    agent = self.agent, start_time = start_time, end_time = end_time, aggressiveness = aggressiveness)
                    xtrade.id = int(row[0])
                    xtrade.status = int(row[14])
                    xtrade.order_dict = order_dict
                    xtrade.filled_vol = filled_vol
                    xtrade.filled_price = filled_price
                    trade_dict[xtrade.id] = xtrade
        return trade_dict
