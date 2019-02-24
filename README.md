# US-Stock-Option-Autotrader

### 简介
 US-Stock-Option-Autotrader 为关心自己资金安全的美股投资者提供了在本地运行的自动交易环境,
 <br>程序运行后会自动同步[第二大脑](http://02.ai)产生的交易信号,从而实现自动交易
 <br>可设置部分包括每个策略分配的资金,多空信号过滤,当日最大交易次数,全局止损等.
### 安装
本项目运行在python 3.6环境下
```
pip install -r requirements.txt
```

### 快速上手

- python脚本运行前，需先启动[FutuOpenD](https://www.futunn.com/download/openAPI)网关客户端
- 详情查看[安装指南](https://futunnopen.github.io/futu-api-doc/api/setup.html)

```
pyhton futu-client.py
```