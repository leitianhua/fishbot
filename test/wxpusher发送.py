import logging

from wxpusher import WxPusher

# 微信WxPusher 消息平台
open_wxpusher = True
wxpusher_uid = ["UID_DebxzN3NJVgefxEhL7FLq5tzPWbg"]
wxpusher_token = "AT_jQkJqc1f9R13kVVdjwxFNcG4pWLNerOq"


def send_dingtalk_message(message, pre=''):
    # 微信wxpusher
    if open_wxpusher:
        r =  WxPusher.send_message(f'{pre}\n {message}', uids=wxpusher_uid, token=wxpusher_token)
        print(r)

if __name__ == '__main__':
    send_dingtalk_message("测试消息")
