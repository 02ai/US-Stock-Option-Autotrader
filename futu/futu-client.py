#coding:utf-8
from futu import *
import futu as ft
import time
import os
import math
import datetime
import poplib
import copy
import json
import requests
import leancloud
import traceback


zuida_zijin_stock=1000 #股票最大资金占用量
zuida_zijin_option=20 #期权最大资金占用量
zuida_cangweishu=2
baoben_chufa=40  #任何仓位盈利40%以上保本
cangwei={}
zuida_yingli={} #保本价格被触发过
zuixiao_yingli={} #跌幅过大后有盈利就出来
#配置 开启监控已有仓位的目标价止盈
jiankong_on=False #自动平仓监控 true表示开启 
xinhao_count=0

ip_address='127.0.0.1'
quote_ctx = OpenQuoteContext(host=ip_address, port=11111)
trd_ctx = OpenUSTradeContext(host=ip_address, port=11111)
trd_ctx.unlock_trade('781623')

#print(quote_ctx.get_global_state())
#print(trd_ctx.get_acc_list())
#print(quote_ctx.get_market_snapshot('US.AAPL'))
t=trd_ctx.position_list_query( )
leancloud.init("vvCEpSpu1WH9k5Q97yoh6cTa-gzGzoHsz", "CtfYTxlbNfc6txXR2Jhm4lTO")

user = leancloud.User()
user.login('stock', 'guoguoguo')

'''
开盘判断
'''
def iskaipan():
  i = datetime.datetime.now()
  if i.hour<4 or i.hour>21 or  (i.hour==21 and  i.minute>30):
    return True
  else:
    return False  


'''
平仓
'''
def close_option(rootcode):
  allpostion=trd_ctx.position_list_query( )
  for index,row in allpostion[1].iterrows():
    #平仓
    #if row['stock_name'].split(" ")[0]==rootcode.upper():    
    if row['code'].startswith(rootcode.upper()): 
      print(trd_ctx.place_order(price=0, order_type=OrderType.MARKET, qty=row['qty'], code=row['code'], trd_side=TrdSide.SELL))   


'''
前置可用资金检查 不能超过总资产比例 todo
'''
def check_bili():

  return False


def check_zhiying():

  return None

import datetime



'''
限制一天的交易次数
'''

'''
取消订单 by code
'''
def quxiao(code):
  dingdan=trd_ctx.order_list_query()
  for index,row in  dingdan[1].iterrows():
    if(row['order_status']==OrderStatus.SUBMITTED and  row['code']==code):
      print(row)
      print(trd_ctx.modify_order(ModifyOrderOp.CANCEL, row['order_id'], 0, 0))


'''
获得报价 bid<ask 
'''
def get_ask_bid(code):
  quote_ctx.subscribe([code], [SubType.ORDER_BOOK])
  r_code,baojia=quote_ctx.get_order_book(code)
  if r_code!=ft.RET_OK:
    raise Exception('order_book失败'.format(baojia))
  quote_ctx.unsubscribe([code], [SubType.ORDER_BOOK]);  
  return baojia['Bid'][0][0] , baojia['Ask'][0][0]
    


'''
已有盈利仓位保本
'''
def check_baoben(row):  
  bid,ask =get_ask_bid(row['code'])
  if bid==0:
    return

  #盈利超过阈值后触发保本订单
  #保本订单
  #if row['pl_ratio']>baoben_chufa:
  if row['code'] in zuida_yingli:
    if zuida_yingli[row['code']]<bid:
      print('最大盈利'+row['code']+':'+str(bid))
      zuida_yingli[row['code']]=bid
    pass
  else:
    zuida_yingli[row['code']]=bid
    pass 

  
  if  row['cost_price']*1.05>bid and   row['code'] in zuida_yingli:
    if zuida_yingli[row['code']]>(1+baoben_chufa/100)*row['cost_price']:
      print('赢利后触发保本订单')
      #先取消
      quxiao(row['code'])
      time.sleep(5)
      #市价卖出
      close_option(row['code'])



  if row['code'] in zuixiao_yingli:
    if zuixiao_yingli[row['code']]>bid:
      print('最小盈利'+row['code']+':'+str(bid))
      zuixiao_yingli[row['code']]=bid
    pass
  else:
    zuixiao_yingli[row['code']]=bid
    pass 
    
  #bid>0.08 避免一下单就平仓  
  if row['cost_price']*1.05<bid  and   row['code'] in zuixiao_yingli and  bid>0.08:
    if zuixiao_yingli[row['code']]<(1-baoben_chufa/100)*row['cost_price']:
      print('触发亏损后的保本订单')
      #先取消
      quxiao(row['code'])
      time.sleep(5)
      #市价卖出
      close_option(row['code'])


def is_number(str):
    try:
        # 因为使用float有一个例外是'NaN'
        if str=='NaN':
            return False
        float(str)
        return True
    except ValueError:
        return False

