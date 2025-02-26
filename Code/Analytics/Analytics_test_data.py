'''
This file contains messages of various lengths used to test the GRPC method
encoding efficiency
'''

SHORT_ENGLISH_MESSAGE = ("That's one small step for man, one giant leap for mankind.\n Our journey to the stars begins with a single step and a boundless hope for tomorrow.\n"+
    "I think, therefore I am.\n This simple declaration has fueled centuries of inquiry and transformed our understanding of existence.\n"+
    "Float like a butterfly, sting like a bee.\n In every fight, we find the courage to overcome our challenges and leave a lasting legacy.\n"+
    "Imagination is more important than knowledge.\n For it is the spark of creativity that drives progress and innovation in our lives.\n"+
    "Be the change you wish to see in the world.\n Each of us holds the power to transform our communities with our actions and our hearts.\n"+
    "Keep your face always toward the sunshine, and shadows will fall behind you.\n In the light of hope, even the darkest days hold the promise of a new beginning.\n"+
    "I have not failed. I've just found 10,000 ways that won't work.\n Every setback is a stepping stone toward success, each lesson guiding us closer to our goals.\n"+
    "Our lives begin to end the day we become silent about things that matter.\n It is our responsibility to speak up and fight for what is right, no matter the cost.\n")

SHORT_CHINESE_MESSAGE = ("床前明月光\n 疑是地上霜\n 举头望明月\n 低头思故乡\n" +
    "春眠不觉晓\n 处处闻啼鸟\n 夜来风雨声\n 花落知多少\n" +
    "日照香炉生紫烟\n 遥看瀑布挂前川\n 飞流直下三千尺\n 疑是银河落九天\n" +
    "离离原上草\n 一岁一枯荣\n 野火烧不尽\n 春风吹又生\n" +
    "故人西辞黄鹤楼\n 烟花三月下扬州\n 孤帆远影碧空尽\n 唯见长江天际流\n" +
    "白日依山尽\n 黄河入海流\n 欲穷千里目\n 更上一层楼\n" +
    "朝辞白帝彩云间\n 千里江陵一日还\n 两岸猿声啼不住\n 轻舟已过万重山\n" +
    "国破山河在\n 城春草木深\n 感时花溅泪\n 恨别鸟惊心\n 烽火连三月\n 家书抵万金\n 白头搔更短\n 浑欲不胜簪\n"+
    "床前明月光\n 疑是地上霜\n 举头望明月\n 低头思故乡\n" +
    "春眠不觉晓\n 处处闻啼鸟\n 夜来风雨声\n 花落知多少\n" +
    "日照香炉生紫烟\n 遥看瀑布挂前川\n 飞流直下三千尺\n 疑是银河落九天\n" +
    "离离原上草\n 一岁一枯荣\n 野火烧不尽\n 春风吹又生\n" +
    "故人西辞黄鹤楼\n 烟花三月下扬州\n 孤帆远影碧空尽\n 唯见长江天际流\n" +
    "白日依山尽\n 黄河入海流\n 欲穷千里目\n 更上一层楼\n" +
    "朝辞白帝彩云间\n 千里江陵一日还\n 两岸猿声啼不住\n 轻舟已过万重山\n" +
    "国破山河在\n 城春草木深\n 感时花溅泪\n 恨别鸟惊心\n 烽火连三月\n 家书抵万金\n 白头搔更短\n 浑欲不胜簪\n")