#同步云端交易
def cloudsync():
  query = leancloud.Query('xinhao')
  query_count=query.count()
  #print("信号位置:",query_count)
  global xinhao_count
  if(xinhao_count==0):
    xinhao_count=query_count
    print(xinhao_count,"保存读取坐标")
  if (query_count!=xinhao_count):
    
    query.add_descending('createdAt')
    if query_count-xinhao_count>0:
      query.limit(10)
      query.skip(query_count-xinhao_count-1) #每次读取一条
      print("query_count:",query_count,"xinhao_count",xinhao_count)
    query_first=query.first()
    print(query_first.get('xinhao'));
    xinhao_count= xinhao_count+1
    #tcode='US.AAPL'
    jsonstring=query_first.get('xinhao')    
    xinhao_json=json.loads(jsonstring)    
    

    #已有仓位检查 防止同一品种多次开仓  
    allpostion=trd_ctx.position_list_query( )
    if allpostion[0]!=0:
      print('已有同类仓位')
      return None
  
  #前置市场状态检查  
    ret, state_dict = quote_ctx.get_global_state()
    if ret != 0:
      return
    mkt_val = state_dict['market_us']
    #print(mkt_val)
    if(mkt_val!=MarketState.AFTERNOON):
      print('未开盘')
      #return
    
    leibie=xinhao_json['leibie']
    stockcode=xinhao_json['stockcode']      
    stockprice=xinhao_json['price']      
    bili=xinhao_json['bili']
  #前置平仓信号
    if(bili==0):      
      print('平仓条件满足')
      if(leibie=='option'):
        close_option(stockcode)
      else:
        print('平仓股票')
        close_option('US.'+stockcode) 

      return None         

  #最大持有仓位数前置检查
    if(xinhao_json['bili']>0 and len(allpostion[1][allpostion[1].qty>0])>=zuida_cangweishu):
      print('已有仓位超过最大可持有仓位数：',zuida_cangweishu)
      return None  
   #仓位计算
    qty=0
    code=''
    if(leibie=='stock' and is_number(stockprice)):
      stockprice=float(stockprice)
      code='US.'+xinhao_json['stockcode']
      if(stockprice   >0):
        qty=math.floor(zuida_zijin_stock*bili/stockprice)
        print('美股下单量:{}'.format(qty))
      else:
        print('股票必须有价格')  
        return None

    if(leibie=='option'):
      qty=1
      stockprice=0
      code=xinhao_json['code']

    ret, data=trd_ctx.place_order(price=stockprice, order_type=xinhao_json['order_type'], qty=qty, code=code, trd_side=xinhao_json['trd_side'])
    print(stockprice, xinhao_json['order_type'], qty, xinhao_json['code'], xinhao_json['trd_side'])
    if ret != ft.RET_OK:
        print('下单失败:{}'.format(data))       
        return None
    else:
        print('下单成功:{}'.format(data))
    

'''
全局监控
已有仓位配对检查 任何仓位都要有止盈止损
'''
def jiankong():
  positions=trd_ctx.position_list_query( )
  dingdan=trd_ctx.order_list_query()
  if iskaipan()==False:
    return None  #没开盘


  if positions[0]!=0: #没有期权
    print(positions)
    return None  
  
  for index,row in positions[1].iterrows():
    #print(row)
    if row['qty']==0:
    #过滤已经平仓的仓位
      continue
    #print(zuida_yingli)
    #print(zuixiao_yingli)
    if row['can_sell_qty']==0:
    #有仓位但是有挂单 
      check_baoben(row)
      continue
    #手动开仓<=>程序开仓止盈
    if row['can_sell_qty']==0:
      return


    pingcangjia=0
    if row['code'] in cangwei:
      celue=cangwei[row['code']]
      print('程序下单')

      
      if(is_number(celue)):
        print('接收参数')
        pingcangjia=row['cost_price']*float(celue)
      else:
        return None
      
    print('下单价格')
    pingcangjia=pingcangjia if pingcangjia>0.1 else 0.1
    print(round(pingcangjia,2))
    
    ret1, data1=trd_ctx.place_order(round(pingcangjia,2), order_type=OrderType.NORMAL, qty=row['can_sell_qty'], code=row['code'] ,trd_side=TrdSide.SELL)
    print(data1)

'''
循环读取同步订单 
实时监控资金等
'''
def xunhuan():
  i = datetime.datetime.now()

  if(i.second%5==0):
    cloudsync()

  if(i.second%10==0 and jiankong_on):    
    jiankong()  #监控手动开仓 程序开仓的止盈 这个可能导致接口请求数量过多 放到15s
 

  
#主循环框架
if __name__=='__main__':
    while True:
        try:
          
          xunhuan()
          time.sleep(1)
        except poplib.error_proto:          

          pass
        except Exception as e:
            print(e)
            traceback.print_exc()
        
        #time.sleep(5)
 